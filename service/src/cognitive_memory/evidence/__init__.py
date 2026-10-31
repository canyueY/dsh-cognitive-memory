# -*- coding: utf-8 -*-
"""Evidence Engine（E1.4 legacy + P3 Evidence objects）。"""

from cognitive_memory.evidence.models import (
    EvidenceAttachIn,
    EvidenceKind,
    EvidenceRecord,
    ValidationState,
)
from cognitive_memory.evidence.object_store import EvidenceObjectStore
from cognitive_memory.evidence.store import attach_evidence, list_evidence_for_memory

__all__ = [
    "EvidenceAttachIn",
    "EvidenceKind",
    "EvidenceObjectStore",
    "EvidenceRecord",
    "ValidationState",
    "attach_evidence",
    "list_evidence_for_memory",
]
