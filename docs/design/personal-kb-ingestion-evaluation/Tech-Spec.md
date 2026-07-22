# 个人知识库、上传切分与检索评测技术设计

## 数据模型

- `knowledge_bases.kind`: `enterprise | personal`。
- `knowledge_bases.owner_user_id`: 个人知识库所有者；企业知识库为空。
- `documents.chunk_strategy`: `fixed | semantic | recursive | format`。
- `documents.chunk_size`、`documents.chunk_overlap`: 本次上传实际使用的切分窗口。
- 企业知识库名称保持部门内唯一；个人知识库按 `owner_user_id` 唯一。

迁移会为全部已有用户补建个人知识库和用户级 `admin` 权限，并将已有文档标记为 `format` 策略以保持历史行为。

## 权限规则

- 企业知识库：按部门可见；只有管理权限账号可从管理端上传。
- 个人知识库：仅所有者可见、检索、上传和重新处理。
- 新增 `personal.document.upload` 权限给普通用户；服务层必须同时验证知识库类型和所有者，防止该权限写入企业库。

## 文档处理

处理顺序保持：文件安全校验 -> 解析/OCR -> Markdown 标准化与 HTML 清洗 -> 切分 -> Embedding -> pgvector 索引。

- `fixed`: 按字符窗口和重叠长度切分。
- `semantic`: 按标题、段落和句子边界聚合，尽量保持语义单元完整。
- `recursive`: 依次按段落、换行、句号、分号、空格和字符递归降级切分。
- `format`: 保留 Markdown 标题、表格、代码块和段落结构；超长单元再按窗口切分。

默认推荐 `recursive`，适合来源不统一的通用文档；结构稳定的 Markdown/制度文档可选 `format`。

## 评测标注迁移

测试集保存标注时记录 chunk ID、document ID 和内容摘要。运行前执行：

1. 活跃 chunk ID 直接使用。
2. 历史 chunk 按相同 document ID 与完全相同内容映射到当前活跃 chunk。
3. 无法精确映射时终止本次测试并提示重新标注。

禁止使用本次检索返回结果自动充当 relevant 集合，否则 Hit Rate 会失去评测意义。

## RAG 精度与速度

- 继续使用关键词与向量混合召回、RRF 融合和文本 Rerank。
- Rerank 输入补充文档标题与标题层级，并过滤只有 Markdown 标题的低信息片段。
- 阈值在 Rerank 后应用；优先比较 `rerank_score`，其次 `vector_score`，最后才使用原始分数。
- 保留答案缓存；不增加额外 LLM 查询改写调用，避免显著增加首字延迟。

## 验证

- Alembic 从 `0017` 升级到新 head，并执行 `alembic check`。
- 单元测试覆盖四种切分、个人知识库权限、用户创建、标注迁移和阈值。
- 组件测试覆盖企业库无上传、个人库上传参数和管理端企业库上传。
- 使用真实医疗知识库运行一次混合检索与测试集评测。
