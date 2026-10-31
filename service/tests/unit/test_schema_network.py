# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.cognition.schema_network import (
    impact_of_schema,
    merge_schemas,
    split_schema,
)
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.governance.capability_gate import (
    ensure_default_capabilities,
    set_capability_level,
)
from cognitive_memory.storage.db import Database


class SchemaNetworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())
        ensure_default_capabilities(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def _mem(self, text: str) -> str:
        m = self.svc.propose_memory(
            MemoryProposeIn(
                content=text,
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.CANDIDATE,
                source_ids=["obs_dummy"],
            )
        )
        return m.id

    def test_split_merge_and_impact(self) -> None:
        mid1 = self._mem("忙碌时请给结论")
        mid2 = self._mem("技术问题要完整推导")
        sid = self.svc.store_cognitive_schema(
            {
                "name": "沟通风格",
                "description": "混合规律",
                "type": "BEHAVIORAL",
                "state": "ACTIVE",
                "confidence": 0.5,
                "evidence": {"supporting": [mid1, mid2], "counter": []},
            }
        )
        dry = split_schema(
            self.svc,
            sid,
            child_specs=[
                {"name": "忙碌简洁", "memory_ids": [mid1]},
                {"name": "技术详尽", "memory_ids": [mid2]},
            ],
            confirm=False,
        )
        self.assertTrue(dry["ok"])
        self.assertTrue(dry["dry_run"])
        self.assertTrue(dry.get("change_plan_id"))

        # confirm alone insufficient
        blocked = split_schema(
            self.svc,
            sid,
            child_specs=[
                {"name": "忙碌简洁", "memory_ids": [mid1]},
                {"name": "技术详尽", "memory_ids": [mid2]},
            ],
            confirm=True,
            existing_plan_id=dry["change_plan_id"],
        )
        self.assertFalse(blocked.get("ok"))
        self.assertEqual(blocked.get("detail"), "capability_locked")

        set_capability_level(
            self.db,
            "SCHEMA_MUTATION",
            level="ACTIVE",
            enabled=True,
            actor="test",
        )
        done = split_schema(
            self.svc,
            sid,
            child_specs=[
                {"name": "忙碌简洁", "memory_ids": [mid1]},
                {"name": "技术详尽", "memory_ids": [mid2]},
            ],
            confirm=True,
            existing_plan_id=dry["change_plan_id"],
        )
        self.assertTrue(done["ok"])
        self.assertEqual(len(done["children"]), 2)
        parent = self.svc.get_cognitive_schema(sid)
        self.assertEqual(parent["state"], "CONTESTED")
        impact = impact_of_schema(self.svc, sid)
        self.assertGreaterEqual(impact["impact_score"], 1)
        self.assertTrue(impact["neighbors"])

        child_ids = [c["id"] for c in done["children"]]
        merged = merge_schemas(
            self.svc, child_ids, name="沟通风格·合并", confirm=True
        )
        self.assertTrue(merged["ok"])
        self.assertTrue(merged.get("merged_id"))
        for cid in child_ids:
            self.assertEqual(self.svc.get_cognitive_schema(cid)["state"], "RETIRED")


if __name__ == "__main__":
    unittest.main()
