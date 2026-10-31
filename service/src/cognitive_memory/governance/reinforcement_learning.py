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
    """RL-A：写入 first-class Experience（不训练）。无 Gate 要求。"""
    # 样本应引用 memory/schema id，不复制个人 LT 正文为第二权威源
    from cognitive_memory.strategy.experience_store import ExperienceStore

    ctx = sample.get("context") if isinstance(sample.get("context"), dict) else {}
    action = sample.get("action") if isinstance(sample.get("action"), dict) else {}
    outcome = sample.get("outcome") if isinstance(sample.get("outcome"), dict) else {}
    memory_ids = sample.get("memory_ids") if isinstance(sample.get("memory_ids"), list) else []
    claim_ids = sample.get("claim_ids") if isinstance(sample.get("claim_ids"), list) else []
    reward = sample.get("reward")
    if reward is not None and not isinstance(reward, (int, float)):
        reward = None
    bank_id = str(sample.get("bank_id") or "personal")
    exp = ExperienceStore(db).create(
        context=ctx,
        action=action,
        outcome=outcome,
        memory_ids=[str(x) for x in memory_ids],
        claim_ids=[str(x) for x in claim_ids],
        reward=float(reward) if reward is not None else None,
        bank_id=bank_id,
        source=str(sample.get("source") or "rl_feedback"),
    )
    return {
        "ok": True,
        "phase": "RL-A",
        "recorded": True,
        "experience_id": exp.get("id"),
        "sample_keys": sorted(sample.keys()),
        "note": "Experience persisted; training still gated",
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
