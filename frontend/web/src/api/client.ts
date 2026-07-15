import axios from "axios";
import type { AxiosInstance, CreateAxiosDefaults } from "axios";

import { mockAdapter } from "../mocks/adapter";

export interface PublicApiError {
  readonly message: string;
  readonly status?: number;
}

interface ApiClientOptions {
  readonly useMock?: boolean;
}

const GENERIC_ERROR_MESSAGE = "请求失败，请稍后重试。";

const publicStatusMessages: Readonly<Record<number, string>> = {
  401: "登录状态已失效，请重新登录。",
  403: "当前账号没有执行此操作的权限。",
  404: "请求的内容不存在或已被移除。",
};

export const createApiClient = (
  options: ApiClientOptions = {},
): AxiosInstance => {
  const config: CreateAxiosDefaults = {
    baseURL: "/api",
    withCredentials: true,
  };

  if (options.useMock === true) {
    config.adapter = mockAdapter;
  }

  return axios.create(config);
};

/**
 * 只向界面暴露安全、稳定的信息，不透传服务端响应体、请求配置或内部堆栈。
 */
export const toPublicApiError = (error: unknown): PublicApiError => {
  if (!axios.isAxiosError(error)) {
    return { message: GENERIC_ERROR_MESSAGE };
  }

  const status = error.response?.status;
  if (status !== undefined) {
    return {
      message:
        publicStatusMessages[status] ??
        (status >= 500
          ? "服务暂时不可用，请稍后重试。"
          : GENERIC_ERROR_MESSAGE),
      status,
    };
  }

  return {
    message:
      error.code === "ERR_NETWORK"
        ? "网络连接失败，请检查网络后重试。"
        : GENERIC_ERROR_MESSAGE,
  };
};

export const apiClient = createApiClient({
  useMock: import.meta.env.MODE === "mock",
});
