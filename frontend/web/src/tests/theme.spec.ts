import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { THEME_STORAGE_KEY, useThemeStore } from "../stores/theme";

class MockMediaQueryList extends EventTarget implements MediaQueryList {
  matches = false;
  readonly media = "(prefers-color-scheme: dark)";
  onchange:
    | ((this: MediaQueryList, ev: MediaQueryListEvent) => unknown)
    | null = null;

  addListener(
    callback:
      | ((this: MediaQueryList, ev: MediaQueryListEvent) => unknown)
      | null,
  ): void {
    if (callback !== null)
      this.addEventListener("change", callback as EventListener);
  }

  removeListener(
    callback:
      | ((this: MediaQueryList, ev: MediaQueryListEvent) => unknown)
      | null,
  ): void {
    if (callback !== null)
      this.removeEventListener("change", callback as EventListener);
  }

  setMatches(matches: boolean): void {
    this.matches = matches;
    const event = new Event("change") as MediaQueryListEvent;
    Object.defineProperty(event, "matches", { value: matches });
    this.dispatchEvent(event);
  }
}

describe("全局主题", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("仅持久化合法主题枚举并可由新 Store 恢复", () => {
    const store = useThemeStore();
    store.startSystemThemeListener();
    store.setThemeMode("dark");

    expect(store.resolvedTheme).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(localStorage).toHaveLength(1);

    store.stopSystemThemeListener();
    setActivePinia(createPinia());
    const restoredStore = useThemeStore();
    restoredStore.startSystemThemeListener();
    expect(restoredStore.mode).toBe("dark");
    expect(restoredStore.resolvedTheme).toBe("dark");

    restoredStore.resetThemeMode();
    expect(restoredStore.mode).toBe("system");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBeNull();
    restoredStore.stopSystemThemeListener();
  });

  it("跟随系统时响应系统配色变化且不写浏览器存储", () => {
    const mediaQuery = new MockMediaQueryList();
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => mediaQuery),
    );

    const store = useThemeStore();
    store.startSystemThemeListener();
    expect(store.mode).toBe("system");
    expect(store.resolvedTheme).toBe("light");

    mediaQuery.setMatches(true);
    expect(store.resolvedTheme).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage).toHaveLength(0);

    store.stopSystemThemeListener();
  });
});
