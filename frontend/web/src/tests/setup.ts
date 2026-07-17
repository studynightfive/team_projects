import { enableAutoUnmount } from "@vue/test-utils";
import { afterEach } from "vitest";

enableAutoUnmount(afterEach);

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
