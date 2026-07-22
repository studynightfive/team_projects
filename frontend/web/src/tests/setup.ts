import { enableAutoUnmount } from "@vue/test-utils";
import { afterEach } from "vitest";

enableAutoUnmount(afterEach);

if (typeof window !== "undefined" && window.matchMedia === undefined) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (query: string): MediaQueryList => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

afterEach(() => {
  if (typeof document === "undefined") {
    return;
  }

  document.body.classList.remove("drawer-open");
  document.body.classList.remove("preview-drawer-open");
  document.body.classList.remove("search-context-open");
  document.body.classList.remove("source-filter-drawer-open");
  delete document.documentElement.dataset.theme;
  document.documentElement.style.removeProperty("color-scheme");
  localStorage.clear();
  sessionStorage.clear();
});
