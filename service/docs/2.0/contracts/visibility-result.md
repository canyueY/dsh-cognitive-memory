# Contract: VisibilityResult

**Version：** visibility.v1  
**Phase：** P1 (frozen fields + algorithm)  

## Decision

`allow | deny | partial | unknown`

## Fields (frozen)

| Field | Type | Notes |
|---|---|---|
| `decision` | enum | allow / deny / partial / unknown |
| `visible_fields` | string[] | Controlled disclosure units granted |
| `denied_fields` | string[] | Explicitly withheld units |
| `usable_justifications` | string[] | Only fully-authorized AND justifications |
| `reason_codes` | string[] | Deterministic codes; sorted when emitted |
| `existence_disclosed` | bool | **MUST be false on deny** |
| `metadata` | object | Optional; never carries Claim body on deny |

## Controlled disclosure units (Claim)

Public defaults: `claim_id`, `lifecycle_status`, `ast_version`  
Sensitive: `verification_status`, `evidence_refs`, `justifications`, `ast`, `content`

## Algorithm (deterministic)

```text
1. If principal.bank not authorized for object_bank → DENY, existence_disclosed=false
2. If purpose not in purpose_constraints (when set) → DENY, existence_disclosed=false
3. If object_policy_allowed=false → DENY, existence_disclosed=false
4. For each requested field:
   - not in whitelist → deny field
   - verification_status|evidence_refs|justifications AND evidence_visible=false → deny field
   - else → visible
5. no visible & some denied → DENY, existence_disclosed=false
6. some denied → PARTIAL, existence_disclosed=true
7. else → ALLOW, existence_disclosed=true
```

## Rules

1. Permission checks **before** retrieval.
2. Cross-bank default deny.
3. Claim body and verification status are controlled disclosure units.
4. If Evidence is not visible, do not disclose Verified markers.
5. AND justifications require full authorization of all parts (no stitching).
6. Fail closed; deny does **not** disclose object existence.
7. Opaque HTTP body for missing OR denied: `{code:not_found, message:resource_unavailable}`.
8. Inference leak tests must assert: denied responses never contain Claim surface text.
