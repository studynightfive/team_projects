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
  readonly activeNavigation: string;
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
    name: "deep-research",
    path: "/research",
    title: "深度研究",
    shell: "user",
    activeNavigation: "深度研究",
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
    name: "search-history",
    path: "/history",
    title: "搜索历史",
    shell: "user",
    activeNavigation: "搜索历史",
  },
  {
    name: "data-sources",
    path: "/data-sources",
    title: "数据源",
    shell: "user",
    activeNavigation: "数据源",
  },
  {
    name: "search-settings",
    path: "/settings",
    title: "搜索设置",
    shell: "user",
    activeNavigation: "搜索设置",
  },
  {
    name: "chat-new",
    path: "/chat",
    title: "AI 助手",
    shell: "user",
    activeNavigation: "AI 助手",
  },
  {
    name: "chat-detail",
    path: "/chat/conv-release-review",
    title: "会话详情",
    shell: "user",
    activeNavigation: "AI 助手",
  },
  {
    name: "conversations",
    path: "/conversations",
    title: "历史会话",
    shell: "user",
    activeNavigation: "历史会话",
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
      expect(wrapper.get(".sidebar-navigation-item.active").text()).toBe(
        activeNavigation,
      );
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
    {
      path: "/chat/conv-release-review",
      moduleName: "AI 助手",
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

  it("M02 个人资料保留在账号菜单且不创建未批准路由", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper, router } = await renderAppAt("/");

    await wrapper.get(".sidebar-profile-trigger").trigger("click");
    await getButton(wrapper, "个人中心").trigger("click");
    await flushPromises();

    expect(document.body.textContent).toContain("个人资料");
    expect(document.body.textContent).toContain("等待认证服务接入");
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

    await wrapper.get('select[title="选择搜索模式"]').setValue("precise");
    const query = wrapper.get("#ai-search-query");
    await query.setValue("复盘");
    await wrapper.get("form.ai-search-box").trigger("submit");
    await flushPromises();
    await vi.waitFor(() => {
      expect(wrapper.find(".result-tabs").exists()).toBe(true);
      expect(wrapper.text()).toContain("本地模拟，无真实耗时");
    });

    expect(
      wrapper.find<HTMLSelectElement>('select[title="选择搜索模式"]').element
        .value,
    ).toBe("precise");

    await getButton(wrapper, "原始结果").trigger("click");
    expect(wrapper.findAll(".source-result-item")).toHaveLength(10);
    await wrapper
      .get('input[placeholder="在结果中搜索"]')
      .setValue("不存在的结果");
    expect(wrapper.findAll(".source-result-item")).toHaveLength(0);
    expect(wrapper.text()).toContain("没有符合条件的结果");

    await query.setValue("");
    await wrapper.get("form.ai-search-box").trigger("submit");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("搜索历史重置关键词并在确认后批量删除当前筛选结果", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const history = await renderAppAt("/history");
    const searchInput = history.wrapper.get(
      'input[placeholder="搜索问题或来源"]',
    );

    await searchInput.setValue("差旅报销");
    expect(history.wrapper.findAll(".history-list article")).toHaveLength(1);
    await getButton(history.wrapper, "重置搜索").trigger("click");
    expect((searchInput.element as HTMLInputElement).value).toBe("");
    expect(history.wrapper.findAll(".history-list article")).toHaveLength(8);

    await searchInput.setValue("差旅报销");
    await getButton(history.wrapper, "批量删除当前筛选结果").trigger("click");
    await flushPromises();
    expect(document.querySelector(".ant-modal-confirm")).not.toBeNull();
    expect(history.wrapper.find(".delete-confirmation").exists()).toBe(false);
    expect(document.body.textContent).toContain("确认批量删除 1 条筛选结果？");
    getDocumentButton("确认批量删除").click();
    await flushPromises();
    expect(history.wrapper.text()).toContain("没有符合条件的搜索记录");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("收藏与搜索历史单条删除使用模态弹窗，取消不会误删", async () => {
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
    favorites.wrapper.unmount();

    const history = await renderAppAt("/history");
    await history.wrapper.get('button[aria-label^="删除"]').trigger("click");
    await flushPromises();
    expect(document.querySelector(".ant-modal-confirm")).not.toBeNull();
    expect(history.wrapper.find(".delete-confirmation").exists()).toBe(false);
    expect(document.body.textContent).toContain("确认删除这条搜索记录？");
    getDocumentButton("取消").click();
    await flushPromises();
  });

  it("新问答逐段展示、停止和历史引用均不启动网络请求", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const chat = await renderAppAt("/chat");
    const promptInput = chat.wrapper.get("#chat-prompt");

    expect(chat.wrapper.findAll(".suggested-prompt")).toHaveLength(3);
    await chat.wrapper.findAll(".suggested-prompt")[0]?.trigger("click");
    expect((promptInput.element as HTMLTextAreaElement).value).toBe(
      "发布上线前需要检查哪些内容？",
    );
    await promptInput.setValue("如何准备发布？");
    await promptInput.trigger("keydown", { key: "Enter", shiftKey: true });
    expect(chat.wrapper.findAll(".message")).toHaveLength(0);
    await promptInput.trigger("keydown", { key: "Enter" });
    expect(chat.wrapper.text()).toContain("如何准备发布？");
    expect(chat.wrapper.get(".preview-status").text()).toBe("正在逐段展示");
    await getButton(chat.wrapper, "停止生成").trigger("click");
    expect(chat.wrapper.get(".preview-status").text()).toBe("已停止本地预览");
    chat.wrapper.unmount();

    const history = await renderAppAt("/chat/conv-release-review");
    expect(history.wrapper.findAll(".message")).toHaveLength(2);
    expect(history.wrapper.get(".citation-card").attributes("href")).toContain(
      "/knowledge/product-handbook/documents/release-guide",
    );
    expect(
      history.wrapper.find(".citation-card .lucide-arrow-up-right").exists(),
    ).toBe(false);
    expect(
      history.wrapper.find(".citation-card .lucide-chevron-right").exists(),
    ).toBe(true);
    history.wrapper.unmount();

    const missing = await renderAppAt("/chat/missing-conversation");
    expect(missing.wrapper.get("h1").text()).toBe("会话不存在");
    expect(missing.wrapper.text()).toContain("未找到这条会话");
    expect(missing.wrapper.find("form.composer").exists()).toBe(false);
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("会话重命名、删除确认和下载筛选只影响当前页面", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const conversations = await renderAppAt("/conversations");
    await getButton(conversations.wrapper, "重命名").trigger("click");
    await conversations.wrapper.get(".title-editor").setValue("本地会话名称");
    await getButton(conversations.wrapper, "保存本地名称").trigger("click");
    expect(conversations.wrapper.text()).toContain("本地会话名称");
    await conversations.wrapper
      .get('button[aria-label^="删除本地会话名称"]')
      .trigger("click");
    await flushPromises();
    expect(document.querySelector(".ant-modal-confirm")).not.toBeNull();
    expect(conversations.wrapper.find(".delete-confirmation").exists()).toBe(
      false,
    );
    getDocumentButton("确认删除").click();
    await flushPromises();
    expect(conversations.wrapper.text()).not.toContain("本地会话名称");
    conversations.wrapper.unmount();

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

describe("M09-M14 管理页面本地交互", () => {
  it("用户和角色筛选提供空状态与本地编辑入口", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const users = await renderAppAt("/admin/users");
    await users.wrapper
      .get('input[placeholder="姓名、邮箱、部门或角色"]')
      .setValue("不存在的用户");
    expect(users.wrapper.text()).toContain("没有匹配的用户");
    await users.wrapper
      .get('input[placeholder="姓名、邮箱、部门或角色"]')
      .setValue("");
    await getButton(users.wrapper, "编辑").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain("编辑用户（本地预览）");
    users.wrapper.unmount();

    const roles = await renderAppAt("/admin/roles");
    await roles.wrapper
      .get('input[placeholder="角色名称、说明或授权范围"]')
      .setValue("不存在的角色");
    expect(roles.wrapper.text()).toContain("没有匹配的角色");
    await roles.wrapper
      .get('input[placeholder="角色名称、说明或授权范围"]')
      .setValue("");
    await getButton(roles.wrapper, "编辑授权预览").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain("角色授权（本地预览）");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("模型密钥默认空、关闭即清空且不写入浏览器存储", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/admin/models");

    await getButton(wrapper, "配置").trigger("click");
    await flushPromises();
    const credential = document.querySelector<HTMLInputElement>(
      'input[autocomplete="new-password"]',
    );
    expect(credential).not.toBeNull();
    if (credential === null) return;

    expect(credential.value).toBe("");
    credential.value = "local-preview-placeholder";
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
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("知识库归档与文档、任务状态逐条更新且不提交服务端", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const knowledgeBases = await renderAppAt("/admin/knowledge-bases");
    await getButton(knowledgeBases.wrapper, "归档").trigger("click");
    expect(knowledgeBases.wrapper.get("tbody tr .status-chip").text()).toBe(
      "归档中",
    );
    knowledgeBases.wrapper.unmount();

    const documents = await renderAppAt("/admin/documents");
    await getButton(documents.wrapper, "重试").trigger("click");
    const retriedDocument = documents.wrapper
      .findAll("tbody tr")
      .find((row) => row.text().includes("服务降级复盘模板"));
    expect(retriedDocument?.text()).toContain("处理中");
    expect(
      documents.wrapper
        .findAll("tbody tr")
        .find((row) => row.text().includes("统一发布流程与回滚指南"))
        ?.text(),
    ).not.toContain("重试");
    await getButton(documents.wrapper, "预览").trigger("click");
    await flushPromises();
    expect(document.body.textContent).toContain("文档详情（本地预览）");
    documents.wrapper.unmount();

    const tasks = await renderAppAt("/admin/tasks");
    expect(tasks.wrapper.get("progress").attributes("aria-label")).toContain(
      "处理进度",
    );
    await getButton(tasks.wrapper, "重试").trigger("click");
    const retriedTask = tasks.wrapper
      .findAll("tbody tr")
      .find((row) => row.text().includes("服务降级复盘模板"));
    expect(retriedTask?.text()).toContain("处理中");
    expect(retriedTask?.text()).toContain("已重新进入处理队列");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("命中率测试保留参数并生成固定本地结果", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/admin/retrieval-tests");

    await wrapper.findAll(".retrieval-form select").at(0)?.setValue("向量");
    await wrapper.get(".retrieval-form").trigger("submit");

    expect(wrapper.findAll(".retrieval-results li")).toHaveLength(3);
    expect(wrapper.text()).toContain("向量模式 · TopK 8");
    expect(wrapper.text()).toContain("demo-retrieval-preview");

    await wrapper.get<HTMLInputElement>('input[type="number"]').setValue(1);
    expect(wrapper.findAll(".retrieval-results li")).toHaveLength(1);

    await wrapper.get<HTMLInputElement>('input[type="number"]').setValue(8);
    await wrapper
      .findAll(".retrieval-form select")
      .at(2)
      ?.setValue("quality-gates");
    await wrapper.get<HTMLInputElement>('input[type="range"]').setValue(0.9);
    expect(wrapper.findAll(".retrieval-results li")).toHaveLength(1);
    expect(wrapper.get(".retrieval-results li").text()).toContain(
      "前端质量门禁清单",
    );

    await wrapper.get<HTMLInputElement>('input[type="range"]').setValue(1);
    expect(wrapper.findAll(".retrieval-results li")).toHaveLength(0);
    expect(wrapper.text()).toContain("没有命中当前参数的固定结果");

    await wrapper
      .findAll(".retrieval-form select")
      .at(1)
      ?.setValue("engineering-playbook");
    await flushPromises();
    expect(wrapper.findAll(".retrieval-results li")).toHaveLength(0);
    expect(wrapper.text()).not.toContain("统一发布流程与回滚指南");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("审计筛选与详情只展示掩码后的示例标识", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/admin/audit-logs");
    const maskedRequestIds = wrapper
      .findAll("tbody tr")
      .map((row) => row.findAll("td")[4]?.text());
    expect(new Set(maskedRequestIds).size).toBe(4);
    expect(
      maskedRequestIds.every((value) =>
        /^demo-req-\*\*[0-9a-f]{2}$/u.test(value ?? ""),
      ),
    ).toBe(true);

    await wrapper.findAll(".filter-bar select").at(1)?.setValue("失败");
    expect(wrapper.findAll("tbody tr")).toHaveLength(1);
    await getButton(wrapper, "查看详情").trigger("click");
    await flushPromises();

    expect(document.body.textContent).toContain("审计详情（只读）");
    expect(document.body.textContent).toContain("demo-req-**82");
    expect(document.body.textContent).toContain("203.0.113.xxx");
    expect(document.body.textContent).not.toContain("demo-req-4a82");
    expect(document.body.textContent).not.toContain("203.0.113.9");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("编辑固定样例会保留多角色、完整权限与原知识库参数", async () => {
    const users = await renderAppAt("/admin/users");
    const multiRoleUser = users.wrapper
      .findAll("tbody tr")
      .find((row) => row.text().includes("周予安"));
    await multiRoleUser?.get("button").trigger("click");
    await flushPromises();
    getDocumentButton("保存本地预览").click();
    await flushPromises();
    expect(
      users.wrapper
        .findAll("tbody tr")
        .find((row) => row.text().includes("周予安"))
        ?.text(),
    ).toContain("平台管理员、知识库编辑者");
    users.wrapper.unmount();

    const roles = await renderAppAt("/admin/roles");
    await getButton(roles.wrapper, "编辑授权预览").trigger("click");
    await flushPromises();
    expect(
      document.querySelectorAll(
        '.checkbox-list input[type="checkbox"]:checked',
      ),
    ).toHaveLength(18);
    getDocumentButton("保存本地预览").click();
    await flushPromises();
    expect(roles.wrapper.get(".role-card").text()).toContain("18");
    roles.wrapper.unmount();

    const knowledgeBases = await renderAppAt("/admin/knowledge-bases");
    const researchBase = knowledgeBases.wrapper
      .findAll("tbody tr")
      .find((row) => row.text().includes("研发效能手册"));
    await researchBase?.get("button").trigger("click");
    await flushPromises();
    const parameters = Array.from(
      document.querySelectorAll<HTMLInputElement>(
        '.ant-drawer input[type="number"]',
      ),
    );
    expect(parameters.map((input) => input.value)).toEqual(["10", "0.58"]);
    const thresholdInput = parameters[1];
    if (thresholdInput === undefined) {
      throw new Error("未找到知识库阈值输入框");
    }
    thresholdInput.value = "";
    thresholdInput.dispatchEvent(new Event("input", { bubbles: true }));
    document
      .querySelector<HTMLFormElement>(".ant-drawer form.drawer-form")
      ?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await flushPromises();
    expect(document.body.textContent).toContain("知识库配置（本地预览）");
    thresholdInput.value = "0.58";
    thresholdInput.dispatchEvent(new Event("input", { bubbles: true }));
    const adminAuthorization = document.querySelector<HTMLInputElement>(
      '.ant-drawer input[value="平台管理员"]',
    );
    adminAuthorization?.click();
    getDocumentButton("保存本地预览").click();
    await flushPromises();
    await researchBase?.get("button").trigger("click");
    await flushPromises();
    expect(
      document.querySelector<HTMLInputElement>(
        '.ant-drawer input[value="平台管理员"]',
      )?.checked,
    ).toBe(true);
  });
});
