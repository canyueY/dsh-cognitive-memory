# Contract: Claim Lifecycle

**Version：** claim.lifecycle.v1  
**Phase：** P1 / P2  

## States

```text
proposed → supported → verified
         ↘ disputed / rejected / expired / superseded / invalidated
```

## Illegal transitions (examples)

- `proposed → verified` direct (must pass supported + evidence)
- Silent Verified while `lifecycle=proposed`
- `redirects_to` set without `superseded|invalidated` tombstone

## Rules

1. Default on propose = `proposed` + `verification_status=unverified`.
2. Only `VerificationEngine.submit_verified` may set Verified (with evidence_refs).
3. Forget / memory cascade → Claim tombstone (`superseded`), never hard-delete Claim rows.
4. Rollback drills restore lifecycle from event log but **force** `verification_status=unverified`.
5. `confirm` ≠ authorization.
