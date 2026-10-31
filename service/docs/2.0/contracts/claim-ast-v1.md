# Contract: Claim AST v1

**Version：** claim.ast.v1  
**Phase：** P0.5 / P1  

## Shapes

```text
Atom(subject, predicate, arguments[], modality?)
Negation(target)
Temporal(interval=[start,end), target)
Conditional(condition, consequence)
Unresolved(raw_text, missing_fields, parse_attempts[], reason_codes[])
```

## Rules

- AST version required on envelope.
- Unexpressible logic → Unresolved (never force Atom).
- Normalization is deterministic; no LLM in normalize path.
- Parser upgrade must not silently rewrite historical Claim AST rows (future persistence).
