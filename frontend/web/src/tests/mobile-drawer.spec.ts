import { nextTick } from "vue";
import { describe, expect, it } from "vitest";

import { renderAppAt } from "./renderApp";

describe("M01 移动端完整导航", () => {
  it.each([
    ["/", 6, "进入管理中心"],
    ["/admin", 11, "返回用户工作区"],
  ] as const)(
    "%s 展开完整模块并通过关闭按钮返回焦点",
    async (path, moduleCount, workspaceSwitch) => {
      const { wrapper } = await renderAppAt(path);
      const trigger = wrapper.get("button.mobile-menu-button");

      expect(trigger.attributes("aria-expanded")).toBe("false");
      expect(trigger.attributes("aria-controls")).toMatch(/mobile-drawer$/u);

      await trigger.trigger("click");
      await nextTick();

      expect(trigger.attributes("aria-expanded")).toBe("true");
      expect(
        wrapper.findAll(".mobile-drawer-list .mobile-drawer-link"),
      ).toHaveLength(moduleCount);
      expect(wrapper.get(".workspace-switch").text()).toBe(workspaceSwitch);
      expect(document.body.classList.contains("drawer-open")).toBe(true);

      const closeButton = wrapper.get<HTMLButtonElement>(
        ".mobile-drawer-close",
      );
      expect(document.activeElement).toBe(closeButton.element);

      await closeButton.trigger("click");
      await nextTick();

      expect(trigger.attributes("aria-expanded")).toBe("false");
      expect(document.activeElement).toBe(trigger.element);
      expect(document.body.classList.contains("drawer-open")).toBe(false);
    },
  );

  it("支持 Escape、遮罩和导航链接关闭", async () => {
    const { wrapper } = await renderAppAt("/");
    const trigger = wrapper.get("button.mobile-menu-button");

    await trigger.trigger("click");
    await wrapper.get(".mobile-drawer").trigger("keydown", { key: "Escape" });
    expect(wrapper.find(".mobile-drawer").exists()).toBe(false);

    await trigger.trigger("click");
    await wrapper.get(".mobile-drawer-backdrop").trigger("click");
    expect(wrapper.find(".mobile-drawer").exists()).toBe(false);

    await trigger.trigger("click");
    await wrapper
      .get(".mobile-drawer-list .mobile-drawer-link")
      .trigger("click");
    expect(wrapper.find(".mobile-drawer").exists()).toBe(false);
  });

  it("在首尾可聚焦元素之间循环 Tab 焦点", async () => {
    const { wrapper } = await renderAppAt("/");
    await wrapper.get("button.mobile-menu-button").trigger("click");
    await nextTick();

    const drawer = wrapper.get(".mobile-drawer");
    const first = wrapper.get<HTMLButtonElement>(".mobile-drawer-close");
    const last = wrapper.get<HTMLAnchorElement>(".workspace-switch");

    last.element.focus();
    await drawer.trigger("keydown", { key: "Tab" });
    expect(document.activeElement).toBe(first.element);

    first.element.focus();
    await drawer.trigger("keydown", { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last.element);
  });

  it("卸载时清除页面滚动锁", async () => {
    const { wrapper } = await renderAppAt("/");
    await wrapper.get("button.mobile-menu-button").trigger("click");
    expect(document.body.classList.contains("drawer-open")).toBe(true);

    wrapper.unmount();

    expect(document.body.classList.contains("drawer-open")).toBe(false);
  });
});
