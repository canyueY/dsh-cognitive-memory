# -*- coding: utf-8 -*-
"""P2 Claim test matrix (S1–S14 starter). Expand until full acceptance."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.security.context import SecurityContext
from cognitive_memory.storage.db import Database


class ClaimMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        self.store = ClaimStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    # S1 simple preference / fact-ish atom
    def test_s1_simple_preference(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星")
        self.assertFalse(r.get("unresolved"))
        self.assertEqual(r["claim"]["ast"]["root"]["kind"], "atom")

    # S2 negation
    def test_s2_negation(self) -> None:
        r = self.store.propose_from_text("我不喜欢摇滚")
        root = r["claim"]["ast"]["root"]
        self.assertIn(root["kind"], ("negation", "atom"))

    # S3 conditional
    def test_s3_conditional(self) -> None:
        r = self.store.propose_from_text("如果下雨就听轻音乐")
        self.assertIn(r["claim"]["ast"]["root"]["kind"], ("conditional", "unresolved", "atom"))

    # S4 duplicate / same_as
    def test_s4_same_as(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我喜欢夜航星")
        self.assertEqual(b.get("same_as"), a["claim_id"])

    # S5 support evidence
    def test_s5_support_evidence(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        e = self.store.attach_evidence(a["claim_id"], "obs_s5", role="support")
        self.assertTrue(e["ok"])
        self.assertEqual(len(self.store.list_evidence(a["claim_id"])), 1)

    # S6 counterevidence → disputed path available
    def test_s6_counter_then_disputed(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        self.store.attach_evidence(a["claim_id"], "obs_c", role="counter")
        self.store.transition(a["claim_id"], "supported", reason="weak")
        d = self.store.transition(a["claim_id"], "disputed", reason="counter")
        self.assertTrue(d.get("ok"))
        self.assertEqual(self.store.get(a["claim_id"])["lifecycle"], "disputed")

    # S7 verified requires evidence refs
    def test_s7_verified_gate(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        self.store.transition(a["claim_id"], "supported", reason="x")
        bad = self.store.transition(a["claim_id"], "verified", reason="no")
        self.assertFalse(bad.get("ok"))

    # S8 unresolved noise
    def test_s8_unresolved(self) -> None:
        r = self.store.propose_from_text("嗯嗯随便聊聊今天天气怎么样系统摘要")
        self.assertTrue(r.get("unresolved") or r["claim"]["ast"]["root"]["kind"] == "unresolved")

    # S9 never silent verified on propose
    def test_s9_no_silent_verified(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星")
        self.assertEqual(r["claim"]["verification_status"], "unverified")
        self.assertEqual(r["claim"]["lifecycle"], "proposed")

    # S10 cross-bank visibility deny (no existence)
    def test_s10_visibility_cross_bank(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星", bank_id="personal")
        denied = self.store.get(
            r["claim_id"],
            principal=SecurityContext(bank_id="projects"),
        )
        self.assertIsNone(denied)

    # S11 same-bank visibility allow
    def test_s11_visibility_same_bank(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星", bank_id="personal")
        ok = self.store.get(
            r["claim_id"],
            principal=SecurityContext(bank_id="personal"),
        )
        self.assertIsNotNone(ok)
        self.assertEqual(ok["visibility"]["decision"], "allow")

    # S12 evidence invisible blocks verification_status field
    def test_s12_evidence_invisible_partial(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星", bank_id="personal")
        pack = self.store.get(
            r["claim_id"],
            principal=SecurityContext(bank_id="personal"),
            evidence_visible=False,
        )
        self.assertIsNotNone(pack)
        self.assertEqual(pack["visibility"]["decision"], "partial")
        self.assertNotIn("verification_status", pack)

    # S13 redirect / merge
    def test_s13_redirect(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我讨厌下雨")
        self.store.redirect(b["claim_id"], a["claim_id"])
        self.assertEqual(
            self.store.get(b["claim_id"], follow_redirect=False)["lifecycle"],
            "superseded",
        )

    # S14 transition after redirect blocked
    def test_s14_no_transition_after_redirect(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我讨厌下雨")
        self.store.redirect(b["claim_id"], a["claim_id"])
        blocked = self.store.transition(b["claim_id"], "supported", reason="x")
        self.assertFalse(blocked.get("ok"))
        self.assertEqual(blocked.get("detail"), "claim_redirected")


if __name__ == "__main__":
    unittest.main()
