# Contract: SecurityContext

**Version：** security.v1  
**Phase：** P1 (frozen fields + bank algorithm)  

## Fields (frozen)

| Field | Type | Default | Notes |
|---|---|---|---|
| `tenant_id` | string | `""` | Multi-tenant envelope (optional on single-node) |
| `bank_id` | string | `"personal"` | Primary bank of the principal |
| `owner_id` | string | `""` | Human / account owner |
| `agent_id` | string | `""` | Acting agent (empty for node admin) |
| `data_classification` | string | `"internal"` | **Not** an ordered privilege ladder |
| `access_scope` | string[] | `[]` | Optional scope tags |
| `purpose_constraints` | string[] | `[]` | Empty = all purposes allowed |
| `authorized_grants` | string[] | `[]` | e.g. `bank:shared` for cross-bank |
| `retention_policy` | string | `"default"` | Retention hint only |

## Bank authorization algorithm

```text
allows_bank(requested):
  req = normalize(requested) or "personal"
  if req == principal.bank_id → true
  if f"bank:{req}" in authorized_grants → true
  else → false   # cross-bank default deny
```

## Purpose algorithm

```text
allows_purpose(purpose):
  if purpose_constraints empty → true
  else → purpose ∈ purpose_constraints
```

## Rules

1. Classification is **not** an ordered privilege ladder.
2. Cross-bank default deny.
3. Agent grant ≠ registration (`authorized=false` until `issue_grant`).
4. `confirm` ≠ authorization (hard deletes need capability + confirm separately).
5. Grant revoke MUST invalidate any in-process permission cache immediately.
