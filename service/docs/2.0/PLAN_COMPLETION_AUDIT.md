# Mnemosyne 2.0 — 任务书完成情况审计

**任务书：** `10.31更新方案.txt`（2143 行）  
**任务书基线：** `c82d47e`  
**当前代码：** `feat/taskbook-p6-p7-p8-p9-complete`（P6 rank + P7 rollback + P8 跨 Bank + P9 scratch trial）  
**基线合并：** `486ab2e`（PR #6）  
**审计日期：** 2026-10-31（续 2）  
**结论：** **代码层主体已近完成，仍不能宣称任务书“全部完成”。** 真实产线 prop、as-of Replay、生产 Claim 迁移与现网发布签字仍外置。

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
| P1 Contract Freeze | 核心契约已补字段/算法 | **NEAR COMPLETE** | 其余摘要契约可继续加厚 |
| P1.5 Governance Closure | `schema_ops`/`schema_network` 接入 `SCHEMA_MUTATION`；`test_schema_gate` | **COMPLETED** | 需确认所有旧入口都覆盖 |
| P2 Claim Vertical Slice | `claims/` + Merge/Split/Relation + S1–S20 | **NEAR COMPLETE** | 生产规模关系评测未做 |
| P3 Evidence Independence | `evidence/object_store.py`、P3 测试、independence | **COMPLETED（代码层）** | 生产历史迁移未做 |
| P4 Knowledge & Truth Maintenance | `tms/`、`knowledge/`、P4/P6 测试 | **COMPLETED（代码层）** | 生产规模验证未做 |
| P5 Experience & Strategy | `strategy/`、Experience、StrategyLog、P5 测试 | **COMPLETED（代码层）** | 真实任务数据少 |
| P6 Strategy Evaluation & MetaController | propensity fixtures + `rank_candidates` + gated eval | **NEAR COMPLETE** | 真实产线 prop 外置 |
| P7 Fault Localization & Repair Validation | inject×4 + auto-repair + **executable rollback** | **NEAR COMPLETE** | 未接生产故障流 |
| P8 Security Hardening & DSH Integration | disclosure + cache revoke + cascade + **cross-bank opaque 404** | **NEAR COMPLETE** | Electron GUI 未验 |
| P9 Migration & Release | dry-run 门禁 + **scratch trial 写入/一致性/回滚** | **NEAR COMPLETE（代码层）** | 生产写仍禁；现网发布外置 |

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
| 13 | 策略效果可验证 | **通过（代码/夹具）**；真实产线 prop 外置 |
| 14 | MetaController 调度 | **通过（代码/`rank_candidates`）**；生产调度外置 |
| 15 | 故障定位/修复有复现/回归/回滚 | **通过（含可执行 rollback drill）** |
| 16 | 关键判断完整 Trace | **部分**（JudgmentTrace 有，as-of Replay 未全） |
| 17 | DSH 不能绕过 Governance | **部分**（宿主工具已通，GUI 未验） |
| 18 | 3.0 基础功能兼容 | 通过（256 tests） |
| 19 | 历史迁移可回滚 | **通过（scratch trial）**；生产迁移仍禁 |
| 20 | 核心能力有自动化测试和阶段验收 | **部分**（代码验收齐；现网发布外置） |

---

## 7. 实际验证结果

在本轮分支上执行：

```text
pytest -q                        256 passed in 23.43s
```

DSH 宿主：

- 真实 `dsh-tools@0.2.1-rc.5` ToolRuntime：10 个工具注册、health/search、进程回收通过；
- 真实 DSH headless（安装的 `0.2.1-rc.3`）：模型实际调用 `memory_health` 和 `memory_search`，`turn_end completed`，Python 子进程 PID 已回收；
- 未验证 Electron 浏览器 GUI 的界面层。

---

## 8. 最终结论

任务书完成度应表述为：

> **P0–P9 代码层主体已近完成（含 P6 rank、P7 可执行回滚、P8 跨 Bank、P9 scratch trial）。仍外置：真实产线 prop、as-of Replay、生产 Claim 迁移、现网发布签字。provenance_complete=0 时禁止生产写。**

不能使用：

```text
P0–P9 COMPLETED
```

来代表任务书含现网发布的全部完成。

建议下一步（外置）：

1. provenance 重建后的受控小规模生产试迁移（仍禁止 auto-Verified）；
2. as-of / Replay 与下游自动重评；
3. 真实产线 propensity 观测；
4. 发布/回滚演练与人工现网签字。
