# -*- coding: utf-8 -*-
"""强化学习 stubs：架构预留，执行入口硬锁 Capability Gate。"""

from __future__ import annotations

from typing import Any

from cognitive_memory.governance.capability_gate import (
    CapabilityLockedError,
    check_capability,
    require_capability,
)
from cognitive_memory.storage.db import Database


def record_feedback_sample(
    db: Database,
    sample: dict[str, Any],
) -> dict[str, Any]:
    """RL-A：仅记录情境/行为/反馈样本元数据（不训练）。无 Gate 要求。"""
    # 样本应引用 memory/schema id，不复制个人 LT 正文为第二权威源
    return {
        "ok": True,
        "phase": "RL-A",
        "recorded": True,
        "sample_keys": sorted(sample.keys()),
        "note": "feedback logged conceptually; buffer persistence deferred",
    }


def run_offline_training(db: Database, request: dict[str, Any] | None = None) -> dict[str, Any]:
    """RL-B：离线训练入口 — 默认 LOCKED。"""
    try:
        require_capability(db, "RL_OFFLINE_TRAINING")
    except CapabilityLockedError as exc:
        pack = check_capability(db, "RL_OFFLINE_TRAINING")
        return {
            "ok": False,
            "detail": "capability_locked",
            "capability": exc.capability,
            "gate": pack,
        }
    return {
        "ok": False,
        "detail": "not_implemented",
        "note": "trainer stub after Gate unlock",
        "request": request or {},
    }


def deploy_policy(db: Database, policy_id: str) -> dict[str, Any]:
    """RL-C：生产策略部署 — 独立 Gate，默认 LOCKED。"""
    try:
        require_capability(db, "RL_POLICY_DEPLOYMENT")
    except CapabilityLockedError as exc:
        return {
            "ok": False,
            "detail": "capability_locked",
            "capability": exc.capability,
            "policy_id": policy_id,
            "gate": check_capability(db, "RL_POLICY_DEPLOYMENT"),
        }
    return {
        "ok": False,
        "detail": "not_implemented",
        "policy_id": policy_id,
    }
