# -*- coding: utf-8 -*-
"""价值与伦理决策辅助 stubs（V-A 可规则分析；V-B/C 受 Gate）。"""

from __future__ import annotations

from typing import Any

from cognitive_memory.governance.capability_gate import (
    CapabilityLockedError,
    check_capability,
    require_capability,
)
from cognitive_memory.storage.db import Database

# 软偏好维度（可学习）；硬约束永不在此调整
VALUE_DIMENSIONS = (
    "harm_avoidance",
    "fairness",
    "honesty",
    "autonomy",
    "privacy",
    "commitment",
    "user_preference",
)

HARD_CONSTRAINTS = (
    "safety_rules",
    "privacy_boundary",
    "user_authorization",
    "system_permissions",
    "capability_gate",
)


def analyze_value_conflict_basic(
    intent: str,
    *,
    stakeholders: list[str] | None = None,
    proposed_action: str = "",
) -> dict[str, Any]:
    """V-A：基础价值冲突说明（无模型训练）。"""
    dims = list(VALUE_DIMENSIONS)
    conflicts: list[dict[str, str]] = []
    text = f"{intent} {proposed_action}".lower()
    if any(k in text for k in ("隐私", "privacy", "泄露", "分享联系人")):
        conflicts.append(
            {
                "between": "privacy vs user_preference",
                "note": "可能涉及隐私硬约束，不可被软偏好覆盖",
            }
        )
    if any(k in text for k in ("授权", "权限", "绕过", "bypass")):
        conflicts.append(
            {
                "between": "user_authorization vs autonomy",
                "note": "授权边界属硬约束",
            }
        )
    return {
        "ok": True,
        "phase": "V-A",
        "intent": intent,
        "stakeholders": stakeholders or ["user"],
        "dimensions": dims,
        "hard_constraints": list(HARD_CONSTRAINTS),
        "conflicts": conflicts,
        "uncertainty": "high" if not conflicts else "medium",
        "note": "解释冲突，不输出单一道德总分",
    }


def run_advanced_value_evaluation(
    db: Database,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """V-B：复杂价值模型 — Gate LOCKED 前禁止。"""
    try:
        require_capability(db, "ADVANCED_VALUE_EVALUATION")
    except CapabilityLockedError as exc:
        return {
            "ok": False,
            "detail": "capability_locked",
            "capability": exc.capability,
            "gate": check_capability(db, "ADVANCED_VALUE_EVALUATION"),
        }
    return {
        "ok": False,
        "detail": "not_implemented",
        "payload": payload or {},
    }


def adapt_value_model(db: Database, patch: dict[str, Any] | None = None) -> dict[str, Any]:
    """V-C：自主价值模型调整 — 严格 Gate；硬约束不可改。"""
    try:
        require_capability(db, "AUTONOMOUS_VALUE_ADAPTATION")
    except CapabilityLockedError as exc:
        return {
            "ok": False,
            "detail": "capability_locked",
            "capability": exc.capability,
            "gate": check_capability(db, "AUTONOMOUS_VALUE_ADAPTATION"),
        }
    # 即使解锁，硬约束键必须拒绝
    bad = [k for k in (patch or {}) if k in HARD_CONSTRAINTS]
    if bad:
        return {"ok": False, "detail": "immutable_hard_constraint", "keys": bad}
    return {"ok": False, "detail": "not_implemented", "patch": patch or {}}
