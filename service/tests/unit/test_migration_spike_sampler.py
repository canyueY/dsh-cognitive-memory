# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.migration_spike.runner import assess_provenance, run_spike
from cognitive_memory.migration_spike.sampler import sample_memories


def _mk_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE memories (
          id TEXT PRIMARY KEY,
          type TEXT, status TEXT, content TEXT,
          created_at TEXT, updated_at TEXT,
          confidence REAL, metadata_json TEXT,
          bank_id TEXT
        );
        CREATE TABLE memory_evidence (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_id TEXT, observation_id TEXT, relation TEXT,
          validation_state TEXT DEFAULT 'unverified',
          created_at TEXT
        );
        """
    )
    rows = [
        ("m1", "semantic", "active", "我喜欢咖啡", "2026-01-01T00:00:00Z", "{}"),
        ("m2", "working", "active", "钥匙位于抽屉", "2026-01-02T00:00:00Z", "{}"),
        ("m3", "episodic", "candidate", "如果下雨就回家", "2026-01-03T00:00:00Z", "{}"),
        ("m4", "semantic", "active", "不是昨天的会议", "2026-01-04T00:00:00Z", "{}"),
        ("m5", "working", "active", "x" * 200, "2026-01-05T00:00:00Z", '{"bank_id":"personal"}'),
        ("m6", "semantic", "active", "今天很冷", "2026-01-06T00:00:00Z", "{}"),
        ("m7", "semantic", "active", "我不喜欢香菜", "2026-01-07T00:00:00Z", '{"domain":"food"}'),
        ("m8", "semantic", "invalidated", "然而其实不是这样", "2026-01-08T00:00:00Z", "{}"),
        ("m9", "semantic", "active", "短句", "2026-01-09T00:00:00Z", "{}"),
        ("m10", "semantic", "active", "用户喜欢茶", "2026-01-10T00:00:00Z", '{"policy":{}}'),
    ]
    for mid, typ, st, content, created, meta in rows:
        conn.execute(
            "INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?)",
            (mid, typ, st, content, created, created, 0.5, meta, "personal"),
        )
    conn.execute(
        "INSERT INTO memory_evidence(memory_id,observation_id,relation,validation_state,created_at) "
        "VALUES ('m1','obs1','supports','unverified','2026-01-01T00:00:00Z')"
    )
    conn.commit()
    conn.close()


class MigrationSpikeTests(unittest.TestCase):
    def test_sampler_and_runner_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "memory.db"
            out = Path(td) / "out"
            _mk_db(db)
            samples = sample_memories(db, per_stratum=2, total_target=20)
            self.assertGreaterEqual(len(samples), 5)
            report = run_spike(db, out, per_stratum=2, total_target=20)
            self.assertGreater(report.sample_count, 0)
            self.assertTrue((out / "migration_samples.jsonl").is_file())
            self.assertTrue((out / "spike_stats.json").is_file())
            # ensure stats recomputable
            lines = (out / "migration_samples.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), report.sample_count)
            row = json.loads(lines[0])
            self.assertIn("parse_status", row)
            self.assertEqual(row.get("default_lifecycle_if_migrated"), "proposed")
            self.assertTrue(row.get("must_not_auto_verify"))

    def test_provenance_unknown_without_links(self) -> None:
        got = assess_provenance({"evidence_count": 0, "metadata": {}})
        self.assertEqual(got["provenance_status"], "unknown")


if __name__ == "__main__":
    unittest.main()
