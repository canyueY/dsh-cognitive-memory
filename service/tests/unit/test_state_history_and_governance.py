import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from cognitive_memory.bootstrap import build_context
from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.claims.ast import Atom,ClaimAST
from cognitive_memory.claims.normalize import normalized_hash
from cognitive_memory.cognition.schema_ops import assimilate_schema,apply_cognitive_change_plan
from cognitive_memory.cognition.schema_network import split_schema
from cognitive_memory.evidence.object_store import EvidenceObjectStore
from cognitive_memory.governance.capability_gate import set_capability_level
from cognitive_memory.tms.engine import TruthMaintenanceEngine
from tests.support import seed_evidence


@pytest.fixture
def ctx(tmp_path):
    c=build_context(data_dir=str(tmp_path/"bank"),token="test")
    yield c
    c.db.close()


def test_proposal_idempotency_and_stale_version_conflict(ctx):
    sid=ctx.service.store_cognitive_schema({"name":"schema","state":"PROPOSED"})
    set_capability_level(ctx.db,"SCHEMA_MUTATION",level="ACTIVE",enabled=True,actor="reviewer")
    plan=assimilate_schema(ctx.service,sid,note="change")
    first=apply_cognitive_change_plan(ctx.service,plan["change_plan_id"],confirm=True)
    assert first["ok"]
    version=ctx.service.get_cognitive_schema(sid)["version"]
    again=apply_cognitive_change_plan(ctx.service,plan["change_plan_id"],confirm=True)
    assert again["idempotent"]
    assert ctx.service.get_cognitive_schema(sid)["version"]==version
    stale=assimilate_schema(ctx.service,sid,note="stale")
    ctx.service.update_cognitive_schema(sid,patch={"description":"concurrent change"})
    out=apply_cognitive_change_plan(ctx.service,stale["change_plan_id"],confirm=True)
    assert out["detail"]=="version_conflict"
    assert ctx.service.get_cognitive_schema(sid)["description"]=="concurrent change"


def test_split_preview_zero_writes_and_private_flag_no_bypass(ctx):
    sid=ctx.service.store_cognitive_schema({"name":"schema","state":"PROPOSED"})
    before=ctx.db.connect().total_changes
    result=split_schema(ctx.service,sid,child_specs=[{"name":"child"}],preview=True)
    assert result["dry_run"]
    assert ctx.db.connect().total_changes==before
    blocked=split_schema(ctx.service,sid,child_specs=[{"name":"child"}],confirm=True,_governance_preauthorized=True)
    assert not blocked["ok"]


def test_asof_and_deterministic_reexecution(ctx):
    store=ClaimStore(ctx.db);cid=store.propose_from_text("我喜欢审计")["claim_id"]
    store.transition(cid,"supported",reason="support",decision_at="2030-01-01T00:00:00Z")
    store.transition(cid,"retracted",reason="correction",decision_at="2031-01-01T00:00:00Z")
    assert store.as_of(cid,"2020-01-01T00:00:00Z") is None
    assert store.as_of(cid,"2030-06-01T00:00:00+00:00")["recorded_lifecycle"]=="supported"
    assert store.as_of(cid,"2032-01-01T00:00:00Z")["recorded_lifecycle"]=="retracted"
    assert store.replay(cid)["ok"]
    assert store.as_of(cid,"yesterday")["detail"]=="invalid_timestamp"


def test_legacy_identity_reused_without_hash_or_id_rewrite(ctx):
    store=ClaimStore(ctx.db);first=store.propose_from_text("我喜欢审计")
    cid=first["claim_id"]
    with ctx.db.transaction() as conn:
        conn.execute("UPDATE claims SET normalized_hash='legacy-hash',normalization_version='claim.normalize.v1' WHERE id=?",(cid,))
    second=store.propose_from_text("我喜欢审计")
    assert second["same_as"]==cid
    assert store.get(cid)["normalized_hash"]=="legacy-hash"
    assert store.replay(cid)["detail"]=="historical_algorithm_unavailable"


def test_quantities_do_not_collapse_unit_case():
    def h(value):
        return normalized_hash(ClaimAST(root=Atom(subject="x",predicate="equals",arguments=[value])))
    assert h("1 kg")==h("1000 g")
    assert h("1 MW")!=h("1 mW")
    assert h("1e9999999 W")!=h("1 W")


def test_revocation_concurrent_with_verification_never_leaves_verified(ctx):
    cid=ClaimStore(ctx.db).propose_from_text("我喜欢审计")["claim_id"]
    seed_evidence(ctx.db,"evd_concurrent")
    def verify():
        return ClaimStore(ctx.db).submit_verified(cid,evidence_refs=["evd_concurrent"],actor="reviewer")
    def revoke():
        return EvidenceObjectStore(ctx.db).assess("evd_concurrent",state="revoked",actor="reviewer")
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(verify);b=pool.submit(revoke)
        a.result();assert b.result()["ok"]
    assert ClaimStore(ctx.db).get(cid)["verification_status"]!="verified"


def test_self_support_and_time_budget_are_explicit():
    engine=TruthMaintenanceEngine()
    engine.add_justification("cycle",["cycle"])
    assert engine.propagate(["cycle"]).scc_unknown==["cycle"]
    result=engine.propagate(["cycle"],max_elapsed_ms=0)
    assert not result.ok
    assert "budget_exceeded" in result.reason_codes


def test_schema_http_preview_does_not_persist(ctx):
    from fastapi.testclient import TestClient
    a=ctx.service.store_cognitive_schema({"name":"a","state":"PROPOSED"})
    b=ctx.service.store_cognitive_schema({"name":"b","state":"PROPOSED"})
    client=TestClient(ctx.app);headers={"Authorization":"Bearer test"}
    before=ctx.db.connect().total_changes
    split=client.post(f"/api/v1/schemas/{a}/split",headers=headers,
                       json={"preview":True,"child_specs":[{"name":"child"}]})
    assert split.status_code==200 and split.json()["dry_run"]
    merged=client.post("/api/v1/schemas/merge",headers=headers,
                        json={"preview":True,"schema_ids":[a,b]})
    assert merged.status_code==200 and merged.json()["dry_run"]
    assert ctx.db.connect().total_changes==before
