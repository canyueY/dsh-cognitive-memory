"""Repeatable synthetic acceptance in a temporary Bank; never opens a user Bank."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cognitive_memory.bootstrap import build_context
from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.cognition.loop_models import CognitiveTask, ExecutableRule, LearningProposal, ValidationSuite
from cognitive_memory.cognition.loops import CognitiveLoops
from cognitive_memory.domain.models import ObservationIn, SourceKind
from cognitive_memory.evidence.object_store import EvidenceObjectStore
from cognitive_memory.governance.capability_gate import set_capability_level


def main():
    with tempfile.TemporaryDirectory(prefix="mnemosyne-theory-", ignore_cleanup_errors=True) as root:
        ctx = build_context(data_dir=root, token="synthetic-demo-only")
        try:
            obs = ctx.service.capture_observation(ObservationIn(
                source_kind=SourceKind.USER_STATEMENT, content="我喜欢咖啡",
                producer="synthetic-demo", metadata={"synthetic": True}))
            evidence = EvidenceObjectStore(ctx.db)
            ev = evidence.create_from_observation(obs.id, content=obs.content)["evidence"]
            assert evidence.assess(ev["id"], state="valid", actor="synthetic-reviewer")["ok"]
            claims = ClaimStore(ctx.db)
            cid = claims.propose_from_text(obs.content)["claim_id"]
            claims.attach_evidence(cid, ev["id"])
            assert claims.submit_verified(cid, evidence_refs=[ev["id"]], actor="synthetic-reviewer")["ok"]
            sid = ctx.service.store_cognitive_schema({"name": "synthetic-evening-rule", "state": "PROPOSED"})
            loops = CognitiveLoops(ctx.service)
            def task(scene):
                return CognitiveTask(goal="synthetic decision", context={"scene": scene}, allowed_actions=["coffee"],
                    actions=[{"id": "coffee", "claim_ids": [cid], "schema_id": sid}])
            suite = loops.register_suite(ValidationSuite(cases=[
                {"id": "heldout-evening", "partition": "heldout", "task": task("evening"), "expected_action": "coffee"},
                {"id": "regression-morning", "partition": "regression", "task": task("morning"), "expected_action": None},
            ]))
            proposal = loops.propose(LearningProposal(schema_id=sid, suite_id=suite["suite_id"],
                rule=ExecutableRule(action_id="coffee", when={"scene": "evening"}, required_claim_ids=[cid]),
                reason="synthetic scope restriction"))
            uid = proposal["update_id"]
            report = loops.evaluate(uid)
            assert report["passed"] and report["regressions"] == 0
            assert not loops.apply(uid, confirm=True)["ok"]
            set_capability_level(ctx.db, "SCHEMA_MUTATION", level="CONTROLLED", enabled=True, actor="synthetic-governance")
            assert loops.apply(uid, confirm=True)["ok"]
            assert loops.run(task("evening"))["selected_action"] == "coffee"
            assert loops.run(task("evening"))["cache_hit"]
            assert loops.run(task("morning"))["status"] == "unknown"
            evidence.assess(ev["id"], state="revoked", actor="synthetic-reviewer")
            assert loops.run(task("evening"))["status"] == "unknown"
            assert loops.rollback(uid, confirm=True)["ok"]
            print(json.dumps({"ok": True, "scope": "synthetic_behavioral_acceptance_only",
                "bank": "temporary", "heldout_net_gain": report["net_heldout_gain"],
                "regressions": report["regressions"], "capability_gate": "passed",
                "context_boundary": "passed", "cache_invalidation": "passed", "rollback": "passed"}))
        finally:
            ctx.db.close()


if __name__ == "__main__":
    main()
