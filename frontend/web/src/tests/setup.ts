import { enableAutoUnmount } from "@vue/test-utils";
import { afterEach } from "vitest";

enableAutoUnmount(afterEach);

afterEach(() => {
  if (typeof document === "undefined") {
    return;
  }

  document.body.classList.remove("drawer-open");
  localStorage.clear();
  sessionStorage.clear();
});
