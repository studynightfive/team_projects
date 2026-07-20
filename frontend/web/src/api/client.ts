import axios, { AxiosHeaders } from "axios";
import type {
  AxiosAdapter,
  AxiosError,
  AxiosInstance,
  CreateAxiosDefaults,
  InternalAxiosRequestConfig,
} from "axios";

import { clearAccessToken, getAccessToken, setAccessToken } from "./session";
import { isMockApiMode } from "../config/runtime";
import { mockAdapter } from "../mocks/adapter";
import type { ApiResponse } from "./contracts";

export interface PublicApiError {
  readonly message: string;
  readonly status?: number;
}

interface ApiClientOptions {
  readonly useMock?: boolean;
  /** 仅供测试注入传输层，生产环境使用 Axios 默认适配器。 */
  readonly adapter?: AxiosAdapter;
}

interface AuthTokenData {
  readonly access_token: string;
}

interface RetriableRequestConfig extends InternalAxiosRequestConfig {
  _authRetried?: boolean;
}

const GENERIC_ERROR_MESSAGE = "请求失败，请稍后重试。";

const publicStatusMessages: Readonly<Record<number, string>> = {
  401: "登录状态已失效，请重新登录。",
  403: "当前账号没有执行此操作的权限。",
  404: "请求的内容不存在或已被移除。",
  409: "当前名称已存在，请换一个名称后重试。",
};

export const createApiClient = (
  options: ApiClientOptions = {},
): AxiosInstance => {
  const useMock = options.useMock === true;
  const config: CreateAxiosDefaults = {
    baseURL: "/api",
    withCredentials: true,
  };

  if (useMock) {
    config.adapter = mockAdapter;
  } else if (options.adapter !== undefined) {
    config.adapter = options.adapter;
  }

  const client = axios.create(config);

  client.interceptors.request.use((requestConfig) => {
    const token = getAccessToken();
    if (token !== undefined && token !== "") {
      const headers = AxiosHeaders.from(requestConfig.headers);
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      requestConfig.headers = headers;
    }
    return requestConfig;
  });

  if (!useMock) {
    const refreshClient = axios.create({
      baseURL: config.baseURL,
      withCredentials: true,
      adapter: options.adapter,
    });
    let refreshPromise: Promise<string> | undefined;

    const refreshAccessToken = (): Promise<string> => {
      if (refreshPromise === undefined) {
        refreshPromise = refreshClient
          .post<ApiResponse<AuthTokenData>>("/v1/auth/refresh")
          .then((refreshResponse) => {
            const token = refreshResponse.data.data?.access_token;
            if (token === undefined || token === "") {
              throw new Error("刷新响应缺少 Access Token");
            }
            setAccessToken(token);
            return token;
          })
          .catch((error: unknown) => {
            clearAccessToken();
            throw error;
          })
          .finally(() => {
            refreshPromise = undefined;
          });
      }
      return refreshPromise;
    };

    client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const status = error.response?.status;
        const originalRequest = error.config as
          | RetriableRequestConfig
          | undefined;
        const url = originalRequest?.url ?? "";

        if (
          status !== 401 ||
          originalRequest === undefined ||
          originalRequest._authRetried === true ||
          url.includes("/v1/auth/login") ||
          url.includes("/v1/auth/refresh")
        ) {
          if (status === 401) {
            clearAccessToken();
          }
          return Promise.reject(error);
        }

        originalRequest._authRetried = true;

        try {
          const token = await refreshAccessToken();
          const headers = AxiosHeaders.from(originalRequest.headers);
          headers.set("Authorization", `Bearer ${token}`);
          originalRequest.headers = headers;
          return client.request(originalRequest);
        } catch {
          return Promise.reject(error);
        }
      },
    );
  }

  return client;
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
  useMock: isMockApiMode,
});

export { clearAccessToken, getAccessToken, setAccessToken };
