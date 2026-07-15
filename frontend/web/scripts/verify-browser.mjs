import { Buffer } from "node:buffer";
import { spawn } from "node:child_process";
import { access, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(scriptDirectory, "../../..");
const outputDirectory = resolve(
  repositoryRoot,
  "docs/verification/m01-web-foundation",
);
const baseUrl = process.env.M01_BASE_URL ?? "http://127.0.0.1:5173";

const cases = [
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
      "桌面指标保持四列",
      metrics.statColumnCount === 4,
      metrics.statColumnCount,
    );
    recordCheck(
      checks,
      "内容有效宽度不超过 1280px",
      metrics.contentInnerWidth <= 1280,
      metrics.contentInnerWidth,
    );
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
    recordCheck(
      checks,
      "移动端指标单列",
      metrics.statColumnCount === 1,
      metrics.statColumnCount,
    );
    recordCheck(
      checks,
      "移动完整导航项正确",
      drawer.navigationCount === (testCase.shell === "user" ? 6 : 7),
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

  if (testCase.shell === "user") {
    recordCheck(
      checks,
      "用户指标共四张",
      metrics.statCardCount === 4,
      metrics.statCardCount,
    );
    recordCheck(
      checks,
      "团队动态内容存在",
      metrics.activityCount === 4,
      metrics.activityCount,
    );
  }

  if (testCase.shell === "admin") {
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
  await mkdir(outputDirectory, { recursive: true });
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
      await evaluate(
        client,
        `(async () => {
          await document.fonts.ready;
          await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
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
            rect(".mobile-bottom-nav"),
            rect(".login-form-container"),
            rect(".state-card")
          ].filter(Boolean);
          const contentStyle = style(".workspace-content");
          const contentRect = rect(".workspace-content");
          const loginGrid = style(".login-page-v2")?.gridTemplateColumns ?? "";
          const loginBrandWidth = rect(".login-brand-panel")?.width ?? 0;
          return {
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            clientWidth: document.documentElement.clientWidth,
            scrollWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
            scrollHeight: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
            h1Count: document.querySelectorAll("h1").length,
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
            sparklineCount: document.querySelectorAll(".admin-stat-grid .sparkline").length,
            sparklinePointCount: document.querySelectorAll(".admin-stat-grid .sparkline-point").length,
            auditHeaderBackground: style(".audit-table thead th")?.backgroundColor,
            disabledInteractiveCount: document.querySelectorAll("button:disabled, input:disabled, select:disabled").length,
            loginBrandRatio: loginBrandWidth / window.innerWidth,
            loginFormWidth: rect(".login-form-container")?.width ?? 0,
            loginColumnCount: loginGrid.split(/\\s+/u).filter(Boolean).length,
            maximumContentRight: Math.ceil(Math.max(0, ...contentRects.map((box) => box.right))),
            minimumInteractiveHeight: Math.floor(Math.min(Infinity, ...interactive.map((box) => box.height))),
          };
        })()`,
      );

      const screenshot = await client.send("Page.captureScreenshot", {
        format: "png",
        fromSurface: true,
        captureBeyondViewport: false,
      });
      const screenshotBuffer = Buffer.from(screenshot.data, "base64");
      metrics.screenshotWidth = screenshotBuffer.readUInt32BE(16);
      metrics.screenshotHeight = screenshotBuffer.readUInt32BE(20);
      await writeFile(
        join(outputDirectory, `${testCase.name}.png`),
        screenshotBuffer,
      );

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

    const report = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      browser: browserVersion.product,
      results,
      consoleErrors,
      apiRequests,
      passed:
        results.every((result) => result.passed) &&
        consoleErrors.length === 0 &&
        apiRequests.length === 0,
    };

    await writeFile(
      join(outputDirectory, "browser-report.json"),
      `${JSON.stringify(report, null, 2)}\n`,
      "utf8",
    );

    for (const result of results) {
      console.log(`${result.passed ? "PASS" : "FAIL"} ${result.name}`);
      for (const check of result.checks.filter((item) => !item.pass)) {
        console.log(`  - ${check.label}: ${check.actual}`);
      }
    }
    console.log(`Console errors: ${consoleErrors.length}`);
    console.log(`Business API requests: ${apiRequests.length}`);

    if (!report.passed) {
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
