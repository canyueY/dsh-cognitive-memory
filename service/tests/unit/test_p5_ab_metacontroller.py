# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.governance.ab_experiment import (
    SEMANTIC_ASSIST_EXPERIMENT,
    assign_arm,
    record_outcome,
    report,
    resolve_semantic_assist_arm,
)
from cognitive_memory.governance.capability_gate import set_capability_level
from cognitive_memory.storage.db import Database
from cognitive_memory.strategy.experience_store import ExperienceStore
from cognitive_memory.strategy.metacontroller import schedule
from cognitive_memory.strategy.strategy_store import StrategyStore


class P5AbMetaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def _unlock_bandit(self) -> None:
        set_capability_level(
            self.db,
            "BANDIT_EXPERIMENT",
            level="ACTIVE",
            enabled=True,
            actor="test",
        )

    def test_ab_locked_by_default(self) -> None:
        out = assign_arm(self.db, SEMANTIC_ASSIST_EXPERIMENT, subject_key="u1")
        self.assertFalse(out["ok"])
        self.assertEqual(out["detail"], "capability_locked")
        rep = report(self.db, SEMANTIC_ASSIST_EXPERIMENT)
        self.assertFalse(rep["ok"])

    def test_ab_assign_outcome_report(self) -> None:
        self._unlock_bandit()
        a = assign_arm(self.db, SEMANTIC_ASSIST_EXPERIMENT, subject_key="user-a")
        self.assertTrue(a["ok"])
        self.assertIn(a["arm"], {"control", "treatment"})
        # same subject → same arm
        b = assign_arm(self.db, SEMANTIC_ASSIST_EXPERIMENT, subject_key="user-a")
        self.assertEqual(a["arm"], b["arm"])
        oc = record_outcome(self.db, a["exposure_id"], reward=1.0, label="used")
        self.assertTrue(oc["ok"])
        rep = report(self.db, SEMANTIC_ASSIST_EXPERIMENT)
        self.assertTrue(rep["ok"])
        self.assertFalse(rep["deploy"]["allowed"])
        self.assertIn(a["arm"], rep["arms"])

    def test_resolve_semantic_assist_arm(self) -> None:
        off = resolve_semantic_assist_arm(self.db, enabled=False)
        self.assertTrue(off["ok"])
        self.assertFalse(off["active"])
        locked = resolve_semantic_assist_arm(self.db, enabled=True, subject_key="x")
        self.assertFalse(locked.get("active"))
        self._unlock_bandit()
        on = resolve_semantic_assist_arm(
            self.db, enabled=True, subject_key="x", query="hello"
        )
        self.assertTrue(on["active"])
        self.assertIsInstance(on["override"], bool)

    def test_meta_recommend_and_retire(self) -> None:
        store = StrategyStore(self.db)
        exps = ExperienceStore(self.db)
        sid = store.propose("calm_night", scope={"mood": "calm"})["strategy"]["id"]
        for r in (1.0, 1.0, 0.8):
            e = exps.create(context={"mood": "calm"}, reward=r)
            store.log(sid, experience_id=e["id"], decision="play", outcome="ok")
        rec = schedule(self.db, action="recommend_activate", strategy_id=sid)
        self.assertTrue(rec["ok"])
        self.assertTrue(rec["recommend"])
        # still not active
        self.assertEqual(store.get(sid)["status"], "proposed")
        act = schedule(self.db, action="activate_if_authorized", strategy_id=sid)
        self.assertFalse(act["ok"])
        self.assertEqual(act["detail"], "capability_locked")
        retired = schedule(self.db, action="propose_retire", strategy_id=sid)
        self.assertTrue(retired["ok"])
        self.assertEqual(store.get(sid)["status"], "retired")

    def test_meta_reevaluate_all_locked(self) -> None:
        StrategyStore(self.db).propose("s")
        out = schedule(self.db, action="reevaluate_all")
        self.assertTrue(out["ok"])
        self.assertEqual(out["evaluated_ok"], 0)

    def test_migration_013(self) -> None:
        with self.db.transaction() as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertIn("ab_exposures", names)
        self.assertIn("ab_outcomes", names)


if __name__ == "__main__":
    unittest.main()
