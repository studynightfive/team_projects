# 账号与支持页面视觉验收

验收覆盖以下路由：

- 用户端：`/notifications`、`/help`、`/preferences`
- 管理端：`/admin/notifications`

每个路由均生成 1440×1000、1280×900 和 375×812 三档截图。用户端和管理端通知路由的桌面截图保持通知预览打开；自动检查包含悬停与键盘聚焦显隐、最近 4 条数量、预览边界、唯一主标题、顶栏标题、根级横向溢出、移动端 44px 触控尺寸、工作区壳层、控制台错误和业务 `/api` 请求。

运行命令：

```powershell
$env:WEB_VERIFY_GROUP = "account-support"
pnpm.cmd run verify:web:browser
Remove-Item Env:WEB_VERIFY_GROUP
```

机器可读结果见 [browser-report.json](./browser-report.json)。当前 12 个用例全部通过，控制台错误和业务 API 请求均为 0。
