# 智能知识库平台六人团队分工协作方案

> 文档版本：2.0  
> 技术基线日期：2026-07-14  
> 团队规模：6 人  
> 架构原则：前后端分离、Git 单仓库、后端模块化单体、异步文档处理、统一接口规范

## 1. 方案目标

本方案用于指导 6 人团队完成知识库平台的设计、开发、联调、测试和上线。为降低沟通与部署成本，首期不拆分微服务，采用以下简化方案：

- 用户使用界面与管理员管理界面相互独立。
- 前端、后端和异步任务进程分离部署。
- 后端采用一个代码工程，按业务模块隔离，不允许跨模块直接修改数据。
- 全部代码、接口文档、部署文件和测试脚本放在同一个 Git 仓库中。
- 文档统一转换为 Markdown 后，再进行分段、索引和检索。
- 用户可以将文档或回答导出为 PDF、Word、Markdown、CSV、TXT。
- 研发流程只保留需求确认、开发、评审、测试、发布五个阶段。

## 2. 首期项目范围

### 2.1 用户使用界面

| 模块 | 主要功能 | 优先级 |
|---|---|---:|
| 登录与个人信息 | 登录、退出、查看个人资料 | P0 |
| 智能问答 | 选择知识库、输入问题、流式回答、停止生成、重新生成 | P0 |
| 引用溯源 | 查看引用文档、页码、原文片段和相关度 | P0 |
| 知识检索 | 关键词检索、向量检索、混合检索、条件筛选 | P0 |
| 文档浏览 | 目录浏览、文档预览、Markdown 内容查看 | P0 |
| 会话管理 | 历史会话、重命名、删除、搜索 | P0 |
| 反馈评价 | 点赞、点踩、原因说明 | P1 |
| 文档导出 | 选择 PDF、Word、Markdown、CSV、TXT 后下载 | P0 |
| 回答导出 | 将单条回答或完整会话导出并保留引用 | P1 |
| 收藏 | 收藏文档、回答和常用问题 | P1 |

### 2.2 管理员管理界面

管理员界面以示例图片中的系统概览、角色管理、用户管理、大模型管理、知识库管理、文档管理和命中率测试为基础。

| 模块 | 主要功能 | 优先级 |
|---|---|---:|
| 系统概览 | 用户数、知识库数、文档数、问答量、成功率、耗时、Token 使用量 | P0 |
| 用户管理 | 创建、编辑、启停、重置密码、分配角色 | P0 |
| 角色管理 | 角色、菜单权限、操作权限、知识库数据权限 | P0 |
| 大模型管理 | 模型供应商、模型名称、密钥、参数、连通性测试 | P0 |
| 知识库管理 | 创建、编辑、归档、删除、授权、检索参数 | P0 |
| 文档管理 | 上传、转换、预览、分段、索引、重试、删除、下载 | P0 |
| 转换任务 | 查看上传、OCR、Markdown 转换、分段和索引进度 | P0 |
| 命中率测试 | 选择知识库、文档、检索方式和问题，查看命中片段 | P0 |
| 评测中心 | 测试集、批量测试、检索指标、回答质量对比 | P1 |
| 审计日志 | 登录、权限、模型、知识库、文档和导出操作记录 | P0 |
| 系统设置 | 文件大小、允许格式、分段参数、导出模板、存储目录 | P1 |

## 3. 简化后的总体架构

```text
用户端 Web                 管理端 Web
    |                          |
    +----------- Nginx --------+
                 |
          FastAPI API Server
                 |
   +-------------+-------------+
   |             |             |
认证权限模块   知识文档模块   RAG 与导出模块
   |             |             |
   +-------------+-------------+
                 |
          PostgreSQL + pgvector
                 |
          本地文件存储卷
                 |
          Redis 异步任务队列
                 |
             Worker 进程
```

### 3.1 部署单元

首期只保留 6 个容器：

1. `user-web`：用户端静态页面。
2. `admin-web`：管理员端静态页面。
3. `api-server`：FastAPI 接口服务。
4. `worker`：文档转换、OCR、分段、索引和导出任务。
5. `postgres`：业务数据、全文检索和向量数据。
6. `redis`：任务队列、短期缓存和分布式锁。

### 3.2 简化原则

- 不在首期拆分认证服务、文档服务、RAG 服务等独立微服务。
- 后端按 Python 包进行模块隔离，通过服务层调用。
- 文档解析、OCR、索引、批量导出使用异步任务。
- 普通查询、管理和检索接口使用同步请求。
- 智能问答采用 Server-Sent Events 流式返回。
- 原始文件和转换后的 Markdown 文件都必须保留。

## 4. 任意文档上传并转换为 Markdown

### 4.1 功能定义

“上传任何形式的文档”在本项目中定义为：

- 上传入口不只依赖扩展名，必须同时检测 MIME 类型、文件头和扩展名。
- 通过可插拔解析器覆盖常见办公文档、文本、网页、表格、演示文稿、电子书和图片。
- 图片和扫描件通过 OCR 提取文字，并在 Markdown 中保留图片引用。
- 无法识别的格式保留原始文件，任务状态标记为“待人工处理”，不得静默丢弃。
- 后续增加新格式时，只需新增解析器适配器，不修改上传接口。

### 4.2 首期支持格式

| 类型 | 扩展名示例 | 处理方式 |
|---|---|---|
| PDF | `.pdf` | 原生文本提取；扫描 PDF 自动 OCR；表格和图片结构识别 |
| Word | `.docx`、`.doc` | DOCX 直接解析；DOC 先由 LibreOffice 转换为 DOCX |
| Excel | `.xlsx`、`.xls` | 工作表转换为 Markdown 表格；超大表格生成附件引用 |
| PowerPoint | `.pptx`、`.ppt` | 每页转换为标题、正文、备注和图片说明 |
| Markdown | `.md`、`.markdown` | 清洗并规范化标题、链接、图片和代码块 |
| 文本 | `.txt`、`.log`、`.rst`、`.org` | 编码识别后转换为 Markdown 段落或代码块 |
| 表格文本 | `.csv`、`.tsv` | 转换为 Markdown 表格；保留原始表格附件 |
| 网页与结构化文本 | `.html`、`.htm`、`.xml`、`.json` | 提取正文、表格和层级结构 |
| 电子书与开放文档 | `.epub`、`.odt`、`.ods`、`.odp`、`.rtf` | 转换为中间格式后生成 Markdown |
| 图片 | `.jpg`、`.jpeg`、`.png`、`.webp`、`.bmp`、`.tif`、`.tiff` | OCR、版面分析、图片说明和原图引用 |
| 邮件 | `.eml` | 提取主题、发件人、正文和附件列表 |

### 4.3 统一转换流程

```text
上传文件
  -> 文件大小和安全校验
  -> MIME 类型识别
  -> 保存原始文件
  -> 选择解析器
  -> 必要时执行 LibreOffice 格式转换
  -> 必要时执行 OCR
  -> 生成统一文档结构
  -> 输出 Markdown
  -> Markdown 清洗和安全过滤
  -> 提取标题、页码、表格、图片和元数据
  -> 文档分段
  -> 生成向量并写入 pgvector
  -> 更新任务状态
```

### 4.4 Markdown 输出规范

每个文档生成以下目录：

```text
storage/documents/{document_id}/
├── original/                 # 原始文件
├── markdown/
│   └── content.md            # 标准化 Markdown
├── assets/                   # 从文档提取的图片和附件
├── preview/                  # 预览文件
└── manifest.json             # 页码、标题、来源、哈希和解析信息
```

`content.md` 必须遵守以下规则：

- 文档标题使用一级标题，章节依次使用二级及以下标题。
- 表格优先转换为标准 Markdown 表格。
- 无法完整表达的复杂表格使用 HTML 表格，并在元数据中标记。
- 图片写为相对路径，例如 `![图片说明](../assets/image-001.png)`。
- OCR 文本标记来源页码和置信度。
- 每个分页位置加入不可见锚点或页码注释，便于引用溯源。
- 删除脚本、危险 HTML 和外部跟踪代码。
- 保留原始文件哈希、解析器版本和转换时间。

### 4.5 转换状态

```text
uploaded -> detecting -> converting -> ocr -> normalizing
         -> chunking -> indexing -> ready
                              \-> failed
                              \-> manual_review
```

用户和管理员均可查看当前阶段、进度、失败原因和重试次数。

## 5. 文档导出与下载

### 5.1 用户可选导出格式

| 格式 | 文件扩展名 | 导出内容 |
|---|---|---|
| PDF | `.pdf` | 带目录、页眉、页脚、引用和分页的阅读版文档 |
| Word | `.docx` | 可继续编辑的标题、段落、表格和图片文档 |
| Markdown | `.md` | 标准化 Markdown；图片以压缩包附件形式一并下载 |
| CSV | `.csv` | 文档元数据、章节、分段、页码、正文和引用等结构化数据 |
| TXT | `.txt` | 去除 Markdown 标记后的纯文本内容 |

### 5.2 可导出范围

用户界面提供“导出”按钮，支持以下范围：

- 当前文档。
- 多选文档。
- 当前问答答案。
- 完整会话。
- 当前检索结果。

多文档导出时生成 ZIP 文件；大型导出任务进入异步队列，完成后在“我的下载”中获取。

### 5.3 CSV 统一字段

```text
document_id,document_name,section_no,heading,page_no,chunk_no,content,source_url,tags
```

### 5.4 导出接口

```text
POST   /api/v1/exports
GET    /api/v1/exports/{export_id}
GET    /api/v1/exports/{export_id}/download
DELETE /api/v1/exports/{export_id}
```

创建导出任务请求示例：

```json
{
  "scope_type": "documents",
  "resource_ids": ["uuid-1", "uuid-2"],
  "format": "docx",
  "include_citations": true,
  "include_assets": true
}
```

## 6. 六人团队分工

## 6.1 分工总览

| 成员 | 角色 | 主责模块 | 备份模块 |
|---|---|---|---|
| 员工 1 | 用户端前端 | 智能问答、知识检索、文档浏览、导出下载 | 管理端公共组件 |
| 员工 2 | 管理端前端 | 管理后台、上传任务、命中率测试、系统概览 | 用户端公共组件 |
| 员工 3 | 后端基础模块 | 登录、用户、角色、权限、审计、系统设置 | 部署和数据库 |
| 员工 4 | 文档处理后端 | 上传、格式识别、OCR、Markdown 转换、分段、索引 | 导出服务 |
| 员工 5 | RAG 与导出后端 | 模型、检索、问答、引用、会话、导出 | 文档处理 |
| 员工 6 | 测试与平台工程 | Git 规范、CI/CD、自动化测试、部署、监控、评测 | 基础后端 |

## 6.2 员工 1：用户端前端

### 负责模块

- 用户登录后的主界面。
- 知识库选择、智能问答和流式消息渲染。
- 文档目录、Markdown 预览、图片预览和引用定位。
- 会话列表、历史记录和反馈。
- 文档、答案、会话和检索结果的导出格式选择。
- “我的下载”任务状态和文件下载。

### 主要接口

```text
GET  /api/v1/me
GET  /api/v1/knowledge-bases/available
POST /api/v1/chat/stream
GET  /api/v1/conversations
GET  /api/v1/documents/{document_id}/markdown
POST /api/v1/retrieval/search
POST /api/v1/exports
GET  /api/v1/exports/{export_id}
GET  /api/v1/exports/{export_id}/download
```

### 验收标准

- 流式回答可停止、重试并展示错误。
- Markdown、表格、代码块和图片能够正常预览。
- 用户可选择五种导出格式。
- 大型导出展示进度，完成后可下载。
- 用户只能查看和导出有权限的资源。

## 6.3 员工 2：管理员端前端

### 负责模块

- 系统概览、用户管理、角色管理和模型管理。
- 知识库管理和文档管理。
- 通用上传组件、批量上传、拖拽上传和进度展示。
- 文档转换详情、OCR 结果、Markdown 预览和失败重试。
- 命中率测试和评测结果页面。
- 审计日志和系统设置页面。

### 主要接口

```text
GET    /api/v1/admin/dashboard
GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/roles
POST   /api/v1/roles
GET    /api/v1/models
POST   /api/v1/models
GET    /api/v1/knowledge-bases
POST   /api/v1/knowledge-bases
POST   /api/v1/knowledge-bases/{kb_id}/documents
GET    /api/v1/tasks/{task_id}
POST   /api/v1/documents/{document_id}/reprocess
POST   /api/v1/retrieval-tests/run
```

### 验收标准

- P0 模块具备完整新增、查看、编辑、启停和删除能力。
- 上传任务按文件展示当前转换阶段和失败原因。
- 管理员可查看原始文件、转换后的 Markdown 和资源图片。
- 菜单和按钮权限与后端权限码一致。

## 6.4 员工 3：后端基础模块

### 负责模块

- 登录、退出、Token 刷新和密码管理。
- 用户、角色、权限和知识库数据权限。
- 审计日志、统一错误码和请求编号。
- 系统配置、文件限制、导出限制和参数字典。
- PostgreSQL 数据模型、Alembic 迁移和基础中间件。

### 主要接口

```text
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/me
GET    /api/v1/users
POST   /api/v1/users
PATCH  /api/v1/users/{user_id}
GET    /api/v1/roles
POST   /api/v1/roles
PUT    /api/v1/roles/{role_id}/permissions
GET    /api/v1/audit-logs
GET    /api/v1/system/settings
PUT    /api/v1/system/settings
```

### 验收标准

- 前端隐藏按钮不能代替后端权限校验。
- 用户、权限、模型、文档和导出操作均写入审计日志。
- 数据库迁移可以正向执行并提供回滚脚本。
- 所有接口返回统一响应结构和请求编号。

## 6.5 员工 4：文档处理后端

### 负责模块

- 文件上传、校验、哈希去重和存储。
- MIME 类型检测和解析器路由。
- PDF、Office、文本、网页、电子书和图片解析。
- LibreOffice 旧格式转换。
- 图片和扫描 PDF 的 OCR。
- Markdown 生成、清洗、资源提取和预览。
- 文档分段、全文索引和向量索引。
- 转换任务状态、进度、失败重试和人工处理状态。

### 主要接口

```text
POST   /api/v1/knowledge-bases/{kb_id}/documents
GET    /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/markdown
GET    /api/v1/documents/{document_id}/assets/{asset_id}
GET    /api/v1/documents/{document_id}/chunks
POST   /api/v1/documents/{document_id}/reprocess
DELETE /api/v1/documents/{document_id}
GET    /api/v1/tasks/{task_id}
```

### 内部模块接口

```python
class DocumentParser:
    def supports(self, mime_type: str, extension: str) -> bool: ...
    async def parse(self, source_path: str) -> "ParsedDocument": ...

class MarkdownConverter:
    async def convert(self, parsed: "ParsedDocument") -> "MarkdownPackage": ...

class Chunker:
    async def split(self, markdown: str, metadata: dict) -> list["Chunk"]: ...
```

### 验收标准

- 首期格式表中的文件均有自动化样本测试。
- 图片和扫描 PDF 可以生成 Markdown 文本。
- 转换后的 Markdown 可追溯到原文页码或工作表。
- 任务失败可重试，重复执行不会生成重复有效索引。
- 无法解析的文件保留原件并进入人工处理状态。

## 6.6 员工 5：RAG 与导出后端

### 负责模块

- 大模型、向量模型和重排模型适配。
- 向量检索、全文检索和混合检索。
- 权限过滤、元数据过滤、TopK 和相似度阈值。
- 流式问答、会话、消息、引用和用户反馈。
- PDF、DOCX、Markdown、CSV、TXT 导出。
- 导出任务、文件打包、下载鉴权和过期清理。

### 主要接口

```text
GET    /api/v1/models
POST   /api/v1/models
POST   /api/v1/models/{model_id}/test
POST   /api/v1/retrieval/search
POST   /api/v1/chat/stream
GET    /api/v1/conversations
GET    /api/v1/conversations/{conversation_id}/messages
POST   /api/v1/messages/{message_id}/feedback
POST   /api/v1/exports
GET    /api/v1/exports/{export_id}
GET    /api/v1/exports/{export_id}/download
DELETE /api/v1/exports/{export_id}
```

### 内部导出接口

```python
class Exporter:
    format_name: str
    async def export(self, content: "ExportContent", output_path: str) -> str: ...
```

需要分别实现：

```text
PdfExporter
DocxExporter
MarkdownExporter
CsvExporter
TxtExporter
```

### 验收标准

- 三种检索方式均可返回来源、页码、片段和相关度。
- 智能回答必须携带可核验引用。
- 五种格式均可导出并成功打开。
- 多文档导出生成 ZIP，下载地址有权限和有效期控制。
- CSV 字段固定，避免不同页面导出结构不一致。

## 6.7 员工 6：测试与平台工程

### 负责模块

- Git 仓库初始化、分支保护和代码评审模板。
- Dockerfile、Docker Compose 和环境配置。
- CI 流水线、静态检查、单元测试、接口测试和前端测试。
- 文档格式样本库、OCR 样本库和导出格式回归测试。
- 命中率测试、RAG 评测、性能测试和发布检查。
- 日志、指标、健康检查、备份和回滚。

### 验收标准

- Pull Request 未通过检查时不能合并到 `main`。
- 每次提交自动执行前后端检查和测试。
- 每个支持格式至少有一个正常样本和一个异常样本。
- 五种导出文件在 CI 中执行生成和基本可读性校验。
- 生产部署使用与测试环境相同的镜像。

## 7. Git 代码仓库规范

## 7.1 仓库形式

统一使用一个 Git Monorepo：

```text
knowledge-base-platform/
├── frontend/
│   ├── user-web/
│   ├── admin-web/
│   └── shared-ui/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── users/
│   │   ├── knowledge/
│   │   ├── documents/
│   │   ├── parsers/
│   │   ├── rag/
│   │   ├── exports/
│   │   ├── audit/
│   │   └── common/
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── uv.lock
├── deploy/
│   ├── docker/
│   ├── nginx/
│   ├── docker-compose.yml
│   ├── docker-compose.test.yml
│   └── env/
├── docs/
│   ├── api/
│   ├── design/
│   └── operations/
├── samples/
│   ├── documents/
│   └── exports/
├── scripts/
├── .github/workflows/
├── package-lock.json
├── Makefile
└── README.md
```

## 7.2 分支策略

为简化流程，只使用以下分支：

- `main`：始终保持可部署。
- `feature/<issue>-<name>`：功能开发。
- `fix/<issue>-<name>`：缺陷修复。
- `release/<version>`：仅在正式发布前短期使用。

不设置长期 `develop` 分支，减少重复合并。

## 7.3 提交与合并

提交格式：

```text
feat(documents): support image OCR
fix(exports): correct csv encoding
refactor(auth): simplify permission check
test(parser): add scanned pdf samples
docs(api): update export endpoints
```

合并要求：

- 每个任务对应一个 Issue。
- 每个 Pull Request 只处理一个明确目标。
- 至少 1 名非作者评审通过。
- 接口变更必须更新 OpenAPI 和前端类型。
- 数据库变更必须包含 Alembic 迁移。
- 禁止直接向 `main` 推送。
- 发布使用 Git Tag，例如 `v1.0.0`。

## 8. 环境与版本基线

以下版本为本项目固定基线，不使用 `latest` 标签。所有依赖升级必须单独创建任务并完成回归测试。

## 8.1 开发和运行环境

| 项目 | 固定版本 | 说明 |
|---|---:|---|
| 开发主机系统 | Ubuntu 24.04.3 LTS 或 Windows 11 24H2 + WSL2 | 推荐在 WSL2 或 Linux 中开发 |
| 生产主机系统 | Ubuntu Server 24.04.3 LTS x86_64 | 容器化部署 |
| Git | 2.43.0 | 代码版本管理 |
| Docker Engine | 27.5.1 | 本地、测试和生产统一 |
| Docker Compose | 2.32.4 | 使用 Compose V2 |
| Python | 3.10.20 | 后端和 Worker 固定版本 |
| uv | 0.8.22 | Python 依赖安装和锁定 |
| Node.js | 22.23.1 LTS | 两个前端工程统一版本 |
| npm | 10.9.8 | 提交 `package-lock.json` |
| Nginx | 1.28.0 | 静态资源和反向代理 |
| PostgreSQL | 17.10 | 业务数据和全文检索 |
| pgvector 扩展 | 0.8.0 | 向量存储和相似度检索 |
| Redis Community Edition | 7.4.9 | 异步任务和缓存 |

说明：Python 3.10 已处于安全维护阶段，因此必须在 Docker 容器中使用固定补丁版本，并将后续升级到 Python 3.12 或更高版本列入第二阶段技术任务。

## 8.2 系统级文档处理工具

| 工具 | 固定版本 | 用途 |
|---|---:|---|
| LibreOffice | 24.2.7 | DOC、XLS、PPT、ODT 等格式转换 |
| Tesseract OCR | 5.3.4 | 图片和扫描 PDF OCR |
| Poppler | 24.02.0 | PDF 页面和文本处理 |
| Ghostscript | 10.02.1 | PDF 处理和兼容性修复 |
| libmagic | 5.45 | MIME 类型识别 |
| Noto CJK Fonts | 20220127 | 中文 PDF 导出字体 |

这些工具统一写入后端 Dockerfile，开发人员不手工安装不同版本。

## 8.3 Python 直接依赖版本

`backend/pyproject.toml` 中所有直接依赖必须使用精确版本：

```toml
[project]
requires-python = "==3.10.20"
dependencies = [
  "fastapi==0.139.0",
  "uvicorn[standard]==0.51.0",
  "pydantic==2.13.4",
  "pydantic-settings==2.12.0",
  "SQLAlchemy==2.0.51",
  "asyncpg==0.30.0",
  "alembic==1.16.5",
  "redis==6.4.0",
  "arq==0.26.3",
  "PyJWT[crypto]==2.10.1",
  "argon2-cffi==25.1.0",
  "python-multipart==0.0.20",
  "httpx==0.28.1",
  "orjson==3.11.4",
  "structlog==25.4.0",
  "prometheus-client==0.23.1",
  "tenacity==9.1.2",
  "docling[rapidocr]==2.112.0",
  "python-magic==0.4.27",
  "Pillow==11.3.0",
  "pandas==2.3.3",
  "openpyxl==3.1.5",
  "python-docx==1.2.0",
  "pypdf==5.9.0",
  "beautifulsoup4==4.14.2",
  "markdown-it-py==4.0.0",
  "mdit-py-plugins==0.5.0",
  "bleach==6.2.0",
  "weasyprint==66.0",
  "pgvector==0.5.0"
]

[dependency-groups]
dev = [
  "pytest==8.4.2",
  "pytest-asyncio==1.1.0",
  "pytest-cov==7.0.0",
  "ruff==0.12.12",
  "mypy==1.18.2"
]
```

安装规则：

```bash
uv sync --frozen
```

`uv.lock` 必须提交到 Git，所有间接依赖版本以该文件为准。

## 8.4 前端直接依赖版本

用户端和管理端使用相同版本，公共版本放在仓库根目录统一管理。

```json
{
  "engines": {
    "node": "22.23.1",
    "npm": "10.9.8"
  },
  "dependencies": {
    "vue": "3.5.39",
    "vue-router": "4.6.3",
    "pinia": "3.0.4",
    "element-plus": "2.14.3",
    "axios": "1.13.2",
    "markdown-it": "14.1.0",
    "dompurify": "3.3.0",
    "file-saver": "2.0.5"
  },
  "devDependencies": {
    "vite": "7.2.2",
    "@vitejs/plugin-vue": "6.0.1",
    "typescript": "5.9.3",
    "vue-tsc": "3.3.7",
    "eslint": "9.39.1",
    "eslint-plugin-vue": "10.6.0",
    "prettier": "3.6.2",
    "vitest": "4.1.10",
    "@vue/test-utils": "2.4.6",
    "jsdom": "27.0.1"
  }
}
```

安装规则：

```bash
npm ci
```

`package-lock.json` 必须提交到 Git，禁止使用 `^`、`~` 或不固定版本。

## 8.5 环境划分

| 环境 | 用途 | 数据 | 部署方式 |
|---|---|---|---|
| `local` | 个人开发 | 本地测试数据 | Docker Compose |
| `test` | 联调、自动化和验收 | 脱敏测试数据 | CI 构建镜像后部署 |
| `prod` | 正式运行 | 正式数据 | 使用测试通过的同一镜像 |

环境差异只允许通过环境变量配置，不允许为不同环境维护不同业务代码。

## 8.6 默认端口

| 服务 | 开发端口 | 生产入口 |
|---|---:|---|
| 用户端 | 5173 | `/` |
| 管理端 | 5174 | `/admin` |
| FastAPI | 8000 | `/api` |
| PostgreSQL | 5432 | 仅内部网络 |
| Redis | 6379 | 仅内部网络 |

## 9. 接口统一规范

## 9.1 基础规则

- 接口前缀统一为 `/api/v1`。
- JSON 字段使用 `snake_case`。
- 时间使用 ISO 8601，数据库保存 UTC。
- ID 使用 UUID。
- 文件上传使用 `multipart/form-data`。
- 普通下载使用流式响应，大型导出使用异步任务。
- API 文档由 FastAPI OpenAPI 自动生成并纳入 Git。

## 9.2 统一响应

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "uuid"
}
```

分页响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 0
  },
  "request_id": "uuid"
}
```

## 9.3 错误码

| 范围 | 模块 |
|---|---|
| 10000-10999 | 通用错误 |
| 11000-11999 | 认证和权限 |
| 12000-12999 | 用户和角色 |
| 13000-13999 | 知识库和文档 |
| 14000-14999 | 文档转换和 OCR |
| 15000-15999 | 检索和问答 |
| 16000-16999 | 导出和下载 |
| 17000-17999 | 评测和系统运维 |

## 9.4 上传接口规范

```text
POST /api/v1/knowledge-bases/{kb_id}/documents
Content-Type: multipart/form-data
```

字段：

```text
files[]             多文件
folder_path         可选目录路径
ocr_enabled         是否启用 OCR，默认自动判断
language            OCR 语言，默认 chi_sim+eng
duplicate_policy    skip、new_version、replace
```

响应返回每个文件对应的 `document_id` 和 `task_id`。

## 9.5 任务接口规范

```json
{
  "task_id": "uuid",
  "task_type": "document_convert",
  "status": "running",
  "stage": "ocr",
  "progress": 65,
  "error_code": null,
  "error_message": null,
  "created_at": "2026-07-14T08:00:00Z",
  "finished_at": null
}
```

## 9.6 安全要求

- 后端必须校验用户是否有查看、下载和导出权限。
- 原始文件和导出文件不能通过可猜测的静态地址公开访问。
- 下载链接必须短期有效或由接口实时鉴权。
- Markdown 预览前必须进行 HTML 安全过滤。
- 文件名、MIME 类型和文件头必须交叉校验。
- 上传目录禁止执行文件。
- 模型密钥、Token 和密码不得写入日志。

## 10. 简化研发流程

### 10.1 五阶段流程

```text
需求确认 -> 开发 -> Pull Request 评审 -> 测试 -> 发布
```

每个任务只需要以下内容：

- 目标和范围。
- 页面或接口说明。
- 验收标准。
- 负责人和协作人。
- 测试样本。

### 10.2 接口协作

1. 后端先提交 OpenAPI 草案。
2. 对应前端在 Pull Request 中确认字段。
3. 前端使用生成的 TypeScript 类型和 Mock 数据开发。
4. 后端完成后执行契约测试。
5. 接口字段变更必须同时更新 OpenAPI、前端类型和测试。

### 10.3 每周协作安排

| 活动 | 频率 | 时长 | 输出 |
|---|---|---:|---|
| 周计划 | 每周一 | 30 分钟 | 本周任务和负责人 |
| 每日站会 | 每工作日 | 15 分钟 | 进度和阻塞 |
| 接口评审 | 有需要时 | 30 分钟内 | OpenAPI 确认 |
| 周验收 | 每周五 | 60 分钟 | 演示、缺陷和下周调整 |

不再设置多层级审批和重复周报，项目状态以 Git Issue、Pull Request 和测试结果为准。

## 11. 八周实施计划

| 周次 | 目标 | 主要交付 |
|---|---|---|
| 第 1 周 | 工程和环境 | Git 仓库、Docker、前后端骨架、数据库、CI |
| 第 2 周 | 用户权限和知识库 | 登录、用户、角色、权限、知识库管理 |
| 第 3 周 | 文档上传和转换 | 多文件上传、MIME 检测、原始文件保存、Docling 转 Markdown |
| 第 4 周 | OCR 和索引 | 图片 OCR、扫描 PDF、分段、全文检索、pgvector |
| 第 5 周 | 用户检索和问答 | 三种检索、流式问答、引用和会话 |
| 第 6 周 | 导出下载 | PDF、DOCX、MD、CSV、TXT、ZIP 和我的下载 |
| 第 7 周 | 管理和评测 | 系统概览、命中率测试、审计日志、异常重试 |
| 第 8 周 | 集成上线 | 自动化、性能、安全、数据备份、发布和回滚演练 |

## 12. 首期验收标准

### 12.1 文档处理

- 支持格式表中的文件可以上传并进入统一任务流程。
- PDF、Word、Markdown、CSV、TXT 和常见图片均能转换为 Markdown。
- 图片和扫描 PDF 能通过 OCR 生成可搜索文本。
- 转换后的 Markdown 能保留标题、段落、表格、图片和来源位置。
- 失败任务显示明确阶段、错误原因和重试入口。
- 原始文件、Markdown 和资源文件均可追溯。

### 12.2 用户界面

- 用户只看到有权限的知识库和文档。
- 用户可以检索、预览、问答并查看引用。
- 用户可以选择 PDF、Word、Markdown、CSV、TXT 导出。
- 下载文件内容与选择范围一致，文件名和中文编码正常。

### 12.3 管理员界面

- 管理员可管理用户、角色、模型、知识库和文档。
- 管理员可查看文档转换全过程和 Markdown 结果。
- 管理员可重试失败任务并执行命中率测试。
- 管理操作可以在审计日志中追踪。

### 12.4 工程质量

- 所有代码通过 Git Pull Request 合并。
- 后端单元测试覆盖率不低于 70%。
- 核心接口具备自动化接口测试。
- 文档格式转换和五种导出具备回归样本。
- 测试环境通过后使用同一镜像发布生产。
- 数据库、原始文件和 Markdown 文件具备备份和恢复方案。

## 13. 主要风险和处理方式

| 风险 | 处理方式 | 负责人 |
|---|---|---|
| 所谓“任何格式”存在未知文件 | MIME 检测、解析器插件、保留原件、人工处理状态 | 员工 4 |
| 图片 OCR 准确率不足 | 语言配置、图像预处理、置信度展示、人工校对入口 | 员工 4、6 |
| Word 或 PDF 导出排版不一致 | 固定导出模板、中文字体、样本回归测试 | 员工 5、6 |
| CSV 无法表达复杂文档 | 统一导出为章节和分段记录，不强制保持原排版 | 员工 5 |
| 大文件处理超时 | 异步任务、分页解析、大小限制、进度和取消 | 员工 4 |
| Markdown 中包含危险 HTML | 服务端清洗、前端 DOMPurify 二次过滤 | 员工 1、4 |
| Python 3.10 生命周期较短 | 固定 3.10.20 容器，第二阶段升级到较新版本 | 员工 6 |
| 依赖版本漂移 | 精确版本、`uv.lock`、`package-lock.json`、禁止 latest | 员工 6 |
| 多人开发接口冲突 | OpenAPI 先行、模块负责人评审、契约测试 | 全员 |

## 14. 完成定义

一个功能只有同时满足以下条件才能关闭：

- 代码已提交到对应功能分支。
- Pull Request 已通过评审。
- 自动化检查和测试通过。
- 接口文档或页面说明已更新。
- 权限、异常、空状态和日志已处理。
- 测试环境已验收。
- 必要的部署和回滚说明已更新。

## 15. 最终责任原则

1. 每个模块只有一名主负责人，备份人只在主负责人不可用时接管。
2. 前端负责交互和展示，后端负责权限、数据和业务正确性。
3. 文档处理模块只输出标准 Markdown 和分段，RAG 模块只通过公开接口使用结果。
4. 导出模块统一处理五种格式，禁止各页面分别实现不一致的导出逻辑。
5. 所有代码和文档必须进入 Git 仓库，不通过聊天工具传递最终版本。
6. 所有依赖必须精确锁定，不使用浮动版本或 `latest` 镜像。
7. 每次上线必须能够回滚代码、数据库迁移和容器镜像。
