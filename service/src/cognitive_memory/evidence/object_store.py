# -*- coding: utf-8 -*-
"""P3 Evidence objects — independent of Memory body.

Never invent provenance. Legacy memory_evidence maps as unknown|partial.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from cognitive_memory.storage.db import Database


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str = "evd") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def fingerprint_of(*, source_type: str, source_ref: str, content: str = "") -> str:
    raw = f"{source_type}|{source_ref}|{content}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def independence_key_of(
    *, source_type: str, producer: str = "", root_source_id: str = ""
) -> str:
    raw = f"{source_type}|{producer}|{root_source_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


class EvidenceObjectStore:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.db.ensure_schema()

    def create(
        self,
        *,
        source_type: str,
        source_ref: str = "",
        bank_id: str = "personal",
        content_for_fingerprint: str = "",
        producer: str = "",
        root_source_id: str = "",
        role_hint: str = "support",
        validation_state: str = "unverified",
        provenance_status: str | None = None,
        chain: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        legacy_memory_id: str | None = None,
        security: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create Evidence. provenance_status defaults: no source → unknown; else partial."""
        st = str(source_type or "").strip() or "unknown"
        ref = str(source_ref or "").strip()
        if provenance_status is None:
            if not ref or st == "unknown":
                provenance_status = "unknown"
            else:
                provenance_status = "partial"  # never auto-complete without chain audit
        fp = fingerprint_of(
            source_type=st, source_ref=ref, content=content_for_fingerprint
        )
        existing = self.find_by_fingerprint(fp, bank_id=bank_id)
        if existing:
            return {"ok": True, "deduped": True, "evidence": existing}
        indep = independence_key_of(
            source_type=st,
            producer=producer,
            root_source_id=root_source_id or ref,
        )
        eid = _new_id()
        now = _now()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO evidences(
                  id, bank_id, source_type, source_ref, fingerprint,
                  provenance_status, independence_key, root_source_id, producer,
                  role_hint, validation_state, security_json, chain_json,
                  metadata_json, legacy_memory_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    bank_id,
                    st,
                    ref,
                    fp,
                    provenance_status,
                    indep,
                    root_source_id or ref,
                    producer,
                    role_hint,
                    validation_state,
                    json.dumps(security or {}, ensure_ascii=False),
                    json.dumps(chain or [], ensure_ascii=False),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    legacy_memory_id,
                    now,
                    now,
                ),
            )
        return {"ok": True, "deduped": False, "evidence": self.get(eid)}

    def create_from_observation(
        self,
        observation_id: str,
        *,
        bank_id: str = "personal",
        producer: str = "",
        legacy_memory_id: str | None = None,
        content: str = "",
        role_hint: str = "support",
    ) -> dict[str, Any]:
        if not str(observation_id or "").strip():
            return {
                "ok": False,
                "detail": "source_ref_required",
                "note": "never_invent_observation_id",
            }
        return self.create(
            source_type="observation",
            source_ref=str(observation_id).strip(),
            bank_id=bank_id,
            content_for_fingerprint=content,
            producer=producer,
            root_source_id=str(observation_id).strip(),
            role_hint=role_hint,
            provenance_status="partial",
            chain=[{"step": "observation", "ref": observation_id}],
            legacy_memory_id=legacy_memory_id,
        )

    def from_legacy_memory_link(
        self,
        *,
        memory_id: str,
        observation_id: str,
        relation: str = "supports",
        bank_id: str = "personal",
        producer: str = "",
    ) -> dict[str, Any]:
        """Map legacy memory_evidence → Evidence object (provenance never invented)."""
        if not observation_id:
            return self.create(
                source_type="legacy_memory_evidence",
                source_ref=memory_id,
                bank_id=bank_id,
                producer=producer,
                provenance_status="unknown",
                role_hint="support" if relation == "supports" else "counter",
                legacy_memory_id=memory_id,
                metadata={"legacy_relation": relation, "missing_observation": True},
            )
        return self.create_from_observation(
            observation_id,
            bank_id=bank_id,
            producer=producer,
            legacy_memory_id=memory_id,
            role_hint="support" if relation == "supports" else "counter",
        )

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        with self.db.exclusive() as conn:
            row = conn.execute(
                "SELECT * FROM evidences WHERE id=?", (evidence_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def find_by_fingerprint(
        self, fingerprint: str, *, bank_id: str = "personal"
    ) -> dict[str, Any] | None:
        with self.db.exclusive() as conn:
            row = conn.execute(
                """
                SELECT * FROM evidences
                WHERE fingerprint=? AND bank_id=?
                ORDER BY created_at ASC LIMIT 1
                """,
                (fingerprint, bank_id),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def independence_conflict(
        self, evidence_ids: list[str]
    ) -> dict[str, Any]:
        """Same independence_key → not independent (P3 gate helper)."""
        keys: dict[str, list[str]] = {}
        unknown=[]
        for eid in evidence_ids:
            ev = self.get(eid)
            if not ev:
                unknown.append(eid)
                continue
            if ev["provenance_status"]=="unknown" or not ev["source_ref"]:
                unknown.append(eid)
            lineage = self.lineage(eid)
            if not lineage["ok"]:
                unknown.append(eid)
            for root in lineage["roots"]:
                keys.setdefault(root, []).append(eid)
        collisions = {k: v for k, v in keys.items() if k and len(v) > 1}
        return {
            "ok": True,
            "independent": not bool(collisions) and not unknown,
            "unknown":unknown,
            "collisions": collisions,
        }

    def lineage(self, evidence_id: str, *, max_nodes: int = 64) -> dict[str, Any]:
        """Resolve declared original roots across producers/types, never count a cycle.

        Root IDs are provenance declarations, not proof of source authenticity.
        Unknown/cyclic/missing/cross-bank ancestry fails closed.
        """
        roots, visited, active = set(), set(), set()
        origin = self.get(evidence_id)
        def visit(eid):
            if eid in active:
                return False
            if eid in visited:
                return True
            if len(visited) >= max_nodes:
                return False
            ev = self.get(eid)
            if not ev or not origin or ev["bank_id"] != origin["bank_id"]:
                return False
            visited.add(eid)
            active.add(eid)
            if ev["provenance_status"] == "unknown" or not ev["source_ref"]:
                return False
            if ev["validation_state"] in {"revoked", "invalidated", "expired", "rejected"}:
                return False
            expiry = ev["metadata"].get("valid_until")
            if expiry:
                try:
                    if datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                        return False
                except (ValueError, TypeError, AttributeError):
                    return False
            parents = ev["metadata"].get("parent_evidence_ids", [])
            if not isinstance(parents, list) or any(not isinstance(p, str) for p in parents):
                return False
            if parents:
                if not all(visit(p) for p in parents):
                    return False
            else:
                roots.add(ev["root_source_id"] or ev["source_ref"])
            active.remove(eid)
            return True
        ok = visit(evidence_id)
        return {"ok": ok, "roots": sorted(roots), "evidence_ids": sorted(visited)}

    def assess(self, evidence_id: str, *, state: str, actor: str,
               provenance_chain: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Explicit reviewer decision. Revocation is durable and invalidates dependencies."""
        from cognitive_memory.tracing.service import JudgmentTraceService
        if state not in {"valid", "revoked", "invalidated", "unverified"}:
            return {"ok":False, "detail":"invalid_evidence_state"}
        with self.db.transaction() as conn:
            ev = self.get(evidence_id)
            if not ev:
                return {"ok":False, "detail":"not_found"}
            chain = provenance_chain if provenance_chain is not None else ev["chain"]
            if state == "valid":
                if not ev["source_ref"] or not chain:
                    return {"ok":False, "detail":"source_and_chain_required"}
                if ev["source_type"] == "observation" and conn.execute(
                    "SELECT 1 FROM observations WHERE id=?", (ev["source_ref"],)
                ).fetchone() is None:
                    return {"ok":False, "detail":"source_missing"}
            conn.execute(
                "UPDATE evidences SET validation_state=?, provenance_status=?, chain_json=?, updated_at=? WHERE id=?",
                (state, "complete" if state == "valid" else ev["provenance_status"],
                 json.dumps(chain, ensure_ascii=False), _now(), evidence_id),
            )
            JudgmentTraceService(self.db).record(
                "evidence.assess", input_refs=[evidence_id, actor],
                reason_codes=[ev["validation_state"], state], governance_critical=True,
            )
            if state in {"revoked", "invalidated", "unverified"}:
                from cognitive_memory.claims.store import ClaimStore
                claims = ClaimStore(self.db)
                affected_refs = {evidence_id}
                descendants = conn.execute("SELECT id,metadata_json FROM evidences WHERE bank_id=?", (ev["bank_id"],)).fetchall()
                changed = True
                while changed:
                    changed = False
                    for child in descendants:
                        parents = json.loads(child["metadata_json"] or "{}").get("parent_evidence_ids", [])
                        if isinstance(parents, list) and child["id"] not in affected_refs and affected_refs.intersection(p for p in parents if isinstance(p, str)):
                            affected_refs.add(child["id"])
                            conn.execute("UPDATE evidences SET validation_state='unverified',updated_at=? WHERE id=?", (_now(), child["id"]))
                            changed = True
                for ref in affected_refs:
                    claims.tms.invalidate_node(ref, reason=state, actor=actor)
                placeholders = ",".join("?" for _ in affected_refs)
                affected = conn.execute(
                    f"SELECT DISTINCT claim_id FROM claim_evidence WHERE evidence_ref IN ({placeholders})", tuple(affected_refs)
                ).fetchall()
                # Also include submitted refs even if the caller did not attach a link.
                for row in conn.execute("SELECT claim_id,evidence_refs_json FROM verification_records"):
                    if affected_refs.intersection(json.loads(row[1])):
                        if row[0] not in {r[0] for r in affected}:
                            affected.append((row[0],))
                for row in affected:
                    claim = claims.get(row[0], follow_redirect=False)
                    if claim and claim["lifecycle"] == "verified":
                        alternatives = [r["evidence_ref"] for r in claims.list_evidence(row[0])
                                        if r["role"] == "support" and r["evidence_ref"] not in affected_refs]
                        from cognitive_memory.verification.assessment import assess_evidence
                        assessment = assess_evidence(self.db, claim, alternatives)
                        if assessment["ok"]:
                            claims.submit_verified(row[0], evidence_refs=alternatives, actor=actor)
                        else:
                            claims.transition(row[0], "supported", reason="evidence_revalidation_required", actor=actor)
                            conn.execute("UPDATE claims SET verification_status='revalidate_required' WHERE id=?", (row[0],))
                            conn.execute("UPDATE verification_records SET status='revalidate_required' WHERE claim_id=?", (row[0],))
        return {"ok":True, "evidence":self.get(evidence_id)}

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        def _j(raw: Any, default: Any) -> Any:
            try:
                return json.loads(raw or ("{}" if isinstance(default, dict) else "[]"))
            except json.JSONDecodeError:
                return default

        return {
            "id": row["id"],
            "bank_id": row["bank_id"],
            "source_type": row["source_type"],
            "source_ref": row["source_ref"],
            "fingerprint": row["fingerprint"],
            "provenance_status": row["provenance_status"],
            "independence_key": row["independence_key"],
            "root_source_id": row["root_source_id"],
            "producer": row["producer"],
            "role_hint": row["role_hint"],
            "validation_state": row["validation_state"],
            "security": _j(row["security_json"], {}),
            "chain": _j(row["chain_json"], []),
            "metadata": _j(row["metadata_json"], {}),
            "legacy_memory_id": row["legacy_memory_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
