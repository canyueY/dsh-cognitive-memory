# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.claims.store import ClaimStore
from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.retrieval.pipeline import run_retrieve
from cognitive_memory.retrieval.semantic_sidepath import (
    assist_rerank,
    evaluate_assist,
    pool_suggest,
)
from cognitive_memory.storage.db import Database


class SemanticSidepathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Database(Path(self.tmp.name) / "memory.db")
        self.svc = MemoryService(self.db, EventBus())
        self.claims = ClaimStore(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_assist_rerank_tags_non_authoritative(self) -> None:
        items = [
            {"id": "a", "content": "我喜欢夜航星", "score": {"total": 0.5, "R": 0.5}},
            {"id": "b", "content": "今天天气不错", "score": {"total": 0.6, "R": 0.6}},
        ]
        pack = assist_rerank("喜欢夜航星这首歌", items, weight=0.4)
        self.assertTrue(pack["assistive_only"])
        self.assertFalse(pack["authoritative"])
        self.assertIn("semantic", pack["items"][0]["score"])
        # night-star item should rise above weather after assist
        self.assertEqual(pack["items"][0]["id"], "a")

    def test_pool_suggest_never_verified(self) -> None:
        corpus = [
            {"id": "1", "content": "主人喜欢听夜航星"},
            {"id": "2", "content": "系统定时任务摘要无关"},
        ]
        sug = pool_suggest("喜欢夜航星", corpus, min_score=0.2)
        self.assertTrue(sug["assistive_only"])
        self.assertFalse(sug["authoritative"])
        self.assertTrue(sug["items"])

    def test_evaluate_assist_novel_hits(self) -> None:
        pool = [
            {"id": "rel", "content": "我喜欢夜航星音乐"},
            {"id": "noise", "content": "打印机缺墨"},
        ]
        ev = evaluate_assist(
            "喜欢听夜航星",
            fts_ids=["noise"],
            relevant_ids=["rel"],
            pool=pool,
            limit=3,
        )
        self.assertIn("rel", ev["assist_novel_hits"])

    def test_retrieve_pipeline_semantic_channel(self) -> None:
        self.svc.propose_memory(
            MemoryProposeIn(
                content="我喜欢夜航星",
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.ACTIVE,
            )
        )
        out = run_retrieve(
            self.svc,
            query="喜欢夜航星",
            force=True,
            semantic_assist=True,
        )
        channels = [c.get("name") for c in (out.get("trace") or {}).get("channels") or []]
        if out.get("items"):
            self.assertIn("semantic_assist", channels)
            self.assertFalse(out["items"][0].get("authoritative"))

    def test_claim_semantic_suggest_unverified(self) -> None:
        self.claims.propose_from_text("我喜欢夜航星")
        self.claims.propose_from_text("我讨厌下雨")
        sug = self.claims.semantic_suggest("喜欢夜航星这首歌", min_score=0.2)
        self.assertEqual(sug.get("verification_status"), "unverified")
        self.assertTrue(sug.get("assistive_only"))
        # must not flip any claim to verified
        for it in sug.get("items") or []:
            cl = self.claims.get(str(it["id"]))
            self.assertEqual(cl["verification_status"], "unverified")
            self.assertNotEqual(cl["lifecycle"], "verified")


if __name__ == "__main__":
    unittest.main()
