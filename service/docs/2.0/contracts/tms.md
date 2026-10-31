# Contract: Truth Maintenance (P4)

**Version：** tms.v1  

## Belief

A node (Claim / Schema / Evidence ref) is:

- `IN` — at least one valid OR-justification
- `OUT` — no valid justification
- `UNKNOWN` — cycle / budget exhausted / incomplete premises

## Justification

- **AND justification**：all `premises` must be IN (and authorized if visibility-gated).
- **OR across justifications**：any one valid AND-justification keeps the node IN.
- Never stitch partial AND parts across principals (`filter_and_justifications`).

## Propagation

- Invalidate premise → mark dependent justifications invalid → recompute dependents.
- Revalidate when alternate justification exists.
- **SCC**：nodes in a strongly connected component without external support → `UNKNOWN` (no infinite overwrite).
- **Budget**：`max_nodes` / `max_depth`; stop with `budget_exhausted` reason; never silent full-graph rewrite.

## Non-goals (this slice)

- Full Knowledge demotion
- Auto ACTIVE schema from TMS alone
- LLM-authored justifications
