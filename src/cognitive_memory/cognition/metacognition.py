# -*- coding: utf-8 -*-
"""元认知反思 stub：结构化输出；不把 LLM 自说自话当验证证据。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cognitive_memory.core.service import MemoryService


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reflect(
    service: MemoryService,
    *,
    judgment: str = "",
    schema_ids: list[str] | None = None,
    memory_ids: list[str] | None = None,
) -> dict[str, Any]:
    """检查依赖图式证据是否充分、是否有反例、是否过度泛化。"""
    schemas: list[dict[str, Any]] = []
    problems: list[str] = []
    for sid in schema_ids or []:
        sch = service.get_cognitive_schema(str(sid))
        if not sch:
            problems.append(f"missing_schema:{sid}")
            continue
        schemas.append(
            {
                "id": sch.get("id"),
                "name": sch.get("name"),
                "state": sch.get("state"),
                "confidence": sch.get("confidence"),
            }
        )
        evid = sch.get("evidence") or {}
        supporting = list(evid.get("supporting") or [])
        counter = list(evid.get("counter") or [])
        if len(supporting) < 2:
            problems.append(f"weak_evidence:{sid}")
        if counter:
            problems.append(f"has_counterexamples:{sid}")
        if float(sch.get("confidence") or 0) > 0.75 and len(supporting) < 3:
            problems.append(f"possible_overconfidence:{sid}")
        app = sch.get("applicability") or {}
        if not app.get("exclusions"):
            problems.append(f"missing_exclusions:{sid}")

    return {
        "ok": True,
        "judgment": judgment,
        "dependent_schemas": schemas,
        "memory_refs": list(memory_ids or []),
        "problems": problems,
        "suggested_actions": (
            ["run accommodate on contested schemas", "gather more independent evidence"]
            if problems
            else ["no_critical_issues"]
        ),
        "uncertainty": "high" if problems else "medium",
        "generated_at": _now(),
        "note": "启发式检查；非正式验证证据",
    }


def analyze_impact(
    service: MemoryService,
    schema_id: str,
) -> dict[str, Any]:
    """影响传播分析 stub：读 relations，生成重评任务列表（不递归改写）。"""
    sch = service.get_cognitive_schema(schema_id)
    if not sch:
        return {"ok": False, "detail": "schema_not_found"}
    rel = sch.get("relations") or {}
    affected: list[dict[str, Any]] = []
    for kind in (
        "supports",
        "contradicts",
        "generalizes",
        "specializes",
        "dependsOn",
        "refines",
    ):
        for nid in rel.get(kind) or []:
            affected.append(
                {
                    "node_id": nid,
                    "relation": kind,
                    "action": "reevaluate",
                    "auto_overwrite": False,
                }
            )
    return {
        "ok": True,
        "changed_schema_id": schema_id,
        "affected": affected,
        "count": len(affected),
        "note": "仅生成重评任务；禁止无条件递归覆盖",
        "generated_at": _now(),
    }
