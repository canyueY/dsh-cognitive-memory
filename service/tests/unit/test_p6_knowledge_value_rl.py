# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.governance.capability_gate import set_capability_level
from cognitive_memory.governance.reinforcement_learning import (
    deploy_policy,
    run_offline_training,
)
from cognitive_memory.governance.value_system import (
    adapt_value_model,
    run_advanced_value_evaluation,
)
from cognitive_memory.knowledge.store import KnowledgeStore
from cognitive_memory.knowledge.validator import validate_knowledge
from cognitive_memory.storage.db import Database
from cognitive_memory.strategy.experience_store import ExperienceStore
from cognitive_memory.strategy.strategy_store import StrategyStore


class P6KnowledgeValueRlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        self.kn = KnowledgeStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_claim_knowledge_requires_ids(self) -> None:
        bad = validate_knowledge(
            {"kind": "claim_knowledge", "name": "x", "claim_ids": []}
        )
        self.assertFalse(bad["ok"])
        good = self.kn.from_claims(["clm_1"], name="pref")
        self.assertTrue(good["ok"])
        self.assertEqual(good["knowledge"]["kind"], "claim_knowledge")

    def test_schema_demotion(self) -> None:
        out = self.kn.from_schema("sch_1", name="struct")
        self.assertTrue(out["ok"])
        self.assertEqual(out["knowledge"]["kind"], "structural_knowledge")
        pat = self.kn.from_schema("sch_1", as_pattern=True)
        self.assertEqual(pat["knowledge"]["kind"], "pattern_knowledge")

    def test_knowledge_active_note(self) -> None:
        kid = self.kn.from_claims(["c1"], name="k")["knowledge"]["id"]
        act = self.kn.set_status(kid, "active")
        self.assertTrue(act["ok"])
        self.assertIn("does_not_verify", act["note"])

    def test_rl_train_and_deploy_gated_then_work(self) -> None:
        sid = StrategyStore(self.db).propose("s")["strategy"]["id"]
        e = ExperienceStore(self.db).create(context={"a": 1}, reward=1.0)
        StrategyStore(self.db).log(sid, experience_id=e["id"])

        locked = run_offline_training(self.db, {"strategy_id": sid})
        self.assertEqual(locked["detail"], "capability_locked")

        set_capability_level(
            self.db, "RL_OFFLINE_TRAINING", level="ACTIVE", enabled=True, actor="t"
        )
        fitted = run_offline_training(self.db, {"strategy_id": sid})
        self.assertTrue(fitted["ok"])
        self.assertEqual(fitted["count"], 1)
        self.assertFalse(fitted["deploy"]["allowed"])
        self.assertEqual(StrategyStore(self.db).get(sid)["status"], "proposed")

        dep_locked = deploy_policy(self.db, sid)
        self.assertEqual(dep_locked["detail"], "capability_locked")
        set_capability_level(
            self.db, "RL_POLICY_DEPLOYMENT", level="ACTIVE", enabled=True, actor="t"
        )
        dep = deploy_policy(self.db, sid)
        self.assertTrue(dep["ok"])
        self.assertEqual(dep["strategy"]["status"], "active")

    def test_value_advanced_and_adapt(self) -> None:
        locked = run_advanced_value_evaluation(self.db, {"intent": "隐私分享"})
        self.assertEqual(locked["detail"], "capability_locked")
        set_capability_level(
            self.db,
            "ADVANCED_VALUE_EVALUATION",
            level="ACTIVE",
            enabled=True,
            actor="t",
        )
        adv = run_advanced_value_evaluation(
            self.db, {"intent": "分享隐私", "proposed_action": "export contacts"}
        )
        self.assertTrue(adv["ok"])
        self.assertIsNone(adv["single_moral_score"])
        self.assertTrue(adv["hard_block_recommended"])

        adapt_locked = adapt_value_model(self.db, {"privacy": 2.0})
        self.assertEqual(adapt_locked["detail"], "capability_locked")
        set_capability_level(
            self.db,
            "AUTONOMOUS_VALUE_ADAPTATION",
            level="ACTIVE",
            enabled=True,
            actor="t",
        )
        hard = adapt_value_model(self.db, {"privacy_boundary": 1})
        self.assertEqual(hard["detail"], "immutable_hard_constraint")
        soft = adapt_value_model(self.db, {"privacy": 2.0, "_actor": "t"})
        self.assertTrue(soft["ok"])
        self.assertAlmostEqual(soft["prefs"]["privacy"], 2.0)

    def test_migration_014(self) -> None:
        with self.db.transaction() as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertIn("knowledge_nodes", names)
        self.assertIn("value_soft_prefs", names)


if __name__ == "__main__":
    unittest.main()
