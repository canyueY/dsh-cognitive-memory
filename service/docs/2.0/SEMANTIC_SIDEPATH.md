# P3 Semantic Side-path

**Version：** retrieval.semantic.assist.v1  

## Role

Semantic similarity is an **assistive recall signal** only.

| May do | Must not do |
|---|---|
| Re-rank FTS hits | Replace Evidence |
| Suggest Claim surfaces | Mark Verified |
| Offline eval of novel hits | Change Claim lifecycle |

## Wiring

- `run_retrieve(..., semantic_assist=True)` → `assist_rerank`
- `ClaimStore.semantic_suggest` / `POST /claims/semantic-suggest`
- Trace channel name: `semantic_assist` with `authoritative=false`

## Default

`semantic_weight=0.25` (capped ≤ 0.6 in blender).
