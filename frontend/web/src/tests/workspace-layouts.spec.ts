import { describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";
import { adminNavigation, userNavigation } from "../data/foundation";
import { renderAppAt } from "./renderApp";

describe("M01 工作区布局", () => {
  it("普通用户布局严格呈现六项导航和 design-only 数据", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/");
    const navigationLabels = wrapper
      .findAll(".sidebar .nav-item")
      .map((item) => item.text().replace(/^./u, "").trim());

    expect(navigationLabels).toEqual(userNavigation.map((item) => item.label));
    expect(wrapper.get('.topbar a[href="/admin"]').text()).toBe("管理中心");
    expect(wrapper.findAll("h1")).toHaveLength(1);
    expect(wrapper.find("header.topbar").exists()).toBe(true);
    expect(wrapper.find("main.content").exists()).toBe(true);
    expect(wrapper.text()).toContain("产品需求资料库");
    expect(wrapper.text()).toContain("知识库使用指南.md");
    expect(
      wrapper
        .get('.document-name[title="检索质量检查清单.pdf"]')
        .attributes("title"),
    ).toBe("检索质量检查清单.pdf");
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it("管理布局严格呈现七项导航和返回用户工作区入口", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/admin");
    const navigationLabels = wrapper
      .findAll(".sidebar .nav-item")
      .map((item) => item.text().replace(/^./u, "").trim());

    expect(navigationLabels).toEqual(adminNavigation.map((item) => item.label));
    expect(wrapper.get('.topbar a[href="/"]').text()).toBe("返回用户工作区");
    expect(wrapper.findAll("h1")).toHaveLength(1);
    expect(wrapper.text()).toContain("治理队列");
    expect(wrapper.text()).toContain("运行正常");
    expect(requestSpy).not.toHaveBeenCalled();
  });
});
