# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.cognition.metacognition import analyze_impact
from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.evidence.object_store import EvidenceObjectStore
from cognitive_memory.storage.db import Database
from cognitive_memory.tms.models import BeliefStatus


class SchemaTmsImpactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_analyze_impact_uses_tms(self) -> None:
        sid = self.svc.store_cognitive_schema(
            {
                "name": "风格",
                "type": "BEHAVIORAL",
                "state": "ACTIVE",
                "confidence": 0.5,
                "evidence": {"supporting": ["m1"], "counter": []},
                "relations": {"dependsOn": []},
                "network_links": [],
            }
        )
        child = self.svc.store_cognitive_schema(
            {
                "name": "子风格",
                "type": "BEHAVIORAL",
                "state": "VALIDATING",
                "confidence": 0.4,
                "evidence": {"supporting": [], "counter": []},
                "network_links": [{"relation": "SPLIT_FROM", "target_id": sid}],
            }
        )
        # parent points to child
        self.svc.update_cognitive_schema(
            sid,
            patch={
                "network_links": [{"relation": "SPLIT_INTO", "target_id": child}],
                "relations": {"specializes": [child]},
            },
        )
        pack = analyze_impact(self.svc, sid)
        self.assertTrue(pack.get("ok"))
        self.assertIn("seed_belief", pack)
        self.assertIn("tms_impact", pack)
        self.assertTrue(any(a.get("action") == "reevaluate" for a in pack.get("affected") or []))
        self.assertTrue(all(a.get("auto_overwrite") is False for a in pack.get("affected") or []))


class TombstoneCascadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())
        self.claims = ClaimStore(self.db)
        self.estore = EvidenceObjectStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_forget_cascades_claim_and_evidence(self) -> None:
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                content="我喜欢夜航星",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        prop = self.claims.propose_from_text(
            "我喜欢夜航星", source_memory_id=mem.id
        )
        cid = prop["claim_id"]
        self.claims.submit_verified(cid, evidence_refs=["obs_x"], actor="u")
        self.estore.from_legacy_memory_link(
            memory_id=mem.id, observation_id="obs_x", relation="supports"
        )
        out = self.svc.forget_memory(mem.id, hard=False)
        self.assertEqual(out.get("status"), MemoryStatus.INVALIDATED.value)
        cascade = out.get("cascade") or {}
        self.assertTrue(cascade.get("ok"))
        self.assertTrue(cascade.get("claims_superseded"))
        claim = self.claims.get(cid, follow_redirect=False)
        self.assertEqual(claim["lifecycle"], "superseded")
        self.assertEqual(claim["verification_status"], "unverified")
        # Belief persisted OUT even if another TmsStore instance ran cascade
        self.assertEqual(self.claims.tms.get_belief(cid).status, BeliefStatus.OUT)
        # claim row still exists (tombstone, not hard-deleted)
        self.assertIsNotNone(claim)


if __name__ == "__main__":
    unittest.main()
