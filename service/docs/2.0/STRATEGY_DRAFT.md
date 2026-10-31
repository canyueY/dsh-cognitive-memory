# P5 Strategy / Experience Draft

**Status：** first-class tables + propensity + gated offline eval  
**Date：** 2026-10-31

## Package

`cognitive_memory/strategy/`

| Module | Role |
|---|---|
| `experience_store` | create/list Experience |
| `strategy_store` | propose/list/retire Strategy + StrategyLog |
| `propensity` | overlap & propensity (no training) |
| `offline_eval` | gated evaluation report |
| `metacontroller` | schedule reflect/reevaluate only |

## Migration

`012_strategy_v1` → `experiences` / `strategies` / `strategy_logs`

## Non-goals (still forbidden)

- Online RL policy weight updates
- Auto ACTIVE without `RL_POLICY_DEPLOYMENT`
- Unbounded MetaController autonomy

## Completed bounds

- MetaController schedule actions including recommend/retire/batch reevaluate
- Online A/B metrics under `BANDIT_EXPERIMENT` (`013_ab_v1`)
