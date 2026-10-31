# -*- coding: utf-8 -*-
"""Mnemosyne 2.0：图式存储 / 发现 / Gate 硬锁 / P1.5 治理收口。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.cognition.schema_discovery import discover_schema_candidates
from cognitive_memory.cognition.schema_ops import (
    accommodate_schema,
    apply_cognitive_change_plan,
    assimilate_schema,
)
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.governance.capability_gate import (
    check_capability,
    ensure_default_capabilities,
    list_capabilities,
    require_capability,
    CapabilityLockedError,
    set_capability_level,
)
from cognitive_memory.governance.reinforcement_learning import (
    deploy_policy,
    run_offline_training,
)
from cognitive_memory.governance.value_system import (
    analyze_value_conflict_basic,
    run_advanced_value_evaluation,
)
from cognitive_memory.storage.db import Database


class SchemaGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())
        ensure_default_capabilities(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_gate_default_locked(self) -> None:
        caps = list_capabilities(self.db)
        self.assertGreaterEqual(len(caps), 6)
        for c in caps:
            self.assertEqual(c["level"], "LOCKED")
            self.assertFalse(c["enabled"])
        pack = check_capability(self.db, "RL_OFFLINE_TRAINING")
        self.assertFalse(pack["allowed"])
        with self.assertRaises(CapabilityLockedError):
            require_capability(self.db, "RL_POLICY_DEPLOYMENT")
        mut = check_capability(self.db, "SCHEMA_MUTATION")
        self.assertFalse(mut["allowed"])

    def test_rl_and_value_stubs_locked(self) -> None:
        tr = run_offline_training(self.db, {})
        self.assertFalse(tr.get("ok"))
        self.assertEqual(tr.get("detail"), "capability_locked")
        dep = deploy_policy(self.db, "p1")
        self.assertEqual(dep.get("detail"), "capability_locked")
        adv = run_advanced_value_evaluation(self.db, {})
        self.assertEqual(adv.get("detail"), "capability_locked")
        basic = analyze_value_conflict_basic("分享用户隐私联系人", proposed_action="发给第三人")
        self.assertTrue(basic.get("ok"))
        self.assertTrue(basic.get("conflicts"))

    def test_schema_store_assimilate_accommodate(self) -> None:
        sid = self.svc.store_cognitive_schema(
            {
                "name": "测试图式·简洁",
                "description": "候选规律",
                "type": "BEHAVIORAL",
                "state": "PROPOSED",
                "confidence": 0.4,
                "evidence": {"supporting": [], "counter": []},
                "applicability": {"scope": ["日常"], "exclusions": []},
            }
        )
        sch = self.svc.get_cognitive_schema(sid)
        self.assertIsNotNone(sch)
        self.assertEqual(sch["state"], "PROPOSED")

        mem = self.svc.propose_memory(
            MemoryProposeIn(
                content="主人在忙碌时说请直接给结论",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        # default: LearningProposal only — no direct mutation
        a = assimilate_schema(self.svc, sid, memory_ids=[mem.id], note="补充证据")
        self.assertTrue(a["ok"])
        self.assertTrue(a.get("dry_run"))
        self.assertTrue(a.get("change_plan_id"))
        sch_after_preview = self.svc.get_cognitive_schema(sid)
        self.assertEqual(
            (sch_after_preview.get("evidence") or {}).get("supporting") or [],
            [],
        )

        # confirm alone is not authorization
        denied_confirm = assimilate_schema(
            self.svc, sid, memory_ids=[mem.id], note="补充证据", confirm=True
        )
        self.assertFalse(denied_confirm.get("ok"))
        self.assertEqual(denied_confirm.get("detail"), "capability_locked")
        self.assertIn("confirm_true_is_not_authorization", str(denied_confirm.get("note")))

        set_capability_level(
            self.db,
            "SCHEMA_MUTATION",
            level="ACTIVE",
            enabled=True,
            actor="test",
        )
        a_ok = assimilate_schema(
            self.svc, sid, memory_ids=[mem.id], note="补充证据", confirm=True
        )
        self.assertTrue(a_ok["ok"])
        self.assertFalse(a_ok.get("dry_run"))
        self.assertIn(mem.id, (a_ok["schema"].get("evidence") or {}).get("supporting") or [])

        mem2 = self.svc.propose_memory(
            MemoryProposeIn(
                content="主人在技术问题上要求完整推导",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        b = accommodate_schema(
            self.svc,
            sid,
            memory_ids=[mem2.id],
            counter_note="技术讨论例外",
        )
        self.assertTrue(b["ok"])
        self.assertTrue(b.get("dry_run"))
        self.assertTrue(b.get("change_plan_id"))
        plan = self.svc.get_cognitive_change_plan(str(b["change_plan_id"]))
        self.assertEqual(plan["status"], "PROPOSED")

        denied = apply_cognitive_change_plan(self.svc, plan["id"], confirm=False)
        self.assertFalse(denied.get("ok"))
        self.assertEqual(denied.get("detail"), "confirm_required")

        # unlock already set — apply should succeed
        applied = apply_cognitive_change_plan(self.svc, plan["id"], confirm=True)
        self.assertTrue(applied.get("ok"))

    def test_confirm_true_does_not_bypass_locked_apply(self) -> None:
        sid = self.svc.store_cognitive_schema(
            {
                "name": "门禁图式",
                "type": "KNOWLEDGE",
                "state": "PROPOSED",
                "confidence": 0.3,
                "evidence": {"supporting": [], "counter": []},
            }
        )
        plan_id = self.svc.store_cognitive_change_plan(
            {
                "operation": "SPECIALIZE",
                "targetSchemaIds": [sid],
                "risk_level": "MEDIUM",
                "approval_required": True,
                "status": "PROPOSED",
                "reason": "gate-test",
                "payload": {"proposed_patch": {"description": "patched"}, "proposed_state": "VALIDATING"},
                "proposed_patch": {"description": "patched"},
            }
        )
        blocked = apply_cognitive_change_plan(self.svc, plan_id, confirm=True)
        self.assertFalse(blocked.get("ok"))
        self.assertEqual(blocked.get("detail"), "capability_locked")
        sch = self.svc.get_cognitive_schema(sid) or {}
        self.assertNotEqual(sch.get("description"), "patched")

    def test_discover_from_memories(self) -> None:
        for i in range(4):
            self.svc.propose_memory(
                MemoryProposeIn(
                    content=f"主人喜欢听夜航星 第{i}次提到 夜航星音乐",
                    type=MemoryType.EPISODIC,
                    status=MemoryStatus.ACTIVE,
                )
            )
        pack = discover_schema_candidates(
            self.svc,
            limit_memories=50,
            min_cluster=3,
            min_similarity=0.15,
            persist=True,
        )
        self.assertTrue(pack.get("ok"))
        self.assertGreaterEqual(int(pack.get("scanned_memories") or 0), 4)
        self.assertIn("candidates", pack)
        listed = self.svc.list_cognitive_schemas(limit=20)
        if pack.get("count"):
            self.assertTrue(listed)
            self.assertEqual(listed[0]["state"], "PROPOSED")

    def test_external_set_capability_does_not_auto_unlock_others(self) -> None:
        set_capability_level(
            self.db,
            "BANDIT_EXPERIMENT",
            level="EXPERIMENTAL",
            enabled=False,
            actor="test",
        )
        bandit = check_capability(self.db, "BANDIT_EXPERIMENT")
        self.assertFalse(bandit["allowed"])
        self.assertTrue(bandit.get("experimental_ok"))
        rl = check_capability(self.db, "RL_OFFLINE_TRAINING")
        self.assertEqual(rl["level"], "LOCKED")


if __name__ == "__main__":
    unittest.main()
