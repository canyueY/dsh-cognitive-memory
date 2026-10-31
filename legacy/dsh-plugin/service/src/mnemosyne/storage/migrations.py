# -*- coding: utf-8 -*-
"""SQLite schema migrations（V1.0 核心表）。"""

from __future__ import annotations

import sqlite3

MIGRATIONS: list[tuple[str, str]] = [
    (
        "001_core",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS observations (
          id TEXT PRIMARY KEY,
          source_kind TEXT NOT NULL,
          content TEXT NOT NULL,
          occurred_at TEXT,
          created_at TEXT NOT NULL,
          producer TEXT NOT NULL DEFAULT 'dsh',
          correlation_id TEXT,
          data_ref TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS memories (
          id TEXT PRIMARY KEY,
          type TEXT NOT NULL,
          status TEXT NOT NULL,
          content TEXT NOT NULL,
          source_ids_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          last_confirmed_at TEXT,
          version INTEGER NOT NULL DEFAULT 1,
          confidence REAL,
          expires_at TEXT,
          metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS memory_versions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_id TEXT NOT NULL,
          version INTEGER NOT NULL,
          snapshot_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(memory_id, version)
        );

        CREATE TABLE IF NOT EXISTS memory_evidence (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_id TEXT NOT NULL,
          observation_id TEXT NOT NULL,
          relation TEXT NOT NULL DEFAULT 'supports',
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          UNIQUE(memory_id, observation_id, relation)
        );

        CREATE TABLE IF NOT EXISTS memory_relations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          from_id TEXT NOT NULL,
          to_id TEXT NOT NULL,
          relation TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memory_feedback (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          memory_id TEXT NOT NULL,
          useful INTEGER,
          incorrect INTEGER,
          note TEXT NOT NULL DEFAULT '',
          producer TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
          event_id TEXT PRIMARY KEY,
          event_type TEXT NOT NULL,
          event_version INTEGER NOT NULL DEFAULT 1,
          occurred_at TEXT NOT NULL,
          recorded_at TEXT NOT NULL,
          producer TEXT NOT NULL,
          correlation_id TEXT,
          causation_id TEXT,
          payload_version INTEGER NOT NULL DEFAULT 1,
          payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS outbox (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_id TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL DEFAULT 'pending',
          attempts INTEGER NOT NULL DEFAULT 0,
          next_attempt_at TEXT,
          last_error TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inbox (
          event_id TEXT PRIMARY KEY,
          consumer TEXT NOT NULL,
          processed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
          id TEXT PRIMARY KEY,
          task_type TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          payload_json TEXT NOT NULL DEFAULT '{}',
          attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          next_attempt_at TEXT
        );

        CREATE TABLE IF NOT EXISTS idempotency_keys (
          key TEXT PRIMARY KEY,
          scope TEXT NOT NULL,
          response_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
          memory_id UNINDEXED,
          content,
          type UNINDEXED,
          status UNINDEXED,
          tokenize = 'unicode61'
        );

        CREATE INDEX IF NOT EXISTS idx_memories_type_status ON memories(type, status);
        CREATE INDEX IF NOT EXISTS idx_observations_kind ON observations(source_kind);
        CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status, next_attempt_at);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, next_attempt_at);
        """,
    ),
]


def apply_migrations(conn: sqlite3.Connection) -> list[str]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )
    applied = {
        row[0]
        for row in conn.execute("SELECT id FROM schema_migrations").fetchall()
    }
    done: list[str] = []
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for mid, sql in MIGRATIONS:
        if mid in applied:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(id, applied_at) VALUES (?, ?)",
            (mid, now),
        )
        done.append(mid)
    conn.commit()
    return done
