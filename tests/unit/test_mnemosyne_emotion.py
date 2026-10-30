# -*- coding: utf-8 -*-
"""Mnemosyne P1–P5：复合情绪、E/T/P/A、shadow、propose、模式、检索重排。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.cognition.emotion_assess import assess_emotion_behavior
from cognitive_memory.cognition.emotion_extract import (
    extract_emotion_for_observation,
    extract_emotion_from_text,
)
from cognitive_memory.cognition.emotion_patterns import scan_emotion_behavior_patterns
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.emotion import (
    SOURCE_SELF_REPORT,
    emotion_retrieval_score,
    normalize_emotion_state,
)
from cognitive_memory.domain.models import (
    ContextBuildIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SearchQuery,
    SourceKind,
)
from cognitive_memory.events.bus import EventBus
from cognitive_memory.storage.db import Database


class MnemosyneEmotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(
            self.db,
            EventBus(),
            spatiotemporal_enable=True,
            emotion_enable=True,
            emotion_retrieval_enabled=True,
        )

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_intensity_confidence_separate(self) -> None:
        st = normalize_emotion_state(
            {
                "emotion_vector": {"anger": 0.9},
                "confidence_vector": {"anger": 0.3},
            }
        )
        self.assertEqual(st["emotion_vector"]["anger"], 0.9)
        self.assertEqual(st["confidence_vector"]["anger"], 0.3)

    def test_compound_emotions(self) -> None:
        pack = extract_emotion_from_text("我现在很生气，又有点焦虑")
        self.assertTrue(pack["has_signal"])
        self.assertEqual(pack["source"], SOURCE_SELF_REPORT)
        vec = pack["emotion_state"]["emotion_vector"]
        self.assertGreater(vec.get("anger", 0), 0.5)
        self.assertGreater(vec.get("anxiety", 0), 0.5)

    def test_no_strong_without_evidence(self) -> None:
        a = assess_emotion_behavior(emotion_state=None, behaviors=["withdrawal"], content="不回了")
        self.assertIn(a["association_level"], ("none", "weak", "conflict"))
        self.assertNotEqual(a["association_level"], "strong")

    def test_pattern_unknown_caps_moderate_not_weak(self) -> None:
        st = normalize_emotion_state(
            {
                "emotion_vector": {"anger": 0.9},
                "confidence_vector": {"anger": 0.9},
                "source": SOURCE_SELF_REPORT,
            }
        )
        a = assess_emotion_behavior(
            emotion_state=st,
            behaviors=["withdrawal"],
            content="我现在很生气，不想再说了",
            has_individual_pattern=False,
        )
        self.assertEqual(a["association_level"], "moderate")
        self.assertIn("pattern_unknown_cap", a["gate_reasons"])

    def test_shadow_extract_no_active_memory(self) -> None:
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.USER_STATEMENT,
                content="我现在很生气，不想再说了",
                idempotency_key="emo-shadow-1",
            )
        )
        pack = extract_emotion_for_observation(
            self.svc, obs.id, shadow_only=True, write_enabled=False
        )
        self.assertTrue(pack.get("ok"))
        self.assertTrue(pack.get("has_signal"))
        self.assertIsNone(pack.get("proposed_memory_id"))
        listed = self.svc.list_emotion_candidates(limit=10, written=False)
        self.assertGreaterEqual(len(listed), 1)
        hits = self.svc.search(SearchQuery(query="情绪事件候选", limit=10))
        self.assertEqual(len(hits), 0)

    def test_write_strong_proposes_candidate_only(self) -> None:
        # 预置跨日模式，使评估可达 strong
        for i, day in enumerate(("2026-10-01", "2026-10-02", "2026-10-03")):
            self.svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content="我现在很生气，不想再说了",
                    occurred_at=f"{day}T12:00:00Z",
                    idempotency_key=f"emo-pat-{i}",
                    metadata={
                        "mnemosyne": {
                            "emotion_state": {
                                "emotion_vector": {"anger": 0.8},
                                "confidence_vector": {"anger": 0.8},
                            },
                            "emotional_event": {"behavior_refs": ["withdrawal"]},
                            "assessment": {"dominant_emotion": "anger"},
                        }
                    },
                )
            )
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.USER_STATEMENT,
                content="我现在很生气，不想再说了",
                idempotency_key="emo-write-1",
            )
        )
        pack = extract_emotion_for_observation(
            self.svc, obs.id, shadow_only=False, write_enabled=True
        )
        self.assertTrue(pack.get("ok"))
        self.assertEqual(pack.get("association_level"), "strong")
        mid = pack.get("proposed_memory_id")
        self.assertIsNotNone(mid)
        mem = self.svc.get_memory(mid)
        self.assertEqual(mem["status"], MemoryStatus.CANDIDATE.value)
        written = self.svc.list_emotion_candidates(limit=20, written=True)
        self.assertTrue(any(w.get("observation_id") == obs.id for w in written))
        # 幂等再跑一次
        pack2 = extract_emotion_for_observation(
            self.svc, obs.id, shadow_only=False, write_enabled=True
        )
        self.assertEqual(pack2.get("proposed_memory_id"), mid)

    def test_emotion_retrieval_score_match_and_conflict(self) -> None:
        q = normalize_emotion_state(
            {
                "emotion_vector": {"anger": 0.8},
                "confidence_vector": {"anger": 0.8},
            }
        )
        match_meta = {
            "mnemosyne": {
                "emotion_state": normalize_emotion_state(
                    {"emotion_vector": {"anger": 0.7}, "confidence_vector": {"anger": 0.7}}
                ),
                "assessment": {"dominant_emotion": "anger"},
                "emotional_event": {"behavior_refs": ["withdrawal"]},
            },
            "emotion_event": True,
        }
        joy_meta = {
            "mnemosyne": {
                "assessment": {"dominant_emotion": "joy"},
                "emotion_state": normalize_emotion_state(
                    {"emotion_vector": {"joy": 0.8}, "confidence_vector": {"joy": 0.8}}
                ),
            }
        }
        s_match = emotion_retrieval_score(
            match_meta, query_emotion=q, query_behaviors=["withdrawal"], enable=True
        )
        s_conflict = emotion_retrieval_score(joy_meta, query_emotion=q, enable=True)
        s_off = emotion_retrieval_score(match_meta, query_emotion=q, enable=False)
        self.assertGreater(s_match, 1.0)
        self.assertLess(s_conflict, 1.0)
        self.assertEqual(s_off, 1.0)

    def test_p5_search_rerank_boosts_matching_emotion(self) -> None:
        svc = MemoryService(
            self.db,
            EventBus(),
            spatiotemporal_enable=False,
            emotion_enable=True,
            emotion_retrieval_enabled=True,
        )
        # 共用锚点词保证 FTS/LIKE 都能命中两条，再靠情绪重排拉开顺序
        joy = svc.propose_memory(
            MemoryProposeIn(
                type=MemoryType.EPISODIC,
                status=MemoryStatus.ACTIVE,
                content="【共用锚点】那天大家都很开心庆祝",
                metadata={
                    "mnemosyne": {
                        "assessment": {"dominant_emotion": "joy"},
                        "emotion_state": normalize_emotion_state(
                            {
                                "emotion_vector": {"joy": 0.9},
                                "confidence_vector": {"joy": 0.9},
                            }
                        ),
                    }
                },
                idempotency_key="p5-joy",
            )
        )
        anger = svc.propose_memory(
            MemoryProposeIn(
                type=MemoryType.EPISODIC,
                status=MemoryStatus.ACTIVE,
                content="【共用锚点】那天我很生气不想再说了",
                metadata={
                    "mnemosyne": {
                        "assessment": {"dominant_emotion": "anger"},
                        "emotion_state": normalize_emotion_state(
                            {
                                "emotion_vector": {"anger": 0.9},
                                "confidence_vector": {"anger": 0.9},
                            }
                        ),
                        "emotional_event": {"behavior_refs": ["withdrawal"]},
                    },
                    "emotion_event": True,
                },
                idempotency_key="p5-anger",
            )
        )
        hits = svc.search(
            SearchQuery(
                query="【共用锚点】我现在很生气",
                limit=10,
                emotion_rerank=True,
            )
        )
        ids = [m.id for m in hits]
        self.assertIn(anger.id, ids)
        self.assertIn(joy.id, ids)
        self.assertLess(ids.index(anger.id), ids.index(joy.id))
        ctx = svc.build_context(
            ContextBuildIn(
                query="【共用锚点】我现在很生气",
                limit=8,
                emotion_rerank=True,
            )
        )
        self.assertTrue(any(f.get("emotion_score") for f in ctx.fragments))

    def test_emotion_pattern_scan(self) -> None:
        for i, day in enumerate(("2026-10-01", "2026-10-02")):
            self.svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.USER_STATEMENT,
                    content=f"seed {i}",
                    occurred_at=f"{day}T10:00:00Z",
                    idempotency_key=f"emo-scan-{i}",
                    metadata={
                        "mnemosyne": {
                            "emotional_event": {"behavior_refs": ["withdrawal"]},
                            "assessment": {"dominant_emotion": "anger"},
                        }
                    },
                )
            )
        pack = scan_emotion_behavior_patterns(
            self.svc, limit_obs=50, min_days=2, min_count=2
        )
        self.assertTrue(pack.get("ok"))
        self.assertGreaterEqual(pack.get("count") or 0, 1)
        hit = pack["pattern_candidates"][0]
        self.assertEqual(hit["emotion"], "anger")
        self.assertEqual(hit["behavior"], "withdrawal")


if __name__ == "__main__":
    unittest.main()
