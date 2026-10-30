# Mnemosyne Interchange Spec（设计草案）

**状态：** Implemented-lite（2026-10-30）— `migration/interchange.py` + Staging/Approval；仍可演进  
**上位：** [IMPLEMENTATION_PLAN](MNEMOSYNE_2.0_IMPLEMENTATION_PLAN.md) D5

---

## 1. 原则

- Interchange Model **只描述外部数据**。  
- Cognitive Ingestion（Observation → Evidence → …）决定如何理解。  
- **迁移成功 ≠ 认知验证通过**。  
- 保留：来源、外部 ID、原始 payload、未知扩展字段、schema_version。

---

## 2. 记录骨架（草案）

```json
{
  "source_system": "external-agent",
  "source_record_id": "record_123",
  "record_type": "memory",
  "schema_version": "1.0",
  "content": {},
  "provenance": {},
  "time": {},
  "extensions": {},
  "raw_payload": {}
}
```

---

## 3. 与现有引擎的关系

| 现有 | 关系 |
| --- | --- |
| `migration/sources.py` JSONL/A-MEM | 特化 source；应逐步 **实现** Interchange 映射，而非平行第二套 |
| `MappedRecord` / idempotency keys | 保留；增加 interchange 字段透传 |
| Preview / Approval / Staging | ✅ `migration/staging.py`（未批准不 Commit） |

---

## 4. Adoption 流程（验收用）

```
Connect → Discover → Import Preview → User Approval
  → Import → Validation → Authority Decision → Adoption Complete
```

Migration = 数据移动能力；Adoption = 用户正式以 Node 为权威的过程。  
**分开验收。**
