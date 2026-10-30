# -*- coding: utf-8 -*-
"""A-MEM 记录 → 认知记忆 Observation / Memory 映射。"""

from __future__ import annotations

from cognitive_memory.migration.models import MappedRecord, SourceRecord

_EPISODIC_HINTS = ("event", "episode", "日记", "对话", "chat", "session", "episodic")
_PROCEDURAL_HINTS = ("how", "步骤", "procedure", "skill", "习惯", "workflow")
_WORKING_HINTS = ("todo", "临时", "working", "scratch")


def _infer_memory_type(tags: list[str], content: str) -> str:
    lower_tags = [str(t).strip().lower() for t in tags if str(t).strip()]
    blob = " ".join(lower_tags) + " " + (content[:120].lower())
    if any(h in blob for h in _WORKING_HINTS):
        return "working"
    if any(h in blob for h in _PROCEDURAL_HINTS):
        return "procedural"
    if any(h in blob for h in _EPISODIC_HINTS):
        return "episodic"
    return "semantic"


def map_source_record(
    record: SourceRecord,
    *,
    producer: str = "migrate.amem",
    min_content_len: int = 2,
    content_obs_limit: int = 4000,
    content_mem_limit: int = 2000,
) -> MappedRecord:
    content = (record.content or "").strip()
    tags = [str(t).strip() for t in (record.tags or []) if str(t).strip()]
    source_id = str(record.source_id or "").strip() or f"hash:{hash(content) & 0xFFFFFFFF:x}"

    if len(content) < min_content_len:
        return MappedRecord(
            source_id=source_id,
            content=content,
            memory_type="semantic",
            memory_status="candidate",
            tags=tags,
            observation_idempotency_key=f"amem:{source_id}",
            memory_idempotency_key=f"amem-mem:{source_id}",
            observation_metadata={},
            memory_metadata={},
            occurred_at=record.occurred_at,
            skip_reason="content_too_short",
        )

    mem_type = _infer_memory_type(tags, content)
    obs_meta = {
        "amem_id": source_id,
        "tags": tags,
        "migrated_from": "a_mem",
        **(record.metadata or {}),
    }
    mem_meta = {
        "migrated_from": "a_mem",
        "amem_id": source_id,
        "tags": tags,
        "producer": producer,
    }
    return MappedRecord(
        source_id=source_id,
        content=content,
        memory_type=mem_type,
        memory_status="candidate",
        tags=tags,
        observation_idempotency_key=f"amem:{source_id}",
        memory_idempotency_key=f"amem-mem:{source_id}",
        observation_metadata=obs_meta,
        memory_metadata=mem_meta,
        occurred_at=record.occurred_at,
        skip_reason=None,
    )


def truncate_for_observation(content: str, limit: int = 4000) -> str:
    return content[: max(1, int(limit))]


def truncate_for_memory(content: str, limit: int = 2000) -> str:
    return content[: max(1, int(limit))]
