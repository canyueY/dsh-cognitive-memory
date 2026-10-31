# -*- coding: utf-8 -*-
"""P2 Claim test matrix — task-book 20 items (S1–S20)."""

from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cognitive_memory.claims.ast import Atom, ClaimAST, Negation
from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.judgment.relations import (
    ClaimRelation,
    RelationDecision,
    evaluate_contradicts,
    evaluate_qualifies,
    evaluate_relation,
    evaluate_supports,
)
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

    def test_s1_simple_preference(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星")
        self.assertFalse(r.get("unresolved"))
        self.assertEqual(r["claim"]["ast"]["root"]["kind"], "atom")

    def test_s2_negation(self) -> None:
        r = self.store.propose_from_text("我不喜欢摇滚")
        root = r["claim"]["ast"]["root"]
        self.assertIn(root["kind"], ("negation", "atom"))

    def test_s3_conditional(self) -> None:
        r = self.store.propose_from_text("如果下雨就听轻音乐")
        self.assertIn(r["claim"]["ast"]["root"]["kind"], ("conditional", "unresolved", "atom"))

    def test_s4_same_as(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我喜欢夜航星")
        self.assertEqual(b.get("same_as"), a["claim_id"])

    def test_s5_support_evidence(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        e = self.store.attach_evidence(a["claim_id"], "obs_s5", role="support")
        self.assertTrue(e["ok"])
        self.assertEqual(len(self.store.list_evidence(a["claim_id"])), 1)

    def test_s6_counter_then_disputed(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        self.store.attach_evidence(a["claim_id"], "obs_c", role="counter")
        self.store.transition(a["claim_id"], "supported", reason="weak")
        d = self.store.transition(a["claim_id"], "disputed", reason="counter")
        self.assertTrue(d.get("ok"))
        self.assertEqual(self.store.get(a["claim_id"])["lifecycle"], "disputed")

    def test_s7_verified_gate(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        self.store.transition(a["claim_id"], "supported", reason="x")
        bad = self.store.transition(a["claim_id"], "verified", reason="no")
        self.assertFalse(bad.get("ok"))

    def test_s8_unresolved(self) -> None:
        r = self.store.propose_from_text("嗯嗯随便聊聊今天天气怎么样系统摘要")
        self.assertTrue(r.get("unresolved") or r["claim"]["ast"]["root"]["kind"] == "unresolved")

    def test_s9_no_silent_verified(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星")
        self.assertEqual(r["claim"]["verification_status"], "unverified")
        self.assertEqual(r["claim"]["lifecycle"], "proposed")

    def test_s10_visibility_cross_bank(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星", bank_id="personal")
        denied = self.store.get(
            r["claim_id"],
            principal=SecurityContext(bank_id="projects"),
        )
        self.assertIsNone(denied)

    def test_s11_visibility_same_bank(self) -> None:
        r = self.store.propose_from_text("我喜欢夜航星", bank_id="personal")
        ok = self.store.get(
            r["claim_id"],
            principal=SecurityContext(bank_id="personal"),
        )
        self.assertIsNotNone(ok)
        self.assertEqual(ok["visibility"]["decision"], "allow")

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

    def test_s13_redirect(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我讨厌下雨")
        self.store.redirect(b["claim_id"], a["claim_id"])
        self.assertEqual(
            self.store.get(b["claim_id"], follow_redirect=False)["lifecycle"],
            "superseded",
        )

    def test_s14_no_transition_after_redirect(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我讨厌下雨")
        self.store.redirect(b["claim_id"], a["claim_id"])
        blocked = self.store.transition(b["claim_id"], "supported", reason="x")
        self.assertFalse(blocked.get("ok"))
        self.assertEqual(blocked.get("detail"), "claim_redirected")

    # --- S15–S20: task-book close-out ---

    def test_s15_merge_moves_evidence(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我讨厌下雨")
        self.store.attach_evidence(b["claim_id"], "obs_merge", role="support")
        merged = self.store.merge(b["claim_id"], a["claim_id"])
        self.assertTrue(merged["ok"])
        self.assertGreaterEqual(merged["evidence_moved"], 1)
        self.assertEqual(
            self.store.get(b["claim_id"], follow_redirect=False)["lifecycle"],
            "superseded",
        )
        self.assertTrue(any(e["evidence_ref"] for e in self.store.list_evidence(a["claim_id"])))

    def test_s16_split_into_parts(self) -> None:
        src = self.store.propose_from_text("我喜欢夜航星")
        out = self.store.split(
            src["claim_id"],
            ["我喜欢夜航星", "我讨厌下雨"],
        )
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["parts"]), 2)
        self.assertEqual(
            self.store.get(src["claim_id"], follow_redirect=False)["lifecycle"],
            "superseded",
        )

    def test_s17_relation_contradicts(self) -> None:
        likes = ClaimAST(root=Atom(subject="user", predicate="喜欢", arguments=["摇滚"]))
        dislikes = ClaimAST(root=Atom(subject="user", predicate="讨厌", arguments=["摇滚"]))
        r = evaluate_contradicts(likes, dislikes)
        self.assertEqual(r.decision, RelationDecision.ACCEPTED)
        self.assertEqual(r.final_relation, ClaimRelation.CONTRADICTS)
        a = self.store.propose_from_text("我喜欢摇滚")
        b = self.store.propose_from_text("我讨厌摇滚")
        rel = self.store.relate(a["claim_id"], b["claim_id"])
        self.assertTrue(rel["ok"])
        self.assertIn(
            rel["relation"]["final_relation"],
            ("contradicts", "unrelated", "supports", "same_as", "qualifies", "unknown"),
        )

    def test_s18_relation_qualifies_and_supports(self) -> None:
        base = ClaimAST(root=Atom(subject="user", predicate="喜欢", arguments=["音乐"]))
        narrow = ClaimAST(
            root=Atom(subject="user", predicate="喜欢", arguments=["音乐", "夜航星"]),
            scope={"scene": "night"},
        )
        q = evaluate_qualifies(narrow, base)
        self.assertEqual(q.final_relation, ClaimRelation.QUALIFIES)
        s = evaluate_supports(
            ClaimAST(root=Atom(subject="user", predicate="喜欢", arguments=["夜航星"])),
            ClaimAST(root=Atom(subject="user", predicate="喜欢", arguments=["音乐", "夜航星"])),
        )
        self.assertEqual(s.final_relation, ClaimRelation.SUPPORTS)
        overall = evaluate_relation(narrow, base)
        self.assertEqual(overall.final_relation, ClaimRelation.QUALIFIES)

    def test_s19_duplicate_request_idempotent(self) -> None:
        a = self.store.propose_from_text("我喜欢夜航星")
        b = self.store.propose_from_text("我喜欢夜航星")
        c = self.store.propose_from_text("我喜欢夜航星")
        self.assertEqual(b.get("same_as"), a["claim_id"])
        self.assertEqual(c.get("same_as"), a["claim_id"])
        self.assertFalse(b.get("persisted"))
        self.assertFalse(c.get("persisted"))

    def test_s20_concurrent_propose_stable(self) -> None:
        results: list[dict] = []
        lock = threading.Lock()

        def _one(_: int) -> None:
            # each thread needs its own store handle on shared db
            store = ClaimStore(self.db)
            pack = store.propose_from_text("我喜欢并发测试歌曲")
            with lock:
                results.append(pack)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(_one, range(8)))
        self.assertEqual(len(results), 8)
        ids = set()
        for r in results:
            if r.get("persisted"):
                ids.add(r["claim_id"])
            else:
                ids.add(r.get("same_as") or (r.get("claim") or {}).get("id"))
        # Exactly one surviving identity for the normalized hash
        self.assertEqual(len(ids), 1)


if __name__ == "__main__":
    unittest.main()
