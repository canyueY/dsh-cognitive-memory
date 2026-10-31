# Contract: Claim Lifecycle

**Version：** claim.lifecycle.v1  

States: `proposed | supported | qualified | verified | disputed | rejected | expired | superseded`

All transitions go through `ClaimLifecycleEngine.transition_claim`. Illegal edges rejected. History append-only.
