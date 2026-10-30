# -*- coding: utf-8 -*-
"""图式同化 / 顺应 / CognitiveChangePlan 应用（默认不自动 ACTIVE）。"""

from __future__ import annotations

from typing import Any

from cognitive_memory.core.service import MemoryService
from cognitive_memory.governance.capability_gate import check_capability


def assimilate_schema(
    service: MemoryService,
    schema_id: str,
    *,
    memory_ids: list[str] | None = None,
    note: str = "",
) -> dict[str, Any]:
    """将新经验关联到现有图式（补充 supporting 证据引用）。"""
    sch = service.get_cognitive_schema(schema_id)
    if not sch:
        return {"ok": False, "detail": "schema_not_found"}
    evid = dict(sch.get("evidence") or {})
    supporting = list(evid.get("supporting") or [])
    added: list[str] = []
    for mid in memory_ids or []:
        mid = str(mid).strip()
        if mid and mid not in supporting:
            supporting.append(mid)
            added.append(mid)
    evid["supporting"] = supporting[:64]
    notes = list(sch.get("assimilation_notes") or [])
    if note:
        notes.append(note)
    patch = {
        "evidence": evid,
        "assimilation_notes": notes[-20:],
        "confidence": min(0.85, float(sch.get("confidence") or 0.4) + 0.02 * len(added)),
    }
    updated = service.update_cognitive_schema(
        schema_id,
        patch=patch,
        change_type="REFINE",
        reason="assimilate",
    )
    return {"ok": True, "schema": updated, "added_evidence": added}


def accommodate_schema(
    service: MemoryService,
    schema_id: str,
    *,
    memory_ids: list[str] | None = None,
    counter_note: str = "",
    propose_split: bool = True,
) -> dict[str, Any]:
    """反例驱动：记录 counter 证据，并可选生成 SPECIALIZE 变更计划（不直接覆盖）。"""
    sch = service.get_cognitive_schema(schema_id)
    if not sch:
        return {"ok": False, "detail": "schema_not_found"}
    evid = dict(sch.get("evidence") or {})
    counter = list(evid.get("counter") or [])
    added: list[str] = []
    for mid in memory_ids or []:
        mid = str(mid).strip()
        if mid and mid not in counter:
            counter.append(mid)
            added.append(mid)
    evid["counter"] = counter[:64]
    app = dict(sch.get("applicability") or {})
    exclusions = list(app.get("exclusions") or [])
    if counter_note and counter_note not in exclusions:
        exclusions.append(counter_note)
    app["exclusions"] = exclusions[-12:]
    new_state = sch.get("state") or "PROPOSED"
    if added and str(new_state).upper() == "ACTIVE":
        new_state = "CONTESTED"
    elif added and str(new_state).upper() == "PROPOSED":
        new_state = "VALIDATING"
    patch = {
        "evidence": evid,
        "applicability": app,
        "confidence": max(0.15, float(sch.get("confidence") or 0.4) - 0.05 * len(added)),
    }
    updated = service.update_cognitive_schema(
        schema_id,
        patch=patch,
        state=str(new_state),
        change_type="SPECIALIZE",
        reason="accommodate",
    )
    plan_id = None
    if propose_split and added:
        plan_id = service.store_cognitive_change_plan(
            {
                "operation": "SPECIALIZE",
                "targetSchemaIds": [schema_id],
                "evidenceRefs": added,
                "expectedImpact": [
                    "缩小原图式适用范围",
                    "可能拆分情境子图式",
                ],
                "risk_level": "MEDIUM",
                "approval_required": True,
                "status": "PROPOSED",
                "reason": counter_note or "counterevidence",
            }
        )
    return {
        "ok": True,
        "schema": updated,
        "added_counter": added,
        "change_plan_id": plan_id,
    }


def apply_cognitive_change_plan(
    service: MemoryService,
    plan_id: str,
    *,
    confirm: bool = False,
) -> dict[str, Any]:
    """应用认知变更计划。激活/退休需 confirm；自动演化需 Gate。"""
    plan = service.get_cognitive_change_plan(plan_id)
    if not plan:
        return {"ok": False, "detail": "plan_not_found"}
    if str(plan.get("status") or "").upper() == "APPLIED":
        return {"ok": False, "detail": "already_applied"}
    risk = str(plan.get("risk_level") or "MEDIUM").upper()
    if risk in ("HIGH", "CRITICAL") and not confirm:
        return {"ok": False, "detail": "confirm_required", "risk_level": risk}
    if plan.get("approval_required") and not confirm:
        return {"ok": False, "detail": "confirm_required"}

    op = str(plan.get("operation") or "UPDATE").upper()
    targets = list(plan.get("targetSchemaIds") or plan.get("target_schema_ids") or [])

    # E2.4：SPLIT / MERGE 委托 schema_network（需 confirm）
    if op in ("SPLIT", "MERGE"):
        if not confirm:
            return {"ok": False, "detail": "confirm_required", "operation": op}
        from cognitive_memory.cognition.schema_network import merge_schemas, split_schema

        payload = plan.get("payload") if isinstance(plan.get("payload"), dict) else {}
        # payload 也可能嵌在 plan 顶层（store 时扁平）
        if not payload:
            payload = {
                k: plan.get(k)
                for k in ("child_specs", "parent_id", "source_ids")
                if plan.get(k) is not None
            }
        if op == "SPLIT":
            parent_id = str(
                (payload.get("parent_id") or (targets[0] if targets else "")) or ""
            )
            result = split_schema(
                service,
                parent_id,
                child_specs=list(payload.get("child_specs") or []),
                note=str(plan.get("reason") or ""),
                confirm=True,
                existing_plan_id=plan_id,
            )
        else:
            result = merge_schemas(
                service,
                list(payload.get("source_ids") or targets),
                note=str(plan.get("reason") or ""),
                confirm=True,
                existing_plan_id=plan_id,
            )
        return result

    # 自动激活受 SCHEMA_AUTO_EVOLUTION 门禁
    if op in ("CREATE", "UPDATE") and risk == "LOW" and not confirm:
        gate = check_capability(service.db, "SCHEMA_AUTO_EVOLUTION")
        if not gate.get("allowed"):
            return {
                "ok": False,
                "detail": "capability_locked",
                "capability": "SCHEMA_AUTO_EVOLUTION",
                "gate": gate,
            }

    applied: list[dict[str, Any]] = []
    for sid in targets:
        sch = service.get_cognitive_schema(str(sid))
        if not sch:
            continue
        if op == "RETIRE":
            updated = service.update_cognitive_schema(
                sid, state="RETIRED", change_type="RETIRE", reason=f"plan:{plan_id}"
            )
        elif op in ("CREATE", "UPDATE", "SPECIALIZE", "GENERALIZE", "REFINE"):
            # 低风险且已确认 → ACTIVE；否则 VALIDATING
            next_state = "ACTIVE" if confirm and risk in ("LOW", "MEDIUM") else "VALIDATING"
            if risk in ("HIGH", "CRITICAL"):
                next_state = "VALIDATING"
            updated = service.update_cognitive_schema(
                sid,
                state=next_state,
                change_type=op if op != "CREATE" else "REFINE",
                reason=f"plan:{plan_id}",
            )
        else:
            updated = service.update_cognitive_schema(
                sid,
                state="VALIDATING",
                change_type=op,
                reason=f"plan:{plan_id}",
            )
        if updated:
            applied.append({"schema_id": sid, "state": updated.get("state")})

    service.update_cognitive_change_plan(
        plan_id,
        status="APPLIED",
        payload_patch={"applied_schemas": applied, "confirm": confirm},
    )
    return {"ok": True, "plan_id": plan_id, "applied": applied, "operation": op}
