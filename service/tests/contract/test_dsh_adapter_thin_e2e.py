# -*- coding: utf-8 -*-
"""场景 A：DSH 形 Adapter 薄化验收 — 仅 HTTP/SDK，不持有核心库连接。"""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cognitive_memory.adapters.dsh_http import FORBIDDEN_IMPORT_PREFIXES, DshHttpAdapter
from cognitive_memory.bootstrap import build_context
from cognitive_memory.sdk import MnemosyneClient


class DshAdapterThinE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.ctx = build_context(data_dir=self.tmp.name, token="dsh-thin-token")
        self.http = TestClient(self.ctx.app)
        self.client = MnemosyneClient(
            "http://test",
            "dsh-thin-token",
            session=self.http,
        )
        self.adapter = DshHttpAdapter(self.client)

    def tearDown(self) -> None:
        self.client.close()
        self.ctx.db.close()
        self.tmp.cleanup()

    def test_host_observe_search_without_db_handle(self) -> None:
        contract = self.adapter.contract()
        self.assertFalse(contract.get("adapter_may_bypass_service"))
        self.assertEqual(contract.get("storage_access"), "service_only")

        obs = self.adapter.observe_dialog("主人说今晚想听雨声")
        self.assertTrue(obs.get("id"))
        mem = self.adapter.propose_from_host(
            "用户偏好雨声",
            source_ids=[obs["id"]],
            metadata={"host": "dsh", "policy": {"allow_forward": False}},
        )
        self.assertTrue(mem.get("id"))
        found = self.adapter.search("雨声")
        self.assertGreaterEqual(found.get("count", 0), 1)

        # Adapter 实例不应暴露 Database
        self.assertFalse(hasattr(self.adapter, "db"))
        self.assertFalse(hasattr(self.adapter, "database"))

    def test_adapter_source_forbids_storage_imports(self) -> None:
        path = Path(__file__).resolve().parents[2] / "src" / "cognitive_memory" / "adapters" / "dsh_http.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                imported.append(mod)
        for banned in FORBIDDEN_IMPORT_PREFIXES:
            for imp in imported:
                self.assertFalse(
                    imp == banned or imp.startswith(banned + "."),
                    f"adapter imported forbidden {imp}",
                )


if __name__ == "__main__":
    unittest.main()
