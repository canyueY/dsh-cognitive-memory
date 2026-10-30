# Changelog

## 2.0.0

- GA 文档收口：`docs/GA_STATUS.md`；黄项清单 Y4 契约加厚完成，Y3 仅留人工双签模板
- `tests/contract/test_emotion_feedback_bank_e2e.py`：情绪 shadow → Bank 隔离 → feedback promote
- 存储边界契约可选扩展至 `mcp/`；E6.5 看板 + HUMAN_SIGNOFF_CHECKLIST（不代签）

## 0.1.1

- Mnemosyne 2.1：`cognitive_memory.migration.MemoryMigrationEngine`（JSONL/A-MEM 源、类型映射、checkpoint 续跑、MigrationReport）
- CLI `migrate-amem` 改为走迁移引擎；支持 `--checkpoint` / `--report` / `--limit` / `--no-resume`

## 0.1.0

- V1.0 工程骨架：FastAPI REST、`MemoryService`、SQLite 迁移、FTS5
- Outbox / Inbox / Tasks 后台调度；规则版情节归纳与候选晋升
- MCP stdio 工具与 REST 共用同一业务核心
- DSH 插件 `dsh-cognitive-memory`：子进程托管 + 工具注册
