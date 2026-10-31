# -*- coding: utf-8 -*-
"""Task-book P7: invariant → earliest → diff → min repro → root → repair validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.fault.invariants import check_claim_invariants
from cognitive_memory.fault.pipeline import run_fault_pipeline
from cognitive_memory.storage.db import Database


class P7FaultPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        self.store = ClaimStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_no_violation_short_circuits(self) -> None:
        c = self.store.propose_from_text("我喜欢夜航星")
        out = run_fault_pipeline(self.db, claim_id=c["claim_id"])
        self.assertTrue(out["ok"])
        self.assertEqual(out["detail"], "no_invariant_violation")

    def test_redirect_without_tombstone_localized_and_repaired(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我讨厌下雨")
        # Inject bad state: redirects_to set but lifecycle still proposed
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE claims SET redirects_to=? WHERE id=?",
                (a["claim_id"], b["claim_id"]),
            )
        bad = self.store.get(b["claim_id"], follow_redirect=False)
        inv = check_claim_invariants(bad, evidence_n=0)
        self.assertFalse(inv["ok"])
        self.assertEqual(inv["violations"][0]["code"], "redirect_without_tombstone")

        def repair() -> dict:
            return self.store.redirect(
                b["claim_id"], a["claim_id"], reason="fault_repair_tombstone"
            )

        out = run_fault_pipeline(
            self.db,
            claim_id=b["claim_id"],
            patch_fn=repair,
            run_regression=True,
        )
        self.assertTrue(out["ok"])
        self.assertTrue(out["fault_id"])
        stages = {s["stage"] for s in out["fault"]["stages"]}
        for need in (
            "invariant_violation",
            "earliest_deviation",
            "differential_trace",
            "minimal_reproduction",
            "candidate_root_cause",
            "patch",
            "targeted_test",
            "regression_test",
            "historical_replay",
            "rollback_test",
            "governance",
        ):
            self.assertIn(need, stages)
        fixed = self.store.get(b["claim_id"], follow_redirect=False)
        self.assertEqual(fixed["lifecycle"], "superseded")
        self.assertEqual(out["fault"]["status"], "validated")

    def test_migration_015_tables(self) -> None:
        with self.db.transaction() as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertIn("fault_cases", names)
        self.assertIn("fault_stages", names)


if __name__ == "__main__":
    unittest.main()
