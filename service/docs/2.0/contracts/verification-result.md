# Contract: VerificationResult / VerificationRecord

**Version：** verification.v1  
**Phase：** P1 (frozen)  

## Status

`verified | not_verified | insufficient | disputed | expired | revalidate_required`

## VerificationRecord fields (frozen)

| Field | Type | Required when Verified |
|---|---|---|
| `record_id` | string | yes |
| `claim_id` | string | yes |
| `status` | enum | yes |
| `evidence_refs` | string[] | **non-empty** for `verified` |
| `actor` | string | yes |
| `verified_at` | string (ISO-8601Z) | yes for `verified` |
| `expired_at` | string\|null | set on expire |
| `detail` | object | optional |

## Engine algorithm

```text
assess(claim, evidence, counterevidence):
  if counterevidence non-empty → disputed
  if evidence empty → insufficient / not_verified
  else → not_verified   # assess NEVER yields verified

submit_verified(claim, evidence, actor, authorized, evidence_still_valid):
  if not authorized → reject
  if not evidence_still_valid → evidence_revoked_before_commit (anti-TOCTOU)
  if evidence_refs empty → ValidationError
  else → persist VerificationRecord(status=verified)
```

## Rules

- Only `VerificationEngine` may submit Verified.
- Verified requires VerificationRecord + evidence_refs + verified_at.
- Expired ≠ false; not_verified ≠ rejected.
- Disputed preferred over supported.
- Submit re-checks evidence validity (anti-TOCTOU).
- Unauthorized callers cannot submit Verified.
- Silent / LLM Verified **forbidden**.
- `confirm` ≠ authorization.
