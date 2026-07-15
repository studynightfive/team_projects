import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";
import StateCard from "../components/StateCard.vue";
import { renderAppAt } from "./renderApp";

describe("M01 路由与通用状态", () => {
  it("提供唯一的静态登录入口且不提交凭据", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/login");

    expect(wrapper.get("h1").text()).toBe("登录工作区");
    expect(wrapper.get('label[for="account"]').text()).toBe("账号");
    expect(wrapper.get('label[for="password"]').text()).toBe("密码");
    expect((wrapper.get("#account").element as HTMLInputElement).value).toBe(
      "",
    );
    expect((wrapper.get("#password").element as HTMLInputElement).value).toBe(
      "",
    );

    await wrapper.get("form").trigger("submit");

    expect(requestSpy).not.toHaveBeenCalled();
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });

  it("进入普通用户工作区与管理中心静态壳层", async () => {
    const userApp = await renderAppAt("/");
    expect(userApp.wrapper.get("h1").text()).toBe("今天从哪里开始？");
    userApp.wrapper.unmount();

    const adminApp = await renderAppAt("/admin");
    expect(adminApp.wrapper.get("h1").text()).toBe("平台运行概况");
  });

  it("403 不渲染管理摘要或管理数据", async () => {
    const { wrapper } = await renderAppAt("/403");

    expect(wrapper.get("h1").text()).toBe("你没有访问权限");
    expect(wrapper.text()).toContain("数据不会被加载");
    expect(wrapper.find("[aria-label='管理摘要']").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("活跃身份");
  });

  it("未知地址显示固定 404 安全出口", async () => {
    const { wrapper } = await renderAppAt("/missing-page");

    expect(wrapper.get("h1").text()).toBe("页面不存在");
    expect(wrapper.text()).toContain("地址可能已变化，或页面已被移除");
    expect(wrapper.get("a.state-action").attributes("href")).toBe("/");
  });

  it.each([
    ["loading", "正在加载页面", undefined],
    ["empty", "暂无内容", "刷新页面"],
    ["error", "暂时无法加载", "重新加载"],
  ] as const)("渲染 %s 状态骨架", async (kind, title, action) => {
    const wrapper = mount(StateCard, {
      props: { kind },
    });

    expect(wrapper.get("h1").text()).toBe(title);
    if (action === undefined) {
      expect(wrapper.find("button").exists()).toBe(false);
      expect(wrapper.find(".loading-line").exists()).toBe(true);
      return;
    }

    expect(wrapper.get("button").text()).toBe(action);
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("action")).toHaveLength(1);
  });
});
