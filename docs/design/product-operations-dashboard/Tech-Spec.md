# 商品运营看板技术设计

## 1. 数据流

```text
用户问答
  -> RAG 检索、重排和回答生成
  -> 确认最终引用
  -> 取第一条引用的 doc_id / doc_title
  -> 写入 retrieval_metrics
  -> 管理看板按商品标识聚合
```

只在回答完成后记录商品归属。流式回答从最终 `citation` 事件提取首条引用，非流式回答从响应的 `hits[0]` 提取。缓存回答继续携带原引用，因此可使用相同口径。

## 2. 数据库变更

`retrieval_metrics` 新增两个可空快照字段：

- `primary_product_id VARCHAR(36)`：最终第一引用文档标识。
- `primary_product_name VARCHAR(500)`：问答发生时的文档标题快照。

两个字段不建立文档外键。文档进入回收站或到期清理后，历史运营指标仍需保留。新增 `(department_id, primary_product_id, created_at)` 索引支持部门和周期聚合。

旧数据保持字段为空，不做基于问题文本的错误回填。

## 3. API 变更

`DashboardMetrics` 新增：

- `product_queries: int`
- `product_match: RateMetric`
- `popular_products: PopularProductItem[]`

`PopularProductItem`：

- `product_id: string`
- `product_name: string`
- `query_count: int`
- `last_queried_at: datetime`

移除 `popular_questions`，前端不再获取或展示完整用户问题统计。旧总量字段继续保留，降低已有客户端升级风险。

## 4. 聚合规则

热门商品只统计满足以下条件的指标：

- `event_type = 'answer'`
- `hit_count > 0`
- `primary_product_id IS NOT NULL`
- `primary_product_name IS NOT NULL`
- 指标创建时间位于请求统计周期内
- 指标部门符合服务端解析后的权限范围

按 `primary_product_id` 分组。商品名称使用该组最近一次查询保存的标题，避免文档改名后把同一商品拆成两条。

## 5. 安全与性能

- 指标表不保存问题和答案正文。
- 商品名称长度限制为 500，写入前去除首尾空白。
- 指标写入继续使用嵌套事务，观测数据异常不得阻断 RAG。
- 查询使用部门、商品和时间联合索引；默认仅返回前 10 个热门商品。

## 6. 验证

- 单元测试：指标字段清理、空引用、重复请求幂等。
- 集成测试：同商品不同问法聚合、跨部门隔离、不同商品拆分。
- 前端测试：显示“热门商品”和商品查询指标，不再显示“高频问题”。
- 契约验证：生成 OpenAPI 与 TypeScript 类型后执行类型检查。
