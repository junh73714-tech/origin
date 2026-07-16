# 成员6 修改报告：RetrievalFilter 对齐成员4

**日期：** 2026-07-16  
**分支：** `feature/m6-hybrid-retrieval`  
**依据：** 成员4反馈「成员6需要修改（待确认）」清单

---

## 1. 修改项与结论

| 问题 | 文件 | 处理 | 结论 |
|------|------|------|------|
| 补充 `user_id` 字段 | `backend/app/retrieval/types.py` | `RetrievalFilter` 增加 `user_id: str = ""` | **已完成** |
| 临时授权类型对齐 | `backend/app/retrieval/types.py` L21 | `temporary_grant_document_ids` **改为对象列表** `effective_temporary_grants` | **已完成（采用对象列表）** |

---

## 2. 设计说明

### 2.1 补充 `user_id`

与成员4 `RetrievalFilter.user_id` / `AccessContextResponse.user_id` 对齐，便于：

- 审计与日志关联
- 后续按用户维度调试过滤
- `to_pgvector_where()` 透出 `user_id`

`build_retrieval_filters` 现从 `access.user_id` 写入。

### 2.2 临时授权：确认为对象列表

**决定：需要改为对象列表**（与成员4 `effective_temporary_grants: list[TemporaryGrantInfo]` 一致）。

| 之前 | 现在 |
|------|------|
| `temporary_grant_document_ids: list[str]` | `effective_temporary_grants: list[TemporaryGrantRef]` |
| 仅有文档 ID，无法带过期/类型 | 含 `resource_type` / `resource_id` / `permission_type` / `effective_time` / `expiration_time` |

新增 `TemporaryGrantRef`（对齐成员4 `TemporaryGrantInfo` 字段）：

```python
class TemporaryGrantRef(BaseModel):
    resource_type: str = "document"
    resource_id: str
    permission_type: str = "read"
    effective_time: datetime | None = None
    expiration_time: datetime | None = None
```

保留只读属性，供 OpenSearch / pgvector `terms` 过滤：

```python
@property
def temporary_grant_document_ids(self) -> list[str]:
    # 仅 resource_type == "document" 的 resource_id
```

适配器 `_active_temporary_grants` 同时兼容：

- 成员4：`{resource_type, resource_id, permission_type, effective_time, expiration_time}`
- 本地测试旧格式：`{document_id, expires_at}`

---

## 3. 涉及文件

| 文件 | 变更 |
|------|------|
| `backend/app/retrieval/types.py` | 新增 `TemporaryGrantRef`；`RetrievalFilter` 增加 `user_id`、`effective_temporary_grants` |
| `backend/app/retrieval/permission_adapter.py` | 规范化临时授权；写入 `user_id` 与对象列表 |
| `backend/app/retrieval/README.md` | 补充类型说明 |
| `backend/tests/retrieval/test_allow_and_temp_grant.py` | 新增成员4形状与对象列表用例 |

---

## 4. 测试结果

```bash
cd backend
python -m pytest tests/retrieval tests/rag tests/conversation -q
```

预期：全部通过（含新增临时授权对象用例）。

---

## 5. 给成员4的说明（可转发）

1. `RetrievalFilter.user_id` 已补齐。  
2. 临时授权已改为对象列表字段名 **`effective_temporary_grants`**，结构对齐 `TemporaryGrantInfo`。  
3. 检索 DSL 仍通过属性 **`temporary_grant_document_ids`** 取文档 ID，无需成员4改 OpenSearch 字段。  
4. 成员6 适配层仍可接收旧字典 `{document_id, expires_at}`，联调无缝。  

成员4 完成 PermissionService 修正后，可再约替换 `DefaultPermissionAdapter`。

---

## 6. 未纳入本次（仍待成员4）

- `scope_hash` 算法统一（完整 SHA256 vs 截断、是否含临时授权）
- `AccessContext` 与 `AccessContextResponse` 双轨合并
- OpenSearch 空 KB 默认拒绝、密级 `== 0` 过滤等成员4侧 P0
