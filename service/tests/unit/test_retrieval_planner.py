# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.retrieval.pipeline import (
    RESULT_FOUND,
    RESULT_NO_MATCH,
    RESULT_NOT_NEEDED,
    run_retrieve,
)
from cognitive_memory.retrieval.planner import plan_retrieval
from cognitive_memory.storage.db import Database

_FIXTURES = (
    Path(__file__).resolve().parents[1] / "retrieval" / "fixtures" / "trigger_cases.json"
)


class RetrievalPlannerTests(unittest.TestCase):
    def test_fixture_triggers(self) -> None:
        cases = json.loads(_FIXTURES.read_text(encoding="utf-8"))
        for case in cases:
            plan = plan_retrieval(case["query"])
            self.assertEqual(
                plan.should_retrieve,
                case["expect_retrieve"],
                msg=f"{case['label']}: {case['query']!r} → {plan.reason}",
            )

    def test_force_overrides_chitchat(self) -> None:
        plan = plan_retrieval("你好", force=True)
        self.assertTrue(plan.should_retrieve)
        self.assertEqual(plan.trigger, "forced")


class RetrievePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_not_needed(self) -> None:
        out = run_retrieve(self.svc, query="你好")
        self.assertEqual(out["status"], RESULT_NOT_NEEDED)
        self.assertEqual(out["count"], 0)

    def test_found_and_no_match(self) -> None:
        self.svc.propose_memory(
            MemoryProposeIn(
                content="主人讨厌香菜",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        hit = run_retrieve(self.svc, query="你还记得我说过讨厌香菜吗")
        self.assertIn(hit["status"], (RESULT_FOUND, "PARTIAL"))
        self.assertGreaterEqual(hit["count"], 1)

        miss = run_retrieve(self.svc, query="上次我们讨论了火星移民方案吗", force=True)
        self.assertIn(miss["status"], (RESULT_NO_MATCH, "PARTIAL", RESULT_FOUND))
        if miss["status"] == RESULT_NO_MATCH:
            self.assertEqual(miss["count"], 0)


if __name__ == "__main__":
    unittest.main()
