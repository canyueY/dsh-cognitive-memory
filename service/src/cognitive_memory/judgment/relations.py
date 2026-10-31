# -*- coding: utf-8 -*-
"""Claim relation results and same_as evaluation (deterministic)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from cognitive_memory.claims.ast import ClaimAST
from cognitive_memory.claims.normalize import normalize_ast, normalize_scope


class ClaimRelation(str, Enum):
    SAME_AS = "same_as"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    SUPPORTS = "supports"
    UNRELATED = "unrelated"
    UNKNOWN = "unknown"


class RelationDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ABSTAINED = "abstained"


class RelationResult(BaseModel):
    candidate_relation: ClaimRelation
    decision: RelationDecision
    final_relation: ClaimRelation
    reason_codes: list[str] = Field(default_factory=list)
    compared_fields: list[str] = Field(default_factory=list)
    unresolved_fields: list[str] = Field(default_factory=list)
    algorithm_version: str = "relation.same_as.v1"

    @model_validator(mode="after")
    def _legal_combo(self) -> "RelationResult":
        validate_relation_result(self.decision, self.final_relation)
        return self


def validate_relation_result(decision: RelationDecision, final_relation: ClaimRelation) -> None:
    if decision is RelationDecision.ACCEPTED and final_relation is ClaimRelation.UNKNOWN:
        raise ValueError("accepted_final_cannot_be_unknown")
    if decision is RelationDecision.REJECTED and final_relation not in (
        ClaimRelation.UNRELATED,
        ClaimRelation.UNKNOWN,
    ):
        raise ValueError("rejected_final_must_be_unrelated_or_unknown")
    if decision is RelationDecision.ABSTAINED and final_relation is not ClaimRelation.UNKNOWN:
        raise ValueError("abstained_final_must_be_unknown")


def evaluate_same_as(a: ClaimAST, b: ClaimAST) -> RelationResult:
    """Deterministic same_as. No LLM. Semantic similarity is not enough."""
    compared = ["ast_version", "normalized_root", "normalized_scope"]
    if a.ast_version != b.ast_version:
        return RelationResult(
            candidate_relation=ClaimRelation.SAME_AS,
            decision=RelationDecision.ABSTAINED,
            final_relation=ClaimRelation.UNKNOWN,
            reason_codes=["ast_version_mismatch"],
            compared_fields=compared,
            unresolved_fields=["ast_version"],
        )
    if a.is_unresolved() or b.is_unresolved():
        return RelationResult(
            candidate_relation=ClaimRelation.SAME_AS,
            decision=RelationDecision.ABSTAINED,
            final_relation=ClaimRelation.UNKNOWN,
            reason_codes=["unresolved_ast"],
            compared_fields=compared,
            unresolved_fields=["root"],
        )
    na = normalize_ast(a)
    nb = normalize_ast(b)
    if na == nb:
        return RelationResult(
            candidate_relation=ClaimRelation.SAME_AS,
            decision=RelationDecision.ACCEPTED,
            final_relation=ClaimRelation.SAME_AS,
            reason_codes=["normalized_equal"],
            compared_fields=compared,
        )
    # Explicit scope difference
    if normalize_scope(a.scope) != normalize_scope(b.scope):
        return RelationResult(
            candidate_relation=ClaimRelation.SAME_AS,
            decision=RelationDecision.REJECTED,
            final_relation=ClaimRelation.UNRELATED,
            reason_codes=["scope_mismatch"],
            compared_fields=compared,
        )
    return RelationResult(
        candidate_relation=ClaimRelation.SAME_AS,
        decision=RelationDecision.REJECTED,
        final_relation=ClaimRelation.UNRELATED,
        reason_codes=["normalized_not_equal"],
        compared_fields=compared,
    )
