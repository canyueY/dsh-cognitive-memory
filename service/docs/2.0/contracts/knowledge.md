# Contract: Knowledge (post-P5)

**Version：** knowledge.v1  

## Types

| Type | Source | Notes |
|---|---|---|
| `claim_knowledge` | Claim ids | Requires ≥1 claim_id; never invents Verified |
| `rule_knowledge` | Rule payload | Soft rules; hard constraints stay in value system |
| `structural_knowledge` | Schema / structure | Schema demotion target |
| `pattern_knowledge` | Pattern discovery | Candidate until validated |
| `strategy_knowledge` | Strategy id | Links Strategy; ACTIVE still gated |

## Validator

- Reject empty type / empty name
- `claim_knowledge` requires `claim_ids`
- `strategy_knowledge` requires `strategy_id`
- Status `active` does **not** authorize Claim Verified
- Status `active` for strategy-linked knowledge does **not** unlock `RL_POLICY_DEPLOYMENT`

## Non-goals

- Knowledge market / cross-user exchange (2.1+)
- Auto ACTIVE Strategy via Knowledge
