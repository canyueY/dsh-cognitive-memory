# -*- coding: utf-8 -*-
"""Task-book P7: invariant → earliest → diff → min repro → root → repair validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.fault.inject import (
    inject_redirect_without_tombstone,
    inject_silent_verified_on_proposed,
    inject_verified_status_lifecycle_mismatch,
    inject_verified_without_evidence,
)
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

    def _assert_full_stages(self, out: dict) -> None:
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

    def test_no_violation_short_circuits(self) -> None:
        c = self.store.propose_from_text("我喜欢夜航星")
        out = run_fault_pipeline(self.db, claim_id=c["claim_id"])
        self.assertTrue(out["ok"])
        self.assertEqual(out["detail"], "no_invariant_violation")

    def test_redirect_without_tombstone_localized_and_repaired(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我讨厌下雨")
        inject_redirect_without_tombstone(
            self.db, claim_id=b["claim_id"], redirects_to=a["claim_id"]
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
        self._assert_full_stages(out)
        fixed = self.store.get(b["claim_id"], follow_redirect=False)
        self.assertEqual(fixed["lifecycle"], "superseded")
        self.assertEqual(out["fault"]["status"], "validated")

    def test_inject_verified_without_evidence_auto_repair(self) -> None:
        c = self.store.propose_from_text("我喜欢夜航星")
        inject_verified_without_evidence(self.db, claim_id=c["claim_id"])
        inv = check_claim_invariants(
            self.store.get(c["claim_id"], follow_redirect=False), evidence_n=0
        )
        self.assertEqual(inv["violations"][0]["code"], "verified_without_evidence")
        out = run_fault_pipeline(
            self.db, claim_id=c["claim_id"], auto_repair=True, run_regression=True
        )
        self._assert_full_stages(out)
        fixed = self.store.get(c["claim_id"], follow_redirect=False)
        self.assertEqual(fixed["lifecycle"], "proposed")
        self.assertNotEqual(fixed["verification_status"], "verified")
        self.assertEqual(out["fault"]["status"], "validated")

    def test_inject_silent_verified_on_proposed_auto_repair(self) -> None:
        c = self.store.propose_from_text("我讨厌下雨")
        inject_silent_verified_on_proposed(self.db, claim_id=c["claim_id"])
        inv = check_claim_invariants(
            self.store.get(c["claim_id"], follow_redirect=False), evidence_n=0
        )
        self.assertEqual(inv["violations"][0]["code"], "silent_verified_on_proposed")
        out = run_fault_pipeline(
            self.db, claim_id=c["claim_id"], auto_repair=True, run_regression=True
        )
        self._assert_full_stages(out)
        fixed = self.store.get(c["claim_id"], follow_redirect=False)
        self.assertEqual(fixed["lifecycle"], "proposed")
        self.assertEqual(fixed["verification_status"], "unverified")
        self.assertEqual(out["fault"]["status"], "validated")

    def test_inject_lifecycle_mismatch_auto_repair(self) -> None:
        c = self.store.propose_from_text("我喜欢夜航星")
        inject_verified_status_lifecycle_mismatch(self.db, claim_id=c["claim_id"])
        inv = check_claim_invariants(
            self.store.get(c["claim_id"], follow_redirect=False), evidence_n=0
        )
        codes = {v["code"] for v in inv["violations"]}
        self.assertIn("verified_status_lifecycle_mismatch", codes)
        out = run_fault_pipeline(
            self.db, claim_id=c["claim_id"], auto_repair=True, run_regression=True
        )
        self._assert_full_stages(out)
        fixed = self.store.get(c["claim_id"], follow_redirect=False)
        self.assertNotEqual(fixed["verification_status"], "verified")
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
