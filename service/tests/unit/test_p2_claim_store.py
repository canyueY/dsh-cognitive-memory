# -*- coding: utf-8 -*-
"""P2 Claim vertical slice — store / same_as / lifecycle / redirect."""

from __future__ import annotations

import tempfile
import unittest
from tests.support import seed_evidence
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.storage.db import Database


class ClaimStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        self.store = ClaimStore(self.db)
        seed_evidence(self.db, 'obs_1')
        seed_evidence(self.db, 'obs_v1')

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_propose_preference_and_same_as(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        self.assertTrue(a["ok"])
        self.assertTrue(a.get("persisted"))
        self.assertEqual(a["claim"]["lifecycle"], "proposed")
        self.assertEqual(a["claim"]["verification_status"], "unverified")
        b = self.store.propose_from_text("我喜欢夜航星")
        self.assertTrue(b["ok"])
        self.assertFalse(b.get("persisted"))
        self.assertEqual(b.get("same_as"), a["claim_id"])

    def test_support_then_verified_requires_evidence(self) -> None:
        r = self.store.propose_from_text("主人喜欢听夜航星")
        cid = r["claim_id"]
        denied = self.store.transition(cid, "verified", reason="skip")
        self.assertFalse(denied.get("ok"))
        self.store.attach_evidence(cid, "obs_1", role="support")
        to_sup = self.store.transition(cid, "supported", reason="has evidence")
        self.assertTrue(to_sup.get("ok"))
        still = self.store.transition(cid, "verified", reason="no refs")
        self.assertFalse(still.get("ok"))
        ok = self.store.transition(
            cid, "verified", reason="record", evidence_refs=["obs_1"]
        )
        self.assertTrue(ok.get("ok"))
        self.assertEqual(self.store.get(cid)["lifecycle"], "verified")

    def test_redirect_supersedes(self) -> None:
        a = self.store.propose_from_text("用户喜欢夜航星")
        # force a distinct claim with different surface but then redirect
        b = self.store.propose_from_text("我讨厌下雨")
        self.assertNotEqual(a["claim_id"], b["claim_id"])
        red = self.store.redirect(b["claim_id"], a["claim_id"], reason="merge-test")
        self.assertTrue(red.get("ok"))
        src = self.store.get(b["claim_id"], follow_redirect=False)
        self.assertEqual(src["lifecycle"], "superseded")
        self.assertEqual(src["redirects_to"], a["claim_id"])
        followed = self.store.get(b["claim_id"], follow_redirect=True)
        self.assertEqual(followed["redirect_resolved"]["id"], a["claim_id"])

    def test_unresolved_persisted_without_verified(self) -> None:
        r = self.store.propose_from_text(
            "今天系统定时任务摘要：已完成若干无关事项，天气一般，随便聊聊"
        )
        self.assertTrue(r["ok"])
        self.assertTrue(r.get("unresolved") or r["claim"]["ast"]["root"]["kind"] == "unresolved")
        self.assertEqual(r["claim"]["verification_status"], "unverified")

    def test_submit_verified_persists_record(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星")
        cid = r["claim_id"]
        denied = self.store.submit_verified(
            cid, evidence_refs=[], actor="u1", authorized=True
        )
        self.assertFalse(denied.get("ok"))
        ok = self.store.submit_verified(
            cid, evidence_refs=["obs_v1"], actor="u1"
        )
        self.assertTrue(ok.get("ok"))
        self.assertEqual(ok["claim"]["lifecycle"], "verified")
        self.assertEqual(ok["claim"]["verification_status"], "verified")
        latest = self.store._ver_store.latest_for_claim(cid)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.status.value, "verified")
        self.assertIn("obs_v1", latest.evidence_refs)


if __name__ == "__main__":
    unittest.main()
