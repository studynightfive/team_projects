# Langfuse RAG 观测配置

## 作用范围

平台使用 Langfuse 记录查询预处理、答案缓存结果、知识库检索、重排和答案生成的耗时与
状态。Langfuse 不是 RAG 的运行依赖：未配置、网络超时或服务异常时，检索和回答继续
执行。

默认 `LANGFUSE_CAPTURE_CONTENT=false`，不会上报用户问题、文档片段或答案正文。云端
首次联调建议保持该值，确认客户的数据合规要求后再决定是否开启正文采集。

## 云端配置

在服务器 `/home/knowledge-base/deploy/env/.env` 中配置以下项目，不要把 Key 提交到 Git：

```dotenv
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=<Langfuse public key>
LANGFUSE_SECRET_KEY=<Langfuse secret key>
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_ENVIRONMENT=production
LANGFUSE_RELEASE=v0.1.0
LANGFUSE_CAPTURE_CONTENT=false
```

如果使用自建 Langfuse，将 `LANGFUSE_BASE_URL` 改为 API 服务可访问的 HTTPS 地址。修改
后只需重建 API 容器配置，不需要重建镜像：

```bash
cd /home/knowledge-base
docker compose --env-file deploy/env/.env \
  -f deploy/docker-compose.yml \
  -f deploy/docker-compose.cloud.yml \
  up -d --no-build --pull never --force-recreate api-server
```

## 验证

1. 在用户页面选择至少一个已有可检索文档的知识库，完成一次问答。
2. 在 Langfuse 中按 `environment=production` 查看 Trace。
3. 一次完整流式问答应包含 `rag-answer-stream`，并能看到 `rag-query-preprocess`、
   `rag-search`、`rag-rerank`（启用重排时）和 `rag-generation` 等阶段。
4. 第二次提出高相似问题，根 Trace 的元数据应显示缓存命中；响应阶段会提示精确或相似
   缓存。

若没有 Trace，先检查服务器能否访问 `LANGFUSE_BASE_URL`，再确认两个 Key 属于同一项目。
应用日志只记录初始化或上报失败的类型，不会打印 Key 和正文。
