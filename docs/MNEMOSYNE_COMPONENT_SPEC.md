# Mnemosyne Component Spec（设计草案）

**状态：** Implemented-lite（2026-10-30）— `components/manager.py` 本地安装；无市场/Git 远程  
**上位：** [ARCHITECTURE §5](MNEMOSYNE_2.0_ARCHITECTURE.md) · [IMPLEMENTATION_PLAN](MNEMOSYNE_2.0_IMPLEMENTATION_PLAN.md)

---

## 1. 与 DSH 插件的关系

| | DSH 社区插件 | Mnemosyne Component |
| --- | --- | --- |
| Manifest | `dsh.plugin.json` 等 | **本规范** Component Manifest |
| 管理者 | DSH / Cordis | Node Component Manager |
| 数据库 | 禁止直连 Mnemosyne DB | 仅经 Service Contract |

同一能力可双包装，但 **不得**共用一套「装了 DSH 插件 = 装了 Mnemosyne 组件」的记账。

---

## 2. 组件类型

| 类型 | 职责 | 例 |
| --- | --- | --- |
| Provider | 提供能力 | Embedding、Reranker |
| Adapter | 连接外部系统 | DSH Adapter |
| Extension | 扩展内部能力 | 检索算法 |
| Consumer | 使用 Node（通常不「安装进」Node） | 外部 Agent Client |

**Storage Provider** 需额外强契约（事务/备份/恢复），不可当普通插件热替换。

---

## 3. Manifest 最小字段（草案）

```json
{
  "component_id": "example.embedding-provider",
  "name": "Example Embedding Provider",
  "version": "1.0.0",
  "type": "provider",
  "provider": "community",
  "interfaces": {
    "provides": ["embedding.generate"],
    "requires": []
  },
  "protocols": ["mnemosyne-component-v1"],
  "permissions": ["memory.read"],
  "compatibility": { "mnemosyne": ">=2.0.0" },
  "lifecycle": { "health_check": true, "config_schema": true }
}
```

**声明权限 ≠ 执行权限** — 运行时必须检查（ENGINEERING_CONSTRAINTS）。

---

## 4. 生命周期

Discover → Inspect → Resolve Dependencies → Review Permissions → Install → Configure → Enable → Health Check → Update / Disable / Remove  

支持：版本固定、依赖/兼容检查、配置验证、权限确认、失败回滚、卸载后数据处理策略。

---

## 5. 分阶段来源（不做跳级）

1. 本地 Manifest  
2. 本地安装  
3. Git 来源  
4. 官方 Registry  
5. 社区 Registry  
6. 签名 / 信誉 / 自动更新  

**2.0 首期止于 1–3。**

---

## 6. Composition Profiles

Standalone · DSH Profile · Personal Agent Profile · Custom  

模板 = 起点，**不锁定**后续选择。
