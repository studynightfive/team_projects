# 列表分页与 AI 搜索精简技术方案

## 组件设计

- `ListPagination.vue`：封装 Ant Design Vue Pagination，统一总数文案、每页数量和移动端布局。
- `useListPagination.ts`：接收筛选后的只读列表，输出当前页、每页数量、总数与当前页数据；列表或筛选结果变化时校正页码。
- 页面只把原来的 `filteredItems` 渲染源替换为 `pagedItems`，不改变写操作和权限判断。

## AI 搜索

- 删除 `UserHomeView` 的常用问题区域及其仅用于展示的数据引用。
- `SearchContextPanel` 先按 `documentId` 去重；无 ID 时按 `title + sourceName` 兜底。
- 引用概览不再渲染 `SearchStatusBadge(pending)`，只保留可打开预览的文档标题。

## 命中率指标

| 字段 | 展示名称 |
| --- | --- |
| `hit_rate` | 命中率（Hit Rate） |
| `mrr` | 平均倒数排名（MRR） |
| `recall_at_k` | 召回率（Recall@K） |
| `precision_at_k` | 准确率（Precision@K） |
| `ndcg_at_k` | 归一化折损累计增益（NDCG@K） |
| `map_at_k` | 平均准确率均值（MAP@K） |

## 验证步骤

1. 组件测试覆盖翻页、每页数量、筛选后复位和空列表。
2. AI 搜索测试覆盖常用问题消失、同文档引用去重和无待确认状态。
3. 命中率页面测试覆盖中英文指标标题。
4. 运行前端全量门禁、后端静态检查与单元测试。
5. 生产构建并在 1440、1280、375 宽度核查列表与分页不重叠。
