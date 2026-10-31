# P0.5 Manual Review Notes

**生成时间：** 2026-10-31  
**库：** `%LOCALAPPDATA%\Mnemosyne Memory Bank\data\memory.db`（只读）  
**规则：** 不写生产 Claim；不自动 verified。

## 观察

1. **音乐域结构化度高**：`[music:inference] …偏好艺术家「X」` 与 `收藏了歌曲《Y》` 可稳定解析为 Atom（modality=preference / behavior）。
2. **日常对话 / 定时任务摘要**（S1 大量样本）几乎全部 Unresolved——符合「不强塞 Atom」。
3. **S4 conditional 抽样** 命中的是含「如果」的长文本，规则需要更干净的短条件句；当前保守失败 → Unresolved。
4. **Provenance**：`provenance_complete_rate=0`——旧 `memory_evidence` 仅是链接，不能当作独立 Evidence；`unverified` 链接标记为 partial。
5. **同 hash 候选**：发现 1 组重复 observed 文本（同曲目重复入库），**不得**自动 same_as 合并；仅作人工复核候选。

## 复核结论（给 P1）

| 问题 | 结论 |
|---|---|
| AST v1 是否够？ | 对音乐行为/偏好够用；对闲聊不够，需 Unresolved 为主路径 |
| Parser | 规则优先 + 后续可选模型辅助；不得静默改历史 AST |
| 默认生命周期 | **proposed**；永不从历史 `unverified` 升 Verified |
| 独立 Claim 表 | **需要**；不能只做 Memory 投影 |
| 不可迁移 | 长对话摘要、定时任务文案、缺来源闲聊 → 保留 Memory |
