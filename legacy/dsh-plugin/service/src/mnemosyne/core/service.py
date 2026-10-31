# -*- coding: utf-8 -*-
"""MemoryService — 唯一业务核心（MCP / REST 共用）。"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from mnemosyne.domain.models import (
    ContextBuildIn,
    ContextBuildOut,
    FeedbackIn,
    Memory,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    MemoryUpdateIn,
    Observation,
    ObservationIn,
    SearchQuery,
    Task,
    TaskCreateIn,
)
from mnemosyne.events.bus import EventBus
from mnemosyne.storage.db import Database
from mnemosyne.storage.ids import new_id


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _loads(s: str | None, default: Any) -> Any:
    if not s:
        return default
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return default


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_QUERY_SPLIT_RE = re.compile(r"[\s,，。.!！?？;；:：/\\|]+")


def _query_terms(query: str, *, max_terms: int = 12) -> list[str]:
    """Chinese has no spaces; derive 2-char shingles for LIKE fallback."""
    terms: list[str] = []
    for token in _QUERY_SPLIT_RE.split(query or ""):
        token = token.strip()
        if not token:
            continue
        if _CJK_RE.search(token):
            if len(token) <= 2:
                terms.append(token)
            else:
                terms.extend(token[i:i + 2] for i in range(len(token) - 1))
        else:
            terms.append(token)
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            out.append(term)
        if len(out) >= max_terms:
            break
    return out


class ConflictError(Exception):
    def __init__(self, message: str, *, code: str = "conflict"):
        super().__init__(message)
        self.code = code


class NotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.code = "not_found"


class MemoryService:
    def __init__(
        self,
        db: Database,
        bus: EventBus | None = None,
        *,
        context_token_budget: int = 1200,
    ):
        self.db = db
        self.bus = bus or EventBus()
        self.context_token_budget = context_token_budget
        self.db.ensure_schema()

    # ---------- helpers ----------

    def _row_memory(self, row: sqlite3.Row) -> Memory:
        return Memory(
            id=row["id"],
            type=MemoryType(row["type"]),
            status=MemoryStatus(row["status"]),
            content=row["content"],
            source_ids=_loads(row["source_ids_json"], []),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_confirmed_at=row["last_confirmed_at"],
            version=int(row["version"]),
            confidence=row["confidence"],
            expires_at=row["expires_at"],
            metadata=_loads(row["metadata_json"], {}),
        )

    def _idempotent_get(self, conn: sqlite3.Connection, key: str | None, scope: str) -> Any | None:
        if not key:
            return None
        row = conn.execute(
            "SELECT response_json FROM idempotency_keys WHERE key=? AND scope=?",
            (key, scope),
        ).fetchone()
        if not row:
            return None
        return _loads(row["response_json"], None)

    def _idempotent_put(
        self, conn: sqlite3.Connection, key: str | None, scope: str, response: Any
    ) -> None:
        if not key:
            return
        conn.execute(
            """
            INSERT OR REPLACE INTO idempotency_keys(key, scope, response_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, scope, json.dumps(response, ensure_ascii=False), _now()),
        )

    def _emit(
        self,
        conn: sqlite3.Connection,
        event_type: str,
        payload: dict[str, Any],
        *,
        producer: str = "mnemosyne",
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> str:
        eid = new_id("evt")
        now = _now()
        envelope = {
            "event_id": eid,
            "event_type": event_type,
            "event_version": 1,
            "occurred_at": now,
            "recorded_at": now,
            "producer": producer,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "payload_version": 1,
            "payload": payload,
        }
        conn.execute(
            """
            INSERT INTO events(
              event_id, event_type, event_version, occurred_at, recorded_at,
              producer, correlation_id, causation_id, payload_version, payload_json
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                eid,
                event_type,
                now,
                now,
                producer,
                correlation_id,
                causation_id,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.execute(
            """
            INSERT INTO outbox(event_id, status, attempts, next_attempt_at, created_at, updated_at)
            VALUES (?, 'pending', 0, ?, ?, ?)
            """,
            (eid, now, now, now),
        )
        return eid

    def _snapshot_version(self, conn: sqlite3.Connection, mem: Memory) -> None:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_versions(memory_id, version, snapshot_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (mem.id, mem.version, mem.model_dump_json(), _now()),
        )

    def _fts_upsert(self, conn: sqlite3.Connection, mem: Memory) -> None:
        conn.execute("DELETE FROM memories_fts WHERE memory_id=?", (mem.id,))
        if mem.status == MemoryStatus.INVALIDATED:
            return
        conn.execute(
            "INSERT INTO memories_fts(memory_id, content, type, status) VALUES (?, ?, ?, ?)",
            (mem.id, mem.content, mem.type.value, mem.status.value),
        )

    # ---------- observations ----------

    def capture_observation(self, body: ObservationIn) -> Observation:
        with self.db.transaction() as conn:
            cached = self._idempotent_get(conn, body.idempotency_key, "observation")
            if cached:
                return Observation.model_validate(cached)
            oid = new_id("obs")
            now = _now()
            conn.execute(
                """
                INSERT INTO observations(
                  id, source_kind, content, occurred_at, created_at, producer,
                  correlation_id, data_ref, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    oid,
                    body.source_kind.value,
                    body.content,
                    body.occurred_at or now,
                    now,
                    body.producer,
                    body.correlation_id,
                    body.data_ref,
                    json.dumps(body.metadata, ensure_ascii=False),
                ),
            )
            obs = Observation(id=oid, created_at=now, **body.model_dump(exclude={"idempotency_key"}))
            self._emit(
                conn,
                "observation.captured",
                {"observation_id": oid, "source_kind": body.source_kind.value},
                producer=body.producer,
                correlation_id=body.correlation_id,
            )
            # 快速通道：对话类观察同步写一条 working 记忆
            if body.source_kind.value in ("dialog", "user_statement"):
                wid = new_id("mem")
                wm = Memory(
                    id=wid,
                    type=MemoryType.WORKING,
                    status=MemoryStatus.ACTIVE,
                    content=body.content[:2000],
                    source_ids=[oid],
                    created_at=now,
                    updated_at=now,
                    last_confirmed_at=now,
                    version=1,
                    metadata={"from_observation": oid},
                )
                self._insert_memory(conn, wm)
                self._emit(
                    conn,
                    "memory.activated",
                    {"memory_id": wid, "type": "working"},
                    producer=body.producer,
                    correlation_id=body.correlation_id,
                )
            # 慢速：请求归纳
            self._create_task_conn(
                conn,
                TaskCreateIn(
                    task_type="memory.consolidation",
                    payload={"observation_id": oid},
                ),
            )
            payload = obs.model_dump()
            self._idempotent_put(conn, body.idempotency_key, "observation", payload)
            return obs

    # ---------- memories ----------

    def _insert_memory(self, conn: sqlite3.Connection, mem: Memory) -> None:
        conn.execute(
            """
            INSERT INTO memories(
              id, type, status, content, source_ids_json, created_at, updated_at,
              last_confirmed_at, version, confidence, expires_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mem.id,
                mem.type.value,
                mem.status.value,
                mem.content,
                json.dumps(mem.source_ids, ensure_ascii=False),
                mem.created_at,
                mem.updated_at,
                mem.last_confirmed_at,
                mem.version,
                mem.confidence,
                mem.expires_at,
                json.dumps(mem.metadata, ensure_ascii=False),
            ),
        )
        self._snapshot_version(conn, mem)
        self._fts_upsert(conn, mem)
        for sid in mem.source_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO memory_evidence(memory_id, observation_id, relation, note, created_at)
                VALUES (?, ?, 'supports', '', ?)
                """,
                (mem.id, sid, _now()),
            )

    def propose_memory(self, body: MemoryProposeIn) -> Memory:
        with self.db.transaction() as conn:
            cached = self._idempotent_get(conn, body.idempotency_key, "memory_propose")
            if cached:
                return Memory.model_validate(cached)
            now = _now()
            mid = new_id("mem")
            mem = Memory(
                id=mid,
                type=body.type,
                status=body.status,
                content=body.content,
                source_ids=list(body.source_ids),
                created_at=now,
                updated_at=now,
                last_confirmed_at=now if body.status == MemoryStatus.ACTIVE else None,
                version=1,
                confidence=body.confidence,
                expires_at=body.expires_at,
                metadata=body.metadata,
            )
            self._insert_memory(conn, mem)
            self._emit(
                conn,
                "memory.candidate_created"
                if body.status == MemoryStatus.CANDIDATE
                else "memory.activated",
                {"memory_id": mid, "type": body.type.value, "status": body.status.value},
            )
            if body.status == MemoryStatus.CANDIDATE:
                self._create_task_conn(
                    conn,
                    TaskCreateIn(
                        task_type="memory.promote_check",
                        payload={"memory_id": mid},
                    ),
                )
            payload = mem.model_dump()
            self._idempotent_put(conn, body.idempotency_key, "memory_propose", payload)
            return mem

    def get_memory(self, memory_id: str, *, include_evidence: bool = False) -> dict[str, Any]:
        conn = self.db.connect()
        row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            raise NotFoundError(f"memory not found: {memory_id}")
        mem = self._row_memory(row)
        out = mem.model_dump()
        if include_evidence:
            ev = conn.execute(
                "SELECT observation_id, relation, note, created_at FROM memory_evidence WHERE memory_id=?",
                (memory_id,),
            ).fetchall()
            out["evidence"] = [dict(r) for r in ev]
            vers = conn.execute(
                "SELECT version, created_at FROM memory_versions WHERE memory_id=? ORDER BY version",
                (memory_id,),
            ).fetchall()
            out["versions"] = [dict(r) for r in vers]
        return out

    def update_memory(self, memory_id: str, body: MemoryUpdateIn) -> Memory:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                raise NotFoundError(f"memory not found: {memory_id}")
            mem = self._row_memory(row)
            if body.expected_version is not None and body.expected_version != mem.version:
                raise ConflictError(
                    f"version mismatch: expected {body.expected_version}, got {mem.version}",
                    code="version_conflict",
                )
            if body.content is not None:
                mem.content = body.content
            if body.status is not None:
                mem.status = body.status
            if body.metadata is not None:
                mem.metadata = body.metadata
            if body.confidence is not None:
                mem.confidence = body.confidence
            if body.expires_at is not None:
                mem.expires_at = body.expires_at
            mem.version += 1
            mem.updated_at = _now()
            if mem.status == MemoryStatus.ACTIVE:
                mem.last_confirmed_at = mem.updated_at
            conn.execute(
                """
                UPDATE memories SET
                  content=?, status=?, metadata_json=?, confidence=?, expires_at=?,
                  version=?, updated_at=?, last_confirmed_at=?
                WHERE id=?
                """,
                (
                    mem.content,
                    mem.status.value,
                    json.dumps(mem.metadata, ensure_ascii=False),
                    mem.confidence,
                    mem.expires_at,
                    mem.version,
                    mem.updated_at,
                    mem.last_confirmed_at,
                    mem.id,
                ),
            )
            self._snapshot_version(conn, mem)
            self._fts_upsert(conn, mem)
            et = (
                "memory.invalidated"
                if mem.status == MemoryStatus.INVALIDATED
                else "memory.updated"
            )
            self._emit(conn, et, {"memory_id": mem.id, "version": mem.version})
            return mem

    def forget_memory(self, memory_id: str, *, hard: bool = False) -> dict[str, Any]:
        """软删除默认：invalidated；hard=True 时清理主表+FTS+证据（版本保留审计）。"""
        if not hard:
            return self.update_memory(
                memory_id,
                MemoryUpdateIn(status=MemoryStatus.INVALIDATED),
            ).model_dump()
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                raise NotFoundError(f"memory not found: {memory_id}")
            conn.execute("DELETE FROM memories_fts WHERE memory_id=?", (memory_id,))
            conn.execute("DELETE FROM memory_evidence WHERE memory_id=?", (memory_id,))
            conn.execute("DELETE FROM memory_feedback WHERE memory_id=?", (memory_id,))
            conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
            self._emit(conn, "memory.invalidated", {"memory_id": memory_id, "hard": True})
            return {"id": memory_id, "deleted": True, "hard": True}

    def search(self, q: SearchQuery) -> list[Memory]:
        conn = self.db.connect()
        limit = max(1, min(50, int(q.limit or 10)))
        statuses = [s.value for s in (q.status or [MemoryStatus.ACTIVE, MemoryStatus.CANDIDATE])]
        types = [t.value for t in (q.types or list(MemoryType))]
        query = (q.query or "").strip()
        rows: list[sqlite3.Row]
        if query:
            # FTS5：简单转义双引号
            safe = query.replace('"', '""')
            # FTS5：多词用 AND；失败则降级 LIKE
            fts_q = " AND ".join(
                f'"{t.replace(chr(34), "")}"' for t in safe.split() if t.strip()
            ) or f'"{safe}"'
            sql = """
              SELECT m.* FROM memories_fts f
              JOIN memories m ON m.id = f.memory_id
              WHERE f MATCH ?
                AND m.status IN ({sts})
                AND m.type IN ({tys})
              LIMIT ?
            """.format(
                sts=",".join("?" * len(statuses)),
                tys=",".join("?" * len(types)),
            )
            try:
                rows = conn.execute(
                    sql, (fts_q, *statuses, *types, limit)
                ).fetchall()
            except (sqlite3.OperationalError, SystemError):
                # Some Python/SQLite builds raise SystemError for a NULL FTS
                # result instead of an sqlite3 error; degrade to LIKE either way.
                rows = []
            if not rows:
                # 降级：LIKE
                like = f"%{query}%"
                rows = conn.execute(
                    f"""
                    SELECT * FROM memories
                    WHERE content LIKE ?
                      AND status IN ({",".join("?" * len(statuses))})
                      AND type IN ({",".join("?" * len(types))})
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (like, *statuses, *types, limit),
                ).fetchall()
                if not rows:
                    # 中文没有空格：整句 FTS/LIKE 都命中不了时，用 2 字滑窗再试一次
                    terms = _query_terms(query)
                    if terms:
                        likes = " OR ".join(["content LIKE ?"] * len(terms))
                        rows = conn.execute(
                            f"""
                            SELECT * FROM memories
                            WHERE ({likes})
                              AND status IN ({",".join("?" * len(statuses))})
                              AND type IN ({",".join("?" * len(types))})
                            ORDER BY updated_at DESC
                            LIMIT ?
                            """,
                            (*[f"%{t}%" for t in terms], *statuses, *types, limit),
                        ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT * FROM memories
                WHERE status IN ({",".join("?" * len(statuses))})
                  AND type IN ({",".join("?" * len(types))})
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (*statuses, *types, limit),
            ).fetchall()
        return [self._row_memory(r) for r in rows]

    def build_context(self, body: ContextBuildIn) -> ContextBuildOut:
        budget = body.token_budget or self.context_token_budget
        hits = self.search(
            SearchQuery(
                query=body.query,
                types=body.types,
                limit=body.limit,
            )
        )
        fragments: list[dict[str, Any]] = []
        used = 0
        lines: list[str] = ["【演化记忆·仅供参考】"]
        for m in hits:
            est = max(1, len(m.content) // 2)
            if used + est > budget and fragments:
                break
            frag = {
                "id": m.id,
                "type": m.type.value,
                "status": m.status.value,
                "content": m.content,
                "version": m.version,
                "source_ids": m.source_ids,
                "token_estimate": est,
            }
            fragments.append(frag)
            used += est
            lines.append(f"- [{m.type.value}] {m.content}")
        return ContextBuildOut(
            fragments=fragments,
            token_estimate=used,
            brief="\n".join(lines) if fragments else "【演化记忆】暂无相关条目",
        )

    def feedback(self, body: FeedbackIn) -> dict[str, Any]:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT id FROM memories WHERE id=?", (body.memory_id,)).fetchone()
            if not row:
                raise NotFoundError(f"memory not found: {body.memory_id}")
            now = _now()
            conn.execute(
                """
                INSERT INTO memory_feedback(memory_id, useful, incorrect, note, producer, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    body.memory_id,
                    None if body.useful is None else int(bool(body.useful)),
                    None if body.incorrect is None else int(bool(body.incorrect)),
                    body.note,
                    body.producer,
                    now,
                ),
            )
            self._emit(
                conn,
                "memory.feedback_received",
                {
                    "memory_id": body.memory_id,
                    "useful": body.useful,
                    "incorrect": body.incorrect,
                },
                producer=body.producer,
            )
            if body.incorrect:
                self._create_task_conn(
                    conn,
                    TaskCreateIn(
                        task_type="memory.review_feedback",
                        payload={"memory_id": body.memory_id, "note": body.note},
                    ),
                )
            return {"ok": True, "memory_id": body.memory_id}

    # ---------- tasks ----------

    def _create_task_conn(self, conn: sqlite3.Connection, body: TaskCreateIn) -> Task:
        cached = self._idempotent_get(conn, body.idempotency_key, "task")
        if cached:
            return Task.model_validate(cached)
        tid = new_id("task")
        now = _now()
        conn.execute(
            """
            INSERT INTO tasks(id, task_type, status, payload_json, attempts, created_at, updated_at, next_attempt_at)
            VALUES (?, ?, 'pending', ?, 0, ?, ?, ?)
            """,
            (tid, body.task_type, json.dumps(body.payload, ensure_ascii=False), now, now, now),
        )
        task = Task(
            id=tid,
            task_type=body.task_type,
            status="pending",
            payload=body.payload,
            created_at=now,
            updated_at=now,
        )
        self._idempotent_put(conn, body.idempotency_key, "task", task.model_dump())
        return task

    def create_task(self, body: TaskCreateIn) -> Task:
        with self.db.transaction() as conn:
            return self._create_task_conn(conn, body)

    def get_task(self, task_id: str) -> Task:
        row = self.db.connect().execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise NotFoundError(f"task not found: {task_id}")
        return Task(
            id=row["id"],
            task_type=row["task_type"],
            status=row["status"],
            payload=_loads(row["payload_json"], {}),
            attempts=int(row["attempts"]),
            last_error=row["last_error"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def health(self) -> dict[str, Any]:
        conn = self.db.connect()
        mem_n = conn.execute("SELECT COUNT(*) AS n FROM memories").fetchone()["n"]
        obs_n = conn.execute("SELECT COUNT(*) AS n FROM observations").fetchone()["n"]
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM outbox WHERE status='pending'"
        ).fetchone()["n"]
        return {
            "ok": True,
            "service": "mnemosyne",
            "version": "0.1.0",
            "memories": mem_n,
            "observations": obs_n,
            "outbox_pending": pending,
            "time": _now(),
        }
