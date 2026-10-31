# Changelog

## Unreleased

- **DSH 0.2.1 宿主接口兼容**
  - `engines.dsh: >=0.2.1-0 <0.3.0`（含 rc；准入以 `engines.dsh` 为准）
  - `dsh.manifestVersion: 1`；peer `@deepseek-ai/dsh-tools` 对齐 0.2.1
  - tool `output.schema` 使用 `{ type: 'object', additionalProperties: true }`（`type:json` / 空 `{}` 会被 0.2.1 `defineTool` 拒绝）
  - `execute(args, exec)` 转发 `exec.signal` 到 MemoryClient
  - 以 `@deepseek-ai/dsh-tools@0.2.1-rc.5` 实机校验全部 memory_* 工具可注册

## 3.0.0

- 合并 `canyueY/mnemosyne` 2.0 Node 到 `canyueY/dsh-mnemosyne`，建立 3.0 单一权威仓
- 根目录保留 DSH 插件适配层；Node / Core / Memory Bank 位于 `service/`
- 旧 DSH 插件完整归档到 `legacy/dsh-plugin/`，并保留 tag `legacy/dsh-plugin-0.2.0`
- 数据目录统一为 `%LOCALAPPDATA%\Mnemosyne Memory Bank`
- Python / npm 版本同步到 `3.0.0`

## 2.0.0

- 见 `service/CHANGELOG.md`；2.0 历史保留在原 `canyueY/mnemosyne` 仓库。
