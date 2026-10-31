# Mnemosyne 2.0 — 任务书完成情况审计

**任务书：** `10.31更新方案.txt`（2143 行）  
**任务书基线：** `c82d47e`  
**当前代码：** `9eb9b93`（P2–P7 + DSH 0.2.1 修复）  
**当前文档：** `d59fa21`（含宿主 E2E 记录）  
**审计日期：** 2026-10-31  
**结论：** **不能按任务书宣称“全部完成”。** 代码主干推进很大，但任务书中的 P7、P8、P9 仍未达到验收条件；P2 也有明确缺口。

---

## 1. 总体判断

当前仓库的 `IMPLEMENTATION_STATUS.md` 写的是：

```text
P0–P1.5 COMPLETED
P2 COMPLETED
P3 COMPLETED
P4 COMPLETED
P5 COMPLETED
P6 COMPLETED
P7 COMPLETED（脚本；人工现网签字外置）
```

但这套编号**不是任务书的编号**。

任务书的阶段是：

```text
P0 Audit
P0.5 Migration Spike
P1 Contract Freeze
P1.5 Governance Closure
P2 Claim Vertical Slice
P3 Evidence Independence
P4 Knowledge & Truth Maintenance
P5 Experience & Strategy
P6 Strategy Evaluation & MetaController
P7 Fault Localization & Repair Validation
P8 Security Hardening & DSH Integration
P9 Migration & Release
```

仓库把 Knowledge 放到 P6、把 GA 检查放到 P7，导致“P7 COMPLETED”并不等于任务书的 P7 完成。

> **准确说法：** P0–P6 的大部分代码与测试已经落地；任务书的 P7、P8、P9 仍缺失或只有局部实现。

---

## 2. 阶段完成矩阵

| 任务书阶段 | 当前证据 | 判定 | 主要缺口 |
|---|---|---|---|
| P0 Repository Audit | 7 份审计文档 + `POST_AUDIT_DELTA` | **COMPLETED** | 无 |
| P0.5 Migration Spike | `P0_5_MIGRATION_SPIKE_REPORT.md`、100 条样本、fixtures | **COMPLETED（有重大发现）** | provenance_complete=0；S8/S9 样本覆盖不足；只读 |
| P1 Contract Freeze | `contracts/` 13 份、P1 测试 | **PARTIAL** | 多数 contract 只有几十行，字段/算法未完全冻结 |
| P1.5 Governance Closure | `schema_ops`/`schema_network` 接入 `SCHEMA_MUTATION`；`test_schema_gate` | **COMPLETED** | 需确认所有旧入口都覆盖 |
| P2 Claim Vertical Slice | `claims/` + Merge/Split/Relation + S1–S20 | **NEAR COMPLETE** | P1 契约仍偏薄；生产规模关系评测未做 |
| P3 Evidence Independence | `evidence/object_store.py`、P3 测试、independence | **COMPLETED（代码层）** | 生产历史迁移未做 |
| P4 Knowledge & Truth Maintenance | `tms/`、`knowledge/`、P4/P6 测试 | **COMPLETED（代码层）** | 生产规模验证未做 |
| P5 Experience & Strategy | `strategy/`、Experience、StrategyLog、P5 测试 | **COMPLETED（代码层）** | 真实任务数据少 |
| P6 Strategy Evaluation & MetaController | A/B、propensity、offline eval、metacontroller | **PARTIAL** | 真实 prop/overlap 数据不足；调度未做生产验证 |
| P7 Fault Localization & Repair Validation | `fault/` + `015_fault_v1` + pipeline 测试 | **IN PROGRESS** | 故障注入覆盖面仍窄；历史回放/回滚仍为记录型演练 |
| P8 Security Hardening & DSH Integration | Visibility/SecurityContext；DSH 0.2.1 宿主 E2E | **PARTIAL** | 推理泄漏、缓存撤销、完整删除传播、跨 Bank 全链路 |
| P9 Migration & Release | 仅有 P0.5 只读 spike | **MISSING** | Claim 迁移、dry run、批次、回滚、发布 |

---

## 3. P2 的具体缺口

P2 文档标为 COMPLETED，但任务书 P2 要求：

- Claim Merge；
- Claim Split；
- Redirect；
- Relation 的 `supports` / `contradicts` / `qualifies`；
- 20 项 Claim 测试；
- 并发提交；
- 重复请求。

当前：

- `claims/store.py` 有 `redirect()`；
- `judgment/relations.py` 主要实现 `evaluate_same_as()`；
- 没有发现 Claim merge/split 函数；
- 没有发现 `/claims/parse`、`/claims/{id}/relations` 的完整 API；
- `test_p2_claim_matrix.py` 是 S1–S14，不是任务书的 20 项；
- 并发/重复请求主要依赖底层幂等，不是 Claim 专项测试。

因此 P2 应标为 **PARTIAL**，而不是完成。

---

## 4. P0.5 的审计发现

P0.5 是只读 spike，执行正确，但结果暴露了真实迁移风险：

| 指标 | 值 |
|---|---:|
| sample_count | 100 |
| claim_extraction_rate | 0.18 |
| unresolved_rate | 0.82 |
| provenance_complete_rate | **0.0** |
| provenance_unknown_rate | 0.54 |
| false_merge_candidate_groups | 1 |

结论：

- 历史 Memory 的 Claim 提取率很低（18%）；
- 绝大多数样本进入 Unresolved；
- 历史来源链完整率为 0；
- 不能直接做全量 Claim 迁移；
- P9 之前必须重新设计 provenance/迁移策略。

P0.5 已完成“发现问题”的任务，但它也证明 **P9 不能直接开始**。

---

## 5. P7 / P8 / P9 的关键缺失

### P7 Fault Localization & Repair Validation

任务书要求：

```text
Invariant Violation
→ Earliest Deviation
→ Differential Trace
→ Minimal Reproduction
→ Candidate Root Cause
→ Patch
→ Targeted Test
→ Regression Test
→ Historical Replay
→ Rollback Test
→ Governance
```

当前没有：

- fault localization 模块；
- differential trace；
- minimal reproduction；
- root cause 记录；
- repair validation 记录；
- 故障注入测试。

`IMPLEMENTATION_STATUS` 的 P7 实际是 `scripts/mnemosyne_claim_ga_check.py`，只是导入/迁移/Gate 检查，不是任务书的 P7。

### P8 Security Hardening & DSH Integration

已完成：

- `SecurityContext`；
- Visibility 的字段/跨 Bank/fail-closed；
- DSH 0.2.1 工具 schema；
- 真实 ToolRuntime + DSH headless 工具调用。

仍缺：

- 推理泄漏测试（Claim 文本、字段、存在性）；
- 权限缓存撤销；
- 完整删除传播（Memory → Evidence → Claim → Knowledge → Strategy → Cache/Index/Trace）；
- 跨 Bank 授权全链路；
- 受限错误信息不泄漏对象存在性的系统测试。

### P9 Migration & Release

当前仅有 P0.5 的 100 条只读抽样，没有：

- Claim 生产迁移；
- dry run + report + 人工审查；
- 小规模试迁移；
- 一致性验证；
- 批次扩大；
- 新旧接口兼容；
- 发布/回滚演练。

---

## 6. 最终 20 项验收对照

| # | 验收项 | 状态 |
|---|---|---|
| 1 | Memory → 有来源 Evidence | 通过（代码/测试） |
| 2 | Evidence → 结构化 Claim | 通过（P2） |
| 3 | 确定性 Claim 身份比较 | 通过（`same_as`） |
| 4 | 支持/反驳/限定/未知关系 | **通过（代码/S17–S18）**；生产语料评测仍缺 |
| 5 | VerificationEngine 验证 | 通过（代码/测试） |
| 6 | 验证撤销/过期/重评 | 通过（测试） |
| 7 | Unknown 贯穿判断链路 | **部分**（TruthValue 有，链路未全） |
| 8 | Visibility 对象/字段/依据 | **部分**（代码有，全链路未验） |
| 9 | Knowledge 建立在可追溯 Claim 上 | 通过（代码/测试） |
| 10 | Evidence 失效触发增量 TMS | 通过（测试） |
| 11 | Experience 记录真实轨迹 | 通过（代码/测试） |
| 12 | Strategy 关联上下文/依据/结果 | 通过（代码/测试） |
| 13 | 策略效果可验证 | **部分**（真实 prop/overlap 数据不足） |
| 14 | MetaController 调度 | **部分**（有实现，生产验证不足） |
| 15 | 故障定位/修复有复现/回归/回滚 | **部分**（P7 pipeline 已落地；注入面仍窄） |
| 16 | 关键判断完整 Trace | **部分**（JudgmentTrace 有，回放/完整性未全） |
| 17 | DSH 不能绕过 Governance | **部分**（宿主工具已通，治理全链路未验） |
| 18 | 3.0 基础功能兼容 | 通过（221 tests） |
| 19 | 历史迁移可回滚 | **未完成** |
| 20 | 核心能力有自动化测试和阶段验收 | **部分**（P7/P9 无） |

---

## 7. 实际验证结果

在 `9eb9b93` 上执行：

```text
pytest -q                        221 passed, 1 warning in 20.36s
npm test                         7 passed
npm run check                    passed
host-compat-021.mjs              2 passed
mnemosyne_claim_ga_check.py      ok: true
```

DSH 宿主：

- 真实 `dsh-tools@0.2.1-rc.5` ToolRuntime：10 个工具注册、health/search、进程回收通过；
- 真实 DSH headless（安装的 `0.2.1-rc.3`）：模型实际调用 `memory_health` 和 `memory_search`，`turn_end completed`，Python 子进程 PID 已回收；
- 未验证 Electron 浏览器 GUI 的界面层。

---

## 8. 最终结论

任务书完成度应表述为：

> **P0–P6 的主体代码与测试已落地；P2 仍需补 Merge/Split/完整关系；P7 完全缺失；P8 只有部分安全与 DSH 集成；P9 尚未开始。**

不能使用：

```text
P0–P7 COMPLETED
```

来代表任务书全部完成。

建议下一步优先级：

1. 修正 `IMPLEMENTATION_STATUS.md` 的阶段编号和完成声明；
2. 补齐 P2 Merge/Split、完整 Relation 判定与 20 项测试；
3. 实现 P7 故障定位/修复验证（先做最小 invariant + fault injection）；
4. 再做 P9 的 dry-run 迁移和小规模试迁移；
5. P8 补推理泄漏、缓存撤销、删除传播全链路。
