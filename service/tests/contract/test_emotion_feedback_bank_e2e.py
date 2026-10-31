# -*- coding: utf-8 -*-
"""Y4：情绪 shadow → 候选 → Bank 记忆 → 反馈 promote 抽样 E2E（加厚，非从零）。"""

from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient

from cognitive_memory.bootstrap import build_context
from cognitive_memory.cognition.emotion_extract import extract_emotion_for_observation
from cognitive_memory.domain.models import (
    FeedbackIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    ObservationIn,
    SearchQuery,
    SourceKind,
)


class EmotionFeedbackBankE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="y4-token")
        # 打开情绪提取；保持 shadow，不自动升格 LT
        self.ctx.service.emotion_enable = True
        self.ctx.service.emotion_write_enabled = False
        self.ctx.service.emotion_shadow_only = True
        self.http = TestClient(self.ctx.app)
        self.h = {"Authorization": "Bearer y4-token"}

    def tearDown(self) -> None:
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_shadow_emotion_then_bank_feedback_promote(self) -> None:
        obs = self.ctx.service.capture_observation(
            ObservationIn(
                source_kind=SourceKind.USER_STATEMENT,
                content="我现在很开心，今天想听雨声白噪声",
                producer="y4-e2e",
                agent_id="agent:y4",
            )
        )
        pack = extract_emotion_for_observation(
            self.ctx.service,
            observation_id=obs.id,
            shadow_only=True,
            write_enabled=False,
        )
        self.assertTrue(pack.get("ok"))
        self.assertTrue(pack.get("has_signal"))
        self.assertTrue(pack.get("shadow_only"))
        self.assertGreaterEqual(int(pack.get("stored_candidates") or 0), 1)
        cands = self.ctx.service.list_emotion_candidates(limit=20)
        self.assertGreaterEqual(len(cands), 1)

        # 正式记忆写入 projects bank（抽样隔离）
        mem = self.ctx.service.propose_memory(
            MemoryProposeIn(
                type=MemoryType.SEMANTIC,
                status=MemoryStatus.CANDIDATE,
                content="用户偏好雨声白噪声（y4-bank）",
                source_ids=[obs.id],
                bank_id="projects",
                metadata={
                    "bank_id": "projects",
                    "epistemic": "fact",
                    "policy": {"allow_forward": False},
                },
            )
        )
        self.assertEqual(mem.bank_id, "projects")
        self.assertEqual(mem.status, MemoryStatus.CANDIDATE)

        # personal 检索不应误当成唯一空间污染断言：至少 projects 能搜到
        found_proj = self.ctx.service.search(
            SearchQuery(query="y4-bank", limit=10, banks=["projects"])
        )
        self.assertGreaterEqual(len(found_proj), 1)

        found_personal = self.ctx.service.search(
            SearchQuery(query="y4-bank", limit=10, banks=["personal"])
        )
        # Bank 隔离：personal 默认不应命中 projects 记忆
        self.assertEqual(len(found_personal), 0)

        fb = self.ctx.service.feedback(
            FeedbackIn(memory_id=mem.id, useful=True, note="y4-ok", producer="y4-e2e")
        )
        self.assertTrue(fb.get("ok"))
        self.assertFalse(fb.get("promoted"))
        self.assertEqual(fb["useful_feedback_count"], 1)
        got = self.ctx.service.get_memory(mem.id)
        status = got.get("status") if isinstance(got, dict) else getattr(got, "status", None)
        status_s = str(getattr(status, "value", None) or status).lower()
        self.assertEqual(status_s, "candidate")

        # HTTP 面：emotion candidates + banks
        banks = self.http.get("/api/v1/banks", headers=self.h)
        self.assertEqual(banks.status_code, 200)
        self.assertGreaterEqual(banks.json().get("count", 0), 1)
        emo = self.http.get("/api/v1/emotion/candidates?limit=10", headers=self.h)
        self.assertEqual(emo.status_code, 200)


if __name__ == "__main__":
    unittest.main()
