# -*- coding: utf-8 -*-
"""反馈学习：区分用户明确反馈、实际结果、Agent 自我评估。

不把三者混成一个“useful=true”：
- user_explicit 走既有 memory_feedback / promote 闭环；
- outcome 按成功/失败调整置信度，但不直接晋升；
- self_eval 只做低权重校准，必须可审计。
"""
from __future__ import annotations

from typing import Any

from cognitive_memory.core.service import MemoryService
from cognitive_memory.domain.models import FeedbackIn, MemoryUpdateIn

USER_EXPLICIT = "user_explicit"
OUTCOME = "outcome"
SELF_EVAL = "self_eval"


def classify_feedback(
    *,
    source: str,
    useful: bool | None = None,
    incorrect: bool | None = None,
    outcome: str | None = None,
    self_score: float | None = None,
) -> dict[str, Any]:
    """返回统一的学习信号；未知来源降级为 self_eval。"""
    src = source if source in (USER_EXPLICIT, OUTCOME, SELF_EVAL) else SELF_EVAL
    signal = 0.0
    if incorrect is True:
        signal = -1.0
    elif useful is True:
        signal = 1.0
    elif outcome in ("success", "ok", "resolved"):
        signal = 0.8
    elif outcome in ("failure", "failed", "error"):
        signal = -0.8
    elif self_score is not None:
        signal = max(-1.0, min(1.0, (float(self_score) - 0.5) * 2.0))
    # 置信度调整：明确用户反馈权重最高，实际结果次之，自评最低
    weight = {USER_EXPLICIT: 0.10, OUTCOME: 0.06, SELF_EVAL: 0.02}[src]
    return {
        "source": src,
        "signal": round(signal, 4),
        "confidence_delta": round(signal * weight, 4),
        "promote_eligible": src == USER_EXPLICIT and signal > 0,
        "review_required": signal < 0,
    }


def apply_feedback_learning(
    service: MemoryService,
    memory_id: str,
    *,
    source: str = USER_EXPLICIT,
    useful: bool | None = None,
    incorrect: bool | None = None,
    outcome: str | None = None,
    self_score: float | None = None,
    note: str = "",
    producer: str = "agent",
) -> dict[str, Any]:
    """记录一次学习信号；user_explicit 复用现有 feedback 闭环。"""
    plan = classify_feedback(
        source=source,
        useful=useful,
        incorrect=incorrect,
        outcome=outcome,
        self_score=self_score,
    )
    if plan["source"] == USER_EXPLICIT:
        result = service.feedback(
            FeedbackIn(
                memory_id=memory_id,
                useful=useful,
                incorrect=incorrect,
                note=note,
                producer=producer,
            )
        )
        return {"ok": bool(result.get("ok")), "plan": plan, "feedback": result}

    current = service.get_memory(memory_id)
    old_conf = float(current.get("confidence") or 0.4)
    new_conf = max(0.05, min(0.99, old_conf + float(plan["confidence_delta"])))
    learning = list((current.get("metadata") or {}).get("learning_history") or [])[-19:]
    learning.append(
        {
            "source": plan["source"],
            "signal": plan["signal"],
            "outcome": outcome,
            "self_score": self_score,
            "note": note,
            "from_confidence": round(old_conf, 4),
            "to_confidence": round(new_conf, 4),
        }
    )
    meta = dict(current.get("metadata") or {})
    meta["learning_history"] = learning
    meta["last_learning"] = plan
    updated = service.update_memory(
        memory_id,
        MemoryUpdateIn(confidence=new_conf, metadata=meta, expected_version=current.get("version")),
    )
    return {
        "ok": bool(updated),
        "plan": plan,
        "memory_id": memory_id,
        "confidence": round(new_conf, 4),
    }
