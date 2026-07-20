# 项目治理与 CI 基线

> 对应 Issue：[#5](https://github.com/studynightfive/team_projects/issues/5)<br>
> 状态：已通过 PR #6 合入 `main`<br>
> 日期：2026-07-15

## 1. 目标

在业务代码进入仓库前固定协作、版本、评审、安全和自动检查边界。治理基线解决的不是“文件不够多”，而是多人并行时缺少单一规则来源导致的接口漂移、重复实现、过时分支和无法验证的合并。

## 2. 范围

- 根项目规则和长期记忆。
- 功能、缺陷 Issue 表单和 Pull Request 模板。
- 项目 README 与固定运行时版本。
- 可在空工程状态运行、在前后端工程出现后自动启用的 CI。
- `main` 的 Pull Request 协作规则与 CI 基线。

治理基线交付不包含业务代码、Docker 环境或具体产品功能；后续功能分支复用这些规则。

## 3. Issue 和分支规则

- 一个功能或缺陷 Issue 对应一个分支和一个 PR。
- 员工 1 的统一前端 P0 按一个整体功能交付：一个总 Issue、一个 `feature/<issue>-unified-web-p0` 长期功能分支、15 个里程碑和一个持续更新的 Draft PR；不创建 15 个里程碑分支或子 Issue。
- 每个前端里程碑必须先在本地通过对应门禁，才允许推送同一长期分支；15 个里程碑、全量本地 E2E、最终 CI 和测试环境验收全部通过后，才将总 PR 转为 Ready。总 PR 合并后才关闭总 Issue 并删除长期分支。
- Issue 必须说明用户价值、目标、范围、非范围、页面/交互状态、API 依赖、验收、本地测试、失败和边界场景。
- 分支从最新 `main` 创建，命名为 `feature/<issue>-<name>` 或 `fix/<issue>-<name>`。
- 依赖分支必须等待父 PR 合并，不建立长期堆叠分支。
- PR 使用 `Closes #<issue>` 关联 Issue，评审和 CI 完成前保持未合并。

## 4. CI 行为

工作流名称为 `CI`，质量检查 Job 名称为 `quality`。项目不要求把它配置成 GitHub 必需状态检查，但 Pull Request 仍需运行并通过该 Job。

### 无工程代码时

- 验证 `AGENTS.md`、`MEMORY.md`、README 和协作模板存在。
- 不因为缺少 `pnpm-lock.yaml` 或 `backend/pyproject.toml` 失败。

### 根 pnpm 锁文件出现后

- 使用 Node.js `22.23.1`、pnpm `11.13.0` 和 pnpm 缓存运行 `pnpm install --frozen-lockfile`。
- 直接运行统一 Web 应用的 typecheck、Lint、test、build 脚本；任一根脚本缺失都必须让 CI 失败。

### 后端项目出现后

- 使用 Python `3.10.20` 和 uv `0.11.26`。
- 执行 `uv sync --project backend --frozen`。
- 执行 Ruff、mypy 和 pytest。

## 5. main 协作规则

仓库协作规则：

- 禁止直接推送，所有变更通过 PR。
- Pull Request 的 `quality` CI 必须通过，分支在最终验收前必须与最新 `main` 同步。
- 至少一名非作者批准，推送新提交后旧批准失效。
- 最后一次推送者不能批准自己的变更。
- 所有 Review 对话必须解决。
- 禁止 force push 和删除 `main`。
- 要求线性历史。

2026-07-15 项目负责人已废除“管理员必须把 `quality` 配置为 GitHub 必需状态检查”的规则。因此不再提供或要求执行分支保护配置脚本；上述协作规则通过本地门禁、Pull Request 流程、CI 结果和评审共同执行。

## 6. 验收标准

- 必需治理文件存在且内容与协作方案一致。
- YAML 与工程配置通过语法或对应工具检查。
- CI 在根 pnpm 锁文件出现后执行统一 Web 的安装、类型检查、Lint、测试和构建；后端工程出现后自动进入后端检查。
- 分支已推送，PR 关联 #5。
- 不依赖仓库管理员配置必需状态检查即可开始工程工作。

## 7. 风险与约束

| 风险 | 处理 |
|---|---|
| GitHub 未强制 required check | 本地门禁、Pull Request CI 与非作者评审仍作为合入条件 |
| 后端工程尚未创建 | CI 使用文件检测，不伪造空项目或无意义依赖 |
| 团队分支长期未合并 | 每个分支保持单一可验收能力并从最新 main 创建 |
| API 字段由前端猜测 | OpenAPI 先行；未确认接口只做静态 UI |
| 依赖版本漂移 | 固定运行时、精确直接依赖并提交锁文件 |
| secret 泄露 | 不读取或输出 secret 值，模板和日志不要求粘贴敏感内容 |

## 8. 验证步骤

```powershell
git diff --check

# GitHub CLI 和仓库权限（不输出凭据）
gh api user --jq .login
gh repo view --json nameWithOwner,viewerPermission
```

CI 合并前还需在 GitHub PR 页面确认 `quality` 实际通过。
