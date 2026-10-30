# -*- coding: utf-8 -*-
"""组件边界：禁止把 sqlite3/Database 当作组件存储面；必须经 StorageProvider。"""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from cognitive_memory.storage.provider import (
    SqliteStorageProvider,
    assert_component_uses_provider,
)


class StorageProviderBoundaryTests(unittest.TestCase):
    def test_provider_protocol_and_health(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            provider = SqliteStorageProvider.from_data_dir(tmp)
            assert_component_uses_provider(provider)
            h = provider.health()
            self.assertEqual(h["provider"], "sqlite")
            self.assertTrue(h["ok"])

    def test_reject_raw_object(self) -> None:
        with self.assertRaises(TypeError):
            assert_component_uses_provider(object())

    def test_components_package_no_direct_sqlite_connect(self) -> None:
        """扫描 components/ 源码：不应出现 sqlite3.connect( 业务直连。"""
        root = Path(__file__).resolve().parents[2] / "src" / "cognitive_memory" / "components"
        self.assertTrue(root.is_dir(), root)
        offenders: list[str] = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    # sqlite3.connect(...)
                    if isinstance(func, ast.Attribute) and func.attr == "connect":
                        if isinstance(func.value, ast.Name) and func.value.id == "sqlite3":
                            offenders.append(str(path.relative_to(root.parent)))
                    # Database( 作为组件内直接构造
                    if isinstance(func, ast.Name) and func.id == "Database":
                        offenders.append(f"{path.name}:Database()")
        self.assertEqual(offenders, [], f"components must not open sqlite/Database directly: {offenders}")

    def test_adapters_package_no_direct_sqlite(self) -> None:
        root = Path(__file__).resolve().parents[2] / "src" / "cognitive_memory" / "adapters"
        offenders: list[str] = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "sqlite3" or alias.name.startswith("sqlite3."):
                            offenders.append(path.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod == "sqlite3" or mod.startswith("cognitive_memory.storage.db"):
                        offenders.append(f"{path.name}:{mod}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
