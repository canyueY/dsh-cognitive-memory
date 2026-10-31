# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.governance.capability_gate import set_capability_level
from cognitive_memory.governance.reinforcement_learning import (
    deploy_policy,
    record_feedback_sample,
    run_offline_training,
)
from cognitive_memory.storage.db import Database
from cognitive_memory.strategy.experience_store import ExperienceStore
from cognitive_memory.strategy.metacontroller import schedule
from cognitive_memory.strategy.offline_eval import run_offline_eval
from cognitive_memory.strategy.propensity import compute_overlap, compute_propensity
from cognitive_memory.strategy.strategy_store import StrategyStore


class P5StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        self.exps = ExperienceStore(self.db)
        self.strats = StrategyStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_experience_create_and_list(self) -> None:
        row = self.exps.create(
            context={"scene": "music"},
            action={"play": "track_a"},
            outcome={"success": True},
            reward=1.0,
            memory_ids=["m1"],
        )
        self.assertTrue(row["ok"])
        self.assertTrue(str(row["id"]).startswith("exp_"))
        items = self.exps.list(limit=10)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["memory_ids"], ["m1"])

    def test_rl_feedback_persists_experience(self) -> None:
        out = record_feedback_sample(
            self.db,
            {
                "context": {"k": "v"},
                "action": {"a": 1},
                "outcome": {"success": True},
                "reward": 0.8,
                "memory_ids": ["mem_x"],
            },
        )
        self.assertTrue(out["ok"])
        self.assertTrue(out.get("experience_id"))
        got = self.exps.get(out["experience_id"])
        self.assertIsNotNone(got)
        self.assertEqual(got["reward"], 0.8)

    def test_strategy_propose_rejects_active(self) -> None:
        bad = self.strats.propose("x", status="active")
        self.assertFalse(bad["ok"])
        good = self.strats.propose("prefer_calm", scope={"mood": "calm"}, status="proposed")
        self.assertTrue(good["ok"])
        self.assertEqual(good["strategy"]["status"], "proposed")

    def test_activate_locked_by_default(self) -> None:
        sid = self.strats.propose("s1")["strategy"]["id"]
        act = self.strats.activate(sid)
        self.assertFalse(act["ok"])
        self.assertEqual(act["detail"], "capability_locked")
        self.assertEqual(self.strats.get(sid)["status"], "proposed")

    def test_activate_after_unlock(self) -> None:
        sid = self.strats.propose("s2")["strategy"]["id"]
        set_capability_level(
            self.db,
            "RL_POLICY_DEPLOYMENT",
            level="ACTIVE",
            enabled=True,
            actor="test",
        )
        act = self.strats.activate(sid)
        self.assertTrue(act["ok"])
        self.assertEqual(act["strategy"]["status"], "active")

    def test_propensity_ungated(self) -> None:
        self.exps.create(
            context={"mood": "calm", "scene": "night"},
            action={"volume": "low"},
            reward=1.0,
        )
        self.exps.create(
            context={"mood": "calm", "scene": "day"},
            action={"volume": "low"},
            reward=0.0,
        )
        prop = compute_propensity(
            self.exps.list(),
            strategy_scope={"mood": "calm"},
        )
        self.assertTrue(prop["ok"])
        self.assertEqual(prop["n"], 2)
        self.assertAlmostEqual(prop["mean_reward"], 0.5)
        ov = compute_overlap({"mood": "calm"}, {"mood": "calm", "scene": "x"})
        self.assertGreater(ov["overlap"], 0.0)

    def test_offline_eval_locked_then_open(self) -> None:
        sid = self.strats.propose("eval_s", scope={"mood": "calm"})["strategy"]["id"]
        e1 = self.exps.create(context={"mood": "calm"}, reward=1.0)
        e2 = self.exps.create(context={"mood": "calm"}, reward=0.2)
        self.strats.log(sid, experience_id=e1["id"], decision="try", outcome="ok")
        self.strats.log(sid, experience_id=e2["id"], decision="try", outcome="meh")

        locked = run_offline_eval(self.db, sid)
        self.assertFalse(locked["ok"])
        self.assertEqual(locked["detail"], "capability_locked")

        set_capability_level(
            self.db,
            "BANDIT_EXPERIMENT",
            level="ACTIVE",
            enabled=True,
            actor="test",
        )
        opened = run_offline_eval(self.db, sid)
        self.assertTrue(opened["ok"])
        self.assertEqual(opened["status_unchanged"], "proposed")
        self.assertIn("propensity", opened)
        refreshed = self.strats.get(sid)
        self.assertIn("score", refreshed["propensity"])

    def test_rl_train_and_deploy_remain_locked(self) -> None:
        train = run_offline_training(self.db, {"allow_train": True})
        self.assertFalse(train["ok"])
        self.assertEqual(train["detail"], "capability_locked")
        dep = deploy_policy(self.db, "p1")
        self.assertFalse(dep["ok"])
        self.assertEqual(dep["detail"], "capability_locked")

    def test_metacontroller_reflect(self) -> None:
        self.strats.propose("a")
        out = schedule(self.db, action="reflect")
        self.assertTrue(out["ok"])
        self.assertGreaterEqual(out["focus_count"], 1)

    def test_migration_012_tables_exist(self) -> None:
        with self.db.transaction() as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertIn("experiences", names)
        self.assertIn("strategies", names)
        self.assertIn("strategy_logs", names)


if __name__ == "__main__":
    unittest.main()
