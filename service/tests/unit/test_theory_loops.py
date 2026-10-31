"""Behavioral acceptance of the reconstructed theory, on isolated real Banks."""
import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from cognitive_memory.bootstrap import build_context
from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.claims.normalize import normalized_hash
from cognitive_memory.claims.parser import parse_memory_text
from cognitive_memory.cognition.feedback_learning import apply_feedback_learning
from cognitive_memory.cognition.loop_models import (
    CognitiveTask, ExecutableRule, LearningProposal, ProfileHypothesis, TaskFeedback, ValidationSuite,
)
from cognitive_memory.cognition.loops import CognitiveLoops
from cognitive_memory.cognition.promote import maybe_promote
from cognitive_memory.domain.models import FeedbackIn, MemoryProposeIn
from cognitive_memory.evidence.object_store import EvidenceObjectStore
from cognitive_memory.governance.capability_gate import set_capability_level
from tests.support import seed_evidence


@pytest.fixture
def env(tmp_path):
    ctx = build_context(data_dir=str(tmp_path), token="theory-node")
    yield ctx, CognitiveLoops(ctx.service)
    ctx.db.close()


def verified(ctx, text="我喜欢咖啡", *, scope=None, root="root-coffee", bank="personal"):
    claims = ClaimStore(ctx.db)
    cid = claims.propose_from_text(text, scope=scope, bank_id=bank)["claim_id"]
    eid = seed_evidence(ctx.db, "evd_" + cid, root=root, bank=bank)
    assert claims.attach_evidence(cid, eid)["ok"]
    result = claims.submit_verified(cid, evidence_refs=[eid], actor="fixture-reviewer")
    assert result["ok"], result
    return cid, eid


def task(cid, **kwargs):
    data = {"goal": "选择有证据支持的饮品", "allowed_actions": ["coffee"],
            "actions": [{"id": "coffee", "claim_ids": [cid]}]}
    data.update(kwargs)
    return CognitiveTask.model_validate(data)


@pytest.mark.parametrize("source,extra", [
    ("user_explicit", {"useful": True}), ("outcome", {"outcome": "success"}),
    ("self_eval", {"self_score": 1}), ("self_eval", {"incorrect": True}),
    ("unrecognized", {"self_score": 1}),
])
def test_feedback_is_not_fact_evidence(env, source, extra):
    ctx, _ = env
    mem = ctx.service.propose_memory(MemoryProposeIn(content="我喜欢咖啡", confidence=0.47))
    apply_feedback_learning(ctx.service, mem.id, source=source, **extra)
    after = ctx.service.get_memory(mem.id)
    assert after["confidence"] == 0.47
    assert after["status"] == "candidate"


def test_feedback_kind_persisted_without_false_attribution(env):
    ctx, _ = env
    mid = ctx.service.propose_memory(MemoryProposeIn(content="偏好待确认")).id
    result = ctx.service.feedback(FeedbackIn(memory_id=mid, incorrect=True, feedback_kind="fact_correction"))
    assert result["attribution"] == "unresolved" and not result["fact_confidence_changed"]
    row = ctx.db.connect().execute("SELECT feedback_kind FROM memory_feedback WHERE memory_id=?", (mid,)).fetchone()
    assert row[0] == "fact_correction"


def test_metadata_and_repetition_cannot_promote_hypothesis(env):
    ctx, _ = env
    m = ctx.service.propose_memory(MemoryProposeIn(content="用户永远内向", source_ids=["not-real"], status="active",
        metadata={"epistemic": "inference", "force_activate": True, "from_user": True, "useful_feedback_count": 100}))
    assert m.status.value == "candidate"
    assert not maybe_promote(ctx.service, m.id)


def test_negation_and_temporal_context_are_not_collapsed():
    values = ["我喜欢咖啡", "我不喜欢咖啡", "今天我喜欢咖啡", "明天我喜欢咖啡"]
    assert len({normalized_hash(parse_memory_text(x).ast) for x in values}) == 4


def test_validity_intervals_do_not_deduplicate_distinct_claims(env):
    ctx, _ = env
    store = ClaimStore(ctx.db)
    a = store.propose_from_text("我喜欢咖啡", validity_from="2025-01-01T00:00:00Z", validity_to="2025-02-01T00:00:00Z")
    b = store.propose_from_text("我喜欢咖啡", validity_from="2026-01-01T00:00:00Z", validity_to="2026-02-01T00:00:00Z")
    assert a["claim_id"] != b["claim_id"]


@pytest.mark.parametrize("text", ["我不太喜欢咖啡", "我暂时喜欢咖啡", "我喜欢咖啡，但下午以后一般不喝"])
def test_qualifiers_are_preserved_as_unknown_instead_of_generalized(text):
    parsed = parse_memory_text(text)
    assert parsed.ast.is_unresolved()
    assert parsed.ast.surface == text


def test_different_importers_do_not_create_independent_roots(env):
    ctx, _ = env
    store = EvidenceObjectStore(ctx.db)
    a = store.create(source_type="web", source_ref="a", root_source_id="original", producer="one")["evidence"]["id"]
    b = store.create(source_type="import", source_ref="b", root_source_id="original", producer="two")["evidence"]["id"]
    assert not store.independence_conflict([a, b])["independent"]


def test_transitive_and_cyclic_provenance(env):
    ctx, _ = env
    store = EvidenceObjectStore(ctx.db)
    a = seed_evidence(ctx.db, "root")
    b = store.create(source_type="summary", source_ref="b", metadata={"parent_evidence_ids": [a]})["evidence"]["id"]
    c = store.create(source_type="import", source_ref="c", metadata={"parent_evidence_ids": [b]})["evidence"]["id"]
    assert not store.independence_conflict([a, c])["independent"]
    with ctx.db.transaction() as conn:
        conn.execute("UPDATE evidences SET metadata_json=? WHERE id=?", (json.dumps({"parent_evidence_ids": [c]}), a))
    assert not store.lineage(c)["ok"]


@pytest.mark.parametrize("kind", ["inference", "summary", "model_output", "self_eval", "generated"])
def test_generated_content_cannot_verify_itself(env, kind):
    ctx, _ = env
    claims = ClaimStore(ctx.db)
    cid = claims.propose_from_text("我喜欢咖啡")["claim_id"]
    ev = EvidenceObjectStore(ctx.db).create(source_type=kind, source_ref="output:1", validation_state="valid",
        provenance_status="complete", chain=[{"ref": "output:1"}])["evidence"]
    result = claims.submit_verified(cid, evidence_refs=[ev["id"]], actor="reviewer")
    assert not result["ok"] and claims.get(cid)["lifecycle"] == "proposed"


def test_task_selection_is_not_execution_success(env):
    ctx, loops = env
    cid, _ = verified(ctx)
    result = loops.run(task(cid))
    assert result["selected_action"] == "coffee"
    assert result["task_success"] is None
    assert result["score_kind"] == "task_priority_not_probability"
    assert ctx.db.connect().execute("SELECT COUNT(*) FROM cognitive_task_runs").fetchone()[0] == 1


def test_context_missing_bank_scope_and_action_authorization(env):
    ctx, loops = env
    cid, _ = verified(ctx, scope={"scene": "evening"})
    assert loops.run(task(cid))["status"] == "unknown"
    assert loops.run(task(cid, context={"scene": "evening"}))["status"] == "selected"
    assert loops.run(task(cid, bank_id="projects", context={"scene": "evening"}))["status"] == "unknown"
    assert loops.run(task(cid, allowed_actions=["water"], context={"scene": "evening"}))["status"] == "unknown"


def test_budget_does_not_silently_drop_low_rank_counter_candidate(env):
    ctx, loops = env
    a, _ = verified(ctx)
    b, _ = verified(ctx, "我喜欢茶", root="root-tea")
    t = task(a, max_steps=1, actions=[{"id": "coffee", "claim_ids": [a, b]}])
    result = loops.run(t)
    assert result["reason"] == "budget_exhausted"
    assert result["selected_action"] is None and result["steps"] == 1


def test_cache_reuse_and_revocation_invalidation(env):
    ctx, loops = env
    cid, eid = verified(ctx)
    assert not loops.run(task(cid))["cache_hit"]
    assert loops.run(task(cid))["cache_hit"]
    EvidenceObjectStore(ctx.db).assess(eid, state="revoked", actor="reviewer")
    result = CognitiveLoops(ctx.service).run(task(cid))
    assert not result["cache_hit"] and result["status"] == "unknown"


def test_cache_rechecks_time_even_without_version_change(env, monkeypatch):
    ctx, loops = env
    cid, _ = verified(ctx)
    assert loops.run(task(cid))["status"] == "selected"
    monkeypatch.setattr("cognitive_memory.cognition.loops._current", lambda *args: False)
    result = loops.run(task(cid))
    assert not result["cache_hit"] and result["status"] == "unknown"


def learning(env, *, bad=False):
    ctx, loops = env
    cid, eid = verified(ctx)
    sid = ctx.service.store_cognitive_schema({"name": "晚间饮品", "state": "PROPOSED", "bank_id": "personal"})
    def case(name, scene, partition, expected):
        t = task(cid, context={"scene": scene}, actions=[{"id": "coffee", "claim_ids": [cid], "schema_id": sid}])
        return {"id": name, "partition": partition, "task": t.model_dump(), "expected_action": expected}
    suite = ValidationSuite(cases=[case("novel-evening", "evening", "heldout", "coffee"),
                                   case("keep-morning-unknown", "morning", "regression", None)])
    vs = loops.register_suite(suite)
    rule = ExecutableRule(action_id="coffee", when={"scene": "morning" if bad else "evening"}, required_claim_ids=[cid])
    p = LearningProposal(schema_id=sid, suite_id=vs["suite_id"], rule=rule, reason="限制适用范围")
    result = loops.propose(p)
    assert result["ok"], result
    return sid, result["update_id"], cid, eid, p


def unlock(ctx):
    return set_capability_level(ctx.db, "SCHEMA_MUTATION", level="CONTROLLED", enabled=True)


def test_preregistered_learning_apply_and_versioned_rollback(env):
    ctx, loops = env
    sid, uid, cid, _, _ = learning(env)
    before = ctx.service.get_cognitive_schema(sid)
    report = loops.evaluate(uid)
    assert report["passed"] and report["net_heldout_gain"] == 1 and report["regressions"] == 0
    assert ctx.service.get_cognitive_schema(sid) == before  # sandbox replay made no schema change
    assert not loops.apply(uid, confirm=True)["ok"]  # confirm alone is not authority
    unlock(ctx)
    applied = loops.apply(uid, confirm=True)
    assert applied["ok"], applied
    assert ctx.service.get_cognitive_schema(sid)["executable_rule"]["when"] == {"scene": "evening"}
    assert not loops.apply(uid, confirm=True)["ok"]
    rolled = loops.rollback(uid, confirm=True)
    assert rolled["ok"] and rolled["schema"]["state"] == before["state"]
    assert rolled["schema"]["executable_rule"] is None
    assert rolled["schema"]["version"] > applied["schema"]["version"]


def test_bad_update_cannot_publish_even_if_report_is_tampered(env):
    ctx, loops = env
    sid, uid, *_ = learning(env, bad=True)
    assert not loops.evaluate(uid)["passed"]
    update = loops.get_update(uid)
    payload = update["payload"]
    payload["report"] = {"ok": True, "passed": True}
    with ctx.db.transaction() as conn:
        conn.execute("UPDATE cognitive_learning_updates SET payload_json=? WHERE id=?", (json.dumps(payload), uid))
    unlock(ctx)
    assert not loops.apply(uid, confirm=True)["ok"]
    assert ctx.service.get_cognitive_schema(sid)["state"] == "PROPOSED"


@pytest.mark.parametrize("change", ["evidence", "schema"])
def test_stale_validation_cannot_publish(env, change):
    ctx, loops = env
    sid, uid, _, eid, _ = learning(env)
    assert loops.evaluate(uid)["passed"]
    if change == "evidence":
        EvidenceObjectStore(ctx.db).assess(eid, state="revoked", actor="reviewer")
    else:
        ctx.service.update_cognitive_schema(sid, patch={"description": "concurrent change"})
    unlock(ctx)
    assert not loops.apply(uid, confirm=True)["ok"]


def test_training_overlap_and_unknown_rule_fields_are_rejected(env):
    _, loops = env
    _, _, _, eid, proposal = learning(env)
    case_overlap = proposal.model_copy(update={"training_case_ids": ["novel-evening"]})
    assert loops.propose(case_overlap)["detail"] == "training_validation_overlap"
    evidence_overlap = proposal.model_copy(update={"training_evidence_ids": [eid]})
    assert loops.propose(evidence_overlap)["detail"] == "training_validation_source_overlap"
    with pytest.raises(ValidationError):
        LearningProposal.model_validate({**proposal.model_dump(), "passed": True})


def test_rollback_cannot_clobber_later_schema_update(env):
    ctx, loops = env
    sid, uid, *_ = learning(env)
    loops.evaluate(uid)
    unlock(ctx)
    assert loops.apply(uid, confirm=True)["ok"]
    ctx.service.update_cognitive_schema(sid, patch={"description": "new independent work"})
    assert loops.rollback(uid, confirm=True)["detail"] == "target_changed"


@pytest.mark.parametrize("kind", ["personality", "preference", "emotion", "value"])
def test_profile_remains_contextual_hypothesis(env, kind):
    ctx, loops = env
    _, eid = verified(ctx)
    p = ProfileHypothesis(subject="user", kind=kind, statement="晚间喜欢安静", context={"scene": "evening"},
                          source="inference", evidence_ids=[eid], guided=True)
    result = loops.record_profile(p)
    assert result["ok"] and not result["grants_changed"]
    m = ctx.service.get_memory(result["memory_id"])
    assert m["status"] == "candidate" and m["metadata"]["profile"]["guided"]
    assert not maybe_promote(ctx.service, m["id"])


def test_rest_routes_validate_and_require_node_token(env):
    ctx, _ = env
    cid, _ = verified(ctx)
    client = TestClient(ctx.app)
    body = task(cid).model_dump()
    assert client.post("/api/v1/cognition/tasks/run", json=body).status_code == 401
    headers = {"Authorization": "Bearer theory-node"}
    result = client.post("/api/v1/cognition/tasks/run", headers=headers, json=body)
    assert result.status_code == 200 and result.json()["selected_action"] == "coffee"
    assert client.post("/api/v1/cognition/tasks/run", headers=headers, json={**body, "max_steps": 0}).status_code == 422
    assert client.post("/api/v1/cognition/tasks/run", headers=headers, json={**body, "passed": True}).status_code == 422


def test_named_subject_negation_and_location_are_preserved():
    positive = parse_memory_text("张三喜欢咖啡").ast
    negative = parse_memory_text("张三不喜欢咖啡").ast
    assert positive.root.subject == "张三"
    assert negative.root.kind == "negation" and negative.root.target.subject == "张三"
    assert parse_memory_text("张三不是老师").ast.root.kind == "negation"
    assert parse_memory_text("张三不在北京").ast.root.kind == "negation"
    assert parse_memory_text("今晚我喜欢咖啡").ast.scope["relative_time"] == "今晚"


def test_atomic_publication_rolls_back_schema_and_receipt_on_failure(env, monkeypatch):
    ctx, loops = env
    sid, uid, *_ = learning(env)
    loops.evaluate(uid)
    unlock(ctx)
    before = ctx.service.get_cognitive_schema(sid)
    old = ctx.service.update_cognitive_schema
    def fail_after_write(*args, **kwargs):
        old(*args, **kwargs)
        raise RuntimeError("injected_storage_failure")
    monkeypatch.setattr(ctx.service, "update_cognitive_schema", fail_after_write)
    with pytest.raises(RuntimeError, match="injected_storage_failure"):
        loops.apply(uid, confirm=True)
    assert ctx.service.get_cognitive_schema(sid) == before
    assert loops.get_update(uid)["status"] == "evaluated"


def test_evidence_retraction_revisits_descendants_but_preserves_independent_support(env):
    ctx, _ = env
    store, claims = EvidenceObjectStore(ctx.db), ClaimStore(ctx.db)
    root = seed_evidence(ctx.db, "evd_root")
    child = store.create(source_type="import", source_ref="copy", validation_state="valid", provenance_status="complete",
                         chain=[{"ref": "copy"}], metadata={"parent_evidence_ids": [root]})["evidence"]["id"]
    cid = claims.propose_from_text("我喜欢茶")["claim_id"]
    claims.attach_evidence(cid, child)
    assert claims.submit_verified(cid, evidence_refs=[child], actor="test")["ok"]
    cid2 = claims.propose_from_text("我喜欢水")["claim_id"]
    independent = seed_evidence(ctx.db, "evd_other")
    claims.attach_evidence(cid2, child)
    claims.attach_evidence(cid2, independent)
    assert claims.submit_verified(cid2, evidence_refs=[child, independent], actor="test")["ok"]
    assert store.assess(root, state="revoked", actor="test")["ok"]
    assert store.get(child)["validation_state"] == "unverified"
    assert claims.get(cid)["verification_status"] != "verified"
    assert claims.get(cid2)["verification_status"] == "verified"


def test_grounded_claim_promotion_has_positive_path(env):
    ctx, _ = env
    mem = ctx.service.propose_memory(MemoryProposeIn(content="我喜欢咖啡", metadata={"epistemic": "fact"}))
    claims = ClaimStore(ctx.db)
    cid = claims.propose_from_text(mem.content, source_memory_id=mem.id)["claim_id"]
    eid = seed_evidence(ctx.db, "evd_promotion")
    claims.attach_evidence(cid, eid)
    assert claims.submit_verified(cid, evidence_refs=[eid], actor="test")["ok"]
    assert maybe_promote(ctx.service, mem.id)
    assert ctx.service.get_memory(mem.id)["status"] == "active"


def test_result_records_cause_hypotheses_without_claiming_diagnosis(env):
    ctx, loops = env
    cid, _ = verified(ctx)
    run = loops.run(task(cid))
    before = ClaimStore(ctx.db).get(cid)
    feedback = TaskFeedback(kind="task_outcome", source="execution", outcome={"success": False},
                            possible_stages=["retrieval", "context"])
    result = loops.record_result(run["run_id"], feedback)
    assert result["ok"] and result["attribution"] == "unresolved"
    assert ClaimStore(ctx.db).get(cid) == before
    assert ctx.db.connect().execute("SELECT COUNT(*) FROM cognitive_task_feedback").fetchone()[0] == 1


def test_python_sdk_reaches_actual_cognitive_routes(env):
    from cognitive_memory.sdk.client import MnemosyneClient
    ctx, _ = env
    cid, _ = verified(ctx)
    client = MnemosyneClient("http://testserver", "theory-node", session=TestClient(ctx.app))
    result = client.run_cognitive_task(task(cid).model_dump())
    assert result["selected_action"] == "coffee"
    assert client.record_cognitive_result(result["run_id"], {"kind": "task_outcome", "source": "execution", "outcome": {"success": True}})["ok"]


def test_counterevidence_blocks_rule_and_cache(env):
    ctx, loops = env
    cid, _ = verified(ctx)
    sid = ctx.service.store_cognitive_schema({"name": "rule", "state": "ACTIVE", "executable_rule":
        {"action_id": "coffee", "required_claim_ids": [cid]}})
    request = task(cid, actions=[{"id": "coffee", "claim_ids": [cid], "schema_id": sid}])
    assert loops.run(request)["status"] == "selected"
    counter, _ = verified(ctx, "我不喜欢咖啡", root="counter-root")
    ctx.service.update_cognitive_schema(sid, patch={"executable_rule":
        {"action_id": "coffee", "required_claim_ids": [cid], "counter_claim_ids": [counter]}})
    result = loops.run(request)
    assert not result["cache_hit"] and result["status"] == "unknown"


def test_cache_and_full_path_agree_without_mutating_claims(env):
    ctx, loops = env
    cid, _ = verified(ctx)
    before = ClaimStore(ctx.db).get(cid)
    first = loops.run(task(cid))
    second = loops.run(task(cid))
    full = loops.run(task(cid, use_cache=False))
    assert first["selected_action"] == second["selected_action"] == full["selected_action"]
    assert second["cache_hit"] and not full["cache_hit"]
    assert ClaimStore(ctx.db).get(cid) == before


def test_migration_preserves_old_bank_and_marks_historical_parser(tmp_path, monkeypatch):
    import cognitive_memory.storage.migrations as migrations
    from cognitive_memory.storage.db import Database
    from cognitive_memory.core.service import MemoryService
    from cognitive_memory.events.bus import EventBus
    original = migrations.MIGRATIONS
    path = tmp_path / "old.db"
    monkeypatch.setattr(migrations, "MIGRATIONS", [m for m in original if m[0] != "017_theory_loops"])
    db = Database(path)
    db.ensure_schema()
    service = MemoryService(db, EventBus())
    mem = service.propose_memory(MemoryProposeIn(content="保留旧记录"))
    db.close()
    monkeypatch.setattr(migrations, "MIGRATIONS", original)
    db = Database(path)
    db.ensure_schema()
    assert db.connect().execute("SELECT content FROM memories WHERE id=?", (mem.id,)).fetchone()[0] == "保留旧记录"
    assert list((tmp_path / "migration-backups").glob("*.db"))
    columns = {r[1] for r in db.connect().execute("PRAGMA table_info(claims)")}
    assert "parser_version" in columns
    db.close()


def test_api_learning_roundtrip_with_fixed_suite(env):
    ctx, loops = env
    _, uid, *_ = learning(env)
    client = TestClient(ctx.app)
    headers = {"Authorization": "Bearer theory-node"}
    path = f"/api/v1/cognition/learning-updates/{uid}"
    assert client.post(path + "/evaluate", headers=headers).json()["passed"]
    assert not client.post(path + "/apply?confirm=true", headers=headers).json()["ok"]
    unlock(ctx)
    assert client.post(path + "/apply?confirm=true", headers=headers).json()["ok"]
    assert client.post(path + "/rollback?confirm=true", headers=headers).json()["ok"]


def test_context_injection_labels_hypotheses_and_honors_budget(env):
    from cognitive_memory.domain.models import ContextBuildIn
    ctx, _ = env
    ctx.service.propose_memory(MemoryProposeIn(content="咖啡偏好仍是猜测", metadata={"epistemic": "inference"}))
    result = ctx.service.build_context(ContextBuildIn(query="咖啡", token_budget=100))
    assert result.fragments and result.fragments[0]["epistemic_status"] == "hypothesis"
    assert "hypothesis" in result.brief
    small = ctx.service.build_context(ContextBuildIn(query="咖啡", token_budget=1))
    assert small.token_estimate <= 1 and not small.fragments
