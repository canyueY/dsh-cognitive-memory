# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cognitive_memory.bootstrap import build_context
from cognitive_memory.core.service import NotFoundError
from cognitive_memory.migration.staging import (
    approve_batch,
    commit_batch,
    dedupe_records,
    preview_batch,
    rollback_batch,
)


class StagingDedupeRollbackTests(unittest.TestCase):
    def test_dedupe_source_and_content(self) -> None:
        records = [
            {
                "source_system": "jsonl",
                "source_record_id": "1",
                "content": {"text": "喜欢雨天"},
            },
            {
                "source_system": "jsonl",
                "source_record_id": "1",
                "content": {"text": "喜欢雨天（重复 id）"},
            },
            {
                "source_system": "jsonl",
                "source_record_id": "2",
                "content": {"text": "喜欢雨天"},
            },
            {
                "source_system": "jsonl",
                "source_record_id": "3",
                "content": {"text": "不吃香菜"},
            },
        ]
        kept, report = dedupe_records(records, strategy="source_then_content")
        self.assertEqual(report["input"], 4)
        self.assertEqual(report["output"], 2)
        self.assertEqual(report["dropped_by"]["source"], 1)
        self.assertEqual(report["dropped_by"]["content"], 1)
        texts = {_text(r) for r in kept}
        self.assertEqual(texts, {"喜欢雨天", "不吃香菜"})

    def test_preview_applies_dedupe(self) -> None:
        batch = preview_batch(
            [
                {
                    "source_system": "x",
                    "source_record_id": "a",
                    "content": {"text": "same"},
                },
                {
                    "source_system": "x",
                    "source_record_id": "a",
                    "content": {"text": "same"},
                },
            ]
        )
        self.assertEqual(len(batch.records), 1)
        self.assertEqual(batch.dedupe_report["dropped"], 1)

        raw = preview_batch(
            [
                {
                    "source_system": "x",
                    "source_record_id": "a",
                    "content": {"text": "same"},
                },
                {
                    "source_system": "x",
                    "source_record_id": "a",
                    "content": {"text": "same"},
                },
            ],
            dedupe=False,
        )
        self.assertEqual(len(raw.records), 2)

    def test_soft_and_hard_rollback_layers(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            ctx = build_context(data_dir=str(Path(tmp.name) / "node"), token="t")
            try:
                batch = preview_batch(
                    [
                        {
                            "source_system": "jsonl",
                            "source_record_id": "rb1",
                            "content": {"text": "回滚样本甲"},
                        }
                    ],
                    dedupe=False,
                )
                approve_batch(batch, actor="tester")
                commit_batch(batch, service=ctx.service, dry_run=False)
                self.assertEqual(batch.state, "committed")
                written = (batch.commit_report or {}).get("written") or []
                self.assertTrue(written)
                mid = written[0].get("memory_id")
                self.assertTrue(mid)

                # soft rollback
                rollback_batch(batch, service=ctx.service, layer="soft", actor="tester")
                self.assertEqual(batch.state, "rolled_back")
                self.assertEqual(batch.rollback_report["layer"], "soft")
                self.assertGreaterEqual(batch.rollback_report["ok_count"], 1)
                got = ctx.service.get_memory(mid)
                status = getattr(got, "status", None) or (
                    got.get("status") if isinstance(got, dict) else None
                )
                status_s = getattr(status, "value", None) or str(status)
                self.assertEqual(str(status_s).lower(), "invalidated")

                # cannot rollback twice
                with self.assertRaises(PermissionError):
                    rollback_batch(batch, service=ctx.service, layer="soft")

                # hard layer on a fresh commit
                batch2 = preview_batch(
                    [
                        {
                            "source_system": "jsonl",
                            "source_record_id": "rb2",
                            "content": {"text": "回滚样本乙"},
                        }
                    ],
                    dedupe=False,
                )
                approve_batch(batch2, actor="tester")
                commit_batch(batch2, service=ctx.service, dry_run=False)
                mid2 = (batch2.commit_report or {}).get("written")[0]["memory_id"]
                rollback_batch(batch2, service=ctx.service, layer="hard", actor="tester")
                self.assertEqual(batch2.rollback_report["layer"], "hard")
                with self.assertRaises(NotFoundError):
                    ctx.service.get_memory(mid2)
            finally:
                ctx.db.close()
        finally:
            tmp.cleanup()


def _text(rec: dict) -> str:
    c = rec.get("content") or {}
    if isinstance(c, dict):
        return str(c.get("text") or "")
    return str(c)


if __name__ == "__main__":
    unittest.main()
