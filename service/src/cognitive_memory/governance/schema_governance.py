# -*- coding: utf-8 -*-
"""Schema mutation governance — LearningProposal entry (P1.5).

confirm=True is never sufficient authorization by itself.
Persistent schema mutations require capability SCHEMA_MUTATION (or
SCHEMA_AUTO_EVOLUTION for low-risk auto paths).
"""

from __future__ import annotations

import json
from typing import Any

from cognitive_memory.governance.capability_gate import check_capability
from cognitive_memory.tracing.service import JudgmentTraceService

# Shared process-local audit sink for unit tests / node process
_TRACE = JudgmentTraceService()


def governance_traces() -> JudgmentTraceService:
    return _TRACE


def authorize_schema_mutation(
    db: Any,
    *,
    confirm: bool,
    preview: bool = False,
    operation: str = "",
    actor: str = "",
    risk_level: str = "MEDIUM",
) -> dict[str, Any]:
    """Unified authorization check for long-term schema mutations."""
    if preview:
        return {
            "ok": True,
            "preview": True,
            "allowed": True,
            "detail": "preview_no_persist",
        }
    if not confirm:
        return {
            "ok": False,
            "allowed": False,
            "detail": "confirm_required",
            "note": "confirm_is_not_authorization",
        }
    # confirm alone is insufficient — need capability
    gate = check_capability(db, "SCHEMA_MUTATION")
    if gate.get("allowed"):
        _TRACE.record(
            "schema_mutation_authorized",
            governance_critical=True,
            reason_codes=["schema_mutation_capability", operation],
            input_refs=[actor or "unknown_actor"],
        )
        return {
            "ok": True,
            "allowed": True,
            "detail": "ok",
            "capability": "SCHEMA_MUTATION",
            "confirm": True,
            "risk_level": risk_level,
        }
    # Low-risk auto evolution still needs SCHEMA_AUTO_EVOLUTION, never confirm alone
    if str(risk_level).upper() == "LOW":
        auto = check_capability(db, "SCHEMA_AUTO_EVOLUTION")
        if auto.get("allowed"):
            return {
                "ok": True,
                "allowed": True,
                "detail": "ok",
                "capability": "SCHEMA_AUTO_EVOLUTION",
                "confirm": True,
                "risk_level": risk_level,
            }
    _TRACE.record(
        "schema_mutation_denied",
        governance_critical=True,
        reason_codes=["capability_locked", "confirm_insufficient", operation],
        input_refs=[actor or "unknown_actor"],
    )
    return {
        "ok": False,
        "allowed": False,
        "detail": "capability_locked",
        "capability": "SCHEMA_MUTATION",
        "confirm_provided": bool(confirm),
        "note": "confirm_true_is_not_authorization",
    }


def proposal_payload(
    *,
    operation: str,
    target_schema_ids: list[str],
    reason: str = "",
    risk_level: str = "MEDIUM",
    evidence_refs: list[str] | None = None,
    patch: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "targetSchemaIds": list(target_schema_ids),
        "evidenceRefs": list(evidence_refs or []),
        "expectedImpact": [f"schema_mutation:{operation}"],
        "risk_level": risk_level,
        "approval_required": True,
        "status": "PROPOSED",
        "reason": reason or operation,
        "payload": payload or {},
        "proposed_patch": patch or {},
        "governance": {
            "entry": "schema_governance.learning_proposal",
            "confirm_alone_insufficient": True,
        },
    }


def dump_audit_note(auth: dict[str, Any]) -> str:
    return json.dumps(auth, ensure_ascii=False)[:500]
