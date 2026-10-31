# -*- coding: utf-8 -*-
"""P2–P5：变化检测、关系、重新评估、模式扫描。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.cognition.change_detect import classify_change, detect_changes_for_observation
from cognitive_memory.cognition.persistence import scan_persistence_patterns
from cognitive_memory.cognition.reevaluate import run_reevaluation
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import (
    ContextBuildIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SourceKind,
)
from cognitive_memory.events.bus import EventBus
from cognitive_memory.storage.db import Database


class SpatiotemporalP2P5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus(), spatiotemporal_enable=True)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_p2_change_detect_dry_run_and_candidates(self) -> None:
        self.svc.propose_memory(
            MemoryProposeIn(
                content="显示器位于房间A",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                metadata={"spatial": {"kind": "room", "name": "房间A", "spaceId": "room-a"}},
            )
        )
        obs = self.svc.capture_observation(
            ObservationIn(
                source_kind=SourceKind.USER_STATEMENT,
                content="显示器已经搬到房间B了",
                metadata={"spatial": {"kind": "room", "name": "房间B", "spaceId": "room-b"}},
                idempotency_key="p2-move",
            )
        )
        result = detect_changes_for_observation(self.svc, obs.id, dry_run=True, apply_l2=False)
        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("dry_run"))
        types = {c.get("change_type") for c in (result.get("candidates") or [])}
        self.assertTrue(types & {"evolves", "continues", "corrects", "uncertain", "new", "supersedes"})
        n = self.svc.store_change_candidates(
            observation_id=obs.id,
            candidates=list(result.get("candidates") or []),
            dry_run=True,
        )
        self.assertGreaterEqual(n, 1)
        listed = self.svc.list_change_candidates(limit=20, applied=False)
        self.assertGreaterEqual(len(listed), 1)
        self.assertTrue(any(x.get("observation_id") == obs.id for x in listed))

    def test_p2_classify_negation(self) -> None:
        v = classify_change("项目已经完成了，不再进行中", "项目目前进行中")
        self.assertIn(v["change_type"], ("corrects", "evolves", "uncertain"))

    def test_p3_link_and_context_relation(self) -> None:
        a = self.svc.propose_memory(
            MemoryProposeIn(
                content="旧位置：键盘在桌面区域",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.SUPERSEDED,
            )
        )
        b = self.svc.propose_memory(
            MemoryProposeIn(
                content="当前：键盘在收纳盒",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        link = self.svc.link_memories(
            from_id=b.id, to_id=a.id, relation="supersedes", note="moved"
        )
        self.assertTrue(link.get("ok"))
        rels = self.svc.list_relations(b.id)
        self.assertTrue(any(r["relation"] == "supersedes" for r in rels))
        ctx = self.svc.build_context(ContextBuildIn(query="键盘", limit=8))
        self.assertTrue(ctx.fragments)

    def test_p4_reevaluate_lists_expired(self) -> None:
        self.svc.propose_memory(
            MemoryProposeIn(
                content="临时计划：周五前交作业",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
                expires_at="2020-01-01T00:00:00Z",
                metadata={"temporal": {"kind": "plan", "validUntil": "2020-01-01T00:00:00Z"}},
            )
        )
        pack = run_reevaluation(self.svc, dry_run=True, limit=20)
        self.assertTrue(pack.get("ok"))
        self.assertGreaterEqual(int(pack.get("count") or 0), 1)
        reasons = []
        for t in pack.get("targets") or []:
            reasons.extend(t.get("reasons") or [])
        self.assertIn("expired", reasons)

    def test_p5_pattern_scan_cross_day(self) -> None:
        for day, text in (
            ("2026-10-01T10:00:00Z", "今天又去滑板了"),
            ("2026-10-05T11:00:00Z", "下午滑板真开心"),
            ("2026-10-12T09:00:00Z", "继续滑板练习"),
            ("2026-10-20T18:00:00Z", "晚上滑板到很晚"),
        ):
            self.svc.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.DIALOG,
                    content=text,
                    occurred_at=day,
                    idempotency_key=f"p5-{day}",
                )
            )
        pack = scan_persistence_patterns(self.svc, limit_obs=50, min_days=2, min_count=2)
        self.assertTrue(pack.get("ok"))
        topics = " ".join(h.get("topic") or "" for h in (pack.get("habit_candidates") or []))
        self.assertIn("滑板", topics)


if __name__ == "__main__":
    unittest.main()
