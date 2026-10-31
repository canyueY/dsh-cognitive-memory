# Contract: JudgmentTrace

**Version：** judgment.trace.v1  
**Phase：** P1  

## Fields (frozen)

| Field | Type | Notes |
|---|---|---|
| `trace_id` | string | Opaque id |
| `judgment_type` | string | e.g. visibility / verify / claim.transition |
| `input_refs` | string[] | Claim/Evidence/Memory ids |
| `output_refs` | string[] | Result object ids |
| `evidence_refs` | string[] | |
| `reason_codes` | string[] | Deterministic |
| `algorithm_version` | string | |
| `rule_version` | string | |
| `governance_critical` | bool | If true → never sampled away |
| `uncertainty` | string | default `unknown` |
| `duration_ms` | number\|null | |
| `timestamp` | string (ISO-8601Z) | |
| `trace_completeness` | string | `complete` \| `failed` |

## Rules

1. Governance-critical traces are **never** sampled away.
2. Trace write failure must be explicit (`failures()` / completeness=`failed`).
3. Missing governance trace → fail closed for that judgment (do not invent success).
4. Replay is read-only over stored traces + lifecycle events.
