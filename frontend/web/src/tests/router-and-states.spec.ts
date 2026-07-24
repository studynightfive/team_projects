import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";
import StateCard from "../components/StateCard.vue";
import { renderAppAt } from "./renderApp";

describe("M01 V2 路由与通用状态", () => {
  it("登录页本地校验空字段且不发送凭据", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/login");

    expect(wrapper.get("h1").text()).toBe("让组织的知识，活在每一次决策里");
    expect(wrapper.get("#login-title").text()).toBe("欢迎回到工作台");
    expect(wrapper.get('label[for="account"]').text()).toBe("账号");
    expect(wrapper.get('label[for="password"]').text()).toBe("密码");

    await wrapper.get("form").trigger("submit");

    expect(wrapper.get("#account-error").text()).toBe("请输入企业邮箱或工号");
    expect(wrapper.get("#password-error").text()).toBe("请输入密码");
    expect(wrapper.get("#account").attributes("aria-invalid")).toBe("true");
    expect(requestSpy).not.toHaveBeenCalled();
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });

  it("登录页支持密码显隐，成功本地校验后仍不访问网络或存储", async () => {
    const requestSpy = vi.spyOn(apiClient, "request");
    const { wrapper } = await renderAppAt("/login");

    await wrapper.get("#account").setValue("demo-user");
    await wrapper.get("#password").setValue("local-only-value");

    const passwordToggle = wrapper.get(".password-toggle");
    expect(wrapper.get("#password").attributes("type")).toBe("password");
    await passwordToggle.trigger("click");
    expect(wrapper.get("#password").attributes("type")).toBe("text");
    expect(passwordToggle.attributes("aria-pressed")).toBe("true");

    await wrapper.get("form").trigger("submit");

    expect(wrapper.find(".field-error").exists()).toBe(false);
    expect(requestSpy).not.toHaveBeenCalled();
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });

  it("进入普通用户工作台与管理中心 V2 页面", async () => {
    const userApp = await renderAppAt("/");
    await vi.waitFor(() => {
      expect(userApp.wrapper.get("h1").text()).toBe("今天想查找什么？");
    });
    userApp.wrapper.unmount();

    const adminApp = await renderAppAt("/admin");
    expect(adminApp.wrapper.get("h1").text()).toBe("业务运营看板");
  });

  it("403 不渲染管理指标或管理数据", async () => {
    const { wrapper } = await renderAppAt("/403");

    expect(wrapper.get("h1").text()).toBe("你没有访问权限");
    expect(wrapper.text()).toContain("数据不会被加载");
    expect(wrapper.find("[aria-label='管理指标']").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("活跃用户数");
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
    expect(wrapper.find(".state-icon svg").exists()).toBe(true);
    if (action === undefined) {
      expect(wrapper.find("button").exists()).toBe(false);
      expect(wrapper.find(".loading-line").exists()).toBe(true);
      return;
    }

    expect(wrapper.get("button").text()).toBe(action);
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("action")).toHaveLength(1);
  });

  it("三页渲染文案不包含 emoji", async () => {
    const emojiPattern = /\p{Emoji_Presentation}/u;

    for (const path of ["/login", "/", "/admin"] as const) {
      const { wrapper } = await renderAppAt(path);
      expect(wrapper.text()).not.toMatch(emojiPattern);
      wrapper.unmount();
    }
  });
});
