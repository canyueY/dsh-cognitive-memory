# P3 Evidence Object Draft

**Status：** migration `010_evidence_objects_v1`  
**Date：** 2026-10-31

## Rules

1. Evidence is first-class (`evidences` table); `memory_evidence` is legacy bridge only.
2. Never invent `source_ref` / observation ids.
3. `provenance_status`: `unknown` (no source) | `partial` (source present) | `complete` (only after explicit chain audit — not auto).
4. `fingerprint` dedupes identical sources; `independence_key` flags correlated evidence.
5. Claim links prefer `evd_*` ids; observation refs are materialized on attach.

## Non-goals (this slice)

- Full independence algorithm / TMS
- Replacing all Memory evidence paths
- Semantic retrieval (separate P3 track)
