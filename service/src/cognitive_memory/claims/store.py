# -*- coding: utf-8 -*-
"""P2 Claim persistence — first-class rows (not Memory projections)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from cognitive_memory.claims.ast import ClaimAST
from cognitive_memory.claims.lifecycle import ClaimLifecycle, ClaimLifecycleEngine
from cognitive_memory.claims.normalize import normalized_hash
from cognitive_memory.claims.parser import parse_memory_text
from cognitive_memory.security.context import SecurityContext
from cognitive_memory.storage.db import Database
from cognitive_memory.tracing.service import JudgmentTraceService
from cognitive_memory.tms.store import TmsStore
from cognitive_memory.verification.engine import VerificationEngine
from cognitive_memory.verification.models import VerificationStatus
from cognitive_memory.verification.persist import PersistentVerificationStore
from cognitive_memory.visibility.models import VisibilityDecision
from cognitive_memory.visibility.service import evaluate_visibility


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str = "clm") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ClaimStore:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.db.ensure_schema()
        self._life = ClaimLifecycleEngine()
        self._ver_engine = VerificationEngine()
        self._ver_store = PersistentVerificationStore(db)
        self.traces = JudgmentTraceService()
        self.tms = TmsStore(db)

    def _record_trace(
        self,
        judgment_type: str,
        *,
        input_refs: list[str] | None = None,
        output_refs: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        reason_codes: list[str] | None = None,
        governance_critical: bool = False,
    ) -> str | None:
        tr = self.traces.record(
            judgment_type,
            input_refs=input_refs,
            output_refs=output_refs,
            evidence_refs=evidence_refs,
            reason_codes=reason_codes,
            algorithm_version="claim.store.v1",
            rule_version="claim.lifecycle.v1",
            governance_critical=governance_critical,
        )
        return tr.trace_id if tr else None

    def propose_from_text(
        self,
        text: str,
        *,
        bank_id: str = "personal",
        source_memory_id: str | None = None,
        scope: dict[str, Any] | None = None,
        persist_unresolved: bool = True,
    ) -> dict[str, Any]:
        """Parse → normalize → persist Claim (lifecycle=proposed). Never verified."""
        parsed = parse_memory_text(text)
        ast: ClaimAST = parsed.ast
        if scope:
            merged_scope = {**(ast.scope or {}), **dict(scope)}
            ast = ast.model_copy(update={"scope": merged_scope})
        if ast.is_unresolved() and not persist_unresolved:
            return {
                "ok": True,
                "persisted": False,
                "unresolved": True,
                "ast": ast.model_dump(),
                "parse": {"confidence": parsed.confidence, "notes": parsed.notes},
            }
        nh = normalized_hash(ast)
        # same_as: reuse existing non-redirected claim with same hash in bank
        existing = self.find_by_hash(nh, bank_id=bank_id)
        if existing and not existing.get("redirects_to"):
            tid = self._record_trace(
                "claim.same_as",
                input_refs=[source_memory_id or "text"],
                output_refs=[existing["id"]],
                reason_codes=["normalized_hash_match"],
            )
            return {
                "ok": True,
                "persisted": False,
                "same_as": existing["id"],
                "claim": existing,
                "ast": ast.model_dump(),
                "trace_id": tid,
            }
        cid = _new_id()
        now = _now()
        row = {
            "id": cid,
            "bank_id": bank_id,
            "ast_version": ast.ast_version,
            "ast_json": json.dumps(ast.model_dump(), ensure_ascii=False),
            "surface": ast.surface or text,
            "normalized_hash": nh,
            "lifecycle": ClaimLifecycle.PROPOSED.value,
            "verification_status": "unverified",
            "scope_json": json.dumps(ast.scope or {}, ensure_ascii=False),
            "source_memory_id": source_memory_id,
            "redirects_to": None,
            "created_at": now,
            "updated_at": now,
        }
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO claims(
                  id, bank_id, ast_version, ast_json, surface, normalized_hash,
                  lifecycle, verification_status, scope_json, source_memory_id,
                  redirects_to, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["bank_id"],
                    row["ast_version"],
                    row["ast_json"],
                    row["surface"],
                    row["normalized_hash"],
                    row["lifecycle"],
                    row["verification_status"],
                    row["scope_json"],
                    row["source_memory_id"],
                    row["redirects_to"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.execute(
                """
                INSERT INTO claim_lifecycle_events(
                  id, claim_id, from_status, to_status, reason, actor,
                  policy_version, evidence_refs_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("cle"),
                    cid,
                    ClaimLifecycle.PROPOSED.value,
                    ClaimLifecycle.PROPOSED.value,
                    "propose_from_text",
                    "system",
                    "claim.lifecycle.v1",
                    "[]",
                    now,
                ),
            )
        self._life._status[cid] = ClaimLifecycle.PROPOSED
        tid = self._record_trace(
            "claim.propose",
            input_refs=[source_memory_id or "text"],
            output_refs=[cid],
            reason_codes=["unresolved"] if ast.is_unresolved() else ["parsed"],
        )
        return {
            "ok": True,
            "persisted": True,
            "claim_id": cid,
            "claim": self.get(cid),
            "ast": ast.model_dump(),
            "unresolved": ast.is_unresolved(),
            "trace_id": tid,
        }

    def get(
        self,
        claim_id: str,
        *,
        follow_redirect: bool = True,
        principal: SecurityContext | None = None,
        evidence_visible: bool = True,
    ) -> dict[str, Any] | None:
        with self.db.exclusive() as conn:
            row = conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
            if conn.in_transaction:
                conn.commit()
        if not row:
            return None
        pack = self._row_to_dict(row)
        if principal is not None:
            vis = evaluate_visibility(
                principal,
                object_ref=claim_id,
                object_bank=str(pack.get("bank_id") or "personal"),
                requested_fields=[
                    "claim_id",
                    "lifecycle_status",
                    "ast_version",
                    "ast",
                    "verification_status",
                    "evidence_refs",
                ],
                evidence_visible=evidence_visible,
            )
            if vis.decision == VisibilityDecision.DENY:
                return None  # fail-closed: no existence disclosure
            pack = self._apply_visibility(pack, vis.visible_fields, vis.denied_fields)
            pack["visibility"] = vis.model_dump(mode="json")
        if follow_redirect and pack.get("redirects_to"):
            target = self.get(
                str(pack["redirects_to"]),
                follow_redirect=True,
                principal=principal,
                evidence_visible=evidence_visible,
            )
            if target:
                pack["redirect_resolved"] = target
        return pack

    @staticmethod
    def _apply_visibility(
        pack: dict[str, Any],
        visible_fields: list[str],
        denied_fields: list[str],
    ) -> dict[str, Any]:
        out = dict(pack)
        # Map contract field names → stored keys
        field_map = {
            "ast": "ast",
            "verification_status": "verification_status",
            "lifecycle_status": "lifecycle",
            "ast_version": "ast_version",
            "claim_id": "id",
            "evidence_refs": "_evidence_refs",
        }
        for f in denied_fields:
            key = field_map.get(f, f)
            if key in out:
                out.pop(key, None)
            if f == "evidence_refs":
                out.pop("evidence", None)
        # Always keep id if claim_id visible or as opaque handle when PARTIAL
        if "claim_id" in visible_fields or "id" in visible_fields:
            out["id"] = pack.get("id")
        return out

    def find_by_hash(self, normalized_hash_value: str, *, bank_id: str) -> dict[str, Any] | None:
        with self.db.exclusive() as conn:
            row = conn.execute(
                """
                SELECT * FROM claims
                WHERE normalized_hash=? AND bank_id=? AND redirects_to IS NULL
                ORDER BY created_at ASC LIMIT 1
                """,
                (normalized_hash_value, bank_id),
            ).fetchone()
            if conn.in_transaction:
                conn.commit()
        return self._row_to_dict(row) if row else None

    def attach_evidence(
        self,
        claim_id: str,
        evidence_ref: str,
        *,
        role: str = "support",
        independent: bool = False,
        materialize_evidence_object: bool = True,
        bank_id: str | None = None,
    ) -> dict[str, Any]:
        claim = self.get(claim_id, follow_redirect=False)
        if not claim:
            return {"ok": False, "detail": "claim_not_found"}
        evidence_object_id: str | None = None
        if materialize_evidence_object and evidence_ref:
            from cognitive_memory.evidence.object_store import EvidenceObjectStore

            estore = EvidenceObjectStore(self.db)
            # Prefer explicit Evidence id; else treat ref as observation source
            if str(evidence_ref).startswith("evd_"):
                existing = estore.get(str(evidence_ref))
                evidence_object_id = existing["id"] if existing else None
            else:
                created = estore.create_from_observation(
                    str(evidence_ref),
                    bank_id=bank_id or str(claim.get("bank_id") or "personal"),
                    role_hint=role,
                    legacy_memory_id=claim.get("source_memory_id"),
                )
                if created.get("ok") and created.get("evidence"):
                    evidence_object_id = created["evidence"]["id"]
                    # Link uses first-class evidence id when available
                    evidence_ref = evidence_object_id
        eid = _new_id("cev")
        now = _now()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO claim_evidence(
                  id, claim_id, evidence_ref, role, independent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (eid, claim_id, evidence_ref, role, 1 if independent else 0, now),
            )
        tid = self._record_trace(
            "claim.attach_evidence",
            input_refs=[claim_id],
            output_refs=[eid],
            evidence_refs=[evidence_ref],
            reason_codes=[role],
        )
        return {
            "ok": True,
            "link_id": eid,
            "evidence_id": evidence_object_id or eid,
            "evidence_ref": evidence_ref,
            "claim_id": claim_id,
            "role": role,
            "trace_id": tid,
        }

    def list_evidence(self, claim_id: str) -> list[dict[str, Any]]:
        with self.db.exclusive() as conn:
            rows = conn.execute(
                "SELECT * FROM claim_evidence WHERE claim_id=? ORDER BY created_at",
                (claim_id,),
            ).fetchall()
            if conn.in_transaction:
                conn.commit()
        return [
            {
                "id": r["id"],
                "claim_id": r["claim_id"],
                "evidence_ref": r["evidence_ref"],
                "role": r["role"],
                "independent": bool(r["independent"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def transition(
        self,
        claim_id: str,
        target_status: str | ClaimLifecycle,
        *,
        reason: str,
        evidence_refs: list[str] | None = None,
        actor: str = "",
    ) -> dict[str, Any]:
        claim = self.get(claim_id, follow_redirect=False)
        if not claim:
            return {"ok": False, "detail": "claim_not_found"}
        if claim.get("redirects_to"):
            return {"ok": False, "detail": "claim_redirected", "redirects_to": claim["redirects_to"]}
        # sync in-memory engine from DB
        self._life._status[claim_id] = ClaimLifecycle(str(claim.get("lifecycle") or "proposed"))
        result = self._life.transition_claim(
            claim_id,
            target_status,
            reason=reason,
            evidence_refs=evidence_refs,
            actor=actor,
        )
        if not result.ok:
            return {
                "ok": False,
                "detail": result.error or "transition_failed",
                "from_status": result.from_status.value,
                "result": result.model_dump(),
            }
        assert result.to_status is not None
        now = _now()
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE claims SET lifecycle=?, updated_at=? WHERE id=?",
                (result.to_status.value, now, claim_id),
            )
            conn.execute(
                """
                INSERT INTO claim_lifecycle_events(
                  id, claim_id, from_status, to_status, reason, actor,
                  policy_version, evidence_refs_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("cle"),
                    claim_id,
                    result.from_status.value,
                    result.to_status.value,
                    reason,
                    actor,
                    result.policy_version,
                    json.dumps(list(evidence_refs or []), ensure_ascii=False),
                    now,
                ),
            )
        tms_pack: dict[str, Any] | None = None
        if result.to_status in (
            ClaimLifecycle.DISPUTED,
            ClaimLifecycle.REJECTED,
            ClaimLifecycle.SUPERSEDED,
            ClaimLifecycle.EXPIRED,
        ):
            tms_pack = self.tms.invalidate_node(
                claim_id, reason=f"lifecycle:{result.to_status.value}", actor=actor
            )
        tid = self._record_trace(
            "claim.transition",
            input_refs=[claim_id],
            output_refs=[claim_id],
            evidence_refs=list(evidence_refs or []),
            reason_codes=[result.from_status.value, result.to_status.value, reason],
            governance_critical=result.to_status
            in (ClaimLifecycle.VERIFIED, ClaimLifecycle.REJECTED, ClaimLifecycle.SUPERSEDED),
        )
        return {
            "ok": True,
            "claim_id": claim_id,
            "from_status": result.from_status.value,
            "to_status": result.to_status.value,
            "claim": self.get(claim_id),
            "trace_id": tid,
            "tms": tms_pack,
        }

    def submit_verified(
        self,
        claim_id: str,
        *,
        evidence_refs: list[str],
        actor: str,
        authorized: bool = True,
        evidence_still_valid: bool = True,
    ) -> dict[str, Any]:
        """Sole path to Verified: engine re-check + persist record + lifecycle."""
        claim = self.get(claim_id, follow_redirect=False)
        if not claim:
            return {"ok": False, "detail": "claim_not_found"}
        if claim.get("redirects_to"):
            return {"ok": False, "detail": "claim_redirected"}
        # Must be supported/qualified before verified
        life = str(claim.get("lifecycle") or "proposed")
        if life not in ("supported", "qualified", "expired"):
            if life == "proposed":
                bump = self.transition(claim_id, "supported", reason="pre_verify", actor=actor)
                if not bump.get("ok"):
                    return {"ok": False, "detail": "cannot_reach_supported", "prior": bump}
        eng = self._ver_engine.submit_verified(
            claim_id=claim_id,
            evidence_refs=evidence_refs,
            actor=actor,
            authorized=authorized,
            evidence_still_valid=evidence_still_valid,
        )
        if not eng.get("ok"):
            return {"ok": False, "detail": eng.get("error") or "verify_denied", "engine": eng}
        # P3 gate: multiple evidence refs must not share independence_key
        if len(evidence_refs) >= 2:
            from cognitive_memory.evidence.object_store import EvidenceObjectStore

            estore = EvidenceObjectStore(self.db)
            ev_ids = []
            for ref in evidence_refs:
                if str(ref).startswith("evd_"):
                    ev_ids.append(str(ref))
                else:
                    created = estore.create_from_observation(str(ref))
                    if created.get("ok") and created.get("evidence"):
                        ev_ids.append(created["evidence"]["id"])
            indep = estore.independence_conflict(ev_ids)
            if not indep.get("independent"):
                return {
                    "ok": False,
                    "detail": "evidence_not_independent",
                    "independence": indep,
                    "note": "correlated_evidence_blocked_before_verified",
                }
        from cognitive_memory.verification.models import VerificationRecord

        rec_data = eng["record"]
        record = VerificationRecord.model_validate(rec_data)
        self._ver_store.insert(record)
        now = _now()
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE claims
                SET verification_status=?, lifecycle=?, updated_at=?
                WHERE id=?
                """,
                (
                    VerificationStatus.VERIFIED.value,
                    ClaimLifecycle.VERIFIED.value,
                    now,
                    claim_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO claim_lifecycle_events(
                  id, claim_id, from_status, to_status, reason, actor,
                  policy_version, evidence_refs_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("cle"),
                    claim_id,
                    life,
                    ClaimLifecycle.VERIFIED.value,
                    "submit_verified",
                    actor,
                    "claim.lifecycle.v1",
                    json.dumps(list(evidence_refs), ensure_ascii=False),
                    now,
                ),
            )
        self._life._status[claim_id] = ClaimLifecycle.VERIFIED
        tms_pack = self.tms.add_and_persist(
            claim_id,
            list(evidence_refs),
            kind="support",
            reason="submit_verified",
            actor=actor,
        )
        tid = self._record_trace(
            "claim.verify",
            input_refs=[claim_id],
            output_refs=[claim_id, record.record_id],
            evidence_refs=list(evidence_refs),
            reason_codes=["verified", "tms_justification"],
            governance_critical=True,
        )
        return {
            "ok": True,
            "claim_id": claim_id,
            "record": record.model_dump(mode="json"),
            "claim": self.get(claim_id),
            "trace_id": tid,
            "tms": tms_pack,
        }

    def redirect(self, source_id: str, target_id: str, *, reason: str = "merge") -> dict[str, Any]:
        src = self.get(source_id, follow_redirect=False)
        tgt = self.get(target_id, follow_redirect=True)
        if not src or not tgt:
            return {"ok": False, "detail": "claim_not_found"}
        if tgt.get("redirect_resolved"):
            resolved_target = str(tgt["redirect_resolved"]["id"])
        else:
            resolved_target = str(tgt["id"])
        if source_id == resolved_target:
            return {"ok": False, "detail": "self_redirect"}
        now = _now()
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE claims SET redirects_to=?, lifecycle=?, updated_at=? WHERE id=?",
                (resolved_target, ClaimLifecycle.SUPERSEDED.value, now, source_id),
            )
            conn.execute(
                """
                INSERT INTO claim_lifecycle_events(
                  id, claim_id, from_status, to_status, reason, actor,
                  policy_version, evidence_refs_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _new_id("cle"),
                    source_id,
                    str(src.get("lifecycle") or "proposed"),
                    ClaimLifecycle.SUPERSEDED.value,
                    reason,
                    "system",
                    "claim.lifecycle.v1",
                    json.dumps([resolved_target], ensure_ascii=False),
                    now,
                ),
            )
        tms_pack = self.tms.invalidate_node(
            source_id, reason=f"redirect:{resolved_target}", actor="system"
        )
        tid = self._record_trace(
            "claim.redirect",
            input_refs=[source_id],
            output_refs=[resolved_target],
            reason_codes=[reason, "superseded", "tms_invalidate"],
            governance_critical=True,
        )
        return {
            "ok": True,
            "source_id": source_id,
            "redirects_to": resolved_target,
            "claim": self.get(source_id, follow_redirect=False),
            "trace_id": tid,
            "tms": tms_pack,
        }

    def merge(
        self,
        source_id: str,
        target_id: str,
        *,
        reason: str = "claim_merge",
        move_evidence: bool = True,
    ) -> dict[str, Any]:
        """Merge source into target: redirect + optional evidence reassignment."""
        if source_id == target_id:
            return {"ok": False, "detail": "self_merge"}
        src = self.get(source_id, follow_redirect=False)
        tgt = self.get(target_id, follow_redirect=True)
        if not src or not tgt:
            return {"ok": False, "detail": "claim_not_found"}
        resolved_target = str(
            (tgt.get("redirect_resolved") or tgt).get("id") or target_id
        )
        moved = 0
        if move_evidence:
            now = _now()
            with self.db.transaction() as conn:
                cur = conn.execute(
                    """
                    UPDATE claim_evidence
                    SET claim_id=?
                    WHERE claim_id=?
                    """,
                    (resolved_target, source_id),
                )
                moved = int(cur.rowcount or 0)
                # touch target
                conn.execute(
                    "UPDATE claims SET updated_at=? WHERE id=?",
                    (now, resolved_target),
                )
        redir = self.redirect(source_id, resolved_target, reason=reason)
        if not redir.get("ok"):
            return redir
        tid = self._record_trace(
            "claim.merge",
            input_refs=[source_id, resolved_target],
            output_refs=[resolved_target],
            evidence_refs=[],
            reason_codes=[reason, f"evidence_moved:{moved}"],
            governance_critical=True,
        )
        return {
            "ok": True,
            "source_id": source_id,
            "target_id": resolved_target,
            "evidence_moved": moved,
            "redirect": redir,
            "claim": self.get(resolved_target),
            "trace_id": tid,
            "note": "merge_does_not_verify",
        }

    def split(
        self,
        claim_id: str,
        parts: list[str],
        *,
        reason: str = "claim_split",
        bank_id: str | None = None,
    ) -> dict[str, Any]:
        """Split one Claim into ≥2 new Claims; original is redirected to the first part."""
        texts = [str(p).strip() for p in (parts or []) if str(p).strip()]
        if len(texts) < 2:
            return {"ok": False, "detail": "split_requires_two_parts"}
        src = self.get(claim_id, follow_redirect=False)
        if not src:
            return {"ok": False, "detail": "claim_not_found"}
        if src.get("redirects_to"):
            return {"ok": False, "detail": "claim_redirected"}
        bank = bank_id or str(src.get("bank_id") or "personal")
        created: list[dict[str, Any]] = []
        for i, text in enumerate(texts):
            # Distinct scope so split parts never collide with source same_as hash
            pack = self.propose_from_text(
                text,
                bank_id=bank,
                scope={"split_from": claim_id, "split_part": i},
            )
            if not pack.get("ok"):
                return {"ok": False, "detail": "part_propose_failed", "part": pack}
            cid = pack.get("claim_id") or (pack.get("same_as") or (pack.get("claim") or {}).get("id"))
            if not cid:
                return {"ok": False, "detail": "part_missing_id", "part": pack}
            if str(cid) == str(claim_id):
                return {"ok": False, "detail": "split_part_collapsed_to_source", "part": pack}
            created.append({"claim_id": str(cid), "propose": pack})
        primary = str(created[0]["claim_id"])
        redir = self.redirect(claim_id, primary, reason=reason)
        if not redir.get("ok"):
            return {"ok": False, "detail": "redirect_failed", "redirect": redir, "created": created}
        tid = self._record_trace(
            "claim.split",
            input_refs=[claim_id],
            output_refs=[str(c["claim_id"]) for c in created],
            reason_codes=[reason],
            governance_critical=True,
        )
        return {
            "ok": True,
            "source_id": claim_id,
            "parts": created,
            "primary_id": primary,
            "redirect": redir,
            "trace_id": tid,
            "note": "split_does_not_verify",
        }

    def relate(self, claim_id_a: str, claim_id_b: str) -> dict[str, Any]:
        """Evaluate typed relation between two persisted Claims."""
        from cognitive_memory.claims.ast import ClaimAST
        from cognitive_memory.judgment.relations import evaluate_relation

        a = self.get(claim_id_a, follow_redirect=True)
        b = self.get(claim_id_b, follow_redirect=True)
        if not a or not b:
            return {"ok": False, "detail": "claim_not_found"}
        try:
            ast_a = ClaimAST.model_validate((a.get("redirect_resolved") or a).get("ast") or a.get("ast"))
            ast_b = ClaimAST.model_validate((b.get("redirect_resolved") or b).get("ast") or b.get("ast"))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "detail": "ast_invalid", "error": str(exc)}
        result = evaluate_relation(ast_a, ast_b)
        tid = self._record_trace(
            "claim.relate",
            input_refs=[claim_id_a, claim_id_b],
            output_refs=[],
            reason_codes=list(result.reason_codes),
        )
        return {
            "ok": True,
            "a": claim_id_a,
            "b": claim_id_b,
            "relation": result.model_dump(mode="json"),
            "trace_id": tid,
        }

    def semantic_suggest(
        self,
        query: str,
        *,
        bank_id: str = "personal",
        limit: int = 5,
        min_score: float = 0.35,
    ) -> dict[str, Any]:
        """Assistive Claim recall by surface similarity — never Verified."""
        from cognitive_memory.retrieval.semantic_sidepath import pool_suggest

        with self.db.exclusive() as conn:
            rows = conn.execute(
                """
                SELECT id, surface, lifecycle, verification_status, bank_id
                FROM claims
                WHERE bank_id=? AND redirects_to IS NULL
                ORDER BY updated_at DESC LIMIT 200
                """,
                (bank_id,),
            ).fetchall()
            if conn.in_transaction:
                conn.commit()
        corpus = [
            {
                "id": r["id"],
                "surface": r["surface"],
                "lifecycle": r["lifecycle"],
                "verification_status": r["verification_status"],
            }
            for r in rows
        ]
        pack = pool_suggest(
            query,
            corpus,
            limit=limit,
            min_score=min_score,
            content_key="surface",
        )
        pack["verification_status"] = "unverified"
        pack["note"] = "semantic_claim_suggest_never_verified"
        tid = self._record_trace(
            "claim.semantic_suggest",
            input_refs=[query[:64]],
            output_refs=[str(x.get("id")) for x in pack.get("items") or []],
            reason_codes=["assistive_only"],
        )
        pack["trace_id"] = tid
        return pack

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        try:
            ast = json.loads(row["ast_json"] or "{}")
        except json.JSONDecodeError:
            ast = {}
        try:
            scope = json.loads(row["scope_json"] or "{}")
        except json.JSONDecodeError:
            scope = {}
        return {
            "id": row["id"],
            "bank_id": row["bank_id"],
            "ast_version": row["ast_version"],
            "ast": ast,
            "surface": row["surface"],
            "normalized_hash": row["normalized_hash"],
            "lifecycle": row["lifecycle"],
            "verification_status": row["verification_status"],
            "scope": scope,
            "source_memory_id": row["source_memory_id"],
            "redirects_to": row["redirects_to"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
