# Changelog

## 0.1.1

- Mnemosyne 2.1：`cognitive_memory.migration.MemoryMigrationEngine`（JSONL/A-MEM 源、类型映射、checkpoint 续跑、MigrationReport）
- CLI `migrate-amem` 改为走迁移引擎；支持 `--checkpoint` / `--report` / `--limit` / `--no-resume`

## 0.1.0

- V1.0 工程骨架：FastAPI REST、`MemoryService`、SQLite 迁移、FTS5
- Outbox / Inbox / Tasks 后台调度；规则版情节归纳与候选晋升
- MCP stdio 工具与 REST 共用同一业务核心
- DSH 插件 `dsh-cognitive-memory`：子进程托管 + 工具注册
