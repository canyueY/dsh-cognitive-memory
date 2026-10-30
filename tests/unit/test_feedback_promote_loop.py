# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest

from cognitive_memory.bootstrap import build_context
from cognitive_memory.domain.models import (
    FeedbackIn,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
)


class FeedbackPromoteLoopTests(unittest.TestCase):
    def test_useful_feedback_promotes_candidate(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            ctx = build_context(data_dir=tmp.name, token="t")
            try:
                mem = ctx.service.propose_memory(
                    MemoryProposeIn(
                        type=MemoryType.SEMANTIC,
                        status=MemoryStatus.CANDIDATE,
                        content="闭环：喜欢雨声",
                        metadata={"epistemic": "fact"},
                    )
                )
                self.assertEqual(mem.status, MemoryStatus.CANDIDATE)
                out = ctx.service.feedback(
                    FeedbackIn(memory_id=mem.id, useful=True, note="yes", producer="test")
                )
                self.assertTrue(out.get("ok"))
                self.assertTrue(out.get("promoted"))
                got = ctx.service.get_memory(mem.id)
                status = got.get("status") if isinstance(got, dict) else getattr(got, "status", None)
                status_s = getattr(status, "value", None) or str(status)
                self.assertEqual(str(status_s).lower(), "active")
            finally:
                ctx.db.close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
