# -*- coding: utf-8 -*-
"""慢速通道：候选晋升规则（V1：多证据 / 用户明确陈述可激活）。"""

from __future__ import annotations

from mnemosyne.core.service import MemoryService
from mnemosyne.domain.models import MemoryStatus, MemoryType, MemoryUpdateIn


def maybe_promote(service: MemoryService, memory_id: str) -> bool:
    if not memory_id:
        return False
    data = service.get_memory(memory_id, include_evidence=True)
    if data.get("status") != MemoryStatus.CANDIDATE.value:
        return False
    evidence = data.get("evidence") or []
    meta = data.get("metadata") or {}
    # 用户明确陈述 / 证据≥2 / 标记 force_activate
    promote = bool(meta.get("force_activate")) or len(evidence) >= 2
    if data.get("type") == MemoryType.SEMANTIC.value and meta.get("from_user") is True:
        promote = True
    if not promote:
        return False
    service.update_memory(
        memory_id,
        MemoryUpdateIn(status=MemoryStatus.ACTIVE, expected_version=data.get("version")),
    )
    return True
