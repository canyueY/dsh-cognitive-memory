# 试用立场：值得用，还不值得只信它

本插件 / 服务当前定位是 **副记忆（并行观察）**，不是「唯一记忆」。

## 推荐用法

1. 独立 `data_dir`（与默认目录分开亦可），**每天备份 SQLite**。
2. 与现有 A-MEM / hybrid 等 **并行 1–2 周**：`enable=true`，`replace_a_mem=false`。
3. 只观察三件事：召回准不准、启动/调用稳不稳、服务挂了对话能否继续。
4. 一旦出现「记错且无法回滚」，立刻关掉 `enable` 或保持副记忆位。

## 每天备份

```bash
# 在仓库或已安装的 service/ 下
pip install -e ./service   # 首次
python -m cognitive_memory.cli backup --data-dir "%LOCALAPPDATA%/DSH/cognitive-memory"
# 或使用脚本（Windows）：
# scripts/backup-daily.ps1
```

恢复：

```bash
python -m cognitive_memory.cli restore <backup.db> --data-dir "..." --force
```

从旧 A-MEM 导入（候选，不直接当 ACTIVE）：

```bash
python -m cognitive_memory.cli migrate-amem --jsonl path/to/export.jsonl
```

## 什么时候可以当主记忆

| 门槛 | 状态 |
| --- | --- |
| `dsh plugin add` 后零配置能起（或 README 配置真生效） | ⏳ 仓库已内含 `service/`；装进 profile 后仍须验证目录是否完整拷贝 |
| 真实对话：`observe` → 下一轮自动 `context`，并有延迟/准确率 | ❌ 未验收 |
| 备份 / 导出 / 旧记忆迁移有可执行答案 | ✅ CLI 有；日常习惯与文档仍须跟上 |
| 最小 CI（插件 + 服务 + 一次端到端） | ⏳ 插件 + 服务单测已在 `.github/workflows/ci.yml`（`plugin/dsh` / `main` 绿）；端到端对话闭环仍未进 CI |
| 连续一周无丢数据 / 串记忆 | ❌ 未跑 |

**一句话：** 现在值得用、值得每天用；证明不会把经历弄丢或弄错之前，先当副记忆。
