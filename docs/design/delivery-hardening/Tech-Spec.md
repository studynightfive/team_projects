# 交付加固技术方案

## 1. 流式数据库会话

FastAPI 的 `yield` 依赖不能作为长时间流式生成器的数据库会话所有者。路由完成并返回
`StreamingResponse` 后，依赖会话可能已经关闭，生成器第一次查询便触发 `DBAPIError`。

修正方案：

1. 路由只完成认证、权限和输入校验，并捕获请求 ID。
2. `event_generator` 内部使用 `async_session_factory()` 创建独立会话。
3. 在该会话中重新读取当前用户，避免使用游离 ORM 对象。
4. 检索、会话保存、指标和审计均在同一个流生命周期内执行。
5. 客户端取消时回滚并关闭会话；异常只记录类型和请求 ID。

`/api/v1/chat/stream` 与 `/api/v1/retrieval/answer/stream` 使用同一原则。

## 2. 前端 SSE 契约

前端继续使用原生 `fetch + ReadableStream + TextDecoder`，支持跨网络分片解析。已知事件：

- `start`：请求、会话和用户消息 ID。
- `stage`：缓存、检索、重排和生成阶段。
- `citation`：可访问文档的引用。
- `delta`：回答增量。
- `done`：耗时、模型、缓存和助手消息 ID。
- `error`：稳定错误码、公开消息、请求 ID 和是否可重试。

未知事件忽略；没有 `done` 且没有明确 `error` 的流视为不完整响应。

## 3. 命中率测试

页面维护两组独立参数：

- `datasetConfig`：测试集运行的模式、TopK、阈值、重排。
- `singleConfig`：单问题即时测试的模式、TopK、阈值、重排。

测试集列表由真实 API 返回，每个测试集使用唯一 ID。新建使用 `POST`，编辑使用
`PATCH`，不得通过复用同一个草稿对象覆盖其他测试集。编辑器的“新增问题”使用
`unshift` 插入顶部，并在下一帧聚焦新输入框。

## 4. 文档回收站

沿用现有 `deleted_at / deleted_by / purge_after`：

- 删除：设置 `purge_after = deleted_at + 30 days`，撤下全部检索投影。
- 恢复：清除删除标记，处理名称冲突，创建重新处理任务。
- 清理：Worker 每日查询到期文档，先撤下检索投影，再删除数据库记录和存储目录。

本轮不重复建立第二套删除模型，只补回归测试和部署验证。

## 5. Cython 原生核心

### 5.1 编译范围

Linux 构建阶段使用固定版本 Cython 编译：

- `app.knowledge.service`
- `app.rag._shared.permissions`
- `app.rag.search.service`
- `app.native.license_core`

运行镜像复制 ABI 匹配的 `.so`，再删除前三个模块对应的 `.py` 和许可证 `.pyx`。
开发环境继续直接运行 Python 源码，保证可调试和可测试。

### 5.2 许可证

许可证为签名 JSON，至少包含 `serial`、`expires_at` 和 `product`。Ed25519 公钥在构建时
编译进扩展；运行时由扩展读取许可证文件并完成验签、产品和有效期校验。Python 适配层
只暴露：

```text
native_core_loaded() -> bool
license_is_valid(path) -> bool
enforce_native_core() -> None
```

接口不返回载荷、序列号或签名；日志只写稳定错误码。生产环境可设置：

```text
NATIVE_CORE_REQUIRED=true
NATIVE_CORE_LICENSE_REQUIRED=true
KNOWLEDGE_CORE_LICENSE_FILE=/run/secrets/knowledge_core_license
```

公钥不是 secret；私钥永远不进入仓库或镜像。

## 6. 角色回归

- 普通用户：本人个人知识库 + 本部门企业知识库，只能管理个人文档。
- 知识库编辑者：继承普通用户能力，并能管理本部门企业知识库和文档。
- 超级管理员：可进入管理中心，并在用户工作区读取全部企业知识库。

前端展示以权限码改善体验，后端部门和所有权校验仍是最终边界。
