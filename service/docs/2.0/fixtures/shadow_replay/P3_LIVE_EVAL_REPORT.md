# P3 Live RO Eval Report

**Date：** 2026-10-31T07:45:40Z  
**Source：** `%LOCALAPPDATA%/Mnemosyne Memory Bank/data/memory.db` (read-only)  
**Shadow：** `live_eval_shadow_v2.db` (gitignored `*.db`)  
**JSON：** `live_eval_shadow_v2.live_eval.json`

## Constraints honored

- No writes to production `memory.db`
- No Claim / Evidence backfill into production
- No Verified
- No auto `provenance_status=complete`

## Method

1. Sample latest 120 memories; derive up to 25 **paraphrase** queries (e.g. `喜欢听{title}` from music inference lines).
2. Lexical FTS-like token overlap vs semantic `pool_suggest` (`min_score=0.2`).
3. Map 50 latest `memory_evidence` rows → shadow `evidences` via `from_legacy_memory_link`.

## Results

| Metric | Value |
|---|---|
| sample_count | 120 |
| query_count | 25 |
| fts_recall_avg | **0.80** |
| assist_novel_total | **3** |
| assist_novel_rate | **0.12** |
| evidence_links_scanned | 50 |
| evidence_objects_created | 50 |
| evidence_partial | 50 |
| evidence_unknown | 0 |
| provenance_complete_forbidden | **0** |
| errors | [] |

## Interpretation

- On paraphrased music queries, FTS already recovers ~80%; semantic assist recovered **12%** additional self-hits that FTS missed (novel assist).
- Semantic scores on short title paraphrases are often low (~0.27); keep weight low (0.25) and assistive-only.
- Legacy evidence links all had observation ids → **partial** provenance; never completed automatically.

## Follow-ups

- Optional: raise paraphrase diversity beyond music titles
- Online A/B not required for P3 gate
- Ready to merge PR #1 when approved
