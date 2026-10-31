# Mnemosyne 2.0 — P0.5 历史迁移 Spike 计划

**审计提交：** `589c694`  
**前置：** P0 审计已完成  
**目标：** 用约 100 条代表性历史 Memory 验证 Claim AST/Parser/Provenance 的可行性；**不写入正式库**。

## 1. 为什么先做 Spike

现有生产库有 58,186 条记忆、57,169 条 evidence 链接，绝大多数为 `unverified`，且没有 Claim AST。

如果直接设计 Claim 表或批量迁移：

- 可能把旧的自由文本误解析成错误命题；
- 可能把同源内容当成独立证据；
- 可能把历史 `candidate` 直接升级成 `verified`；
- 可能在新 Claim 上丢失原 Memory 权限。

因此必须先做小样本、手工复核、只读/影子迁移。

## 2. 样本设计

不能简单随机抽 100 条。按以下分层抽样（建议每层 8–15 条）：

| 层 | 样本类型 | 目的 |
|---|---|---|
| S1 | 简单事实 | 基本 Atom/实体/谓词 |
| S2 | 用户偏好 | modality=preference；不能等同客观事实 |
| S3 | 时间敏感信息 | temporal scope / 过期 |
| S4 | 条件性信息 | Conditional / scope |
| S5 | 否定表达 | Negation 范围 |
| S6 | 多来源同义表达 | same_as 候选 |
| S7 | 冲突信息 | contradicts / disputed |
| S8 | 不完整来源 | provenance_unknown |
| S9 | 权限敏感内容 | security scope |
| S10 | 无法结构化内容 | Unresolved 比例 |

建议从以下来源各取一部分：

- 高活跃 working memory；
- episodic candidate；
- semantic candidate；
- music domain observations；
- 含 `metadata.policy` 的记录；
- 含 `bank_id` 非 personal 的记录（如有）。

## 3. 迁移产物

本 Spike 只产出报告和样本，不写正式 Claim 表：

```text
docs/2.0/migration-spike/
  MIGRATION_SPIKE_REPORT.md
  migration_samples.jsonl
  parser_errors.jsonl
  provenance_gaps.jsonl
  manual_review_notes.md
```

每条样本至少包含：

```json
{
  "case_id": "...",
  "source_memory_id": "...",
  "source_text": "...",
  "source_kind": "...",
  "created_at": "...",
  "bank_id": "...",
  "metadata": {},
  "expected_claim_ast": null,
  "parsed_claim_ast": null,
  "parse_status": "parsed|unresolved|needs_review",
  "parse_confidence": 0.0,
  "provenance_status": "complete|partial|unknown",
  "security_scope": {},
  "notes": ""
}
```

## 4. 必测指标

| 指标 | 目标 |
|---|---|
| Claim 映射成功率 | 基线测量，不预设 |
| Unresolved 比例 | 基线测量；复杂文本允许高 |
| 来源完整率 | 基线测量 |
| 时间范围保留率 | 高 |
| 条件保留率 | 高 |
| 误合并率 | 越低越好；必须人工复核 |
| 误拆分率 | 越低越好 |
| 权限映射正确率 | 必须可解释 |
| 历史数据丢失率 | 0（只读迁移） |

> 不预设“成功率 ≥ 90%”之类数值；先测真实分布，再由 P1 决定阈值。

## 5. 迁移规则

1. 原始 Memory 保持只读。
2. 来源不完整标记 `legacy_provenance_incomplete`。
3. 未解析内容进入 `Unresolved`，不得强塞 Atom。
4. 不自动把历史 Memory 标为 `verified`。
5. 不自动合并同义 Claim；先生成候选。
6. 不跨 Bank 聚合。
7. 迁移结果进入 shadow 表/文件，不进入正式 Claim 表。
8. 失败可回滚，不修改源数据。

## 6. 决策门

Spike 结束后，P1 必须回答：

- Claim AST v1 是否足以表达真实样本？
- Parser 需要规则、模型，还是混合？
- 多少比例必须落到 `Unresolved`？
- 旧 Memory 的 provenance 缺失是否可接受？
- 是否需要 Claim 独立表，还是先做投影？
- 哪些历史数据不能迁移，只能保留为 Memory？
- 迁移后 Claim 的默认状态是什么（proposed，而非 verified）？

## 7. 禁止事项

- 不在生产库直接建 Claim 表并回填。
- 不把 `memory_evidence.relation=supports` 自动解释为 Claim 已验证。
- 不把同一内容的多次摘要当作独立证据。
- 不为了“结构化率”而强行解析。
- 不把历史 `confidence` 直接复制成 Claim confidence。

## 8. 完成标准

- 100 条分层样本完成解析/人工复核；
- 生成 `MIGRATION_SPIKE_REPORT.md`；
- 列出 Parser/AST 的失败模式；
- 给出 P1 契约修订建议；
- 给出 P2 Claim 表/迁移的最小 schema 草案；
- 不修改生产数据。
