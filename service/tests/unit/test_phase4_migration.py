# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.bootstrap import build_context
from cognitive_memory.governance.authority import AuthorityState, get_authority
from cognitive_memory.migration.compat_gateway import CompatGateway, CompatMode
from cognitive_memory.migration.export_interchange import export_interchange_jsonl
from cognitive_memory.migration.importers import iter_markdown, iter_sqlite_table
from cognitive_memory.migration.interchange import parse_interchange
from cognitive_memory.migration.mem0_adapter import iter_mem0_payloads
from cognitive_memory.migration.staging import (
    StagingStore,
    approve_batch,
    commit_batch,
    preview_batch,
    reject_batch,
)


class Phase4MigrationTests(unittest.TestCase):
    def test_interchange_preserves_unknown_fields(self) -> None:
        raw = {
            "source_system": "custom",
            "source_record_id": "r1",
            "content": {"text": "hello"},
            "weird_field": {"keep": True},
            "another": 42,
        }
        rec = parse_interchange(raw)
        self.assertEqual(rec.extensions.get("weird_field"), {"keep": True})
        self.assertEqual(rec.extensions.get("another"), 42)
        self.assertTrue(rec.checksum)
        src = rec.to_source_record()
        self.assertIn("hello", src.content)

    def test_staging_requires_approval(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            store = StagingStore(Path(tmp.name) / "staging")
            batch = preview_batch(
                [
                    {
                        "source_system": "jsonl",
                        "source_record_id": "1",
                        "content": {"text": "喜欢雨天"},
                    }
                ],
                store=store,
            )
            self.assertEqual(batch.state, "pending_approval")
            with self.assertRaises(PermissionError):
                commit_batch(batch)
            approve_batch(batch, actor="tester", store=store)
            committed = commit_batch(batch, dry_run=True, store=store)
            self.assertEqual(committed.state, "committed")
            self.assertTrue(committed.commit_report)

            batch2 = preview_batch(
                [{"source_system": "x", "source_record_id": "2", "content": {"text": "no"}}],
                store=store,
            )
            reject_batch(batch2, reason="nope", store=store)
            self.assertEqual(batch2.state, "rejected")
        finally:
            tmp.cleanup()

    def test_three_importers_and_mem0_and_export(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(tmp.name)
        try:
            md = root / "notes.md"
            md.write_text("## 偏好\n\n喜欢夜航星\n\n## 忌口\n\n不吃香菜\n", encoding="utf-8")
            md_recs = list(iter_markdown(md))
            self.assertGreaterEqual(len(md_recs), 2)

            dbp = root / "legacy.db"
            conn = sqlite3.connect(dbp)
            conn.execute("CREATE TABLE memories(id TEXT, content TEXT)")
            conn.execute("INSERT INTO memories VALUES ('a','来自sqlite')")
            conn.commit()
            conn.close()
            sql_recs = list(iter_sqlite_table(dbp))
            self.assertEqual(len(sql_recs), 1)

            mem0 = list(
                iter_mem0_payloads([{"id": "m1", "memory": "来自mem0", "categories": ["pref"]}])
            )
            self.assertEqual(len(mem0), 1)
            self.assertEqual(mem0[0].provenance.get("importer"), "mem0_adapter")

            out = root / "export.jsonl"
            pack = export_interchange_jsonl(md_recs + sql_recs + mem0, out)
            self.assertEqual(pack["count"], len(md_recs) + 1 + 1)
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), pack["count"])
            # 再进 staging → approve → commit 到真实服务
            ctx = build_context(data_dir=str(root / "node"), token="t")
            try:
                batch = preview_batch(md_recs[:1])
                approve_batch(batch, actor="test")
                commit_batch(batch, service=ctx.service, dry_run=False)
                self.assertGreaterEqual(ctx.service.health().get("observations", 0), 1)
                auth = get_authority(ctx.db)
                self.assertEqual(auth["state"], AuthorityState.MNEMOSYNE_PRIMARY.value)
            finally:
                ctx.db.close()
        finally:
            tmp.cleanup()

    def test_compat_gateway_dual_off_by_default(self) -> None:
        gw = CompatGateway()
        self.assertEqual(gw.mode, CompatMode.READ_ONLY)
        self.assertFalse(gw.allow_write_legacy_from_mnemosyne())
        with self.assertRaises(PermissionError):
            gw.set_mode("dual", allow_dual=False)
        snap = gw.set_mode("dual", allow_dual=True)
        self.assertTrue(snap["dual_enabled"])
        gw.set_mode("one_way")
        self.assertTrue(gw.allow_write_mnemosyne_from_legacy())
        self.assertFalse(gw.allow_write_legacy_from_mnemosyne())


if __name__ == "__main__":
    unittest.main()
