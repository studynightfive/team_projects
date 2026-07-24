# 普通用户 AI 工作台与部门知识库范围修复技术方案

## 接口契约

新增：

```http
GET /api/v1/models/available?kind=chat
Authorization: Bearer <access-token>
```

任意已登录用户可访问，仅返回已启用模型：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "model-id",
      "provider_code": "deepseek",
      "model_name": "deepseek-chat",
      "kind": "chat"
    }
  ],
  "request_id": null
}
```

接口不返回 API Key 状态、模型参数、向量维度、重排数量等管理字段。原有
`GET /api/v1/models` 继续要求 `admin.model.view` 权限。

## 前端处理

- AI 搜索首页改用 `/v1/models/available`。
- 模型列表失败时使用环境默认模型，不能让工作台整体失败。
- 搜索结果页并行加载知识库和模型，分别处理失败状态。
- 知识库下拉框仍完全采用真实 `/v1/knowledge-bases` 响应。

## 后端处理

- 新增最小化的 `AvailableModelResponse`。
- 用户部门更新事务内同步：
  `knowledge_bases.kind = personal AND owner_user_id = user.id`。
- 即使用户部门字段值未变化，也执行个人知识库同步，以修复历史错位数据。
- 部门过滤继续由 `knowledge.service._accessible_kb_ids` 负责。

## 验证步骤

1. 后端单元测试验证接口字段、启用状态过滤和个人知识库同步。
2. 运行 Ruff、mypy、后端测试。
3. 运行前端类型检查、Lint、组件测试和生产构建。
4. 重新导出 OpenAPI 并生成 TypeScript 类型。
5. 重建本地 API 与 Web 容器。
6. 通过管理员 API重新保存演示用户部门。
7. 使用医疗部门普通用户登录，验证工作台和知识库范围。

