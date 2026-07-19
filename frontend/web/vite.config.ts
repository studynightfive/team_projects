import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { loadEnv, type ServerOptions } from "vite";
import { defineConfig } from "vitest/config";

const DEFAULT_API_PROXY_TARGET = "http://127.0.0.1:8000";

export const apiProxyForMode = (
  mode: string,
  target = DEFAULT_API_PROXY_TARGET,
): ServerOptions["proxy"] =>
  mode === "api"
    ? {
        "/api": {
          target,
          changeOrigin: true,
        },
      }
    : undefined;

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
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
      proxy: apiProxyForMode(mode, env.VITE_API_PROXY_TARGET),
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/tests/setup.ts"],
      clearMocks: true,
    },
  };
});
