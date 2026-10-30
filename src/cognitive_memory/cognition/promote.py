# -*- coding: utf-8 -*-
"""慢速通道：候选晋升（E2.3 条件显式化）。禁止静默 ACTIVE。"""

from __future__ import annotations

from typing import Any

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import MemoryStatus, MemoryType, MemoryUpdateIn

# 显式晋升规则（文档化 + 测试锚点）
PROMOTION_RULES: dict[str, Any] = {
    "version": "2.0-e2.3",
    "rules": [
        {
            "id": "force_activate",
            "when": "metadata.force_activate == true",
            "effect": "candidate → active",
        },
        {
            "id": "multi_evidence",
            "when": "len(evidence) >= 2",
            "effect": "candidate → active",
        },
        {
            "id": "user_semantic_fact",
            "when": "type==semantic AND metadata.from_user==true",
            "effect": "candidate → active",
        },
        {
            "id": "useful_feedback",
            "when": "useful_feedback_count >= 1",
            "effect": "candidate → active",
        },
    ],
    "forbidden": [
        "silent_active_without_rule",
        "agent_inference_direct_active",
    ],
}


def evaluate_promotion(data: dict[str, Any]) -> dict[str, Any]:
    """只评估、不写库。返回 matched 规则 id 列表。"""
    if data.get("status") != MemoryStatus.CANDIDATE.value:
        return {"promote": False, "matched": [], "reason": "not_candidate"}
    evidence = data.get("evidence") or []
    meta = data.get("metadata") or {}
    matched: list[str] = []
    if bool(meta.get("force_activate")):
        matched.append("force_activate")
    if len(evidence) >= 2:
        matched.append("multi_evidence")
    if data.get("type") == MemoryType.SEMANTIC.value and meta.get("from_user") is True:
        matched.append("user_semantic_fact")
    useful_n = int(data.get("useful_feedback_count") or meta.get("useful_feedback_count") or 0)
    if useful_n >= 1:
        matched.append("useful_feedback")
    # 推断类禁止仅凭单条无用户标记晋升（useful_feedback / multi_evidence / force 可放行）
    epistemic = str(meta.get("epistemic") or "")
    strong = {"force_activate", "multi_evidence", "useful_feedback"}
    if epistemic == "inference" and not (strong & set(matched)):
        return {
            "promote": False,
            "matched": matched,
            "reason": "inference_requires_stronger_evidence",
        }
    return {
        "promote": bool(matched),
        "matched": matched,
        "reason": "matched" if matched else "no_rule",
    }


def maybe_promote(service: MemoryService, memory_id: str) -> bool:
    if not memory_id:
        return False
    data = service.get_memory(memory_id, include_evidence=True)
    decision = evaluate_promotion(data)
    if not decision.get("promote"):
        return False
    service.update_memory(
        memory_id,
        MemoryUpdateIn(status=MemoryStatus.ACTIVE, expected_version=data.get("version")),
    )
    return True


def maybe_promote_with_feedback(
    service: MemoryService, memory_id: str, *, useful_count: int
) -> bool:
    """feedback → promote 闭环入口：把 useful 计数注入评估。"""
    if not memory_id:
        return False
    data = service.get_memory(memory_id, include_evidence=True)
    data["useful_feedback_count"] = int(useful_count)
    meta = dict(data.get("metadata") or {})
    meta["useful_feedback_count"] = int(useful_count)
    data["metadata"] = meta
    decision = evaluate_promotion(data)
    if not decision.get("promote"):
        return False
    service.update_memory(
        memory_id,
        MemoryUpdateIn(status=MemoryStatus.ACTIVE, expected_version=data.get("version")),
    )
    return True
