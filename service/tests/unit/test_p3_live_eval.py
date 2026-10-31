# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryProposeIn, MemoryStatus, MemoryType
from cognitive_memory.events.bus import EventBus
from cognitive_memory.retrieval.live_eval import run_live_eval
from cognitive_memory.storage.db import Database


class LiveEvalTests(unittest.TestCase):
    def test_writes_only_shadow_and_report(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            src_path = Path(td) / "source.db"
            shadow_path = Path(td) / "eval_shadow.db"
            src = Database(src_path)
            svc = MemoryService(src, EventBus())
            m1 = svc.propose_memory(
                MemoryProposeIn(
                    content="我喜欢夜航星",
                    type=MemoryType.SEMANTIC,
                    status=MemoryStatus.ACTIVE,
                )
            )
            svc.propose_memory(
                MemoryProposeIn(
                    content="打印机缺墨请更换",
                    type=MemoryType.EPISODIC,
                    status=MemoryStatus.ACTIVE,
                )
            )
            # optional evidence link if observations exist — skip if not
            src.close()

            report = run_live_eval(
                src_path,
                shadow_path,
                memory_limit=10,
                query_limit=5,
                evidence_limit=10,
            )
            self.assertTrue(report.ok)
            self.assertGreaterEqual(report.sample_count, 2)
            self.assertEqual(report.provenance_complete_forbidden, 0)
            sidecar = shadow_path.with_suffix(".live_eval.json")
            self.assertTrue(sidecar.is_file())
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertTrue(data["ok"])
            _ = m1


if __name__ == "__main__":
    unittest.main()
