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
            if conn.in_transaction:
                conn.commit()
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
            if conn.in_transaction:
                conn.commit()
        return self._row_to_dict(row) if row else None

    def independence_conflict(
        self, evidence_ids: list[str]
    ) -> dict[str, Any]:
        """Same independence_key → not independent (P3 gate helper)."""
        keys: dict[str, list[str]] = {}
        for eid in evidence_ids:
            ev = self.get(eid)
            if not ev:
                continue
            k = str(ev.get("independence_key") or "")
            keys.setdefault(k, []).append(eid)
        collisions = {k: v for k, v in keys.items() if k and len(v) > 1}
        return {
            "ok": True,
            "independent": not bool(collisions),
            "collisions": collisions,
        }

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
