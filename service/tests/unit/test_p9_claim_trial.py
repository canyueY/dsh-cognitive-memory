# -*- coding: utf-8 -*-
"""P9 scratch trial migration + rollback (never production)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.migration.claim_trial import (
    build_synthetic_complete_samples,
    run_scratch_trial,
)


class P9ClaimTrialTests(unittest.TestCase):
    def test_zero_complete_blocks_scratch_write(self) -> None:
        samples = [
            {"id": "m1", "content": "我喜欢夜航星", "evidence_count": 0},
            {"id": "m2", "content": "今天天气不错", "evidence_count": 0},
        ]
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            out = run_scratch_trial(
                samples,
                scratch_db_path=Path(td) / "scratch.db",
                apply_writes=True,
                rollback=True,
            )
        self.assertTrue(out["plan"]["write_blocked"])
        self.assertFalse(out["applied"])
        self.assertEqual(out["written_claim_ids"], [])

    def test_synthetic_complete_writes_then_rolls_back(self) -> None:
        samples = build_synthetic_complete_samples(3)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            path = Path(td) / "scratch.db"
            out = run_scratch_trial(
                samples,
                scratch_db_path=path,
                apply_writes=True,
                rollback=True,
            )
            self.assertFalse(out["plan"]["write_blocked"])
            self.assertGreater(out["plan"]["provenance_complete_rate"], 0.5)
            self.assertTrue(out["applied"])
            self.assertTrue(out["written_claim_ids"])
            self.assertTrue(out["consistency"]["ok"])
            self.assertTrue(out["rolled_back"])
            self.assertTrue(out["rollback_ok"])
            for a in out["plan"]["actions"]:
                self.assertTrue(a["forbid_verified"])
                self.assertEqual(
                    a["decision"]["verification_if_written"], "unverified"
                )


if __name__ == "__main__":
    unittest.main()
