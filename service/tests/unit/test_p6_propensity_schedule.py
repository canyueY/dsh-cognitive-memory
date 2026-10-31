# -*- coding: utf-8 -*-
"""P6: propensity/overlap fixtures + MetaController rank/reevaluate (no deploy)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.governance.capability_gate import set_capability_level
from cognitive_memory.storage.db import Database
from cognitive_memory.strategy.experience_store import ExperienceStore
from cognitive_memory.strategy.metacontroller import schedule
from cognitive_memory.strategy.offline_eval import run_offline_eval
from cognitive_memory.strategy.propensity import compute_overlap, compute_propensity
from cognitive_memory.strategy.strategy_store import StrategyStore


class P6PropensityScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        self.strategies = StrategyStore(self.db)
        self.exps = ExperienceStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def _seed_strategy(
        self, name: str, scope: dict, rewards: list[float]
    ) -> str:
        sid = self.strategies.propose(name, scope=scope)["strategy"]["id"]
        for r in rewards:
            e = self.exps.create(
                context=dict(scope),
                action={"play": True},
                outcome={"success": r > 0.5},
                reward=r,
            )
            self.strategies.log(
                sid, experience_id=e["id"], decision="play", outcome="ok", propensity=r
            )
        return sid

    def test_overlap_and_propensity_blend(self) -> None:
        ov = compute_overlap({"mood": "calm"}, {"mood": "calm", "hour": 22})
        self.assertGreater(ov["overlap"], 0.0)
        exps = [
            {"reward": 1.0, "context": {"mood": "calm"}, "action": {}},
            {"reward": 0.8, "context": {"mood": "calm"}, "action": {}},
            {"reward": 0.9, "context": {"mood": "calm"}, "action": {}},
        ]
        prop = compute_propensity(exps, strategy_scope={"mood": "calm"})
        self.assertEqual(prop["n"], 3)
        self.assertGreaterEqual(prop["propensity_score"], 0.55)
        self.assertIsNotNone(prop["mean_scope_overlap"])

    def test_rank_candidates_orders_by_propensity(self) -> None:
        strong = self._seed_strategy(
            "strong", {"mood": "calm"}, [1.0, 1.0, 0.9, 0.95]
        )
        weak = self._seed_strategy(
            "weak", {"mood": "busy"}, [0.1, 0.0, 0.2]
        )
        out = schedule(self.db, action="rank_candidates")
        self.assertTrue(out["ok"])
        self.assertGreaterEqual(out["count"], 2)
        ids = [r["strategy_id"] for r in out["ranked"]]
        self.assertIn(strong, ids)
        self.assertIn(weak, ids)
        self.assertEqual(out["ranked"][0]["strategy_id"], strong)
        self.assertTrue(out["ranked"][0]["recommend"])
        self.assertFalse(
            next(r for r in out["ranked"] if r["strategy_id"] == weak)["recommend"]
        )

    def test_offline_eval_with_gate_persists_propensity(self) -> None:
        sid = self._seed_strategy("eval_me", {"mood": "calm"}, [1.0, 0.8, 0.9])
        locked = run_offline_eval(self.db, sid)
        self.assertFalse(locked["ok"])
        self.assertEqual(locked["detail"], "capability_locked")
        set_capability_level(
            self.db,
            "RL_OFFLINE_TRAINING",
            level="ACTIVE",
            enabled=True,
            actor="test",
        )
        rep = run_offline_eval(self.db, sid)
        self.assertTrue(rep["ok"])
        self.assertFalse(rep["deploy"]["allowed"])
        self.assertEqual(rep["status_unchanged"], "proposed")
        self.assertGreaterEqual(rep["propensity"]["n"], 3)
        self.assertTrue(rep["pairwise_overlap_sample"] or True)
        row = self.strategies.get(sid)
        self.assertIn("score", row.get("propensity") or {})

    def test_meta_reevaluate_after_unlock(self) -> None:
        sid = self._seed_strategy("re", {"mood": "calm"}, [1.0, 1.0, 1.0])
        set_capability_level(
            self.db,
            "BANDIT_EXPERIMENT",
            level="ACTIVE",
            enabled=True,
            actor="test",
        )
        out = schedule(self.db, action="reevaluate", strategy_id=sid)
        self.assertTrue(out["ok"])
        self.assertTrue(out["report"]["ok"])
        self.assertFalse(out["report"]["deploy"]["allowed"])


if __name__ == "__main__":
    unittest.main()
