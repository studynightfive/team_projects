import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import type { ServerOptions } from "vite";
import { defineConfig } from "vitest/config";

export const apiProxyForMode = (mode: string): ServerOptions["proxy"] =>
  mode === "api"
    ? {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      }
    : undefined;

export default defineConfig(({ mode }) => ({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: apiProxyForMode(mode),
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
    clearMocks: true,
  },
}));
