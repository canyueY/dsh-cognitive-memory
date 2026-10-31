# Contract: Evidence Provenance

**Version：** evidence.provenance.v1  
**Phase：** P1 / P3 / P9 gate  

## Provenance status

`unknown | partial | complete`

## complete requires (all)

1. Independent Evidence object id (not legacy memory link alone)
2. `source_type` + `source_ref` non-empty
3. `fingerprint` present
4. Provenance chain length ≥ 1 with producer
5. `validation_state` ≠ revoked

Legacy `memory_evidence` links alone → at most `partial`.

## P9 migration gate

```text
IF provenance_complete_rate < 0.01:
  block production Claim writes
  dry-run routes samples → hold_unresolved / needs_review
  never auto-verify
  never invent sources
```

P0.5 finding: production sample `provenance_complete_rate = 0.0` → P9 write path blocked until provenance redesign.
