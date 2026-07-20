# RAG 真实 API 与 DeepSeek 接入修正记录

> 历史记录：本文记录 2026-07-19 的联调范围。当前接口、权限与默认模型以生成的 `docs/api/openapi.yaml`、`backend/app/common/config.py` 和部署模板为准。

## 背景

本次修正面向交付演示闭环：用户登录后进入工作区，上传并处理文档，检索命中真实文档片段，再由 DeepSeek 基于受限引用上下文生成回答，避免把检索结果直接拼接成伪答案。

## 当时完成的链路

1. 后端提供 `POST /api/v1/retrieval/answer`，复用检索、引用过滤与会话落库能力。
2. 前端 AI 搜索在真实 API 模式下调用 RAG 回答接口，同时展示答案和原始引用。
3. 历史会话、搜索历史、知识空间和收藏改为读取真实后端数据。
4. Docker 与环境模板增加 DeepSeek 配置入口；密钥只允许保存在未提交的本地环境文件或生产 Secret 管理系统中。

## 当前配置约定

```env
DEEPSEEK_API_KEY=<YOUR_DEEPSEEK_API_KEY>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_MODEL=deepseek-chat
```

配置变化后可重建 API 与 Worker：

```powershell
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml up -d --build api-server worker
```

未配置 `DEEPSEEK_API_KEY` 时，本地关键词检索仍可工作；需要调用外部模型的 RAG 生成会返回稳定的配置错误，不会伪装为真实模型回答。

## 边界与风险

- 检索和引用必须继续执行知识库权限过滤，前端隐藏入口不能替代后端鉴权。
- 模型地址和密钥由管理端受控配置；日志、错误响应和文档不得暴露密钥或原始异常。
- 外部模型的可用性、配额和回答质量不属于离线测试覆盖范围，发布前需要在获授权的环境做小流量验收。
