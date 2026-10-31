# P2 Claim Table / Index Draft

**Status：** draft for migration `009_claims_v1`  
**Date：** 2026-10-31

## Principles

- Claims are first-class rows (not Memory projections).
- AST JSON is immutable once written; parser upgrades create new rows or supersede.
- Lifecycle status is separate from VerificationRecord.
- `normalized_hash` supports same_as / redirect without rewriting AST.

## Tables

### `claims`

| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | `clm_…` |
| bank_id | TEXT | fail-closed visibility |
| ast_version | TEXT | e.g. `claim.ast.v1` |
| ast_json | TEXT | ClaimAST envelope |
| surface | TEXT | audit surface text |
| normalized_hash | TEXT | deterministic same_as key |
| lifecycle | TEXT | proposed/supported/… |
| verification_status | TEXT | unverified/… (no silent verified) |
| scope_json | TEXT | bank/domain/time |
| source_memory_id | TEXT NULL | optional link |
| redirects_to | TEXT NULL | merge/redirect target |
| created_at / updated_at | TEXT | UTC |

Indexes: `(bank_id, lifecycle)`, `(normalized_hash)`, `(source_memory_id)`, `(redirects_to)`.

### `claim_evidence`

| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | |
| claim_id | TEXT | FK logical |
| evidence_ref | TEXT | observation/memory/verification id |
| role | TEXT | support / counter |
| independent | INTEGER | provenance flag |
| created_at | TEXT | |

### `claim_lifecycle_events`

Append-only transition log (from/to/reason/actor/policy_version/evidence_refs_json).

### `verification_records`

Optional P2 store for VerificationRecord (status, evidence_refs, actor, verified_at). Verified never without refs.

## Non-goals (P2 slice)

- No bulk production backfill.
- No LLM verified.
- No TMS / Strategy / MetaController.
