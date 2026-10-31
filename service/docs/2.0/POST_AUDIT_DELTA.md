# Mnemosyne 2.0 — P0 审计后状态增量

**历史审计代码快照：** `589c694`
**历史审计文档提交：** `c82d47e`  
**当前检查提交：** `9eb9b93`（`Merge pull request #4 from canyueY/feat/mnemosyne-host-output-schema-021`）  
**日期：** 2026-10-31  
**用途：** 修正 P0 审计之后已合入的 P2–P7 与 DSH 0.2.1 宿主修复，不覆盖历史审计原文。

> **重要：** `P0_REPOSITORY_AUDIT.md` 及同目录其他 P0 文档记录的是代码快照 `589c694` / 文档提交 `c82d47e` 的状态。  
> 当前 `main` 已经包含 Claim 纵向切片、Evidence 对象、TMS、Strategy、Knowledge 和 DSH 0.2.1 宿主修复。  
> 因此“Claim Missing / Evidence 只是链接”等结论**只适用于历史快照**，不适用于当前 `main`。

---

## 1. 当前新增能力

| 能力 | 当前实现 | 状态 |
|---|---|---|
| Claim AST | `claims/ast.py`：Atom / Negation / Temporal / Conditional / Unresolved | Implemented |
| Claim Parser | `claims/parser.py`：规则解析，保守进入 Unresolved；无 LLM | Implemented-lite |
| Claim Store | `claims/store.py`：propose / get / evidence / transition / verify / redirect / semantic_suggest | Implemented |
| Claim Lifecycle | `claims/lifecycle.py`：proposed → supported → qualified → verified → disputed → expired / superseded / rejected | Implemented |
| Claim Judgment | `judgment/relations.py`：RelationResult / `same_as`；`judgment/truth_value.py`：三值逻辑 | Implemented |
| Evidence Object | `evidence/object_store.py`；`evidences` API/表 | Implemented |
| Verification | `verification/engine.py`、`persist.py`、`verification_records` 表 | Implemented |
| Visibility | `visibility/service.py`：fail-closed、字段级、旧 Justification 过滤 | Implemented-lite |
| Truth Maintenance | `tms/engine.py`、`store.py`、`scc.py`、`schema_bridge.py`、`tombstone.py` | Implemented |
| Experience / Strategy | `strategy/experience_store.py`、`strategy_store.py`、`propensity.py`、`offline_eval.py`、`metacontroller.py` | Implemented |
| Knowledge | `knowledge/store.py`、`validator.py`、`knowledge_nodes` 表 | Implemented |
| Judgment Trace | `tracing/service.py`、`JudgmentTrace` | Implemented |
| DSH 宿主 | `src/tool-spec.js` 输出 schema 改为 `{ type: 'object', additionalProperties: true }`；engines.dsh / peer 对齐 0.2.1 | Implemented |
| DSH 宿主 E2E | 真实 `@deepseek-ai/dsh-tools@0.2.1-rc.5` + Python 子进程；见 [HOST_E2E_VERIFICATION.md](HOST_E2E_VERIFICATION.md) | Passed |

---

## 2. 当前 schema 增量

新增表：

```text
claims
claim_evidence
claim_lifecycle_events
verification_records
evidences
tms_justifications
tms_beliefs
experiences
strategies
strategy_logs
ab_exposures
ab_outcomes
knowledge_nodes
value_soft_prefs
```

这意味着 P0 审计中“无 Claim 表 / 无 VerificationRecord / 无 TMS / 无 Strategy”的表述已经过时。

---

## 3. 测试结果

在 `9eb9b93` 上重新执行：

| 套件 | 结果 |
|---|---|
| Python service tests | **221 passed, 1 warning in 20.36s** |
| Node plugin tests | **7 passed** |
| `npm run check` | 通过 |
| `node src/test/host-compat-021.mjs` | **2 passed** |

Claim 相关测试：

```text
tests/unit/test_claim_ast_parser.py
tests/unit/test_p2_claim_matrix.py
tests/unit/test_p2_claim_store.py
```

合计 **28 个 Claim 测试**。

---

## 4. DSH 0.2.1 宿主修复

修复点：

- `tool output.schema` 不再使用空 `{}` 或非法 `type: "json"`；
- 统一改为：

```js
{ type: 'object', additionalProperties: true }
```

- `package.json` / `dsh.plugin.json` 对齐 `dsh 0.2.1`；
- peer `@deepseek-ai/dsh-tools` 改为 `>=0.2.1-0 <0.3.0`；
- 以 `@deepseek-ai/dsh-tools@0.2.1-rc.5` 校验全部 `memory_*` 工具可注册。

本地验证：

```text
npm test                 7 passed
npm run check            passed
host-compat-021.mjs      2 passed
```

---

## 5. 仍然需要保留的警告

即使 P2–P7 已合入，也不能把当前 `main` 等同于“2.0 全部完成”：

1. **Parser 是规则解析，不是完整自然语言理解**；复杂表达仍会进入 `Unresolved`。
2. **Claim 测试是单元/矩阵测试**，还缺真实历史数据上的 P0.5 迁移验收。
3. **Visibility 是确定性实现**，但跨 Bank、OR Justification、推理泄漏的完整验收仍需独立测试。
4. **TMS/Strategy/Knowledge 是新代码**，需要真实数据与回放评估，不应只看单测。
5. **生产 Bank 仍是旧数据**；新增表尚未对现有 58k memories 做全量 Claim 映射。
6. **DSH 0.2.1 修复已本地验证**，但仍应以真实宿主加载插件做一次端到端冒烟。

---

## 6. 结论

历史 P0 审计的结论需要拆成两层：

| 时点 | 结论 |
|---|---|
| `c82d47e` | Claim Missing；Evidence 只是链接；P2 尚未开始 |
| `9eb9b93` | Claim/Evidence/Verification/TMS/Strategy/Knowledge 已有实现与测试；进入 P2–P7 代码验收阶段 |

当前正确表述：

> **Mnemosyne 2.0 的 Claim 纵向切片与后续 P2–P7 代码已经合入；下一步不是继续争论“有没有 Claim”，而是用 P0.5 真实数据迁移、宿主端到端与独立实验来验证这些实现。**

历史文档保留不动；本增量作为当前 `main` 的状态说明。
