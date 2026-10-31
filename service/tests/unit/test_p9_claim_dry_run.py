# -*- coding: utf-8 -*-
"""P9 provenance-gated Claim migration dry-run (read-only; no production writes)."""

from __future__ import annotations

import unittest

from cognitive_memory.migration.claim_dry_run import (
    assert_write_allowed,
    plan_claim_migration_dry_run,
)


class P9ClaimDryRunTests(unittest.TestCase):
    def test_zero_provenance_blocks_writes(self) -> None:
        samples = [
            {
                "id": "m1",
                "content": "我喜欢夜航星",
                "evidence_count": 0,
                "bank_id": "personal",
            },
            {
                "id": "m2",
                "content": "随便聊聊今天天气",
                "evidence_count": 0,
                "bank_id": "personal",
            },
        ]
        plan = plan_claim_migration_dry_run(samples)
        self.assertTrue(plan.write_blocked)
        self.assertEqual(plan.provenance_complete_rate, 0.0)
        self.assertIn("provenance_complete_rate", plan.block_reason)
        body = plan.to_dict()
        self.assertFalse(body["allow_write"])
        self.assertEqual(body["note"], "dry_run_only; no Claim/Memory writes performed")
        for action in plan.actions:
            self.assertTrue(action["forbid_verified"])
            self.assertEqual(
                action["decision"]["verification_if_written"], "unverified"
            )
            self.assertNotEqual(action["decision"]["lifecycle_if_written"], "verified")
        guard = assert_write_allowed(plan)
        self.assertFalse(guard["ok"])
        self.assertTrue(guard["blocked"])
        self.assertEqual(guard["written"], 0)

    def test_partial_links_still_hold(self) -> None:
        samples = [
            {
                "id": "m3",
                "content": "我喜欢夜航星",
                "evidence_count": 2,
                "validation_states": "unverified",
                "bank_id": "personal",
            }
        ]
        plan = plan_claim_migration_dry_run(samples)
        self.assertTrue(plan.write_blocked)
        self.assertEqual(plan.actions[0]["decision"]["action"], "hold_unresolved")
        self.assertTrue(plan.actions[0]["decision"]["requires_manual_review"])


if __name__ == "__main__":
    unittest.main()
