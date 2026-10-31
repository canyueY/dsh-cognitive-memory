import json
import pytest
from fastapi.testclient import TestClient
from cognitive_memory.migration.manager import read_provider,verify_batch
from cognitive_memory.migration.staging import preview_batch,approve_batch,commit_batch,rollback_batch
from cognitive_memory.bootstrap import build_context
from tests.unit.test_audit_regressions import agent


@pytest.mark.parametrize("provider,payload",[
    ("mem0",[{"id":"1","memory":"mem0 fixture"}]),
    ("zep",[{"uuid":"1","fact":"zep fixture","edges":[{"target":"2"}]}]),
    ("letta",{"blocks":[{"label":"human","value":"letta fixture"}]}),
    ("langchain",{"documents":[{"id":"1","page_content":"langchain fixture","metadata":{"topic":"x"}}]}),
])
def test_exports_keep_originals_and_roundtrip(tmp_path,provider,payload):
    source=tmp_path/f"{provider}.json";source.write_text(json.dumps(payload),encoding="utf-8")
    original=source.read_bytes()
    records=read_provider(source,provider)
    assert records and records[0].raw_payload
    ctx=build_context(data_dir=str(tmp_path/"bank"),token="t")
    try:
        batch=preview_batch(records);approve_batch(batch,actor="test")
        commit_batch(batch,service=ctx.service)
        assert verify_batch(batch,ctx.service)["ok"]
        # A second batch may reuse the original memory, but cannot erase it on rollback.
        repeat=preview_batch(records);approve_batch(repeat,actor="test")
        commit_batch(repeat,service=ctx.service)
        assert not repeat.commit_report["written"][0]["created"]
        rollback_batch(repeat,service=ctx.service)
        mid=batch.commit_report["written"][0]["memory_id"]
        assert ctx.db.connect().execute("SELECT status FROM memories WHERE id=?",(mid,)).fetchone()[0]!="invalidated"
    finally:
        ctx.db.close()
    assert source.read_bytes()==original


def test_compat_api_subset_and_bank_permissions(tmp_path):
    ctx=build_context(data_dir=str(tmp_path/"bank"),token="audit-node")
    try:
        client=TestClient(ctx.app);headers=agent(client)
        result=client.post("/api/v1/compat/mem0/add",headers=headers,
            json={"content":"compatibility fixture","idempotency_key":"one"})
        assert result.status_code==200,result.text
        mid=result.json()["id"]
        again=client.post("/api/v1/compat/mem0/add",headers=headers,
            json={"content":"compatibility fixture","idempotency_key":"one"})
        assert again.json()["id"]==mid
        assert client.get(f"/api/v1/compat/mem0/{mid}",headers=headers).json()["memory"]=="compatibility fixture"
        found=client.post("/api/v1/compat/mem0/search",headers=headers,json={"query":"compatibility"})
        assert found.json()["results"]
        assert client.post("/api/v1/compat/mem0/search",headers=headers,json={"bank_id":"projects"}).status_code==404
        assert client.delete(f"/api/v1/compat/mem0/{mid}?hard=true",headers=headers).status_code==501
        deleted=client.delete(f"/api/v1/compat/mem0/{mid}",headers=headers)
        assert deleted.json()["physical_erasure"] is False
    finally:
        ctx.db.close()


def test_import_does_not_drop_store_denial_or_source_bank(tmp_path):
    ctx=build_context(data_dir=str(tmp_path/"bank"),token="t")
    try:
        denied=preview_batch([{"source_system":"fixture","source_record_id":"private",
                               "content":"must not persist","metadata":{"policy":{"allow_store":False}}}])
        approve_batch(denied,actor="reviewer");commit_batch(denied,service=ctx.service)
        assert denied.state=="failed"
        assert ctx.db.connect().execute("SELECT COUNT(*) FROM memories").fetchone()[0]==0
        assert ctx.db.connect().execute("SELECT COUNT(*) FROM observations").fetchone()[0]==0
        shared=preview_batch([{"source_system":"fixture","source_record_id":"shared",
                               "content":"shared import","extensions":{"bank_id":"shared"}}])
        approve_batch(shared,actor="reviewer");commit_batch(shared,service=ctx.service)
        mid=shared.commit_report["written"][0]["memory_id"]
        assert ctx.db.connect().execute("SELECT bank_id FROM memories WHERE id=?",(mid,)).fetchone()[0]=="shared"
    finally:
        ctx.db.close()
