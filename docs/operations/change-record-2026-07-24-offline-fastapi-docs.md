# 2026-07-24 FastAPI 文档离线资源修正记录

## 修正原因

FastAPI 默认生成的 Swagger UI 页面从 `cdn.jsdelivr.net` 加载 JavaScript 和 CSS。
在演示网络无法访问该 CDN 时，`/api/v1/docs` 虽然返回 200，浏览器仍会显示空白页面。

## 验收标准

- `/api/v1/docs` 返回 200，并且只引用项目自身的 Swagger UI 静态资源。
- `/api/v1/docs-assets/swagger-ui-bundle.js` 和
  `/api/v1/docs-assets/swagger-ui.css` 返回 200。
- `/api/v1/openapi.json` 继续作为文档契约来源。
- API、Worker 和生产镜像继续使用同一份锁定依赖。

## 修正范围

- FastAPI 关闭默认 CDN 文档页面，注册自托管 Swagger UI 页面。
- API 镜像通过固定版本 Python 依赖携带支持 OpenAPI 3.1 的 Swagger UI 5 静态资源。
- Nginx 将 `/api/` 标记为高优先级前缀，避免文档 JS/CSS 被前端静态资源规则截获。
- Swagger 使用同源外部初始化脚本，不放宽项目现有的 `script-src 'self'` 安全策略。
- 增加文档路由回归测试，防止后续重新引入外部 CDN。

## 风险与回滚

- Swagger UI 资源会略微增加 API 镜像体积，但不会进入业务请求链路。
- 若需回滚，可恢复 FastAPI 默认 `docs_url` 并删除静态资源挂载和对应依赖。

## 验证结果

- 文档路由与静态资源测试 5 项通过。
- Ruff 与 mypy 通过。
- Docker API 和 Web 镜像重建成功，数据库迁移正常退出。
- `/api/v1/docs`、本地 Swagger JS/CSS、`/api/v1/openapi.json` 和 Ready 均返回 200。
- 真实浏览器成功渲染 OpenAPI 3.1 文档和 82 个接口操作，没有控制台错误。
