# Mnemosyne 2.0 — P0 性能与容量基线

**审计提交：** `589c694`  
**日期：** 2026-10-31（Asia/Shanghai）  
**性质：** 初始基线，不是生产性能承诺。

## 1. 方法

### 1.1 合成基准

- 临时 SQLite 数据库；
- `MemoryService` 进程内调用；
- 2,000 条 synthetic semantic memories；
- 每条 1 个 `source_id`；
- 查询 3 组，每组 3 次；
- 环境：Windows 本机、WAL、无网络、无并发。

### 1.2 生产库盘点

- 对 `%LOCALAPPDATA%\Mnemosyne Memory Bank\data\memory.db` 做只读聚合；
- 不读取记忆正文；
- 使用 immutable 只读连接；
- 数据是审计时点快照。

### 1.3 测试基线

- `pytest -q`：122 passed in 9.19s；
- readiness suite：G1/G3/G4/G5/G6/G7 smoke gates ok。

---

## 2. 合成基准确认值

| 指标 | 结果 |
|---|---:|
| DB 大小（2k 条） | 4,972,544 bytes |
| 初始化/迁移 | 38.0 ms |
| 写入 2,000 条 | 2,257.55 ms |
| 单条写入 | 1.129 ms |
| 检索 9 次 | 1.07–1.94 ms |
| 检索中位数 | 1.20 ms |
| 检索 P95 | 1.83 ms |
| 单次检索 | 1.15 ms |
| 上下文组装 | 1.44–1.53 ms |
| health | 0.93 ms |

### 解释

- 2k 条库很小，FTS 索引全部在页缓存中；
- 1.13 ms/条是**单条同步写入**，不是批量吞吐；
- 检索是 FTS/LIKE 路径，不包含 Claim 关系、权限计算、语义向量、网络；
- 不能把 1.2 ms 当作 58k 生产库的 P95。

---

## 3. 生产库容量基线

| 指标 | 值 |
|---|---:|
| `memory.db` 大小 | 574,582,784 bytes（约 548 MB） |
| observations | 41,870 |
| memories | 58,186 |
| memory_versions | 58,159 |
| memory_evidence | 57,169 |
| memory_relations | 446 |
| memory_feedback | 0 |
| cognitive_schemas | 8 |
| schema_versions | 36 |
| events | 100,475 |
| outbox | 100,475 |
| tasks | 98,932 |
| pending outbox | 2,538 |
| pending tasks | 3,194 |
| music observations | 1,102 |
| music memories | 约 990–1,017 |

### 数据状态

| 类型 | 状态 | 数量 |
|---|---|---:|
| episodic | candidate | 41,758 |
| working | active | 16,401 |
| semantic | candidate | 27 |

| evidence 状态 | 数量 |
|---|---:|
| unverified / observation | 57,163 |
| supports / observation | 6 |

---

## 4. 观察与风险

### 4.1 存储增长

- 548 MB / 58k memories ≈ 9.4 KB/条（含版本、FTS、事件、任务）；
- `events` / `outbox` / `tasks` 各约 10 万行，已经与记忆本体同量级；
- 尚无自动 retention/compaction 基线。

### 4.2 队列积压

- 2,538 pending outbox；
- 3,194 pending tasks；
- 需要区分“正常运行中的短期积压”和“worker 未消费”的长期积压；
- P0 应补：排空时间、worker 吞吐、失败重试分布、最老 pending 年龄。

### 4.3 质量

- 57,163 条 evidence 为 `unverified`；
- 生产 `memory_evidence.relation` 全部为 `supports`，无 `contradicts`；
- Schema 主要是 ontology（CONCEPT/DOMAIN/EVENT_TYPE/SIGNAL），不是用户知识；
- 这不是性能问题，但会影响 P0.5 迁移样本的代表性。

---

## 5. 候选非功能目标（待基线确认）

| 指标 | 候选方向 | 当前状态 |
|---|---|---|
| 普通检索 P95 | < 300 ms | 合成 1.83 ms；生产未测 |
| 上下文组装 P95 | < 300 ms | 合成约 1.5 ms |
| 普通 Trace 开销 | < 5% | 未测（尚无 JudgmentTrace） |
| 关键治理事件丢失 | 0 | 未测 |
| Outbox 排空 | 可观测、可配置 | 2,538 pending |
| Task 排空 | 可观测、可配置 | 3,194 pending |
| 单次局部回放 | < 60 s | 未实现 |
| DB 增长 | 有 retention/compaction | 548 MB，未设上限 |

> 这些是候选目标，不是已验证承诺。P1 前必须用生产规模数据重测。

---

## 6. 复现命令

合成基准（在 `service/` 下）：

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python scripts/mnemosyne_readiness_suite.py
```

生产库只读盘点：

```python
from pathlib import Path
import os, sqlite3
p = Path(os.environ["LOCALAPPDATA"]) / "Mnemosyne Memory Bank" / "data" / "memory.db"
c = sqlite3.connect(f"file:{p}?mode=ro&immutable=1", uri=True)
print(c.execute("SELECT count(*) FROM memories").fetchone()[0])
```

> 不要对生产库执行写入基准；需要时先做 SQLite backup/copy。

---

## 7. 结论

- 现有 FTS/内存路径在小库上足够快；
- 生产库已有 548 MB、10 万级事件/任务，容量与队列是 P0 的真实风险；
- 2.0 引入 Claim/Verification/Trace 后，性能预算必须重新测；
- P0 不把“合成 1.2 ms”写成“生产 P95”。
