# Contract: Schema Mutation Governance (P1.5)

**Version：** schema.governance.v1  
**Capability：** `SCHEMA_MUTATION`（默认 LOCKED）

## Rules

1. Long-term schema mutations (`assimilate` / `accommodate` / `split` / `merge` / `apply`) MUST enter via LearningProposal (`cognitive_change_plans`).
2. `confirm=true` is **not** authorization.
3. Persist requires `confirm=true` **and** capability `SCHEMA_MUTATION` (or `SCHEMA_AUTO_EVOLUTION` for LOW-risk auto paths only).
4. Preview / dry-run MUST NOT mutate schema rows.
5. Governance denials emit JudgmentTrace with `governance_critical=true`.

## Bypass closure

| Path | Before P1.5 | After |
|---|---|---|
| `assimilate_schema` | direct `update_cognitive_schema` | proposal → gate → apply |
| `accommodate_schema` | direct update + optional plan | proposal → gate → apply |
| `split_schema` / `merge_schemas` | `confirm=true` executes | `confirm` + `SCHEMA_MUTATION` |
| `apply_cognitive_change_plan` | confirm only | confirm + `SCHEMA_MUTATION` |
