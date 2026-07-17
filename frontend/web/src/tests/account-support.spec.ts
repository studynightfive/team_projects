import { flushPromises, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";
import { renderAppAt } from "./renderApp";

const getButton = (wrapper: VueWrapper, label: string) => {
  const button = wrapper
    .findAll("button")
    .find((candidate) => candidate.text().trim() === label);
  if (button === undefined) throw new Error(`未找到按钮：${label}`);
  return button;
};

describe("账号与支持页面", () => {
  it.each([
    ["/notifications", "user-notifications", "通知中心", "user"],
    ["/help", "help-center", "帮助中心", "user"],
    ["/preferences", "account-preferences", "偏好设置", "user"],
    ["/admin/notifications", "admin-notifications", "通知中心", "admin"],
  ] as const)(
    "%s 使用正确路由、标题和工作区壳层",
    async (path, routeName, title, shell) => {
      const requestSpy = vi.spyOn(apiClient, "request");
      const { wrapper, router } = await renderAppAt(path);

      expect(router.currentRoute.value.name).toBe(routeName);
      expect(wrapper.get("h1").text()).toBe(title);
      expect(wrapper.find(".business-page").exists()).toBe(true);
      expect(wrapper.find(`#${shell}-view`).exists()).toBe(true);
      expect(wrapper.get(".workspace-topbar").text()).toContain(title);
      expect(requestSpy).not.toHaveBeenCalled();
    },
  );

  it("现有顶栏、通知预览和账号菜单进入对应用户页面", async () => {
    const { wrapper } = await renderAppAt("/");

    expect(
      wrapper
        .get('.notification-button[href="/notifications"]')
        .attributes("aria-label"),
    ).toContain("3 条未读消息");
    expect(
      wrapper.get('.help-button[href="/help"]').attributes("aria-label"),
    ).toBe("查看帮助");
    expect(wrapper.findAll(".notification-preview-item")).toHaveLength(4);
    expect(wrapper.get(".notification-preview-header").text()).toContain(
      "3 条未读",
    );
    expect(
      wrapper.get('.notification-preview-item[href="/downloads"]').text(),
    ).toContain("《发布流程手册》导出已完成");
    expect(
      wrapper.get('.notification-preview-footer[href="/notifications"]'),
    ).toBeDefined();

    await wrapper
      .get('.notification-preview-item[href="/downloads"]')
      .trigger("click");
    await flushPromises();
    expect(wrapper.get(".notification-button").attributes("aria-label")).toBe(
      "查看通知，当前有 2 条未读消息",
    );

    await wrapper.get(".sidebar-profile-trigger").trigger("click");
    expect(
      wrapper.get('.sidebar-profile-menu a[href="/preferences"]').text(),
    ).toBe("偏好设置");
  });

  it("通知筛选和已读操作同步更新用户顶栏计数", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/notifications");

    expect(wrapper.findAll(".notification-list article")).toHaveLength(5);
    expect(wrapper.get(".local-preview-badge").text()).toContain("3 条未读");

    await getButton(wrapper, "未读").trigger("click");
    expect(wrapper.findAll(".notification-list article")).toHaveLength(3);

    await getButton(wrapper, "全部标为已读").trigger("click");
    expect(wrapper.find(".notification-list").exists()).toBe(false);
    expect(wrapper.get(".inline-state").text()).toContain("没有符合条件的通知");
    expect(wrapper.get(".notification-button").attributes("aria-label")).toBe(
      "查看通知，当前没有未读消息",
    );
    expect(wrapper.find(".notification-dot").exists()).toBe(false);
    expect(requestSpy).not.toHaveBeenCalled();
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });

  it("管理通知使用独立的六条未读固定样例", async () => {
    const { wrapper } = await renderAppAt("/admin/notifications");

    expect(wrapper.findAll(".notification-list article")).toHaveLength(6);
    expect(wrapper.get(".local-preview-badge").text()).toContain("6 条未读");
    expect(wrapper.get(".notification-button").attributes("href")).toBe(
      "/admin/notifications",
    );
    expect(wrapper.findAll(".notification-preview-item")).toHaveLength(4);
    expect(wrapper.get(".notification-preview-header").text()).toContain(
      "6 条未读",
    );
    expect(
      wrapper.get('.notification-preview-item[href="/admin/tasks"]').text(),
    ).toContain("2 个文档处理任务需要复核");

    await wrapper.get(".notification-list .text-button").trigger("click");
    expect(wrapper.get(".local-preview-badge").text()).toContain("5 条未读");
  });

  it("帮助中心按关键词和分类筛选原生折叠问答", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/help");

    expect(wrapper.findAll(".faq-list details")).toHaveLength(8);
    await wrapper
      .get<HTMLInputElement>(".help-search-field input")
      .setValue("令牌");
    expect(wrapper.findAll(".faq-list details")).toHaveLength(1);
    expect(wrapper.get(".faq-list").text()).toContain(
      "前端会把登录令牌保存在哪里",
    );

    await wrapper
      .get<HTMLSelectElement>(".help-category-field select")
      .setValue("知识与文档");
    expect(wrapper.find(".faq-list").exists()).toBe(false);
    expect(wrapper.get(".inline-state").text()).toContain("没有找到相关帮助");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("偏好可在当前页面保存并恢复默认且不写浏览器存储", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/preferences");
    const workspaceSelect = wrapper.findAll<HTMLSelectElement>(
      ".preference-fields select",
    )[0];
    if (workspaceSelect === undefined) throw new Error("未找到默认工作入口");

    await workspaceSelect.setValue("knowledge");
    expect(wrapper.get(".preferences-summary").text()).toContain("企业知识库");
    expect(
      getButton(wrapper, "保存本地偏好").attributes("disabled"),
    ).toBeUndefined();

    await wrapper.get("form").trigger("submit");
    expect(
      getButton(wrapper, "偏好已保存").attributes("disabled"),
    ).toBeDefined();
    expect(wrapper.get(".preference-status").text()).toContain("当前页面保存");

    await getButton(wrapper, "恢复默认").trigger("click");
    await getButton(wrapper, "确认恢复").trigger("click");
    await flushPromises();
    expect(wrapper.get(".preferences-summary").text()).toContain("AI 搜索");
    expect(wrapper.get(".preference-status").text()).toContain("恢复默认偏好");
    expect(requestSpy).not.toHaveBeenCalled();
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });
});
