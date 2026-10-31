# -*- coding: utf-8 -*-
"""SQLite 连接与事务辅助（单连接 + 锁，便于 Windows 下干净关闭）。"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .migrations import apply_migrations


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._initialized = False

    def connect(self) -> sqlite3.Connection:
        with self._lock:
            if self._conn is None:
                self._conn = sqlite3.connect(self.path, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA foreign_keys=ON")
            return self._conn

    def ensure_schema(self) -> list[str]:
        with self._lock:
            if self._initialized:
                return []
            done = apply_migrations(self.connect())
            self._initialized = True
            return done

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = self.connect()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
