# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.cognition.feedback_learning import (
    OUTCOME,
    SELF_EVAL,
    USER_EXPLICIT,
    apply_feedback_learning,
    classify_feedback,
)
from cognitive_memory.cognition.schema_evolution import (
    ACCOMMODATION,
    ASSIMILATION,
    CONFLICT,
    classify_evolution,
    evolve_schema,
)
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.retrieval.semantic import SemanticScorer, hashed_embedding
from cognitive_memory.storage.db import Database


class ExperienceLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def _mem(self, text: str, *, status=MemoryStatus.CANDIDATE) -> str:
        m = self.svc.propose_memory(
            MemoryProposeIn(
                content=text,
                type=MemoryType.SEMANTIC,
                status=status,
                metadata={"epistemic": "fact"},
            )
        )
        return m.id

    def test_schema_evolution_modes(self) -> None:
        sid = self.svc.store_cognitive_schema(
            {
                "name": "用户偏好表达方式",
                "type": "BEHAVIORAL",
                "state": "ACTIVE",
                "confidence": 0.5,
                "evidence": {"supporting": ["m1"], "counter": []},
            }
        )
        dry = evolve_schema(self.svc, sid, supporting=["m2"], confirm=False)
        self.assertEqual(dry["mode"], ASSIMILATION)
        done = evolve_schema(self.svc, sid, supporting=["m2"], confirm=True)
        self.assertEqual(done["mode"], ASSIMILATION)
        self.assertGreater(done["schema"]["confidence"], 0.5)
        self.assertTrue(done["schema"]["evolution_history"])

        acc = evolve_schema(
            self.svc,
            sid,
            counter=["m3"],
            applicability={"scene": "work"},
            confirm=True,
        )
        self.assertEqual(acc["mode"], ACCOMMODATION)
        conflict = evolve_schema(
            self.svc,
            sid,
            counter=["m4", "m5"],
            confirm=True,
        )
        self.assertEqual(conflict["mode"], CONFLICT)
        self.assertEqual(conflict["schema"]["state"], "CONTESTED")

    def test_classify_evolution(self) -> None:
        self.assertEqual(classify_evolution(supporting_count=2, counter_count=0), ASSIMILATION)
        self.assertEqual(classify_evolution(supporting_count=2, counter_count=1), ACCOMMODATION)
        self.assertEqual(classify_evolution(supporting_count=1, counter_count=2), CONFLICT)

    def test_feedback_learning_distinguishes_sources(self) -> None:
        mid = self._mem("用户喜欢先给结论")
        base = self.svc.get_memory(mid)["confidence"] or 0.4
        out = apply_feedback_learning(
            self.svc, mid, source=OUTCOME, outcome="success", note="结果正确"
        )
        self.assertTrue(out["ok"])
        self.assertGreater(out["confidence"], base)
        self.assertEqual(out["plan"]["source"], OUTCOME)
        self.assertFalse(out["plan"]["promote_eligible"])

        self.assertGreater(
            classify_feedback(source=USER_EXPLICIT, useful=True)["confidence_delta"],
            classify_feedback(source=SELF_EVAL, self_score=1.0)["confidence_delta"],
        )

    def test_semantic_space_is_optional_signal(self) -> None:
        self.assertEqual(len(hashed_embedding("夜航星")), 512)
        s = SemanticScorer()
        related = s.score("喜欢夜航星", "夜航星是用户喜欢的歌")
        unrelated = s.score("喜欢夜航星", "明天下午开会")
        self.assertGreater(related, unrelated)
        # 语义只加分，不压过主排序
        self.assertLess(abs(SemanticScorer.blend(0.8, 0.0, weight=0.25) - 0.6), 1e-9)


if __name__ == "__main__":
    unittest.main()
