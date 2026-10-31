# MurasamePet 演化记忆状态机与证据更新规范（草案 V0.1）

> 目标：把心理学启发变成开发 Agent 可实现的算法规格。  
> 总路线图：[`MNEMOSYNE_ROADMAP.md`](./MNEMOSYNE_ROADMAP.md)。  
> 实现落点：`services/mnemosyne`（规则可换 LLM，协议先稳定）。

本文定义：**对象模型、状态、转移条件、证据类型、冲突与衰减、决策日志、验收测试**。阈值与权重字段均为**可配置默认值**，须用实验校准，不得当作心理学常数。

---

## 1. 对象模型

| 类型 | 含义 | 可否直接进对话上下文 |
| --- | --- | --- |
| **Observation** | 原始观察：来源、时间、原文/结构化载荷、producer | 否（可附证据片段） |
| **Episode** | 有边界的情节：起因 / 过程 / 结果 / 实体 / 时间范围 / 证据指针 | 摘要可进；过程可寻址 |
| **CandidateMemory** | 候选断言：待验证的事实 / 兴趣 / 关系 | 谨慎；默认低优先级 |
| **Memory** | Active 长期记忆：已达证据门槛的断言 | 是（按检索策略） |
| **Evidence** | 指向 Observation / Episode / Feedback 的可寻址证据 + 层级 | 随记忆返回 |
| **InterestSignal** | 视频/行为兴趣信号（分层，非单一分数） | 经聚合后再参与晋升 |

**硬规则：** Observation ≠ Memory；模型推断不得直接写成 Active Memory。

### 1.1 Memory 字段（最小集）

```text
id, type(working|episodic|semantic|procedural|interest),
status(see §2), content, entities[],
version, created_at, updated_at, last_verified_at,
evidence_ids[], counter_evidence_ids[],
confidence_score? (仅当存在校准规则时写入),
algorithm_version, prompt_version?, model_id?,
supersedes_id?, conflict_with_ids[]
```

### 1.2 InterestSignal 字段（最小集）

```text
id, topic_or_entity, source_kind(video|chat|game|browser|...),
tier(passive|attention|engage|explicit),
polarity(+1|-1|0), strength(0..1 原始强度，非「可信度」),
ref(video_id/segment/dialog_turn/...), occurred_at,
session_id?, algorithm_version
```

---

## 2. 状态机

### 2.1 通用记忆状态

```text
OBSERVED → BUFFERED → EPISODIZED → CANDIDATE → ACTIVE
                                              ↘ SUPERSEDED / INVALIDATED / ARCHIVED
CANDIDATE → DECAYED / REJECTED
ACTIVE → NEEDS_REVIEW → ACTIVE | SUPERSEDED | INVALIDATED
```

| 状态 | 含义 |
| --- | --- |
| OBSERVED | 已落库观察，未准入认知链 |
| BUFFERED | 通过准入，在短期缓冲 / 关联窗口中 |
| EPISODIZED | 已归入或生成 Episode |
| CANDIDATE | 提出断言，证据未达 ACTIVE 门槛 |
| ACTIVE | 可参与常规检索与行为策略 |
| NEEDS_REVIEW | 出现冲突或强反例，暂停高置信使用 |
| SUPERSEDED | 被新版本取代（保留历史） |
| INVALIDATED | 用户纠正或确认错误 |
| ARCHIVED | 低优先级，不进默认上下文 |
| DECAYED / REJECTED | 候选超时或准入失败 |

### 2.2 兴趣专用状态（可配置）

```text
UNKNOWN → WEAK_SIGNAL → CANDIDATE → CONFIRMED
                ↘ STALE ←←←←←←←←←←←←←←←←┘
CONFIRMED → NEEDS_REVIEW → CONFIRMED | STALE | REJECTED
```

与通用状态映射建议：`WEAK_SIGNAL/CANDIDATE` → CandidateMemory；`CONFIRMED` → Active Memory（type=interest）。

### 2.3 转移条件（默认门槛，可配置）

| 转移 | 必要条件（AND，默认可调） |
| --- | --- |
| OBSERVED → BUFFERED | 通过准入评分：价值 / 可靠性 / 新颖度 / 持续性 / 明确反馈 任一达标，且未命中 deny |
| BUFFERED → EPISODIZED | 窗口关闭（话题切换 / 场景变化 / 行为边界 / 超时）且关联打分通过 |
| EPISODIZED → CANDIDATE | 情节可提炼稳定断言；非单次被动暴露单独晋升兴趣 |
| CANDIDATE → ACTIVE / CONFIRMED | 证据门槛：见 §3；且无未解决冲突 |
| * → NEEDS_REVIEW | 强反例或用户纠正；不立即抹掉正向证据总量 |
| ACTIVE → SUPERSEDED | 新版本写入且声明 `supersedes_id` |
| ACTIVE → INVALIDATED | 用户明确纠正事实，或审计判定有害错误 |
| CANDIDATE → DECAYED | 超过 TTL（默认 7–30 天可配）且无新证据 |
| CONFIRMED → STALE | 长期无支持证据 + 基线显示「不活跃」≠ 强否定时降优先级 |

**禁止：** 单次 Observation（尤其被动暴露）直接 → ACTIVE / CONFIRMED。

---

## 3. 证据类型与分层

### 3.1 行为证据层级（权重默认起点）

| tier | 名称 | 默认权重起点 `w` | 说明 |
| --- | --- | --- | --- |
| `passive` | 被动暴露 | 0.15 | 后台/自动播放；单独不足以晋升 |
| `attention` | 注意力 | 0.4 | 停留、回看、主动暂停 |
| `engage` | 主动参与 | 0.7 | 搜索、评论、讨论、追问 |
| `explicit` | 明确反馈 | 1.0 | 直接喜欢/不喜欢/想深入 |

兴趣支持分（示意，非概率）：

```text
support = Σ (w_tier * strength * recency_factor * source_trust)
oppose  = Σ (同结构，polarity 为负或明确否定)
net     = support - oppose_discount * oppose
```

`oppose_discount` 默认 &lt; 1，避免**一次反例抹掉大量可靠正向证据**；用户 `explicit` 否定可提高 `oppose_discount` 或直接 `NEEDS_REVIEW`。

### 3.2 晋升门槛（默认）

| 目标状态 | 建议门槛 |
| --- | --- |
| WEAK_SIGNAL | ≥1 条非 passive 信号，或多次 passive 跨会话 |
| CANDIDATE | net ≥ T_cand 且至少 2 个独立来源或 1 个 engage+ |
| CONFIRMED | net ≥ T_conf 且含 engage 或 explicit；跨 ≥2 天 |
| 降级 STALE | 窗口内无新支持且 net 低于 T_stale |

`T_*`、窗口长度写入 `algorithm_version` 配置，变更必须可对比实验。

### 3.3 元记忆

每条 Active/Candidate 应可回答：

- 来源有哪些？（evidence_ids）  
- 最后验证时间？  
- 不确定性如何表达？（无校准则用状态枚举，不伪造 0.87 置信度）  

---

## 4. 冲突、版本与修正

| 规则 | 行为 |
| --- | --- |
| 不静默覆盖 | 更新必须 `version++`，旧版 `SUPERSEDED` 或保留快照 |
| 冲突挂起 | 互斥断言同时 ACTIVE → 双方或弱方进 `NEEDS_REVIEW` |
| 变更理由 | 写入 `reason` + `algorithm_version` + 触发证据 |
| 删除级联 | 用户删除观察时，标记派生 Candidate/Memory 待重算或失效 |
| 纠错优先检索 | `INVALIDATED` 不得再作为正依据召回 |

---

## 5. 衰减与遗忘

不使用单一全局时间衰减公式。按类型策略：

| 类型 | 策略要点 |
| --- | --- |
| working | 会话/短窗口硬上限，溢出只留意图与锚点 |
| episodic | 压缩摘要 + 保留证据指针；摘要可进上下文 |
| semantic / interest | 证据驱动升降；不活跃 → ARCHIVED/STALE 而非直接删除 |
| procedural | 需多次验证才巩固；一次成功 ≠ 固定规则 |

---

## 6. 决策日志与可重放

每次准入 / 分段 / 关联 / 晋升 / 降级 / 修正应写结构化日志：

```text
ts, algorithm_version, decision(admit|segment|link|promote|demote|correct|ignore),
subject_id, subject_kind, inputs_summary, scores{}, thresholds{}, reason, outcome_status
```

要求：

- 可用同一组脱敏 Observation 重放，对比不同 `algorithm_version`  
- 管理后台或 CLI 可按 subject 拉出「为何记住 / 为何未晋升」  

---

## 7. 与检索 / 行为的接口约定

| 出口 | 约定 |
| --- | --- |
| `contexts/build` | 优先 ACTIVE；附带状态、时间、证据摘要；聚合近重复 |
| 主动行为策略 | 仅 CONFIRMED/ACTIVE 兴趣可提高「主动提起」权重；WEAK 只影响观察灵敏度 |
| 反馈入口 | `memory_feedback` / 用户纠正 → Evidence(explicit) + 可能 NEEDS_REVIEW |

图谱（Graphiti 等）写入的是 **已晋升事实关系**；准入与晋升仍由本状态机决定。

---

## 8. 验收测试（最小集）

### 8.1 基础

1. 推断内容不能在无 Observation 时直接成为 ACTIVE。  
2. 同一事实重复提交 → 版本合并，不产生 N 条 ACTIVE。  
3. 用户纠正后，旧断言不可再作为正依据。  

### 8.2 兴趣 / 视频

4. 仅后台播放 → 不得 CONFIRMED。  
5. 跨天 engage + 对话追问 → 可达 CANDIDATE/CONFIRMED。  
6. 明确「不喜欢」→ NEEDS_REVIEW 或降低 net，且可解释。  
7. CONFIRMED 兴趣可追溯到视频/片段/对话时间点。  

### 8.3 检索与体验

8. 「上个月第一次」类时间查询不串台。  
9. 上下文预算内近重复记忆被聚合。  
10. 图库不可用时 FTS/本地索引仍能返回近期 ACTIVE。  

### 8.4 资源与安全

11. 任务失败可重试；幂等键防重复情节。  
12. 删除观察后派生记忆被标记或清除，审计可查。  

---

## 9. 实现映射（当前代码）

| 规格概念 | 当前落点（演进中） |
| --- | --- |
| Observation | `observations` 表 + `capture_observation` |
| Memory / version | `memories` + `memory_versions` |
| Candidate / 晋升 | `cognition/promote.py`（规则版，待状态机化） |
| 巩固 | `cognition/consolidate.py` |
| Outbox / Tasks | `jobs/dispatcher.py` |
| 检索 | FTS5 / LIKE；Graphiti 为 P1 接入项 |
| 视频观察 | `episode_write` → `submit_video_observation`；兴趣状态机为 P2 |

P0 完成标志：本文件中的状态与证据字段在存储层可查询，决策日志可重放，§8.1 测试全绿。
