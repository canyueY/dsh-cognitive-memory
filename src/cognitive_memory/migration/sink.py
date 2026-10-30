# -*- coding: utf-8 -*-
"""迁移写入端：进程内 MemoryService / 可替换协议。"""

from __future__ import annotations

from typing import Any, Protocol

from cognitive_memory.migration.mapping import truncate_for_memory, truncate_for_observation
from cognitive_memory.migration.models import MappedRecord, WriteResult


class MigrationSink(Protocol):
    def write(self, mapped: MappedRecord, *, dry_run: bool = False) -> WriteResult: ...


class InProcessSink:
    """写入本地 `MemoryService`（capture_observation + propose_memory）。"""

    def __init__(self, service: Any, *, producer: str = "migrate.amem") -> None:
        self.service = service
        self.producer = producer

    def write(self, mapped: MappedRecord, *, dry_run: bool = False) -> WriteResult:
        if mapped.skip_reason:
            return WriteResult(
                source_id=mapped.source_id,
                ok=True,
                skipped=True,
                dry_run=dry_run,
                error=mapped.skip_reason,
            )
        if dry_run:
            return WriteResult(source_id=mapped.source_id, ok=True, dry_run=True)

        from cognitive_memory.domain.models import (
            MemoryProposeIn,
            MemoryStatus,
            MemoryType,
            ObservationIn,
            SourceKind,
        )

        try:
            mem_type = MemoryType(mapped.memory_type)
        except ValueError:
            mem_type = MemoryType.SEMANTIC
        try:
            mem_status = MemoryStatus(mapped.memory_status)
        except ValueError:
            mem_status = MemoryStatus.CANDIDATE

        try:
            obs = self.service.capture_observation(
                ObservationIn(
                    source_kind=SourceKind.SYSTEM,
                    content=truncate_for_observation(mapped.content),
                    occurred_at=mapped.occurred_at,
                    producer=self.producer,
                    metadata=mapped.observation_metadata,
                    idempotency_key=mapped.observation_idempotency_key,
                )
            )
            mem = self.service.propose_memory(
                MemoryProposeIn(
                    type=mem_type,
                    status=mem_status,
                    content=truncate_for_memory(mapped.content),
                    source_ids=[obs.id],
                    metadata=mapped.memory_metadata,
                    idempotency_key=mapped.memory_idempotency_key,
                )
            )
            return WriteResult(
                source_id=mapped.source_id,
                ok=True,
                observation_id=getattr(obs, "id", None),
                memory_id=getattr(mem, "id", None),
            )
        except Exception as exc:  # noqa: BLE001 — 引擎层汇总错误
            return WriteResult(source_id=mapped.source_id, ok=False, error=str(exc))


class RecordingSink:
    """测试用：只记录调用，不落库。"""

    def __init__(self) -> None:
        self.writes: list[MappedRecord] = []

    def write(self, mapped: MappedRecord, *, dry_run: bool = False) -> WriteResult:
        if mapped.skip_reason:
            return WriteResult(
                source_id=mapped.source_id,
                ok=True,
                skipped=True,
                dry_run=dry_run,
                error=mapped.skip_reason,
            )
        self.writes.append(mapped)
        if dry_run:
            return WriteResult(source_id=mapped.source_id, ok=True, dry_run=True)
        return WriteResult(
            source_id=mapped.source_id,
            ok=True,
            observation_id=f"obs-{mapped.source_id}",
            memory_id=f"mem-{mapped.source_id}",
        )
