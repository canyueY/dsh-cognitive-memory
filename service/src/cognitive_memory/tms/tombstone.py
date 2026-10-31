# -*- coding: utf-8 -*-
"""P4 R17：Memory 失效 → Claim/Evidence/TMS 级联 tombstone（不静默硬删 Claim）。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from cognitive_memory.storage.db import Database
from cognitive_memory.tms.store import TmsStore


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str = "cle") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def cascade_memory_invalidated(
    db: Database,
    memory_id: str,
    *,
    hard: bool = False,
    actor: str = "system",
) -> dict[str, Any]:
    """Mark related Claims superseded/expired-ish via TMS; soft-tombstone evidence objects.

    Never invents replacements. Hard delete of memory does not hard-delete Claims —
    Claims keep rows with lifecycle superseded + redirects cleared, verification unverified.
    """
    db.ensure_schema()
    tms = TmsStore(db)
    now = _now()
    claims_touched: list[dict[str, Any]] = []
    evidence_touched: list[str] = []

    with db.transaction() as conn:
        # Claims sourced from this memory
        rows = conn.execute(
            """
            SELECT id, lifecycle, verification_status FROM claims
            WHERE source_memory_id=? AND redirects_to IS NULL
            """,
            (memory_id,),
        ).fetchall()
        for row in rows:
            cid = row["id"]
            conn.execute(
                """
                UPDATE claims
                SET lifecycle='superseded',
                    verification_status='unverified',
                    updated_at=?
                WHERE id=?
                """,
                (now, cid),
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
                    row["lifecycle"] or "proposed",
                    "superseded",
                    f"memory_tombstone:{memory_id}:hard={hard}",
                    actor,
                    "claim.lifecycle.v1",
                    f'["{memory_id}"]',
                    now,
                ),
            )
            claims_touched.append({"claim_id": cid, "lifecycle": "superseded"})

        # Evidence objects linked via legacy_memory_id
        try:
            ev_rows = conn.execute(
                "SELECT id FROM evidences WHERE legacy_memory_id=?",
                (memory_id,),
            ).fetchall()
        except Exception:
            ev_rows = []
        for er in ev_rows:
            eid = er["id"]
            meta = {"tombstone": True, "tombstone_memory_id": memory_id}
            conn.execute(
                """
                UPDATE evidences
                SET validation_state='revoked',
                    provenance_status='unknown',
                    updated_at=?,
                    metadata_json=?
                WHERE id=?
                """,
                (now, json.dumps(meta, ensure_ascii=False), eid),
            )
            evidence_touched.append(eid)

        # claim_evidence links that reference this memory id directly
        try:
            conn.execute(
                """
                UPDATE claim_evidence
                SET role='revoked'
                WHERE evidence_ref=? OR evidence_ref=?
                """,
                (memory_id, f"mem:{memory_id}"),
            )
        except Exception:
            pass

    # TMS invalidate outside the same exclusive txn (uses own transactions)
    tms_results = []
    tms_results.append(
        tms.invalidate_node(f"mem:{memory_id}", reason="memory_tombstone", actor=actor)
    )
    for c in claims_touched:
        tms_results.append(
            tms.invalidate_node(c["claim_id"], reason="memory_tombstone", actor=actor)
        )
    for eid in evidence_touched:
        tms_results.append(
            tms.invalidate_node(eid, reason="memory_tombstone", actor=actor)
        )

    return {
        "ok": True,
        "memory_id": memory_id,
        "hard": hard,
        "claims_superseded": claims_touched,
        "evidence_revoked": evidence_touched,
        "tms": tms_results,
        "note": "claims_kept_as_tombstone_rows_not_hard_deleted",
        "generated_at": now,
    }
