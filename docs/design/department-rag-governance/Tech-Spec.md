# 部门化知识库与 RAG 交付增强技术方案

## 数据模型

- 新增 `departments`：`id`、`name`、`description`、`admin_user_id`、时间戳。
- `users.department_id` 外键指向 `departments.id`。
- `knowledge_bases.department_id` 外键指向 `departments.id`。
- 迁移创建“默认部门”，承接已有用户和知识库；知识库名称唯一约束调整为部门内规范化唯一。

## API 契约

### 部门

- `GET /api/v1/departments`：管理员读取部门列表。
- `POST /api/v1/departments`：超级管理员创建部门并指定管理员。
- `PATCH /api/v1/departments/{department_id}`：修改名称、说明或管理员。

### 用户与知识库

- `POST/PATCH /api/v1/users` 增加 `department_id`。
- `/api/v1/me` 和用户列表返回部门摘要。
- `POST /api/v1/knowledge-bases` 支持 `department_id`；部门管理员只能创建到自己的部门。
- 知识库列表、文档访问和 RAG 检索统一按部门过滤。

### 安全守卫

- `app.rag.guard` 负责 Unicode 规范化、空白与常见分隔符折叠、分类关键词检测。
- `/retrieval/search`、`/retrieval/answer`、`/chat/stream` 和单题评测在任何模型调用前执行守卫。
- 拒绝响应使用业务校验错误；日志只记录分类，不记录原始违规正文。

### 答案导出

- `POST /api/v1/exports/answer` 接收 `question`、`answer`、`format` 与可选引用元数据。
- 后端在受控临时目录生成单个答案文件并直接返回，不创建参考文档导出任务。
- 支持 `markdown`、`txt`、`docx`；文件名由服务端生成并清理。

### 单题评测

- `POST /api/v1/retrieval-tests/single` 接收知识库、问题、检索模式、TopK、阈值和模型选项。
- 返回真实检索候选、是否命中、命中率和耗时；单题未提供人工相关片段时，“命中”定义为至少一个候选达到阈值。

## 模型 Provider

统一使用现有 OpenAI 兼容适配器，扩展 Provider 代码为 `moonshot`、`zhipu`、`minimax`、`volcengine`，并保留 `dashscope`、`deepseek`、`openai`、`anthropic`、`ollama`、`custom`。前端提供常用供应商预设，API Key 仍只写不读。

## 云部署

FastAPI 继续由 `api-server` 容器通过 Uvicorn 提供 API，Nginx 代理 `/api`。本次只补充文档和健康验证，不引入第二套 Web 框架。

## 验证

1. Alembic 空库升级、`alembic check`。
2. 部门隔离、部门管理员创建知识库、违规输入、答案导出、单题评测和 Provider 枚举单元/接口测试。
3. OpenAPI 重新生成并检查前端类型。
4. 前端 TypeScript、ESLint、Vitest 和生产构建。
5. Docker FastAPI 健康检查与关键 API 冒烟测试。
