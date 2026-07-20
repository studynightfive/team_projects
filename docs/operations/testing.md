# 测试指南

## 前端

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
```

Mock 浏览器回归需要先启动 `pnpm.cmd run dev:web`，再运行 `pnpm.cmd run verify:web:browser`。

## 后端与样本

以下命令构建包含锁定开发依赖的测试镜像，迁移独立测试数据库，并依次执行 Ruff、strict mypy、pytest 和样本完整性校验：

```powershell
docker compose -f deploy/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
```

测试项目使用 `knowledge-base-platform-test` 的专用网络和命名卷，不连接开发数据库。需要重新验证空数据库迁移时，可在确认项目名后删除测试卷再运行；不要删除 `kb-postgres-data` 或 `kb-storage-data`。

pytest 当前强制最低 50% 行覆盖率。覆盖率通过不等于真实集成、安全或性能验收；禁止用整文件 skip 或空 `pass` 测试充当门禁。
