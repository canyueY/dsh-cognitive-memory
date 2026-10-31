# Contract: RelationResult

**Version：** relation.v1  
**Phase：** P1 / P2  

## Relations

```text
same_as | contradicts | qualifies | supports | unrelated | unknown
```

## Decisions

```text
accepted | rejected | abstained
```

## Output fields (frozen)

| Field | Type | Notes |
|---|---|---|
| `decision` | enum | accepted / rejected / abstained |
| `final_relation` | enum | see Legal combinations |
| `confidence` | number\|null | Optional; never invents Verified |
| `reason_codes` | string[] | Deterministic |
| `algorithm_version` | string | e.g. `relation.v2` |
| `left_claim_id` | string | |
| `right_claim_id` | string | |
| `abstain_reason` | string\|null | Required when abstained |

## Legal combinations

| decision | final_relation |
|---|---|
| accepted | candidate relation, **not** `unknown` |
| rejected | `unrelated` or `unknown` |
| abstained | `unknown` |

## same_as (deterministic)

```text
same_as(a,b) iff
  a.ast_version == b.ast_version
  AND normalize(a.ast) == normalize(b.ast)
  AND normalize(a.scope) == normalize(b.scope)
```

Properties: reflexive, symmetric, transitive. No LLM. Semantic similarity ≠ same_as.
Cross-version without verified migration map → `unknown` / abstained.
Scope participates in identity hash (prevents self-redirect on split).

## contradicts / qualifies / supports (rule sketch)

| Relation | Signal (non-exhaustive) |
|---|---|
| `contradicts` | Negation of same normalized atom; or mutually exclusive preference polarity |
| `qualifies` | Temporal / Conditional wrapper over shared atom; scope narrowing |
| `supports` | Independent evidence roles; non-negated same-direction preference |

When signals conflict or incomplete → `abstained` / `unknown` (fail closed).
