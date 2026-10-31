# Contract: Experience / Strategy (P5)

**Version：** strategy.v1  

## Experience

First-class row: `context` + `action` + `outcome` + optional `memory_ids` / `claim_ids`.  
Never copies long-term memory body as a second authority.  
Never marks Claim Verified.

## Strategy

Named policy hypothesis with `scope`, `status` (`proposed|experimental|active|retired`), `propensity` stats.  
`active` production status requires capability `RL_POLICY_DEPLOYMENT` (default LOCKED).

## StrategyLog

Append-only decision/outcome records linking Experience ↔ Strategy.  
Used for propensity / overlap / offline eval — not online RL loops by default.

## Offline eval

- May compute propensity scores and overlap reports without Gate.
- May run offline eval report under `BANDIT_EXPERIMENT` or `RL_OFFLINE_TRAINING`.
- Must not deploy / mutate production Strategy to `active` without `RL_POLICY_DEPLOYMENT`.
