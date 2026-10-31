"""Acceptance cases from the three-note audit, using real scratch SQLite state."""
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from cognitive_memory.bootstrap import build_context
from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.claims.ast import Atom, ClaimAST
from cognitive_memory.claims.normalize import normalized_hash
from cognitive_memory.security.context import SecurityContext
from cognitive_memory.evidence.object_store import EvidenceObjectStore
from cognitive_memory.migration.staging import preview_batch, approve_batch, commit_batch
from cognitive_memory.cognition.schema_ops import assimilate_schema
from cognitive_memory.tracing.service import JudgmentTraceService
from tests.support import seed_evidence


@pytest.fixture
def ctx():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
        context = build_context(data_dir=root, token="audit-node")
        yield context
        context.db.close()


def agent(client, banks=("personal",)):
    h={"Authorization":"Bearer audit-node"}
    client.post("/api/v1/agents/register",headers=h,json={"agent_id":"audit","display_name":"Audit"})
    r=client.post("/api/v1/agents/audit/grants",headers=h,
                  json={"permissions":["memory.read","memory.write"],"banks":list(banks)})
    assert r.status_code == 200, r.text
    return {"X-Agent-Id":"audit","X-Agent-Token":r.json()["agent_token"]}


@pytest.mark.parametrize("operation,payload",[
    ("transition",{"target_status":"supported","reason":"probe"}),
    ("retract",{"reason":"probe"}),("expire",{"reason":"probe"}),
    ("verify",{"evidence_refs":["missing"]}),
    ("evidence",{"evidence_ref":"missing"}),
    ("merge",{"target_id":"missing"}),("redirect",{"target_id":"missing"}),
    ("split",{"parts":["我喜欢甲","我喜欢乙"]}),
    ("relations",{"other_id":"missing"}),
])
def test_cross_bank_write_and_inference_denied(ctx,operation,payload):
    store=ClaimStore(ctx.db)
    cid=store.propose_from_text("我喜欢私密项目",bank_id="projects")["claim_id"]
    client=TestClient(ctx.app);h=agent(client)
    assert client.get(f"/api/v1/claims/{cid}",headers=h).status_code == 404
    r=client.post(f"/api/v1/claims/{cid}/{operation}",headers=h,json=payload)
    assert r.status_code == 404, r.text
    assert store.get(cid)["lifecycle"] == "proposed"


def test_secondary_object_scope_and_actor(ctx):
    store=ClaimStore(ctx.db);client=TestClient(ctx.app);h=agent(client)
    own=store.propose_from_text("我喜欢公开项目")["claim_id"]
    other=store.propose_from_text("我喜欢私密项目",bank_id="projects")["claim_id"]
    r=client.post(f"/api/v1/claims/{own}/supersede",headers=h,
                  json={"replacement_claim_id":other,"reason":"probe"})
    assert r.status_code == 404
    assert store.get(own)["lifecycle"] == "proposed"


def test_missing_evidence_never_verified_or_partially_committed(ctx):
    store=ClaimStore(ctx.db);cid=store.propose_from_text("我喜欢审计")["claim_id"]
    before=store.get(cid)
    result=store.submit_verified(cid,evidence_refs=["evd_missing"],actor="audit")
    assert not result["ok"]
    assert store.get(cid) == before
    assert ctx.db.connect().execute("SELECT COUNT(*) FROM verification_records").fetchone()[0] == 0


def test_valid_evidence_verified_and_revocation_rechecks(ctx):
    store=ClaimStore(ctx.db);cid=store.propose_from_text("我喜欢审计")["claim_id"]
    eid=seed_evidence(ctx.db,"evd_valid")
    store.attach_evidence(cid,eid)
    result=store.submit_verified(cid,evidence_refs=[eid],actor="reviewer")
    assert result["ok"], result
    again=store.submit_verified(cid,evidence_refs=[eid],actor="reviewer")
    assert again["idempotent"]
    assert ctx.db.connect().execute("SELECT COUNT(*) FROM verification_records").fetchone()[0] == 1
    EvidenceObjectStore(ctx.db).assess(eid,state="revoked",actor="reviewer")
    assert store.get(cid)["verification_status"] != "verified"
    assert not store.submit_verified(cid,evidence_refs=[eid],actor="reviewer")["ok"]


def test_counterevidence_cannot_be_overridden_by_boolean(ctx):
    store=ClaimStore(ctx.db);cid=store.propose_from_text("我喜欢审计")["claim_id"]
    seed_evidence(ctx.db,"evd_support");seed_evidence(ctx.db,"evd_counter")
    store.attach_evidence(cid,"evd_counter",role="counter")
    out=store.submit_verified(cid,evidence_refs=["evd_support"],actor="reviewer",evidence_still_valid=True)
    assert not out["ok"] and out["detail"] == "disputed"


def test_hidden_evidence_removes_all_verified_markers(ctx):
    store=ClaimStore(ctx.db);cid=store.propose_from_text("我喜欢审计")["claim_id"]
    seed_evidence(ctx.db,"evd_valid")
    assert store.submit_verified(cid,evidence_refs=["evd_valid"],actor="reviewer")["ok"]
    result=store.get(cid,principal=SecurityContext(),evidence_visible=False)
    assert "verification_status" not in result
    assert result.get("lifecycle") != "verified"


def test_trace_durable_and_trace_failure_rolls_back(ctx):
    store=ClaimStore(ctx.db);cid=store.propose_from_text("我喜欢审计")["claim_id"]
    traces=JudgmentTraceService(ctx.db).list_traces()
    assert traces and all(t.trace_id for t in traces)
    seed_evidence(ctx.db,"evd_valid")
    with pytest.raises(RuntimeError):
        with ctx.db.transaction():
            assert store.submit_verified(cid,evidence_refs=["evd_valid"],actor="reviewer")["ok"]
            JudgmentTraceService(ctx.db).record("critical",governance_critical=True,fail_write=True)
    assert store.get(cid)["lifecycle"] == "proposed"
    assert ctx.db.connect().execute("SELECT COUNT(*) FROM verification_records").fetchone()[0] == 0


def test_identity_preserves_argument_order_decimal_and_null():
    def h(args):
        return normalized_hash(ClaimAST(root=Atom(subject="x",predicate="connects",arguments=args)))
    assert h(["A","B"]) != h(["B","A"])
    assert h(["1.2"]) != h(["12"])
    assert h([""]) != h([])
    assert h(["a b"]) != h(["ab"])


def test_preview_has_no_database_writes(ctx):
    sid=ctx.service.store_cognitive_schema({"name":"fixture","state":"PROPOSED"})
    before=ctx.db.connect().total_changes
    result=assimilate_schema(ctx.service,sid,preview=True,note="preview")
    assert result["dry_run"]
    assert ctx.db.connect().total_changes == before


def test_approved_payload_change_rejected(ctx):
    batch=preview_batch([{"source_system":"fixture","source_record_id":"1","content":"original"}])
    approve_batch(batch,actor="reviewer",expected_checksum=batch.checksum)
    batch.records[0]["content"]={"text":"changed"}
    with pytest.raises(PermissionError,match="approved_payload_changed"):
        commit_batch(batch,service=ctx.service)
    assert ctx.db.connect().execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0


def test_wrong_version_and_concurrent_duplicate(ctx):
    store=ClaimStore(ctx.db);cid=store.propose_from_text("我喜欢审计")["claim_id"]
    seed_evidence(ctx.db,"evd_valid")
    assert store.submit_verified(cid,evidence_refs=["evd_valid"],actor="r",expected_version=99)["detail"] == "version_conflict"
    def write(_):
        return ClaimStore(ctx.db).propose_from_text("我喜欢并发")
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(write,range(8)))
    assert sum(bool(r.get("persisted")) for r in rows) == 1


def test_hidden_evidence_does_not_leak_through_decision_history(ctx):
    store=ClaimStore(ctx.db)
    cid=store.propose_from_text("我喜欢审计")["claim_id"]
    seed_evidence(ctx.db,"evd_restricted")
    assert store.submit_verified(cid,evidence_refs=["evd_restricted"],actor="reviewer")["ok"]
    with ctx.db.transaction() as conn:
        conn.execute("UPDATE evidences SET security_json=? WHERE id='evd_restricted'",
                     ('{"owner_id":"another-owner"}',))
    client=TestClient(ctx.app);headers=agent(client)
    result=client.get(f"/api/v1/claims/{cid}",headers=headers)
    assert result.status_code==200
    assert "verification_status" not in result.json()["claim"]
    assert result.json()["claim"].get("lifecycle")!="verified"
    assert client.get(f"/api/v1/claims/{cid}/decisions",headers=headers).status_code==404
    assert client.get("/api/v1/evidences/evd_restricted",headers=headers).status_code==404


def test_grant_revoked_after_request_auth_is_rechecked_at_commit(ctx):
    from fastapi import HTTPException
    from cognitive_memory.governance.access import AccessContext,recheck_write_access
    from cognitive_memory.identity.grants import revoke_grant
    client=TestClient(ctx.app);agent(client)
    grant_id=ctx.db.connect().execute("SELECT id FROM agent_grants WHERE agent_id='audit'").fetchone()[0]
    snapshot=AccessContext(kind="agent",actor_id="audit",banks=["personal"],grant_id=grant_id)
    revoke_grant(ctx.db,"audit",reason="concurrent revoke")
    with pytest.raises(HTTPException) as denied:
        with ctx.db.transaction():
            recheck_write_access(ctx.db,snapshot)
    assert denied.value.status_code==403
