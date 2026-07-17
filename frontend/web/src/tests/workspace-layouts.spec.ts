import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { apiClient } from "../api/client";
import {
  adminNavigation,
  serviceStatusTone,
  userMobileNavigation,
  userNavigation,
} from "../data/foundation";
import { renderAppAt } from "./renderApp";

describe("M01 V2 工作区布局", () => {
  it("普通用户布局呈现完整导航与 AI 搜索工作台", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/");
    await vi.waitFor(() => {
      expect(wrapper.get("h1").text()).toBe("今天想查找什么？");
    });
    const navigationLabels = wrapper
      .findAll(".app-sidebar .sidebar-navigation-item")
      .map((item) => item.text().trim());

    expect(navigationLabels).toEqual(userNavigation.map((item) => item.label));
    expect(navigationLabels.slice(0, 2)).toEqual(["AI 搜索", "AI 助手"]);
    expect(userMobileNavigation.map((item) => item.shortLabel)).toEqual([
      "搜索",
      "知识库",
      "历史",
      "助手",
    ]);
    expect(navigationLabels).not.toContain("搜索设置");
    await wrapper.get(".sidebar-profile-trigger").trigger("click");
    expect(
      wrapper.get('.sidebar-profile-menu a[href="/settings"]').text(),
    ).toBe("搜索设置");
    expect(wrapper.get('.topbar-workspace-link[href="/admin"]').text()).toBe(
      "管理中心",
    );
    expect(wrapper.findAll("h1")).toHaveLength(1);
    expect(wrapper.find("header.workspace-topbar").exists()).toBe(true);
    expect(wrapper.find("main.workspace-content").exists()).toBe(true);
    expect(wrapper.findAll(".search-suggestion-list button")).toHaveLength(6);
    expect(wrapper.findAll(".quick-action-list button")).toHaveLength(5);
    expect(wrapper.findAll(".recent-search-list button")).toHaveLength(4);
    expect(wrapper.findAll(".knowledge-space-list a")).toHaveLength(3);
    expect(wrapper.findAll(".data-source-summary-list article")).toHaveLength(
      4,
    );
    expect(wrapper.text()).toContain("企业知识中心");
    expect(wrapper.text()).toContain("模拟数据");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("管理布局呈现七项导航、四条趋势与审计表", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/admin");
    const navigationLabels = wrapper
      .findAll(".app-sidebar .sidebar-navigation-item")
      .map((item) => item.text().trim());

    expect(navigationLabels).toEqual(adminNavigation.map((item) => item.label));
    expect(wrapper.get('.admin-topbar-actions a[href="/"]').text()).toBe(
      "返回用户工作区",
    );
    expect(wrapper.findAll("h1")).toHaveLength(1);
    expect(wrapper.findAll(".admin-stat-grid .stat-card")).toHaveLength(4);
    expect(wrapper.findAll(".admin-stat-grid .sparkline")).toHaveLength(4);
    expect(wrapper.findAll(".sparkline-point")).toHaveLength(28);
    expect(wrapper.findAll(".service-row")).toHaveLength(3);
    expect(wrapper.findAll(".service-row .status-badge.success")).toHaveLength(
      3,
    );
    expect(serviceStatusTone).toEqual({
      运行正常: "success",
      降级: "warning",
      异常: "failed",
    });
    expect(wrapper.findAll(".governance-row")).toHaveLength(3);
    expect(wrapper.findAll(".audit-table tbody tr")).toHaveLength(4);
    expect(wrapper.text()).toContain("运行正常");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("侧边栏可折叠并保留明确的 ARIA 状态", async () => {
    const { wrapper } = await renderAppAt("/");
    const toggle = wrapper.get(".sidebar-collapse-button");

    expect(toggle.attributes("aria-expanded")).toBe("true");
    await toggle.trigger("click");

    expect(wrapper.get(".workspace-shell").classes()).toContain(
      "sidebar-collapsed",
    );
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(toggle.attributes("aria-label")).toBe("展开侧边栏");
    expect(
      wrapper.get(".sidebar-navigation-item").attributes("aria-label"),
    ).toBe("AI 搜索");
    expect(
      wrapper.get(".sidebar-profile-trigger").attributes("aria-label"),
    ).toBe("李明");
  });

  it("账号按钮组按 Escape 关闭并把焦点还给触发按钮", async () => {
    const { wrapper } = await renderAppAt("/");
    const trigger = wrapper.get(".sidebar-profile-trigger");

    await trigger.trigger("click");
    const action = wrapper.get(".sidebar-profile-menu button");
    (action.element as HTMLButtonElement).focus();

    await action.trigger("keydown", { key: "Escape" });
    await nextTick();

    expect(wrapper.find(".sidebar-profile-menu").exists()).toBe(false);
    expect(document.activeElement).toBe(trigger.element);
  });

  it("账号菜单点击内部保持打开，点击外部区域关闭", async () => {
    const { wrapper } = await renderAppAt("/");

    await wrapper.get(".sidebar-profile-trigger").trigger("click");
    await wrapper.get(".sidebar-profile-menu").trigger("click");
    expect(wrapper.find(".sidebar-profile-menu").exists()).toBe(true);

    await wrapper.get("main.workspace-content").trigger("click");
    expect(wrapper.find(".sidebar-profile-menu").exists()).toBe(false);
  });
});
