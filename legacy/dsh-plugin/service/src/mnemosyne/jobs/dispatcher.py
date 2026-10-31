# -*- coding: utf-8 -*-
"""Outbox dispatcher + 任务 worker（至少一次投递 + 幂等消费）。"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from mnemosyne.core.service import MemoryService
from mnemosyne.events.bus import EventBus
from mnemosyne.storage.db import Database


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


class BackgroundRuntime:
    def __init__(
        self,
        db: Database,
        bus: EventBus,
        service: MemoryService,
        *,
        poll_interval_ms: int = 200,
        max_retries: int = 5,
    ):
        self.db = db
        self.bus = bus
        self.service = service
        self.poll_interval = max(0.05, poll_interval_ms / 1000.0)
        self.max_retries = max_retries
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._task_handlers: dict[str, Callable[[dict[str, Any]], None]] = {
            "memory.consolidation": self._handle_consolidation,
            "memory.promote_check": self._handle_promote,
            "memory.review_feedback": self._handle_feedback_review,
        }

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="cm-dispatcher", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.dispatch_outbox_once()
                self.run_tasks_once()
            except Exception as exc:  # noqa: BLE001
                print(f"[dispatcher] loop error: {exc}", flush=True)
            self._stop.wait(self.poll_interval)

    def dispatch_outbox_once(self, limit: int = 32) -> int:
        conn = self.db.connect()
        now = _now()
        rows = conn.execute(
            """
            SELECT o.id, o.event_id, o.attempts, e.event_type, e.payload_json,
                   e.producer, e.correlation_id, e.causation_id, e.occurred_at, e.recorded_at
            FROM outbox o
            JOIN events e ON e.event_id = o.event_id
            WHERE o.status='pending' AND (o.next_attempt_at IS NULL OR o.next_attempt_at <= ?)
            ORDER BY o.id ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        n = 0
        for row in rows:
            event_id = row["event_id"]
            consumer = "local_bus"
            exists = conn.execute(
                "SELECT 1 FROM inbox WHERE event_id=? AND consumer=?",
                (event_id, consumer),
            ).fetchone()
            envelope = {
                "event_id": event_id,
                "event_type": row["event_type"],
                "event_version": 1,
                "occurred_at": row["occurred_at"],
                "recorded_at": row["recorded_at"],
                "producer": row["producer"],
                "correlation_id": row["correlation_id"],
                "causation_id": row["causation_id"],
                "payload_version": 1,
                "payload": json.loads(row["payload_json"] or "{}"),
            }
            try:
                if not exists:
                    self.bus.publish_local(envelope)
                    conn.execute(
                        "INSERT OR IGNORE INTO inbox(event_id, consumer, processed_at) VALUES (?, ?, ?)",
                        (event_id, consumer, _now()),
                    )
                conn.execute(
                    "UPDATE outbox SET status='delivered', updated_at=? WHERE event_id=?",
                    (_now(), event_id),
                )
                conn.commit()
                n += 1
            except Exception as exc:  # noqa: BLE001
                attempts = int(row["attempts"]) + 1
                if attempts >= self.max_retries:
                    status = "dead"
                    next_at = None
                else:
                    status = "pending"
                    next_at = (_now_dt() + timedelta(seconds=2 ** attempts)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                    self.bus.publish_local(
                        {
                            "event_id": f"retry_{event_id}_{attempts}",
                            "event_type": "task.retry_scheduled",
                            "event_version": 1,
                            "occurred_at": _now(),
                            "recorded_at": _now(),
                            "producer": "dispatcher",
                            "correlation_id": event_id,
                            "causation_id": event_id,
                            "payload_version": 1,
                            "payload": {"event_id": event_id, "attempts": attempts},
                        }
                    )
                conn.execute(
                    """
                    UPDATE outbox SET status=?, attempts=?, next_attempt_at=?, last_error=?, updated_at=?
                    WHERE event_id=?
                    """,
                    (status, attempts, next_at, str(exc)[:500], _now(), event_id),
                )
                conn.commit()
        return n

    def run_tasks_once(self, limit: int = 16) -> int:
        conn = self.db.connect()
        now = _now()
        rows = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status='pending' AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        n = 0
        for row in rows:
            tid = row["id"]
            ttype = row["task_type"]
            payload = json.loads(row["payload_json"] or "{}")
            handler = self._task_handlers.get(ttype)
            conn.execute(
                "UPDATE tasks SET status='running', updated_at=? WHERE id=?",
                (_now(), tid),
            )
            conn.commit()
            try:
                if handler:
                    handler(payload)
                conn.execute(
                    "UPDATE tasks SET status='done', updated_at=?, last_error='' WHERE id=?",
                    (_now(), tid),
                )
                conn.commit()
                n += 1
            except Exception as exc:  # noqa: BLE001
                attempts = int(row["attempts"]) + 1
                if attempts >= self.max_retries:
                    status = "dead"
                    next_at = None
                else:
                    status = "pending"
                    next_at = (_now_dt() + timedelta(seconds=2 ** attempts)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                conn.execute(
                    """
                    UPDATE tasks SET status=?, attempts=?, next_attempt_at=?, last_error=?, updated_at=?
                    WHERE id=?
                    """,
                    (status, attempts, next_at, str(exc)[:500], _now(), tid),
                )
                conn.commit()
        return n

    def _handle_consolidation(self, payload: dict[str, Any]) -> None:
        """慢速通道 V1：把观察整理为 episodic 候选（规则式，可后续换 LLM）。"""
        from mnemosyne.cognition.consolidate import consolidate_observation

        consolidate_observation(self.service, payload.get("observation_id") or "")

    def _handle_promote(self, payload: dict[str, Any]) -> None:
        from mnemosyne.cognition.promote import maybe_promote

        maybe_promote(self.service, payload.get("memory_id") or "")

    def _handle_feedback_review(self, payload: dict[str, Any]) -> None:
        mid = payload.get("memory_id") or ""
        if not mid:
            return
        # 标记不正确 → 失效
        from mnemosyne.domain.models import MemoryStatus, MemoryUpdateIn

        self.service.update_memory(mid, MemoryUpdateIn(status=MemoryStatus.INVALIDATED))
