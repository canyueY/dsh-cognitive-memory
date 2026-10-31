# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest

from cognitive_memory.bootstrap import build_context
from cognitive_memory.mcp.server import TOOLS, _dispatch


class McpObservePreviewTests(unittest.TestCase):
    def test_tools_include_observe_and_import_preview(self) -> None:
        names = {t["name"] for t in TOOLS}
        self.assertIn("memory_observe", names)
        self.assertIn("memory_import_preview", names)

    def test_observe_requires_confirm_and_works(self) -> None:
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            ctx = build_context(data_dir=tmp.name, token="t")
            try:
                with self.assertRaises(ValueError):
                    _dispatch(ctx.service, "memory_observe", {"content": "x"})
                out = _dispatch(
                    ctx.service,
                    "memory_observe",
                    {"content": "mcp observe", "confirm": True, "producer": "mcp-test"},
                )
                self.assertTrue(out.get("id"))
                preview = _dispatch(
                    ctx.service,
                    "memory_import_preview",
                    {
                        "records": [
                            {
                                "source_system": "jsonl",
                                "source_record_id": "1",
                                "content": {"text": "preview"},
                            }
                        ]
                    },
                )
                self.assertEqual(preview.get("state"), "pending_approval")
                self.assertGreaterEqual(preview.get("count", 0), 1)
            finally:
                ctx.db.close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
