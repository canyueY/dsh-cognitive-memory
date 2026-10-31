# Contract: VerificationResult / VerificationRecord

**Version：** verification.v1  

## Status

`verified | not_verified | insufficient | disputed | expired | revalidate_required`

## Rules

- Only `VerificationEngine` may submit Verified.
- Verified requires VerificationRecord + evidence_refs + verified_at.
- Expired ≠ false; not_verified ≠ rejected.
- Disputed preferred over supported.
- Submit re-checks evidence validity (anti-TOCTOU).
- Unauthorized callers cannot submit Verified.
