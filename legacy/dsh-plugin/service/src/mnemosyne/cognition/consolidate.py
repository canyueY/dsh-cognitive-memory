# -*- coding: utf-8 -*-
"""慢速通道：观察 → 情节候选（V1 规则版，可替换为 LLM）。"""

from __future__ import annotations

import json
import sqlite3

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import MemoryProposeIn, MemoryStatus, MemoryType, SourceKind


def consolidate_observation(service: MemoryService, observation_id: str) -> str | None:
    if not observation_id:
        return None
    conn = service.db.connect()
    row = conn.execute("SELECT * FROM observations WHERE id=?", (observation_id,)).fetchone()
    if not row:
        return None
    # 已有以该观察为证据的 episodic → 跳过
    exists = conn.execute(
        """
        SELECT m.id FROM memories m
        JOIN memory_evidence e ON e.memory_id = m.id
        WHERE e.observation_id=? AND m.type='episodic'
        LIMIT 1
        """,
        (observation_id,),
    ).fetchone()
    if exists:
        return exists["id"]

    kind = row["source_kind"]
    content = row["content"]
    # 对话类已有 working；视频/系统观察生成 episodic 候选
    if kind in (SourceKind.DIALOG.value, SourceKind.USER_STATEMENT.value):
        # 从 working 提升为 episodic 候选摘要
        summary = f"对话片段：{content[:400]}"
        mem_type = MemoryType.EPISODIC
        status = MemoryStatus.CANDIDATE
    elif kind == SourceKind.VIDEO_OBSERVATION.value:
        summary = f"视频观察：{content[:500]}"
        mem_type = MemoryType.EPISODIC
        status = MemoryStatus.CANDIDATE
    else:
        summary = content[:500]
        mem_type = MemoryType.EPISODIC
        status = MemoryStatus.CANDIDATE

    mem = service.propose_memory(
        MemoryProposeIn(
            type=mem_type,
            status=status,
            content=summary,
            source_ids=[observation_id],
            metadata={"consolidation": "rule_v1", "source_kind": kind},
            idempotency_key=f"consol:{observation_id}",
        )
    )
    return mem.id
