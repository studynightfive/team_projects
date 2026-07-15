# M01 生产实现验收证据

本目录记录 `frontend/web` M01 `web-foundation` 的真实浏览器验收结果。截图来自 Vue/Vite 生产实现，不是静态 `artifact.html`。

## 验收结果

- 用户工作区：1440×1000、1280×900、375×812 通过。
- 管理中心：1440×1000、1280×900、375×812 通过。
- 登录、403、404：1440×1000、1280×900、375×812 通过。
- 根节点横向溢出：0 个失败页面。
- 浏览器控制台错误：0。
- 业务 `/api` 网络请求：0，符合 M01 静态壳层边界。
- 移动抽屉：模块数量、焦点进入、Escape 关闭、焦点返回和滚动锁清理通过。

机器可读结果见 [`browser-report.json`](browser-report.json)。报告同时记录浏览器版本、每页布局指标和逐项断言。

## 重复执行

先在仓库根目录启动 Mock 模式：

```powershell
npm.cmd run dev:web
```

再在另一个终端执行：

```powershell
npm.cmd run verify:web:browser
```

验证脚本通过 Chrome DevTools Protocol 强制精确视口，不使用 Windows Headless Chrome 会被最小窗口宽度影响的 `--window-size=375` 结果。浏览器不在默认路径时，通过 `CHROME_PATH` 指定可执行文件路径；该变量只能是本机路径，不能包含凭据。

## 截图清单

- `user-shell-1440.png`
- `user-shell-1280.png`
- `user-shell-375.png`
- `admin-shell-1440.png`
- `admin-shell-1280.png`
- `admin-shell-375.png`
- `login-1440.png`
- `login-1280.png`
- `login-375.png`
- `forbidden-1440.png`
- `forbidden-1280.png`
- `forbidden-375.png`
- `not-found-1440.png`
- `not-found-1280.png`
- `not-found-375.png`
