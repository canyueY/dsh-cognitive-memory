# Contract: Experience / Strategy / MetaController (P5–P6)

**Version：** strategy.v1  

## Experience

First-class row: `context` + `action` + `outcome` + optional `memory_ids` / `claim_ids` + `reward`.  
Never copies long-term memory body as a second authority.  
Never marks Claim Verified.

## Strategy

Named policy hypothesis with `scope`, `status` (`proposed|experimental|active|retired`), `propensity` stats.  
`active` production status requires capability `RL_POLICY_DEPLOYMENT` (default LOCKED).

## StrategyLog

Append-only decision/outcome records linking Experience ↔ Strategy.  
Used for propensity / overlap / offline eval — not online RL loops by default.

## Propensity algorithm (frozen)

```text
score = 0.7 * mean_reward + 0.3 * mean_scope_overlap
overlap = Jaccard(token_set(scope), token_set(context∪action))
recommend_activate iff score ≥ 0.55 AND n ≥ 3
```

Statistics only — never mutates Strategy status.

## Offline eval

- May compute propensity scores and overlap reports without Gate.
- May run offline eval report under `BANDIT_EXPERIMENT` or `RL_OFFLINE_TRAINING`.
- Must not deploy / mutate production Strategy to `active` without `RL_POLICY_DEPLOYMENT`.

## MetaController actions

`reflect | reevaluate | reevaluate_all | propose_retire | recommend_activate | rank_candidates | activate_if_authorized | ab_assign`

`rank_candidates` / `recommend_activate` are recommendation-only.
