# Contract: TruthValue (strong Kleene)

**Version：** tv.v1  
**Phase：** P1  

## Enum

```text
TRUE | FALSE | UNKNOWN
```

## Operations

AND / OR / NOT follow strong Kleene three-valued logic (see task book §5.4).

## Separations

| Result | Domain |
|---|---|
| `not_found` | retrieval |
| `not_authorized` | visibility / access |
| `UNKNOWN` | logical judgment |

`UNKNOWN` must not auto-promote to Supported/Verified or count as positive/negative training evidence.
