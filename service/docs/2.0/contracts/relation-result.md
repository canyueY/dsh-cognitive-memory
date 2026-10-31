# Contract: RelationResult

**Version：** relation.v1  
**Phase：** P1  

## Relations

```text
same_as | contradicts | qualifies | supports | unrelated | unknown
```

## Decisions

```text
accepted | rejected | abstained
```

## Legal combinations

| decision | final_relation |
|---|---|
| accepted | candidate relation, **not** `unknown` |
| rejected | `unrelated` or `unknown` |
| abstained | `unknown` |

## same_as (P2 rule, specified in P1)

```text
same_as(a,b) iff
  a.ast_version == b.ast_version
  AND normalize(a.ast) == normalize(b.ast)
  AND normalize(a.scope) == normalize(b.scope)
```

Properties: reflexive, symmetric, transitive. No LLM. Semantic similarity ≠ same_as.
Cross-version without verified migration map → `unknown` / abstained.
