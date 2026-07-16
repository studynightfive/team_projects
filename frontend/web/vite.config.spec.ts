// @vitest-environment node

import { describe, expect, it } from "vitest";

import { apiProxyForMode } from "./vite.config";

describe("Vite API 代理模式", () => {
  it("Mock mode 不暴露真实 API 代理", () => {
    expect(apiProxyForMode("mock")).toBeUndefined();
  });

  it("仅 API mode 代理 /api", () => {
    expect(apiProxyForMode("api")).toEqual({
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    });
  });
});
