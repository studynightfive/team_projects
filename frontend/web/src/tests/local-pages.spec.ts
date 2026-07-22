import {
  flushPromises,
  type DOMWrapper,
  type VueWrapper,
} from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";
import {
  adminNavigation,
  type NavigationChildItem,
  userNavigation,
} from "../data/foundation";
import { renderAppAt } from "./renderApp";

interface BusinessRouteCase {
  readonly name: string;
  readonly path: string;
  readonly title: string;
  readonly shell: "user" | "admin";
  readonly activeNavigation?: string;
}

const businessRoutes: readonly BusinessRouteCase[] = [
  {
    name: "knowledge-list",
    path: "/knowledge",
    title: "企业知识库",
    shell: "user",
    activeNavigation: "企业知识库",
  },
  {
    name: "knowledge-detail",
    path: "/knowledge/product-handbook",
    title: "文档目录",
    shell: "user",
    activeNavigation: "企业知识库",
  },
  {
    name: "document-detail",
    path: "/knowledge/product-handbook/documents/release-guide",
    title: "文档预览",
    shell: "user",
    activeNavigation: "企业知识库",
  },
  {
    name: "search",
    path: "/search",
    title: "搜索结果",
    shell: "user",
    activeNavigation: "AI 搜索",
  },
  {
    name: "knowledge-spaces",
    path: "/spaces",
    title: "我的空间",
    shell: "user",
    activeNavigation: "我的空间",
  },
  {
    name: "search-favorites",
    path: "/favorites",
    title: "收藏内容",
    shell: "user",
    activeNavigation: "收藏内容",
  },
  {
    name: "search-settings",
    path: "/settings",
    title: "搜索设置",
    shell: "user",
  },
  {
    name: "downloads",
    path: "/downloads",
    title: "我的下载",
    shell: "user",
    activeNavigation: "我的下载",
  },
  {
    name: "admin-users",
    path: "/admin/users",
    title: "用户管理",
    shell: "admin",
    activeNavigation: "用户与角色",
  },
  {
    name: "admin-departments",
    path: "/admin/departments",
    title: "部门管理",
    shell: "admin",
    activeNavigation: "用户与角色",
  },
  {
    name: "admin-roles",
    path: "/admin/roles",
    title: "角色管理",
    shell: "admin",
    activeNavigation: "用户与角色",
  },
  {
    name: "admin-models",
    path: "/admin/models",
    title: "模型管理",
    shell: "admin",
    activeNavigation: "模型管理",
  },
  {
    name: "admin-knowledge-bases",
    path: "/admin/knowledge-bases",
    title: "知识库管理",
    shell: "admin",
    activeNavigation: "知识库管理",
  },
  {
    name: "admin-documents",
    path: "/admin/documents",
    title: "文档管理",
    shell: "admin",
    activeNavigation: "文档与任务",
  },
  {
    name: "admin-tasks",
    path: "/admin/tasks",
    title: "任务中心",
    shell: "admin",
    activeNavigation: "文档与任务",
  },
  {
    name: "admin-retrieval-tests",
    path: "/admin/retrieval-tests",
    title: "命中率测试",
    shell: "admin",
    activeNavigation: "命中率测试",
  },
  {
    name: "admin-audit-logs",
    path: "/admin/audit-logs",
    title: "审计日志",
    shell: "admin",
    activeNavigation: "审计日志",
  },
];

const getButton = (wrapper: VueWrapper, label: string): DOMWrapper<Element> => {
  const button = wrapper
    .findAll("button")
    .find((candidate) => candidate.text().includes(label));
  if (button === undefined) {
    throw new Error(`未找到按钮：${label}`);
  }
  return button;
};

const getDocumentButton = (label: string): HTMLButtonElement => {
  const normalizedLabel = label.replace(/\s+/g, "");
  const button = Array.from(document.querySelectorAll("button")).find(
    (candidate) =>
      candidate.textContent?.replace(/\s+/g, "").includes(normalizedLabel) ===
      true,
  );
  if (button === undefined) {
    throw new Error(`未找到文档按钮：${label}`);
  }
  return button;
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("M02-M14 本地业务路由", () => {
  it.each(businessRoutes)(
    "$path 渲染统一页面、正确导航且不访问 API",
    async ({ name, path, title, shell, activeNavigation }) => {
      const requestSpy = vi.spyOn(apiClient, "request");
      const { wrapper, router } = await renderAppAt(path);

      expect(router.currentRoute.value.name).toBe(name);
      expect(wrapper.findAll("h1")).toHaveLength(1);
      expect(wrapper.findAll(".business-page")).toHaveLength(1);
      expect(
        wrapper
          .get(
            shell === "user"
              ? ".topbar-breadcrumb strong"
              : ".admin-current-title",
          )
          .text(),
      ).toBe(title);
      if (activeNavigation === undefined) {
        expect(wrapper.find(".sidebar-navigation-item.active").exists()).toBe(
          false,
        );
      } else {
        expect(wrapper.get(".sidebar-navigation-item.active").text()).toBe(
          activeNavigation,
        );
      }
      expect(
        wrapper
          .findAll(".app-sidebar a.sidebar-navigation-item")
          .every((link) => link.attributes("href") !== "#"),
      ).toBe(true);
      expect(requestSpy).not.toHaveBeenCalled();
      expect(localStorage).toHaveLength(0);
      expect(sessionStorage).toHaveLength(0);
    },
  );

  it.each(["/history", "/conversations"])(
    "%s 已删除并返回统一 404 页面",
    async (path) => {
      const { wrapper, router } = await renderAppAt(path);
      expect(router.currentRoute.value.name).toBe("not-found");
      expect(wrapper.text()).toContain("页面不存在");
    },
  );

  it("用户直达模块的侧栏、顶部标题和页面主标题保持一致", async () => {
    const { wrapper, router } = await renderAppAt("/");

    for (const item of userNavigation) {
      await router.push(item.to);
      await flushPromises();

      expect(wrapper.get(".topbar-breadcrumb strong").text()).toBe(item.label);
      if (item.to !== "/") {
        expect(wrapper.get("h1").text()).toBe(item.label);
      }
    }
  });

  it.each([
    { path: "/search", moduleName: "AI 搜索" },
    {
      path: "/knowledge/product-handbook",
      moduleName: "企业知识库",
    },
    {
      path: "/knowledge/product-handbook/documents/release-guide",
      moduleName: "企业知识库",
    },
  ])("$path 的详情上下文归属于 $moduleName", async ({ path, moduleName }) => {
    const { wrapper, router } = await renderAppAt(path);

    expect(router.currentRoute.value.meta.parentTitle).toBe(moduleName);
    expect(wrapper.get(".topbar-breadcrumb span").text()).toBe(moduleName);
    const eyebrow = wrapper.find(".page-eyebrow");
    if (eyebrow.exists()) {
      expect(eyebrow.text()).toContain(moduleName);
    } else {
      expect(wrapper.get("h1").text()).toContain(moduleName);
    }
  });

  it("管理端直达模块及组合导航子模块使用同一名称", async () => {
    const directModules = adminNavigation.flatMap<NavigationChildItem>(
      (item) => {
        if ("children" in item) return item.children;
        return item.to === "/admin" ? [] : [{ label: item.label, to: item.to }];
      },
    );
    const { wrapper, router } = await renderAppAt("/admin/models");

    for (const item of directModules) {
      await router.push(item.to);
      await flushPromises();

      expect(wrapper.get(".admin-current-title").text()).toBe(item.label);
      expect(wrapper.get("h1").text()).toBe(item.label);
    }
  });

  it("桌面与移动完整导航覆盖正式入口并保持可点击", async () => {
    expect(userNavigation.every((item) => item.to !== undefined)).toBe(true);
    expect(adminNavigation.every((item) => item.to !== undefined)).toBe(true);

    const userApp = await renderAppAt("/knowledge");
    await userApp.wrapper.get(".mobile-menu-button").trigger("click");
    expect(
      userApp.wrapper
        .findAll(".mobile-drawer-list a")
        .map((link) => link.attributes("href")),
    ).toEqual(userNavigation.map((item) => item.to));
    await userApp.wrapper
      .get('.mobile-drawer-list a[href="/"]')
      .trigger("click");
    await flushPromises();
    expect(userApp.router.currentRoute.value.path).toBe("/");
    userApp.wrapper.unmount();

    const adminApp = await renderAppAt("/admin/users");
    await adminApp.wrapper.get(".mobile-menu-button").trigger("click");
    const expectedAdminLinks = adminNavigation.flatMap((item) => [
      item.to,
      ...("children" in item ? item.children.map((child) => child.to) : []),
    ]);
    expect(
      adminApp.wrapper
        .findAll(".mobile-drawer-list a")
        .map((link) => link.attributes("href")),
    ).toEqual(expectedAdminLinks);
    await adminApp.wrapper
      .get('.mobile-drawer-list a[href="/admin/roles"]')
      .trigger("click");
    await flushPromises();
    expect(adminApp.router.currentRoute.value.path).toBe("/admin/roles");
  });

  it("M02 个人资料弹窗提供清晰概览与偏好入口且不创建未批准路由", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper, router } = await renderAppAt("/");

    await wrapper.get(".sidebar-profile-trigger").trigger("click");
    await getButton(wrapper, "个人中心").trigger("click");
    await flushPromises();

    const profilePreview = document.body.querySelector(".profile-preview");
    expect(document.body.textContent).toContain("个人资料");
    expect(profilePreview).not.toBeNull();
    expect(profilePreview?.textContent).toContain("已通过统一认证");
    expect(profilePreview?.textContent).toContain("/api/v1/me");
    expect(
      profilePreview?.querySelectorAll(".profile-preview-detail-card"),
    ).toHaveLength(3);
    expect(
      profilePreview?.querySelector(".profile-preview-note strong")
        ?.textContent,
    ).toBe("资料接入说明");
    const preferencesLink = profilePreview?.querySelector<HTMLAnchorElement>(
      '.profile-preview-action[href="/preferences"]',
    );
    expect(preferencesLink).not.toBeNull();
    expect(router.resolve("/profile").name).toBe("not-found");
    expect(requestSpy).not.toHaveBeenCalled();
  });
});

describe("M03-M07 用户页面本地交互", () => {
  it("知识库筛选、文档选择和页码定位只更新本地状态", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const knowledge = await renderAppAt("/knowledge");
    await knowledge.wrapper
      .get('input[placeholder="搜索名称或说明"]')
      .setValue("不存在的知识库");
    expect(knowledge.wrapper.text()).toContain("没有匹配的知识库");
    knowledge.wrapper.unmount();

    const directory = await renderAppAt("/knowledge/product-handbook");
    await directory.wrapper.get('tbody input[type="checkbox"]').setValue(true);
    expect(getButton(directory.wrapper, "导出所选").text()).toContain("1");
    expect(
      getButton(directory.wrapper, "导出所选").attributes("disabled"),
    ).toBe(undefined);
    directory.wrapper.unmount();

    const documentView = await renderAppAt(
      "/knowledge/product-handbook/documents/release-guide?page=8",
    );
    expect(
      documentView.wrapper.get(".page-outline button.active").text(),
    ).toContain("回滚流程");
    documentView.wrapper.unmount();

    const otherDocument = await renderAppAt(
      "/knowledge/product-handbook/documents/quality-gates",
    );
    expect(otherDocument.wrapper.text()).toContain(
      "前端质量门禁清单正文尚未加入固定样例",
    );
    expect(otherDocument.wrapper.text()).not.toContain("发布目标");
    otherDocument.wrapper.unmount();

    const unrelatedDirectory = await renderAppAt(
      "/knowledge/engineering-playbook",
    );
    expect(unrelatedDirectory.wrapper.text()).toContain("没有匹配的文档");
    expect(unrelatedDirectory.wrapper.text()).not.toContain(
      "统一发布流程与回滚指南.md",
    );
    unrelatedDirectory.wrapper.unmount();

    const mismatchedDocument = await renderAppAt(
      "/knowledge/engineering-playbook/documents/release-guide",
    );
    expect(mismatchedDocument.wrapper.text()).toContain("此知识库中未找到文档");
    expect(mismatchedDocument.wrapper.text()).not.toContain("发布目标");
    expect(
      mismatchedDocument.wrapper
        .findAll("button")
        .some((button) => button.text().includes("导出文档")),
    ).toBe(false);
    mismatchedDocument.wrapper.unmount();

    const missingParent = await renderAppAt(
      "/knowledge/not-real/documents/release-guide",
    );
    expect(missingParent.wrapper.text()).toContain("未找到知识库");
    expect(missingParent.wrapper.text()).not.toContain("发布目标");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("AI 搜索保留查询参数、切换结果视图且空问题不会访问业务 API", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const home = await renderAppAt("/");
    await home.wrapper.get("#global-search-input").setValue("回滚");
    await home.wrapper
      .get("#global-search-input")
      .trigger("keydown", { key: "Enter" });
    await flushPromises();
    expect(home.router.currentRoute.value.path).toBe("/search");
    expect(home.router.currentRoute.value.query.q).toBe("回滚");
    expect(
      (home.wrapper.get("#ai-search-query").element as HTMLTextAreaElement)
        .value,
    ).toBe("回滚");
    home.wrapper.unmount();

    const { wrapper } = await renderAppAt("/search?q=发布");
    await vi.waitFor(() => {
      expect(wrapper.find(".result-tabs").exists()).toBe(true);
    });

    expect(wrapper.find('select[title="选择搜索模式"]').exists()).toBe(false);
    const query = wrapper.get("#ai-search-query");
    await query.setValue("复盘");
    await wrapper.get("form.ai-search-box").trigger("submit");
    await flushPromises();
    await vi.waitFor(() => {
      expect(wrapper.find(".result-tabs").exists()).toBe(true);
      expect(wrapper.text()).toContain("本地模拟，无真实耗时");
    });

    await getButton(wrapper, "原始结果").trigger("click");
    expect(wrapper.findAll(".source-result-item")).toHaveLength(3);
    await wrapper
      .get('input[placeholder="在结果中搜索"]')
      .setValue("不存在的结果");
    expect(wrapper.findAll(".source-result-item")).toHaveLength(0);
    expect(wrapper.text()).toContain("没有符合条件的结果");

    await query.setValue("");
    await wrapper.get("form.ai-search-box").trigger("submit");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("收藏单条删除使用模态弹窗，取消不会误删", async () => {
    const favorites = await renderAppAt("/favorites");
    const favoriteTitle = favorites.wrapper.get(".favorite-copy h2").text();

    await favorites.wrapper
      .get('button[aria-label^="删除收藏"]')
      .trigger("click");
    await flushPromises();
    expect(document.querySelector(".ant-modal-confirm")).not.toBeNull();
    expect(favorites.wrapper.find(".delete-confirmation").exists()).toBe(false);
    expect(document.body.textContent).toContain("确认删除这条收藏？");
    getDocumentButton("取消").click();
    await flushPromises();
    expect(favorites.wrapper.text()).toContain(favoriteTitle);

    await favorites.wrapper
      .get('button[aria-label^="删除收藏"]')
      .trigger("click");
    await flushPromises();
    getDocumentButton("确认删除").click();
    await flushPromises();
    expect(favorites.wrapper.text()).not.toContain(favoriteTitle);
  });

  it("下载筛选和删除确认只影响当前页面", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const downloads = await renderAppAt("/downloads");
    await downloads.wrapper
      .get('input[placeholder="搜索文件名或格式"]')
      .setValue("统一发布流程");
    expect(downloads.wrapper.findAll("tbody tr")).toHaveLength(1);
    expect(downloads.wrapper.get("progress").attributes("aria-label")).toBe(
      "统一发布流程与回滚指南.pdf导出进度 100%",
    );
    await downloads.wrapper
      .get('button[aria-label^="删除统一发布流程"]')
      .trigger("click");
    await flushPromises();
    expect(document.querySelector(".ant-modal-confirm")).not.toBeNull();
    expect(downloads.wrapper.find(".delete-confirmation").exists()).toBe(false);
    getDocumentButton("确认删除").click();
    await flushPromises();
    expect(downloads.wrapper.text()).toContain("没有匹配的导出任务");
    expect(requestSpy).not.toHaveBeenCalled();
  });
});

describe("M09-M14 管理页面真实 API 渲染", () => {
  it("用户和角色页面使用 API 数据并提供真实编辑入口", async () => {
    const users = await renderAppAt("/admin/users");
    await flushPromises();
    expect(users.wrapper.text()).toContain("admin");
    expect(users.wrapper.text()).toContain("liuhaiwang");
    await users.wrapper
      .get('input[placeholder="账号 ID、姓名或角色"]')
      .setValue("不存在的用户");
    expect(users.wrapper.text()).toContain("没有匹配的用户");
    await users.wrapper
      .get('input[placeholder="账号 ID、姓名或角色"]')
      .setValue("");
    await getButton(users.wrapper, "编辑").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain("编辑用户");
    users.wrapper.unmount();

    const roles = await renderAppAt("/admin/roles");
    await flushPromises();
    expect(roles.wrapper.text()).toContain("超级管理员");
    await roles.wrapper
      .get('input[placeholder="角色名称、说明或状态"]')
      .setValue("不存在的角色");
    expect(roles.wrapper.text()).toContain("没有匹配的角色");
    await roles.wrapper
      .get('input[placeholder="角色名称、说明或状态"]')
      .setValue("");
    await getButton(roles.wrapper, "编辑授权").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain("角色授权");
  });

  it("新增模型后持久展示配置且不泄露密钥", async () => {
    const { wrapper } = await renderAppAt("/admin/models");
    await flushPromises();

    await getButton(wrapper, "新增模型").trigger("click");
    await flushPromises();
    const modelName = document.querySelector<HTMLInputElement>(
      "#model-name-input",
    );
    const credential = document.querySelector<HTMLInputElement>(
      'input[autocomplete="new-password"]',
    );
    expect(modelName).not.toBeNull();
    expect(credential).not.toBeNull();
    if (modelName === null || credential === null) return;

    modelName.value = "deepseek-reasoner";
    modelName.dispatchEvent(new Event("input", { bubbles: true }));
    credential.value = "local-secret-placeholder";
    credential.dispatchEvent(new Event("input", { bubbles: true }));
    getDocumentButton("保存配置").click();
    await flushPromises();

    expect(wrapper.text()).toContain("deepseek-reasoner");
    expect(document.body.textContent).not.toContain("local-secret-placeholder");
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });

  it("模型密钥默认空、关闭即清空且不写入浏览器存储", async () => {
    const { wrapper } = await renderAppAt("/admin/models");
    await flushPromises();

    await getButton(wrapper, "配置").trigger("click");
    await flushPromises();
    const credential = document.querySelector<HTMLInputElement>(
      'input[autocomplete="new-password"]',
    );
    expect(credential).not.toBeNull();
    if (credential === null) return;

    expect(credential.value).toBe("");
    credential.value = "local-secret-placeholder";
    credential.dispatchEvent(new Event("input", { bubbles: true }));
    getDocumentButton("取消并清空密钥").click();
    await flushPromises();
    await getButton(wrapper, "配置").trigger("click");
    await flushPromises();

    expect(
      Array.from(
        document.querySelectorAll<HTMLInputElement>(
          'input[autocomplete="new-password"]',
        ),
      ).at(-1)?.value,
    ).toBe("");
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });

  it("知识库、文档和任务页面展示 API 返回的真实状态", async () => {
    const knowledgeBases = await renderAppAt("/admin/knowledge-bases");
    await flushPromises();
    expect(knowledgeBases.wrapper.text()).toContain("默认知识库");
    expect(knowledgeBases.wrapper.text()).toContain("医疗信息化知识库");
    knowledgeBases.wrapper.unmount();

    const documents = await renderAppAt("/admin/documents");
    await flushPromises();
    expect(documents.wrapper.text()).toContain("医疗信息化IT系统分析文档");
    expect(documents.wrapper.text()).toContain("服务降级复盘模板");
    await getButton(documents.wrapper, "详情").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain("文档详情");
    documents.wrapper.unmount();

    const tasks = await renderAppAt("/admin/tasks");
    await flushPromises();
    expect(tasks.wrapper.get("progress").attributes("aria-label")).toContain(
      "处理进度",
    );
    expect(tasks.wrapper.text()).toContain("转换失败");
  });

  it("命中率测试读取真实测试集和运行记录", async () => {
    const { wrapper } = await renderAppAt("/admin/retrieval-tests");
    await flushPromises();

    expect(wrapper.text()).toContain("医疗信息化验收测试集");
    expect(wrapper.text()).toContain("run-1");
    await wrapper.get(".retrieval-form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("真实测试记录");
    await getButton(wrapper, "查看结果").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("命中率（Hit Rate）");
    expect(wrapper.text()).toContain("平均倒数排名（MRR）");
    expect(wrapper.text()).toContain("是否命中（Hit）");
  });

  it("审计日志使用 API 数据并掩码网络标识", async () => {
    const { wrapper } = await renderAppAt("/admin/audit-logs");
    await flushPromises();
    const maskedRequestIds = wrapper
      .findAll("tbody tr")
      .map((row) => row.findAll("td")[4]?.text());
    expect(new Set(maskedRequestIds).size).toBe(4);
    expect(
      maskedRequestIds.every((value) =>
        /^demo-r\*\*\*\*[0-9a-f]{4}$/u.test(value ?? ""),
      ),
    ).toBe(true);

    await wrapper.findAll(".filter-bar select").at(0)?.setValue("失败");
    expect(wrapper.findAll("tbody tr")).toHaveLength(1);
    await getButton(wrapper, "查看详情").trigger("click");
    await flushPromises();

    expect(document.body.textContent).toContain("审计详情");
    expect(document.body.textContent).toContain("203.0.113.xxx");
    expect(document.body.textContent).not.toContain("203.0.113.10");
  });
});
