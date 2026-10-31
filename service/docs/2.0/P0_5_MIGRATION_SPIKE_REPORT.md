# Mnemosyne 2.0 — P0.5 Historical Migration Spike Report

**阶段：** P0.5  
**状态：** COMPLETED（只读；无生产写入）  
**日期：** 2026-10-31  
**代码基线：** 本地工作区基于 P0 文档树 + 生产 Memory Bank 只读抽样  
**远程基线：** GitHub `canyueY/dsh-mnemosyne@c82d47e`（P0 审计提交；本机完整 clone 因网络受阻，实现落在本地 `dsh-mnemosyne/service`）

## 1. 做了什么

1. 实现 Claim AST v1（`Atom|Negation|Temporal|Conditional|Unresolved`）。
2. 实现确定性规范化（无 LLM）与 `normalized_hash`。
3. 实现最小规则 Parser（偏好 / 音乐收藏 / 否定 / 条件 / 时空包装）。
4. 实现分层只读抽样器（目标 100 条）与 spike runner。
5. 对生产 `memory.db`（58,186 memories）只读执行 spike，产出 fixtures。

**禁止事项均遵守：** 未写 Claim 表、未改 Memory、未自动提升 verified、未伪造 provenance。

## 2. 产物路径

```text
service/docs/2.0/fixtures/migration_samples/
  migration_samples.jsonl
  parser_errors.jsonl
  provenance_gaps.jsonl
  spike_stats.json
  manual_review_notes.md
service/src/cognitive_memory/claims/
service/src/cognitive_memory/migration_spike/
service/tests/unit/test_claim_ast_parser.py
service/tests/unit/test_migration_spike_sampler.py
```

## 3. 统计（可从 jsonl 重算）

来源：`spike_stats.json`（2026-10-31T07:10:58Z）

| 指标 | 值 |
|---|---:|
| sample_count | 100 |
| claim_extraction_rate | 0.18 |
| multi_claim_memory_rate | 0.46 |
| ast_validity_rate | 1.0 |
| unresolved_rate | 0.82 |
| needs_review_rate | 0.0 |
| provenance_complete_rate | 0.0 |
| provenance_unknown_rate | 0.54 |
| security_mapping_failure_rate | 0.0 |
| false_merge_candidate_groups | 1 |
| review_required_rate | 0.82 |

### 分层

| 层 | n | parsed | unresolved |
|---|---:|---:|---:|
| S1_simple_fact | 41 | 0 | 41 |
| S2_preference | 10 | 10 | 0 |
| S3_temporal | 10 | 0 | 10 |
| S4_conditional | 10 | 0 | 10 |
| S5_negation | 9 | 2 | 7 |
| S6_synonym_candidate | 6 | 6 | 0 |
| S7_conflict_candidate | 7 | 0 | 7 |
| S10_unstructured | 7 | 0 | 7 |

说明：S8/S9 在本轮被去重/空查询挤占；不影响「不得伪造来源」结论（provenance_complete=0）。

## 4. 失败模式

1. **闲聊 / 任务摘要**：无稳定谓词 → Unresolved。
2. **含「如果」的长对话**：条件规则未命中干净结构 → Unresolved。
3. **时间相对词**（今天/昨天）若无命题核心 → Unresolved。
4. **旧 evidence 链接**：只能 partial/unknown，**complete=0**。
5. **重复 observed 文本**：1 组 hash 碰撞 → 人工复核，禁止自动 merge。

## 5. P1 决策建议

1. **Claim 必须独立持久化**（ADR-001）。
2. **默认 lifecycle = proposed**；历史 unverified ≠ Verified。
3. **Parser = 规则优先**；模型辅助仅产出 Candidate / needs_review。
4. **AST v1 保留 Unresolved 为主路径**；不要为抬升提取率而放宽。
5. **Evidence 独立对象**（P3）前，迁移只生成影子 Candidate。
6. **same_as** 仅规范化相等；语义相似不得 same_as。

## 6. 测试

```text
PYTHONPATH=src python -m unittest discover -s tests/unit -p "test_claim*.py" -v
PYTHONPATH=src python -m unittest discover -s tests/unit -p "test_migration*.py" -v
→ 11 passed
```

Live spike：

```text
python -m cognitive_memory.migration_spike.cli --db <memory.db> --out docs/2.0/fixtures/migration_samples
→ ok, sample_count=100
```

## 7. 未解决问题 / 风险

- 本机未能稳定 `git fetch` 远程 `dsh-mnemosyne`；交付需在网络恢复后 rebase/push 到 `main`。
- S1 样本被音乐/任务噪声主导，代表性偏斜；P1 后可补人工标注集。
- 未跑全量旧回归套件（下一步 P1 前补跑）。

## 8. 下一步

进入 **P1 Semantic Contract Freeze**：冻结四类判定契约 + 无 DB 耦合的类型测试；然后 **P1.5 Schema Governance Closure**。
