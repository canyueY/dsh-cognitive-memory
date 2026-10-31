# Mnemosyne 3.0 合并说明

3.0 将原 `canyueY/mnemosyne`（Node / Core）合并进 `canyueY/dsh-mnemosyne`，并把它作为唯一权威仓。

## 仓库结构

| 路径 | 作用 |
| --- | --- |
| `service/` | 独立 Node：Core、REST/MCP、Memory Bank、测试与文档 |
| `src/` + `package.json` | DSH 插件适配层，负责启动/守护 Node 与注册工具 |
| `legacy/dsh-plugin/` | 0.2 旧插件完整归档，仅供追溯 |

## 版本与兼容

- Python 包版本：`3.0.0`
- npm 包版本：`3.0.0`
- 旧 `dsh-mnemosyne@0.2` 的 npm 历史仍可安装，但不再接收新能力；
- 旧插件状态保留在 Git tag `legacy/dsh-plugin-0.2.0`；
- 数据目录统一为 `%LOCALAPPDATA%\Mnemosyne Memory Bank`（可用 `MNEMOSYNE_MEMORY_BANK` 覆盖）。

## 安装

```bash
pip install -e ./service[dev]
mnemosyne doctor
```

DSH 插件：

```bash
dsh plugin --profile web add github:canyueY/dsh-mnemosyne#main
```

## 迁移原则

- 不再维护两个平行的 Node 仓库；
- 旧插件文件只作为归档，不参与 3.0 主路径；
- 新增能力写入 `service/`，DSH 适配层只做接入，不承载核心记忆逻辑。
