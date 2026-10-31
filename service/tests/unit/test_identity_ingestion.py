# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import (
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SourceKind,
)
from cognitive_memory.events.bus import EventBus
from cognitive_memory.identity import ensure_default_principals, list_principals
from cognitive_memory.ingestion import coerce_long_term_status, ingest_observation
from cognitive_memory.storage.db import Database


class IdentityIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.db.ensure_schema()
        ensure_default_principals(self.db)
        self.svc = MemoryService(self.db, EventBus())

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_default_principals_seeded(self) -> None:
        items = list_principals(self.db)
        kinds = {p.kind.value for p in items}
        ids = {p.id for p in items}
        self.assertIn("node", kinds)
        self.assertIn("user", kinds)
        self.assertIn("agent", kinds)
        self.assertIn("local-node", ids)
        self.assertIn("user:local", ids)
        self.assertGreaterEqual(self.svc.health().get("principals", 0), 4)

    def test_ingest_attaches_identity(self) -> None:
        obs = ingest_observation(
            self.svc,
            ObservationIn(
                source_kind=SourceKind.DIALOG,
                content="你好",
                producer="dsh",
            ),
        )
        ident = (obs.metadata or {}).get("identity") or {}
        self.assertEqual(ident.get("agent_id"), "agent:dsh")
        self.assertEqual(ident.get("subject_id"), "user:local")
        self.assertEqual(ident.get("node_id"), "local-node")

    def test_long_term_active_without_sources_coerced(self) -> None:
        status, meta = coerce_long_term_status(
            memory_type="semantic",
            status="active",
            source_ids=[],
            metadata={},
        )
        self.assertEqual(status, "candidate")
        self.assertIn("promotion_guard", meta)

        mem = self.svc.propose_memory(
            MemoryProposeIn(
                type=MemoryType.SEMANTIC,
                content="无证据长期记忆",
                status=MemoryStatus.ACTIVE,
                source_ids=[],
            )
        )
        self.assertEqual(mem.status, MemoryStatus.CANDIDATE)
        self.assertIn("promotion_guard", mem.metadata)

    def test_long_term_active_with_observation_ok(self) -> None:
        obs = ingest_observation(
            self.svc,
            ObservationIn(
                source_kind=SourceKind.USER_STATEMENT,
                content="我喜欢芙莉莲",
                producer="test",
            ),
        )
        mem = self.svc.propose_memory(
            MemoryProposeIn(
                type=MemoryType.SEMANTIC,
                content="喜欢芙莉莲",
                status=MemoryStatus.ACTIVE,
                source_ids=[obs.id],
            )
        )
        self.assertEqual(mem.status, MemoryStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()
