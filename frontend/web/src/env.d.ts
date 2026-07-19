/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USE_REAL_API?: "true" | "false";
  readonly VITE_API_PROXY_TARGET?: string;
}
