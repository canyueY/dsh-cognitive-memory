# P4 TMS Draft

**Status：** engine + Claim wiring (in-memory + optional persist)  
**Date：** 2026-10-31

## Package

`cognitive_memory/tms/`

| Module | Role |
|---|---|
| `models` | Justification, Edge, Belief |
| `scc` | Tarjan SCC |
| `engine` | add/retract justification, propagate with budget |
| `store` | optional SQLite persistence (`011_tms_v1`) |

## Claim wiring

- `submit_verified` → AND-justification from evidence refs
- `transition(disputed|rejected|superseded)` → retract / invalidate
- `redirect` → dependent claims reevaluate (OUT or alternate)

## API

- `POST /tms/justifications`
- `POST /tms/propagate`
- `GET /tms/belief/{node_id}`
