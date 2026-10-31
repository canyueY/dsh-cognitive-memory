"""Explicit synthetic evidence fixtures, stored in each test's scratch database."""
from cognitive_memory.evidence.object_store import EvidenceObjectStore


def seed_evidence(db, reference, *, root=None, bank="personal"):
    ev = EvidenceObjectStore(db).create(
        source_type="test_fixture", source_ref=f"fixture:{reference}",
        bank_id=bank, producer="test", root_source_id=root or reference,
        validation_state="valid", provenance_status="complete",
        chain=[{"step":"synthetic_fixture","ref":reference}],
    )["evidence"]
    with db.transaction() as conn:
        conn.execute("UPDATE evidences SET id=? WHERE id=?", (reference, ev["id"]))
    return reference
