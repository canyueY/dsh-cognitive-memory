# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.evidence.object_store import EvidenceObjectStore
from cognitive_memory.storage.db import Database


class EvidenceObjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        self.estore = EvidenceObjectStore(self.db)
        self.claims = ClaimStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_create_partial_never_complete_without_chain_audit(self) -> None:
        r = self.estore.create_from_observation("obs_a", content="hello")
        self.assertTrue(r["ok"])
        self.assertEqual(r["evidence"]["provenance_status"], "partial")
        self.assertNotEqual(r["evidence"]["provenance_status"], "complete")

    def test_no_source_is_unknown(self) -> None:
        r = self.estore.create(source_type="unknown", source_ref="")
        self.assertEqual(r["evidence"]["provenance_status"], "unknown")

    def test_fingerprint_dedupe(self) -> None:
        a = self.estore.create_from_observation("obs_dup", content="x")
        b = self.estore.create_from_observation("obs_dup", content="x")
        self.assertTrue(b.get("deduped"))
        self.assertEqual(a["evidence"]["id"], b["evidence"]["id"])

    def test_independence_collision(self) -> None:
        a = self.estore.create_from_observation("obs_1", producer="p")
        # same producer+root → same independence key family when same root
        b = self.estore.create(
            source_type="observation",
            source_ref="obs_1_alias",
            producer="p",
            root_source_id="obs_1",
            content_for_fingerprint="different",
        )
        # Force same independence key by matching create params
        a_key = a["evidence"]["independence_key"]
        # create second with identical independence inputs
        c = self.estore.create(
            source_type="observation",
            source_ref="obs_other",
            producer="p",
            root_source_id="obs_1",
            content_for_fingerprint="zz",
        )
        check = self.estore.independence_conflict(
            [a["evidence"]["id"], c["evidence"]["id"]]
        )
        self.assertEqual(a_key, c["evidence"]["independence_key"])
        self.assertFalse(check["independent"])
        _ = b

    def test_claim_attach_materializes_evidence_object(self) -> None:
        prop = self.claims.propose_from_text("我喜欢夜航星")
        link = self.claims.attach_evidence(prop["claim_id"], "obs_live_1")
        self.assertTrue(link["ok"])
        self.assertTrue(str(link["evidence_ref"]).startswith("evd_"))
        self.assertIsNotNone(link.get("trace_id"))
        ev = self.estore.get(link["evidence_ref"])
        self.assertIsNotNone(ev)
        self.assertEqual(ev["source_ref"], "obs_live_1")

    def test_claim_propose_emits_trace(self) -> None:
        r = self.claims.propose_from_text("我喜欢夜航星")
        self.assertTrue(r.get("trace_id"))
        self.assertGreaterEqual(len(self.claims.traces.list_traces()), 1)

    def test_legacy_missing_observation_unknown(self) -> None:
        r = self.estore.from_legacy_memory_link(
            memory_id="mem_1", observation_id="", relation="supports"
        )
        self.assertEqual(r["evidence"]["provenance_status"], "unknown")

    def test_verify_blocks_correlated_evidence(self) -> None:
        prop = self.claims.propose_from_text("我喜欢夜航星")
        cid = prop["claim_id"]
        # Two refs sharing root → same independence_key after materialize
        a = self.estore.create(
            source_type="test_fixture",
            source_ref="obs_x1",
            validation_state="valid", provenance_status="complete",
            chain=[{"step":"fixture","ref":"obs_x1"}],
            producer="same",
            root_source_id="root_r",
            content_for_fingerprint="a",
        )
        b = self.estore.create(
            source_type="test_fixture",
            source_ref="obs_x2",
            validation_state="valid", provenance_status="complete",
            chain=[{"step":"fixture","ref":"obs_x2"}],
            producer="same",
            root_source_id="root_r",
            content_for_fingerprint="b",
        )
        blocked = self.claims.submit_verified(
            cid,
            evidence_refs=[a["evidence"]["id"], b["evidence"]["id"]],
            actor="u",
        )
        self.assertFalse(blocked.get("ok"))
        self.assertEqual(blocked.get("detail"), "evidence_not_independent")


if __name__ == "__main__":
    unittest.main()
