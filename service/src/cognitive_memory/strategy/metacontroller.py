# -*- coding: utf-8 -*-
"""Thin MetaController: schedule reflect / reevaluate only (no autonomy)."""

from __future__ import annotations

from typing import Any

from cognitive_memory.storage.db import Database
from cognitive_memory.strategy.offline_eval import run_offline_eval
from cognitive_memory.strategy.strategy_store import StrategyStore


def schedule(
    db: Database,
    *,
    action: str = "reflect",
    strategy_id: str | None = None,
) -> dict[str, Any]:
    """
    P5 MetaController stub.
    - reflect: list proposed/experimental strategies
    - reevaluate: run gated offline_eval when strategy_id given
    Never auto-activates.
    """
    act = (action or "reflect").strip().lower()
    store = StrategyStore(db)
    if act == "reflect":
        items = store.list(limit=50)
        focus = [
            s
            for s in items
            if s.get("status") in {"proposed", "experimental"}
        ]
        return {
            "ok": True,
            "action": "reflect",
            "focus_count": len(focus),
            "focus": focus[:20],
            "note": "scheduling only; no status mutation",
        }
    if act == "reevaluate":
        if not strategy_id:
            return {"ok": False, "detail": "strategy_id_required", "action": act}
        report = run_offline_eval(db, strategy_id)
        return {
            "ok": bool(report.get("ok")),
            "action": "reevaluate",
            "report": report,
            "note": "reevaluate does not deploy",
        }
    return {"ok": False, "detail": "unknown_action", "action": act}
