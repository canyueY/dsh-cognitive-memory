# Engineering Constraints

**状态：** Active（2026-10-30 随 Mnemosyne 2.0 Master Plan 入库）  
**上位：** [MNEMOSYNE_2.0_MASTER_PLAN.md](MNEMOSYNE_2.0_MASTER_PLAN.md)

本文件固定工程安全边界。部署方式、协议字段或连通状态**不得**削弱下列原则。

---

## 原则一：部署不默认放宽

部署环境、网络暴露方式和组件接入方式不能隐式扩大访问权限。

- 本机 loopback 默认可达 ≠ 对局域网/公网开放  
- 插件已安装 ≠ 已授予记忆读写  
- 调试开关不得进入默认生产配置  

## 原则二：字段不等于执法

声明 `allow_train`、`allow_forward`、`allow_store` 等字段，不代表系统已经实际执行相应策略。

- 契约/Schema 可出现策略字段，但未实现执法前必须文档标明 **declarative only**  
- 不得仅因字段存在而向用户承诺「不会被训练/转发」  

## 原则三：通信不等于可信

建立连接、完成注册、通过协议校验，都不代表对端可信。

- 注册组件不自动获得数据访问权限  
- 协议通过只证明报文形状，不证明身份与授权  
- 跨节点能力须显式授权、范围、过期与撤销  

---

## 适用

所有 Mnemosyne Node 代码路径、宿主 Bridge、DSH 插件、迁移工具、Admin API 与未来 PCIP/Federation 实现。

---

## 组件与外部 Agent 的执行要求（2.0 补充）

在三条原则之上，落地时还必须做到：

1. **组件 Manifest 中的 permissions 必须在运行时检查**；安装成功 ≠ 已授权读写 Memory Bank。  
2. **DSH 社区插件与 Mnemosyne Component 分账**；禁止因「已装 DSH 插件」跳过 Node 侧授权。  
3. **外部 Agent** 须具备：身份、能力、资源范围、用户同意、有效期、撤销、审计；注册/连通 ≠ 可信。  
4. **禁止** Adapter / Provider / 脚本直接打开核心 SQLite；一律经 Service Contract。  
5. **字段策略**（`allow_train` / `allow_forward` / `allow_store` / `retain_until`）须经 `governance/policy.py` 执法：写入拒绝 `allow_store=false`；导出过滤 `allow_forward=false`；RL train 拒绝未允许样本；过期 `retain_until` 禁止 forward/train。验收：`tests/security/test_policy_enforcement.py`。  
6. **Storage Provider** 变更须带备份/恢复与迁移验收，不得按普通热插拔组件处理；组件/Adapter 禁止 `sqlite3.connect` 直连（`tests/contract/test_storage_provider_boundary.py`）。
