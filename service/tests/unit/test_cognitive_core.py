# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.core.service import ConflictError, MemoryService
from cognitive_memory.domain.models import (
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SearchQuery,
    SourceKind,
)
from cognitive_memory.evidence import EvidenceAttachIn, EvidenceKind, ValidationState
from cognitive_memory.events.bus import EventBus
from cognitive_memory.governance.authority import (
    AuthorityState,
    ensure_authority_row,
)
from cognitive_memory.identity import ensure_default_principals
from cognitive_memory.memory.banks import ensure_default_banks
from cognitive_memory.storage.db import Database


class CognitiveCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        ensure_default_principals(self.db)
        ensure_default_banks(self.db)
        ensure_authority_row(self.db)
        self.svc = MemoryService(self.db, EventBus())

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_evidence_attach_has_provenance(self) -> None:
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.USER_STATEMENT,
                content="主人说讨厌香菜",
                producer="test",
            )
        )
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                content="讨厌香菜",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.CANDIDATE,
                source_ids=[obs.id],
            )
        )
        rec = self.svc.attach_evidence(
            EvidenceAttachIn(
                memory_id=mem.id,
                observation_id=obs.id,
                relation="supports",
                confidence=0.9,
                evidence_kind=EvidenceKind.OBSERVATION,
                validation_state=ValidationState.SUPPORTS,
                producer="test",
                metadata={"channel": "unit"},
            )
        )
        self.assertEqual(rec["provenance"]["observation_id"], obs.id)
        self.assertEqual(rec["confidence"], 0.9)
        listed = self.svc.list_evidence(mem.id)
        self.assertTrue(any(e["observation_id"] == obs.id for e in listed))
        got = self.svc.get_memory(mem.id, include_evidence=True)
        self.assertTrue(got["evidence"])
        self.assertIn("provenance", got["evidence"][0])

    def test_bank_isolation_shared_not_in_personal_search(self) -> None:
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.SYSTEM,
                content="共享知识：滑板技巧",
                producer="test",
            )
        )
        shared = self.svc.propose_memory(
            MemoryProposeIn(
                content="滑板技巧：重心前移",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                source_ids=[obs.id],
                bank_id="shared",
            )
        )
        self.assertEqual(shared.bank_id, "shared")
        personal_hits = self.svc.search(SearchQuery(query="滑板技巧", limit=20))
        self.assertFalse(any(m.id == shared.id for m in personal_hits))
        shared_hits = self.svc.search(
            SearchQuery(query="滑板技巧", banks=["shared"], limit=20)
        )
        self.assertTrue(any(m.id == shared.id for m in shared_hits))
        banks = {b["id"] for b in self.svc.list_banks()}
        self.assertIn("personal", banks)
        self.assertIn("shared", banks)

    def test_authority_state_machine(self) -> None:
        st = self.svc.get_authority()
        self.assertEqual(st["state"], AuthorityState.MNEMOSYNE_PRIMARY.value)
        with self.assertRaises(ConflictError):
            self.svc.transition_authority("dual_sync", allow_dual=False)
        dual = self.svc.transition_authority(
            "dual_sync", allow_dual=True, reason="explicit test"
        )
        self.assertEqual(dual["state"], "dual_sync")
        back = self.svc.transition_authority("mnemosyne_primary", reason="back")
        self.assertEqual(back["state"], "mnemosyne_primary")
        contract = self.svc.service_contract()
        self.assertFalse(contract["adapter_may_bypass_service"])
        self.assertIn("attach_evidence", contract["operations"])


if __name__ == "__main__":
    unittest.main()
