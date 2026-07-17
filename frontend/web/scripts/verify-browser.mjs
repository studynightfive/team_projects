import { Buffer } from "node:buffer";
import { execFile, spawn } from "node:child_process";
import { access, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join, resolve, sep } from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(scriptDirectory, "../../..");
const m01OutputDirectory = resolve(
  repositoryRoot,
  "docs/verification/m01-web-foundation",
);
const localPagesOutputDirectory = resolve(
  repositoryRoot,
  "docs/verification/m02-m14-local-pages",
);
const accountSupportOutputDirectory = resolve(
  repositoryRoot,
  "docs/verification/account-support-pages",
);
const baseUrl =
  process.env.WEB_BASE_URL ??
  process.env.M01_BASE_URL ??
  "http://127.0.0.1:5173";
const execFileAsync = promisify(execFile);

const getSourceState = async () => {
  const [{ stdout: sourceCommit }, { stdout: status }] = await Promise.all([
    execFileAsync("git", ["rev-parse", "HEAD"], { cwd: repositoryRoot }),
    execFileAsync(
      "git",
      ["status", "--porcelain=v1", "--untracked-files=all"],
      { cwd: repositoryRoot },
    ),
  ]);
  const sourceChanges = status
    .split(/\r?\n/u)
    .filter(Boolean)
    .map((line) => line.slice(3))
    .filter((path) => !path.startsWith("docs/verification/"));

  return {
    sourceCommit: sourceCommit.trim(),
    sourceWorktreeDirty: sourceChanges.length > 0,
  };
};

const m01Cases = [
  {
    name: "user-shell-1920",
    path: "/",
    width: 1920,
    height: 1080,
    shell: "user",
  },
  {
    name: "user-shell-1440",
    path: "/",
    width: 1440,
    height: 1000,
    shell: "user",
  },
  {
    name: "user-shell-1280",
    path: "/",
    width: 1280,
    height: 900,
    shell: "user",
  },
  { name: "user-shell-375", path: "/", width: 375, height: 812, shell: "user" },
  {
    name: "user-shell-collapsed-1440",
    path: "/",
    width: 1440,
    height: 1000,
    shell: "user",
    collapsed: true,
  },
  {
    name: "admin-shell-1920",
    path: "/admin",
    width: 1920,
    height: 1080,
    shell: "admin",
  },
  {
    name: "admin-shell-1440",
    path: "/admin",
    width: 1440,
    height: 1000,
    shell: "admin",
  },
  {
    name: "admin-shell-1280",
    path: "/admin",
    width: 1280,
    height: 900,
    shell: "admin",
  },
  {
    name: "admin-shell-375",
    path: "/admin",
    width: 375,
    height: 812,
    shell: "admin",
  },
  {
    name: "admin-shell-collapsed-1440",
    path: "/admin",
    width: 1440,
    height: 1000,
    shell: "admin",
    collapsed: true,
  },
  { name: "login-1920", path: "/login", width: 1920, height: 1080 },
  { name: "login-1440", path: "/login", width: 1440, height: 1000 },
  { name: "login-1280", path: "/login", width: 1280, height: 900 },
  { name: "login-375", path: "/login", width: 375, height: 812 },
  { name: "forbidden-1440", path: "/403", width: 1440, height: 1000 },
  { name: "forbidden-1280", path: "/403", width: 1280, height: 900 },
  { name: "forbidden-375", path: "/403", width: 375, height: 812 },
  {
    name: "not-found-1440",
    path: "/does-not-exist",
    width: 1440,
    height: 1000,
  },
  {
    name: "not-found-1280",
    path: "/does-not-exist",
    width: 1280,
    height: 900,
  },
  {
    name: "not-found-375",
    path: "/does-not-exist",
    width: 375,
    height: 812,
  },
];

const localPageRoutes = [
  {
    name: "knowledge-list",
    path: "/knowledge",
    shell: "user",
    title: "企业知识库",
  },
  {
    name: "knowledge-detail",
    path: "/knowledge/product-handbook",
    shell: "user",
    title: "文档目录",
  },
  {
    name: "document-detail",
    path: "/knowledge/product-handbook/documents/release-guide",
    shell: "user",
    title: "文档预览",
  },
  {
    name: "search",
    path: "/search",
    shell: "user",
    title: "搜索结果",
  },
  {
    name: "chat-new",
    path: "/chat",
    shell: "user",
    title: "AI 助手",
  },
  {
    name: "chat-detail",
    path: "/chat/conv-release-review",
    shell: "user",
    title: "会话详情",
  },
  {
    name: "conversations",
    path: "/conversations",
    shell: "user",
    title: "历史会话",
  },
  {
    name: "downloads",
    path: "/downloads",
    shell: "user",
    title: "我的下载",
  },
  {
    name: "admin-users",
    path: "/admin/users",
    shell: "admin",
    title: "用户管理",
  },
  {
    name: "admin-roles",
    path: "/admin/roles",
    shell: "admin",
    title: "角色管理",
  },
  {
    name: "admin-models",
    path: "/admin/models",
    shell: "admin",
    title: "模型管理",
  },
  {
    name: "admin-knowledge-bases",
    path: "/admin/knowledge-bases",
    shell: "admin",
    title: "知识库管理",
  },
  {
    name: "admin-documents",
    path: "/admin/documents",
    shell: "admin",
    title: "文档管理",
  },
  {
    name: "admin-tasks",
    path: "/admin/tasks",
    shell: "admin",
    title: "任务中心",
  },
  {
    name: "admin-retrieval-tests",
    path: "/admin/retrieval-tests",
    shell: "admin",
    title: "命中率测试",
  },
  {
    name: "admin-audit-logs",
    path: "/admin/audit-logs",
    shell: "admin",
    title: "审计日志",
  },
];

const localPageCases = localPageRoutes.flatMap((route) =>
  [
    { suffix: "1440", width: 1440, height: 1000 },
    { suffix: "1280", width: 1280, height: 900 },
    { suffix: "375", width: 375, height: 812 },
  ].map((viewport) => ({
    ...route,
    ...viewport,
    name: `${route.name}-${viewport.suffix}`,
    group: "local-pages",
  })),
);

localPageCases.push(
  {
    name: "document-detail-collapsed-1440",
    path: "/knowledge/product-handbook/documents/release-guide",
    shell: "user",
    title: "文档预览",
    width: 1440,
    height: 1000,
    collapsed: true,
    group: "local-pages",
  },
  {
    name: "admin-users-collapsed-1440",
    path: "/admin/users",
    shell: "admin",
    title: "用户管理",
    width: 1440,
    height: 1000,
    collapsed: true,
    group: "local-pages",
  },
);

const accountSupportRoutes = [
  {
    name: "notifications",
    path: "/notifications",
    shell: "user",
    title: "通知中心",
    notificationPreview: true,
  },
  {
    name: "help",
    path: "/help",
    shell: "user",
    title: "帮助中心",
  },
  {
    name: "preferences",
    path: "/preferences",
    shell: "user",
    title: "偏好设置",
  },
  {
    name: "admin-notifications",
    path: "/admin/notifications",
    shell: "admin",
    title: "通知中心",
    notificationPreview: true,
  },
];

const accountSupportCases = accountSupportRoutes.flatMap((route) =>
  [
    { suffix: "1440", width: 1440, height: 1000 },
    { suffix: "1280", width: 1280, height: 900 },
    { suffix: "375", width: 375, height: 812 },
  ].map((viewport) => ({
    ...route,
    ...viewport,
    name: `${route.name}-${viewport.suffix}`,
    group: "account-support",
  })),
);

const allCases = [
  ...m01Cases.map((testCase) => ({ ...testCase, group: "m01" })),
  ...localPageCases,
  ...accountSupportCases,
];
const requestedGroup = process.env.WEB_VERIFY_GROUP;
const cases =
  requestedGroup === undefined
    ? allCases
    : allCases.filter((testCase) => testCase.group === requestedGroup);

if (cases.length === 0) {
  throw new Error(`没有可运行的浏览器验收分组：${requestedGroup}`);
}

const delay = (milliseconds) =>
  new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));

const findChrome = async () => {
  const candidates = [
    process.env.CHROME_PATH,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ].filter(Boolean);

  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // 继续检查下一个已知安装路径。
    }
  }

  throw new Error("未找到 Chrome/Edge；可通过 CHROME_PATH 指定浏览器路径。");
};

const reservePort = () =>
  new Promise((resolvePort, rejectPort) => {
    const server = createServer();
    server.once("error", rejectPort);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (address === null || typeof address === "string") {
        server.close();
        rejectPort(new Error("无法分配 Chrome 调试端口。"));
        return;
      }

      server.close(() => resolvePort(address.port));
    });
  });

const waitForTarget = async (port) => {
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`);
      if (response.ok) {
        const targets = await response.json();
        const page = targets.find((target) => target.type === "page");
        if (page?.webSocketDebuggerUrl !== undefined) {
          return page.webSocketDebuggerUrl;
        }
      }
    } catch {
      // Chrome 启动期间端口尚不可用，短暂等待后重试。
    }
    await delay(100);
  }

  throw new Error("Chrome DevTools Protocol 启动超时。");
};

class CdpClient {
  constructor(webSocketUrl) {
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    this.socket = new globalThis.WebSocket(webSocketUrl);
    this.socket.binaryType = "arraybuffer";
  }

  async connect() {
    await new Promise((resolveOpen, rejectOpen) => {
      const timeout = setTimeout(
        () => rejectOpen(new Error("CDP WebSocket 连接超时。")),
        10_000,
      );
      this.socket.addEventListener(
        "open",
        () => {
          clearTimeout(timeout);
          resolveOpen();
        },
        { once: true },
      );
      this.socket.addEventListener(
        "error",
        () => {
          clearTimeout(timeout);
          rejectOpen(new Error("CDP WebSocket 连接失败。"));
        },
        { once: true },
      );
    });

    this.socket.addEventListener("message", (event) => {
      const text =
        typeof event.data === "string"
          ? event.data
          : Buffer.from(event.data).toString("utf8");
      const message = JSON.parse(text);

      if (message.id !== undefined) {
        const pending = this.pending.get(message.id);
        if (pending === undefined) return;
        this.pending.delete(message.id);
        if (message.error !== undefined) {
          pending.reject(new Error(message.error.message));
        } else {
          pending.resolve(message.result ?? {});
        }
        return;
      }

      if (message.method !== undefined) {
        for (const listener of this.listeners.get(message.method) ?? []) {
          listener(message.params ?? {});
        }
      }
    });
  }

  send(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;

    return new Promise((resolveCommand, rejectCommand) => {
      this.pending.set(id, { resolve: resolveCommand, reject: rejectCommand });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) ?? [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }

  waitFor(method, timeoutMilliseconds = 10_000) {
    return new Promise((resolveEvent, rejectEvent) => {
      const timeout = setTimeout(() => {
        const listeners = this.listeners.get(method) ?? [];
        this.listeners.set(
          method,
          listeners.filter((listener) => listener !== handleEvent),
        );
        rejectEvent(new Error(`等待 ${method} 超时。`));
      }, timeoutMilliseconds);

      const handleEvent = (params) => {
        clearTimeout(timeout);
        const listeners = this.listeners.get(method) ?? [];
        this.listeners.set(
          method,
          listeners.filter((listener) => listener !== handleEvent),
        );
        resolveEvent(params);
      };

      this.on(method, handleEvent);
    });
  }

  close() {
    this.socket.close();
  }
}

const evaluate = async (client, expression) => {
  const result = await client.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });

  if (result.exceptionDetails !== undefined) {
    throw new Error(result.exceptionDetails.text ?? "浏览器表达式执行失败。");
  }

  return result.result?.value;
};

const recordCheck = (checks, label, pass, actual) => {
  checks.push({ label, pass, actual });
};

const verifyMetrics = (testCase, metrics, drawer, loginState) => {
  const checks = [];
  recordCheck(
    checks,
    "视口宽度精确",
    metrics.innerWidth === testCase.width,
    metrics.innerWidth,
  );
  recordCheck(
    checks,
    "根节点无横向溢出",
    metrics.scrollWidth <= metrics.clientWidth,
    `${metrics.scrollWidth}/${metrics.clientWidth}`,
  );
  recordCheck(
    checks,
    "页面只有一个主标题",
    metrics.h1Count === 1,
    metrics.h1Count,
  );
  recordCheck(
    checks,
    "截图尺寸精确",
    metrics.screenshotWidth === testCase.width &&
      metrics.screenshotHeight === testCase.height,
    `${metrics.screenshotWidth}x${metrics.screenshotHeight}`,
  );
  recordCheck(checks, "页面文案无 emoji", !metrics.hasEmoji, metrics.hasEmoji);
  recordCheck(
    checks,
    "页面使用线性 SVG 图标",
    metrics.svgIconCount > 0,
    metrics.svgIconCount,
  );

  if (
    testCase.group === "local-pages" ||
    testCase.group === "account-support"
  ) {
    recordCheck(
      checks,
      "业务页使用统一 business-page 根节点",
      metrics.businessPageCount === 1,
      metrics.businessPageCount,
    );
    recordCheck(
      checks,
      "顶栏标题与路由一致",
      metrics.topbarTitle === testCase.title && metrics.topbarTitleVisible,
      `${metrics.topbarTitle}/${metrics.topbarTitleVisible ? "可见" : "隐藏"}`,
    );
  }

  if (testCase.notificationPreview === true) {
    recordCheck(
      checks,
      "通知预览固定展示最近四条",
      metrics.notificationPreviewItemCount === 4,
      metrics.notificationPreviewItemCount,
    );
    if (testCase.width >= 768) {
      recordCheck(
        checks,
        "桌面悬停可打开通知预览",
        metrics.notificationPreviewHoverVisible === true,
        metrics.notificationPreviewHoverVisible,
      );
      recordCheck(
        checks,
        "键盘聚焦可打开通知预览",
        metrics.notificationPreviewFocusVisible === true,
        metrics.notificationPreviewFocusVisible,
      );
      recordCheck(
        checks,
        "通知预览未越过视口",
        metrics.notificationPreviewWithinViewport === true,
        metrics.notificationPreviewWithinViewport,
      );
    } else {
      recordCheck(
        checks,
        "移动端隐藏悬停通知预览",
        metrics.notificationPreviewDisplay === "none",
        metrics.notificationPreviewDisplay,
      );
    }
  }

  if (testCase.width < 768) {
    recordCheck(
      checks,
      "关键内容未越过视口",
      metrics.maximumContentRight <= testCase.width,
      metrics.maximumContentRight,
    );
    recordCheck(
      checks,
      "主要交互高度至少 44px",
      metrics.minimumInteractiveHeight >= 44,
      metrics.minimumInteractiveHeight,
    );
  }

  if (testCase.shell !== undefined && testCase.width >= 768) {
    const expectedSidebarWidth = testCase.collapsed ? 64 : 240;
    recordCheck(
      checks,
      testCase.collapsed ? "折叠侧栏宽度 64px" : "桌面侧栏宽度 240px",
      metrics.sidebarWidth === expectedSidebarWidth,
      metrics.sidebarWidth,
    );
    recordCheck(
      checks,
      "桌面顶栏高度 56px",
      metrics.topbarHeight === 56,
      metrics.topbarHeight,
    );
    recordCheck(
      checks,
      "桌面菜单按钮隐藏",
      metrics.mobileMenuDisplay === "none",
      metrics.mobileMenuDisplay,
    );
    recordCheck(
      checks,
      "内容有效宽度不超过 1280px",
      metrics.contentInnerWidth <= 1280,
      metrics.contentInnerWidth,
    );
    if (testCase.group === "m01" && testCase.shell === "admin") {
      recordCheck(
        checks,
        "桌面指标保持四列",
        metrics.statColumnCount === 4,
        metrics.statColumnCount,
      );
    }
  }

  if (testCase.shell !== undefined && testCase.width < 768) {
    recordCheck(
      checks,
      "移动端侧栏无占位",
      metrics.sidebarDisplay === "none",
      metrics.sidebarDisplay,
    );
    recordCheck(
      checks,
      "移动端顶栏高度 56px",
      metrics.topbarHeight === 56,
      metrics.topbarHeight,
    );
    recordCheck(
      checks,
      "移动端内容 gutter 16px",
      metrics.contentPaddingLeft === 16 && metrics.contentPaddingRight === 16,
      `${metrics.contentPaddingLeft}/${metrics.contentPaddingRight}`,
    );
    if (testCase.group === "m01" && testCase.shell === "admin") {
      recordCheck(
        checks,
        "移动端指标单列",
        metrics.statColumnCount === 1,
        metrics.statColumnCount,
      );
    }
    recordCheck(
      checks,
      "移动完整导航项正确",
      drawer.navigationCount === 11,
      drawer.navigationCount,
    );
    recordCheck(
      checks,
      "抽屉打开后焦点进入关闭按钮",
      drawer.focusEntered,
      drawer.focusEntered,
    );
    recordCheck(checks, "Escape 关闭抽屉", drawer.closed, drawer.closed);
    recordCheck(
      checks,
      "关闭后焦点返回菜单按钮",
      drawer.focusReturned,
      drawer.focusReturned,
    );
    recordCheck(
      checks,
      "关闭后解除滚动锁",
      drawer.bodyUnlocked,
      drawer.bodyUnlocked,
    );
  }

  if (testCase.group === "m01" && testCase.shell === "user") {
    recordCheck(
      checks,
      "AI 搜索首页主视觉存在",
      metrics.searchHeroCount === 1,
      metrics.searchHeroCount,
    );
    recordCheck(
      checks,
      "高频任务共五项",
      metrics.quickActionCount === 5,
      metrics.quickActionCount,
    );
    recordCheck(
      checks,
      "继续工作与常用知识板块存在",
      metrics.homeInformationSectionCount === 2,
      metrics.homeInformationSectionCount,
    );
    recordCheck(
      checks,
      "数据源状态共四项",
      metrics.dataSourceCardCount === 4,
      metrics.dataSourceCardCount,
    );
  }

  if (testCase.group === "m01" && testCase.shell === "admin") {
    recordCheck(
      checks,
      "管理指标共四张",
      metrics.statCardCount === 4,
      metrics.statCardCount,
    );
    recordCheck(
      checks,
      "四张管理卡均有 Sparkline",
      metrics.sparklineCount === 4,
      metrics.sparklineCount,
    );
    recordCheck(
      checks,
      "Sparkline 共 28 个数据点",
      metrics.sparklinePointCount === 28,
      metrics.sparklinePointCount,
    );
    recordCheck(
      checks,
      "审计表头使用 slate-100",
      metrics.auditHeaderBackground === "rgb(241, 245, 249)",
      metrics.auditHeaderBackground,
    );
    recordCheck(
      checks,
      "分页提供禁用态",
      metrics.disabledInteractiveCount >= 1,
      metrics.disabledInteractiveCount,
    );
  }

  if (testCase.path === "/login") {
    if (testCase.width >= 1280) {
      recordCheck(
        checks,
        "登录桌面布局为 55:45 分屏",
        metrics.loginBrandRatio >= 0.545 && metrics.loginBrandRatio <= 0.555,
        metrics.loginBrandRatio,
      );
      recordCheck(
        checks,
        "登录桌面首屏无页面级滚动",
        metrics.scrollHeight <= metrics.innerHeight,
        `${metrics.scrollHeight}/${metrics.innerHeight}`,
      );
      recordCheck(
        checks,
        "登录表单宽度不超过 360px",
        metrics.loginFormWidth <= 360,
        metrics.loginFormWidth,
      );
    } else {
      recordCheck(
        checks,
        "登录移动端为单栏布局",
        metrics.loginColumnCount === 1,
        metrics.loginColumnCount,
      );
    }

    recordCheck(
      checks,
      "登录空提交显示两个错误",
      loginState.errorCount === 2,
      loginState.errorCount,
    );
    recordCheck(
      checks,
      "登录错误与控件 ARIA 关联",
      loginState.accountInvalid && loginState.passwordInvalid,
      `${loginState.accountInvalid}/${loginState.passwordInvalid}`,
    );
    recordCheck(
      checks,
      "密码显隐切换可用",
      loginState.passwordVisible,
      loginState.passwordVisible,
    );
    recordCheck(
      checks,
      "登录交互不持久化凭据",
      loginState.localStorageLength === 0 &&
        loginState.sessionStorageLength === 0,
      `${loginState.localStorageLength}/${loginState.sessionStorageLength}`,
    );
  }

  return checks;
};

const run = async () => {
  await Promise.all([
    mkdir(m01OutputDirectory, { recursive: true }),
    mkdir(localPagesOutputDirectory, { recursive: true }),
    mkdir(accountSupportOutputDirectory, { recursive: true }),
  ]);
  const sourceState = await getSourceState();
  const chromePath = await findChrome();
  const port = await reservePort();
  const profileDirectory = await mkdtemp(join(tmpdir(), "codex-m01-cdp-"));
  const chrome = spawn(
    chromePath,
    [
      "--headless=new",
      "--disable-background-networking",
      "--disable-extensions",
      "--disable-gpu",
      "--force-device-scale-factor=1",
      "--hide-scrollbars",
      "--no-first-run",
      `--remote-debugging-port=${port}`,
      "--remote-allow-origins=*",
      `--user-data-dir=${profileDirectory}`,
      "about:blank",
    ],
    { stdio: "ignore", windowsHide: true },
  );

  let client;
  try {
    const webSocketUrl = await waitForTarget(port);
    client = new CdpClient(webSocketUrl);
    await client.connect();
    await Promise.all([
      client.send("Page.enable"),
      client.send("Runtime.enable"),
      client.send("Console.enable"),
      client.send("Log.enable"),
      client.send("Network.enable"),
    ]);

    const browserVersion = await client.send("Browser.getVersion");
    const consoleErrors = [];
    const apiRequests = [];
    let activeCase = "startup";

    client.on("Runtime.exceptionThrown", (params) => {
      consoleErrors.push({
        case: activeCase,
        source: "exception",
        text: params.exceptionDetails?.text ?? "Runtime exception",
      });
    });
    client.on("Console.messageAdded", (params) => {
      if (params.message?.level === "error") {
        consoleErrors.push({
          case: activeCase,
          source: "console",
          text: params.message.text,
        });
      }
    });
    client.on("Log.entryAdded", (params) => {
      if (params.entry?.level === "error") {
        consoleErrors.push({
          case: activeCase,
          source: "log",
          text: params.entry.text,
          url: params.entry.url,
        });
      }
    });
    client.on("Network.requestWillBeSent", (params) => {
      try {
        const url = new URL(params.request.url);
        if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
          apiRequests.push({
            case: activeCase,
            method: params.request.method,
            url: url.pathname,
          });
        }
      } catch {
        // 非 HTTP(S) 内部请求不属于业务 API。
      }
    });

    const results = [];
    for (const testCase of cases) {
      activeCase = testCase.name;
      await client.send("Emulation.setDeviceMetricsOverride", {
        width: testCase.width,
        height: testCase.height,
        deviceScaleFactor: 1,
        mobile: false,
        screenWidth: testCase.width,
        screenHeight: testCase.height,
      });

      const loaded = client.waitFor("Page.loadEventFired");
      await client.send("Page.navigate", { url: `${baseUrl}${testCase.path}` });
      await loaded;
      const readySelector =
        testCase.group === "m01" ? "h1" : ".business-page h1";
      await evaluate(
        client,
        `(async () => {
          const deadline = Date.now() + 5000;
          while (document.querySelector(${JSON.stringify(readySelector)}) === null) {
            if (Date.now() >= deadline) {
              throw new Error("页面内容渲染超时");
            }
            await new Promise((resolve) => setTimeout(resolve, 50));
          }
          await document.fonts.ready;
          await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
          await new Promise((resolve) => setTimeout(resolve, 100));
          return true;
        })()`,
      );

      if (testCase.collapsed) {
        await evaluate(
          client,
          `(async () => {
            document.querySelector(".sidebar-collapse-button")?.click();
            await new Promise((resolve) => setTimeout(resolve, 260));
            return true;
          })()`,
        );
      }

      let notificationPreviewHoverVisible = false;
      if (testCase.notificationPreview === true && testCase.width >= 768) {
        const triggerPoint = await evaluate(
          client,
          `(() => {
            const box = document.querySelector(".notification-button")?.getBoundingClientRect();
            return box === undefined
              ? undefined
              : { x: box.left + box.width / 2, y: box.top + box.height / 2 };
          })()`,
        );
        if (triggerPoint === undefined) {
          throw new Error("未找到通知预览触发按钮。");
        }
        await client.send("Input.dispatchMouseEvent", {
          type: "mouseMoved",
          x: triggerPoint.x,
          y: triggerPoint.y,
        });
        await delay(100);
        notificationPreviewHoverVisible = await evaluate(
          client,
          `(() => {
            const popover = document.querySelector(".notification-popover");
            const box = popover?.getBoundingClientRect();
            return popover !== null &&
              getComputedStyle(popover).display !== "none" &&
              box.width > 0 && box.height > 0;
          })()`,
        );
      }

      const metrics = await evaluate(
        client,
        `(() => {
          const element = (selector) => document.querySelector(selector);
          const rect = (selector) => element(selector)?.getBoundingClientRect();
          const style = (selector) => {
            const target = element(selector);
            return target ? getComputedStyle(target) : undefined;
          };
          const interactive = [...document.querySelectorAll(
            "button, a[href], input:not([type='checkbox']), select, [tabindex]"
          )].map((target) => target.getBoundingClientRect()).filter((box) => box.width > 0 && box.height > 0);
          const contentRects = [
            rect(".stat-grid"),
            rect(".user-content-grid"),
            rect(".admin-operations-grid"),
            rect(".dashboard-heading"),
            rect(".admin-page-heading"),
            rect(".business-page"),
            rect(".mobile-bottom-nav"),
            rect(".login-form-container"),
            rect(".state-card")
          ].filter(Boolean);
          const contentStyle = style(".workspace-content");
          const contentRect = rect(".workspace-content");
          const loginGrid = style(".login-page-v2")?.gridTemplateColumns ?? "";
          const loginBrandWidth = rect(".login-brand-panel")?.width ?? 0;
          const topbarTitleElement =
            document.querySelector(".topbar-breadcrumb strong") ??
            document.querySelector(".admin-current-title");
          const topbarTitleRect = topbarTitleElement?.getBoundingClientRect();
          const notificationPreviewRect = rect(".notification-popover-surface");
          return {
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            clientWidth: document.documentElement.clientWidth,
            scrollWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
            scrollHeight: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
            h1Count: document.querySelectorAll("h1").length,
            businessPageCount: document.querySelectorAll(".business-page").length,
            topbarTitle: topbarTitleElement?.textContent?.trim() ?? "",
            topbarTitleVisible:
              topbarTitleRect !== undefined &&
              topbarTitleRect.width > 0 &&
              topbarTitleRect.height > 0,
            hasEmoji: /\\p{Emoji_Presentation}/u.test(document.body.innerText),
            svgIconCount: document.querySelectorAll("svg.lucide, svg[data-lucide]").length,
            sidebarDisplay: style(".app-sidebar")?.display,
            sidebarWidth: rect(".app-sidebar")?.width,
            topbarHeight: rect(".workspace-topbar")?.height,
            mobileMenuDisplay: style(".mobile-menu-button")?.display,
            contentPaddingLeft: Number.parseFloat(contentStyle?.paddingLeft ?? "0"),
            contentPaddingRight: Number.parseFloat(contentStyle?.paddingRight ?? "0"),
            contentInnerWidth: contentRect === undefined
              ? 0
              : Math.round(contentRect.width - Number.parseFloat(contentStyle?.paddingLeft ?? "0") - Number.parseFloat(contentStyle?.paddingRight ?? "0")),
            statColumnCount: (style(".stat-grid")?.gridTemplateColumns ?? "")
              .split(/\\s+/u).filter(Boolean).length,
            statCardCount: document.querySelectorAll(".stat-grid .stat-card").length,
            activityCount: document.querySelectorAll(".activity-list li").length,
            searchHeroCount: document.querySelectorAll(".search-hero").length,
            quickActionCount: document.querySelectorAll(".quick-action-list > button").length,
            homeInformationSectionCount: document.querySelectorAll(".home-information-grid > section").length,
            dataSourceCardCount: document.querySelectorAll(".data-source-summary-list > article").length,
            sparklineCount: document.querySelectorAll(".admin-stat-grid .sparkline").length,
            sparklinePointCount: document.querySelectorAll(".admin-stat-grid .sparkline-point").length,
            auditHeaderBackground: style(".audit-table thead th")?.backgroundColor,
            disabledInteractiveCount: document.querySelectorAll("button:disabled, input:disabled, select:disabled").length,
            loginBrandRatio: loginBrandWidth / window.innerWidth,
            loginFormWidth: rect(".login-form-container")?.width ?? 0,
            loginColumnCount: loginGrid.split(/\\s+/u).filter(Boolean).length,
            maximumContentRight: Math.ceil(Math.max(0, ...contentRects.map((box) => box.right))),
            minimumInteractiveHeight: Math.floor(Math.min(Infinity, ...interactive.map((box) => box.height))),
            notificationPreviewDisplay: style(".notification-popover")?.display ?? "missing",
            notificationPreviewItemCount: document.querySelectorAll(".notification-preview-item").length,
            notificationPreviewWithinViewport:
              notificationPreviewRect !== undefined &&
              notificationPreviewRect.left >= 0 &&
              notificationPreviewRect.right <= window.innerWidth &&
              notificationPreviewRect.bottom <= window.innerHeight,
          };
        })()`,
      );
      metrics.notificationPreviewHoverVisible = notificationPreviewHoverVisible;

      const screenshot = await client.send("Page.captureScreenshot", {
        format: "png",
        fromSurface: true,
        captureBeyondViewport: false,
      });
      const screenshotBuffer = Buffer.from(screenshot.data, "base64");
      metrics.screenshotWidth = screenshotBuffer.readUInt32BE(16);
      metrics.screenshotHeight = screenshotBuffer.readUInt32BE(20);
      const outputDirectory =
        testCase.group === "m01"
          ? m01OutputDirectory
          : testCase.group === "local-pages"
            ? localPagesOutputDirectory
            : accountSupportOutputDirectory;
      await writeFile(
        join(outputDirectory, `${testCase.name}.png`),
        screenshotBuffer,
      );

      if (testCase.notificationPreview === true && testCase.width >= 768) {
        await client.send("Input.dispatchMouseEvent", {
          type: "mouseMoved",
          x: 1,
          y: 1,
        });
        metrics.notificationPreviewFocusVisible = await evaluate(
          client,
          `(async () => {
            const trigger = document.querySelector(".notification-button");
            trigger?.focus();
            await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            const popover = document.querySelector(".notification-popover");
            const box = popover?.getBoundingClientRect();
            return trigger !== null && document.activeElement === trigger &&
              popover !== null && getComputedStyle(popover).display !== "none" &&
              box.width > 0 && box.height > 0;
          })()`,
        );
      }

      let drawer = {};
      if (testCase.shell !== undefined && testCase.width < 768) {
        drawer = await evaluate(
          client,
          `(async () => {
            const trigger = document.querySelector(".mobile-menu-button");
            trigger.click();
            await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            const drawer = document.querySelector(".mobile-drawer");
            const closeButton = document.querySelector(".mobile-drawer-close");
            const result = {
              navigationCount: drawer.querySelectorAll(".mobile-drawer-list .mobile-drawer-link").length,
              focusEntered: document.activeElement === closeButton,
            };
            drawer.dispatchEvent(new KeyboardEvent("keydown", {
              key: "Escape",
              bubbles: true,
              cancelable: true,
            }));
            await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            return {
              ...result,
              closed: document.querySelector(".mobile-drawer") === null,
              focusReturned: document.activeElement === trigger,
              bodyUnlocked: !document.body.classList.contains("drawer-open"),
            };
          })()`,
        );
      }

      let loginState = {};
      if (testCase.path === "/login") {
        loginState = await evaluate(
          client,
          `(async () => {
            const account = document.querySelector("#account");
            const password = document.querySelector("#password");
            const form = document.querySelector("form");
            const toggle = document.querySelector(".password-toggle");
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
            await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            toggle.click();
            await new Promise((resolve) => requestAnimationFrame(resolve));
            return {
              errorCount: document.querySelectorAll(".field-error").length,
              accountInvalid: account.getAttribute("aria-invalid") === "true",
              passwordInvalid: password.getAttribute("aria-invalid") === "true",
              passwordVisible: password.type === "text" && toggle.getAttribute("aria-pressed") === "true",
              localStorageLength: localStorage.length,
              sessionStorageLength: sessionStorage.length,
            };
          })()`,
        );
      }

      const checks = verifyMetrics(testCase, metrics, drawer, loginState);
      results.push({
        group: testCase.group,
        name: testCase.name,
        path: testCase.path,
        viewport: `${testCase.width}x${testCase.height}`,
        screenshot: `${testCase.name}.png`,
        metrics,
        drawer,
        loginState,
        checks,
        passed: checks.every((check) => check.pass),
      });
    }

    const createReport = (group) => {
      const groupResults = results.filter((result) => result.group === group);
      const caseNames = new Set(groupResults.map((result) => result.name));
      const groupConsoleErrors = consoleErrors.filter((entry) =>
        caseNames.has(entry.case),
      );
      const groupApiRequests = apiRequests.filter((entry) =>
        caseNames.has(entry.case),
      );

      return {
        generatedAt: new Date().toISOString(),
        ...sourceState,
        baseUrl,
        browser: browserVersion.product,
        results: groupResults,
        consoleErrors: groupConsoleErrors,
        apiRequests: groupApiRequests,
        passed:
          groupResults.every((result) => result.passed) &&
          groupConsoleErrors.length === 0 &&
          groupApiRequests.length === 0,
      };
    };

    const m01Report = createReport("m01");
    const localPagesReport = createReport("local-pages");
    const accountSupportReport = createReport("account-support");
    const reportTargets = [
      {
        group: "m01",
        directory: m01OutputDirectory,
        report: m01Report,
      },
      {
        group: "local-pages",
        directory: localPagesOutputDirectory,
        report: localPagesReport,
      },
      {
        group: "account-support",
        directory: accountSupportOutputDirectory,
        report: accountSupportReport,
      },
    ].filter(
      (target) =>
        requestedGroup === undefined || target.group === requestedGroup,
    );
    await Promise.all(
      reportTargets.map((target) =>
        writeFile(
          join(target.directory, "browser-report.json"),
          `${JSON.stringify(target.report, null, 2)}\n`,
          "utf8",
        ),
      ),
    );

    for (const result of results) {
      console.log(`${result.passed ? "PASS" : "FAIL"} ${result.name}`);
      for (const check of result.checks.filter((item) => !item.pass)) {
        console.log(`  - ${check.label}: ${check.actual}`);
      }
    }
    console.log(`Console errors: ${consoleErrors.length}`);
    console.log(`Business API requests: ${apiRequests.length}`);

    if (reportTargets.some((target) => !target.report.passed)) {
      process.exitCode = 1;
    }
  } finally {
    client?.close();
    chrome.kill();
    const safeTempRoot = `${resolve(tmpdir())}${sep}`.toLowerCase();
    const resolvedProfile = resolve(profileDirectory).toLowerCase();
    if (!resolvedProfile.startsWith(safeTempRoot)) {
      console.error("拒绝清理临时目录之外的 Chrome profile。");
      process.exitCode = 1;
    } else {
      await rm(profileDirectory, {
        recursive: true,
        force: true,
        maxRetries: 5,
        retryDelay: 100,
      });
    }
  }
};

await run();
