# -*- coding: utf-8 -*-
"""Mnemosyne Memory Bank 默认路径与旧 DSH 路径隔离。"""

from __future__ import annotations

import os
import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest import mock

from cognitive_memory.storage.paths import (
    MEMORY_BANK_NAME,
    copy_memory_bank,
    default_data_root,
    ensure_layout,
    legacy_dsh_data_root,
    migration_status,
)


class MemoryBankPathsTests(unittest.TestCase):
    def test_default_is_named_memory_bank_not_dsh(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            for k in ("MNEMOSYNE_MEMORY_BANK", "MNEMOSYNE_DATA_DIR", "DSH_MEMORY_DATA_DIR"):
                os.environ.pop(k, None)
            root = default_data_root()
            self.assertEqual(root.name, MEMORY_BANK_NAME)
            self.assertNotEqual(root, legacy_dsh_data_root())
            norm = str(root).replace("\\", "/")
            self.assertFalse(norm.endswith("DSH/cognitive-memory"))
            self.assertIn("Mnemosyne Memory Bank", norm)

    def test_env_override_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "BankA"
            with mock.patch.dict(
                os.environ,
                {
                    "MNEMOSYNE_MEMORY_BANK": str(bank),
                    "DSH_MEMORY_DATA_DIR": str(Path(tmp) / "legacy"),
                },
                clear=False,
            ):
                self.assertEqual(default_data_root(), bank.resolve())

    def test_copy_legacy_to_bank(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "DSH" / "cognitive-memory"
            dst = Path(tmp) / MEMORY_BANK_NAME
            ensure_layout(src)
            conn=sqlite3.connect(src / "data" / "memory.db")
            conn.execute("CREATE TABLE fixture(content TEXT)")
            conn.execute("INSERT INTO fixture VALUES ('preserved')")
            conn.commit()
            conn.close()
            (src / "runtime" / "token").write_text("t", encoding="utf-8")
            st = migration_status(target=dst, legacy=src)
            self.assertTrue(st["recommend_migrate"])
            result = copy_memory_bank(src, dst)
            self.assertTrue(result["ok"], result)
            self.assertTrue((dst / "data" / "memory.db").is_file())
            self.assertTrue((src / "MIGRATED_TO_MNEMOSYNE_MEMORY_BANK.txt").is_file())
            self.assertTrue((dst / "README.txt").is_file())


if __name__ == "__main__":
    unittest.main()
