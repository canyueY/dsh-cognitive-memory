# -*- coding: utf-8 -*-
"""Evidence Engine（E1.4）：证据与记忆正文分离 + provenance。"""

from cognitive_memory.evidence.models import (
    EvidenceAttachIn,
    EvidenceKind,
    EvidenceRecord,
    ValidationState,
)
from cognitive_memory.evidence.store import attach_evidence, list_evidence_for_memory

__all__ = [
    "EvidenceAttachIn",
    "EvidenceKind",
    "EvidenceRecord",
    "ValidationState",
    "attach_evidence",
    "list_evidence_for_memory",
]
