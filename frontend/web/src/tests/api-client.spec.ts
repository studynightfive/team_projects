import {
  AxiosError,
  AxiosHeaders,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { describe, expect, it, vi } from "vitest";

import { createApiClient, toPublicApiError } from "../api/client";
import { clearAccessToken, setAccessToken } from "../api/session";
import { MOCK_NOT_FOUND } from "../mocks/adapter";

const createResponseError = (
  status: number,
  secretMarker: string,
): AxiosError => {
  const config = {
    headers: new AxiosHeaders(),
  } as InternalAxiosRequestConfig;
  const response: AxiosResponse = {
    data: { detail: secretMarker },
    status,
    statusText: "Failure",
    headers: new AxiosHeaders(),
    config,
  };

  return new AxiosError(
    `内部路径 C:\\private\\${secretMarker}`,
    "ERR_BAD_RESPONSE",
    config,
    undefined,
    response,
  );
};

const rejectWithStatus = (
  config: InternalAxiosRequestConfig,
  status: number,
): Promise<never> =>
  Promise.reject(
    new AxiosError(
      "request failed",
      "ERR_BAD_RESPONSE",
      config,
      undefined,
      {
        data: {},
        status,
        statusText: "Failure",
        headers: new AxiosHeaders(),
        config,
      },
    ),
  );

describe("M01 API Client 与 Mock Adapter", () => {
  it("固定 /api、Cookie 请求且不生成 Authorization", () => {
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");
    const client = createApiClient();

    expect(client.defaults.baseURL).toBe("/api");
    expect(client.defaults.withCredentials).toBe(true);
    expect(client.defaults.headers.common.Authorization).toBeUndefined();
    expect(setItemSpy).not.toHaveBeenCalled();
  });

  it("Mock 模式默认拒绝未注册请求且不回退真实网络", async () => {
    const client = createApiClient({ useMock: true });

    await expect(client.get("/unregistered")).rejects.toMatchObject({
      code: MOCK_NOT_FOUND,
    });
  });

  it("把未知错误和网络错误收窄为安全文案", () => {
    expect(toPublicApiError(new Error("secret stack"))).toEqual({
      message: "请求失败，请稍后重试。",
    });
    expect(
      toPublicApiError(new AxiosError("private host", "ERR_NETWORK")),
    ).toEqual({
      message: "网络连接失败，请检查网络后重试。",
    });
  });

  it("响应错误只公开状态码和通用文案", () => {
    const secretMarker = "DO_NOT_EXPOSE";
    const serverError = toPublicApiError(
      createResponseError(503, secretMarker),
    );
    const unauthorizedError = toPublicApiError(
      createResponseError(401, secretMarker),
    );
    const forbiddenError = toPublicApiError(
      createResponseError(403, secretMarker),
    );

    expect(serverError).toEqual({
      message: "服务暂时不可用，请稍后重试。",
      status: 503,
    });
    expect(forbiddenError).toEqual({
      message: "当前账号没有执行此操作的权限。",
      status: 403,
    });
    expect(unauthorizedError).toEqual({
      message: "登录状态已失效，请重新登录。",
      status: 401,
    });
    expect(
      JSON.stringify({ serverError, unauthorizedError, forbiddenError }),
    ).not.toContain(secretMarker);
    expect(
      JSON.stringify({ serverError, unauthorizedError, forbiddenError }),
    ).not.toContain("private");
  });

  it("Access Token 过期后刷新并用新 Token 重放原请求", async () => {
    let refreshCalls = 0;
    const adapter: AxiosAdapter = async (config) => {
      if (config.url === "/v1/auth/refresh") {
        refreshCalls += 1;
        return {
          data: {
            code: 0,
            message: "ok",
            data: { access_token: "fresh-token" },
            request_id: "refresh",
          },
          status: 200,
          statusText: "OK",
          headers: new AxiosHeaders(),
          config,
        };
      }
      if (AxiosHeaders.from(config.headers).get("Authorization") !== "Bearer fresh-token") {
        return rejectWithStatus(config, 401);
      }
      return {
        data: { ok: true },
        status: 200,
        statusText: "OK",
        headers: new AxiosHeaders(),
        config,
      };
    };
    setAccessToken("expired-token");

    const response = await createApiClient({ adapter }).get("/v1/protected");

    expect(response.data).toEqual({ ok: true });
    expect(refreshCalls).toBe(1);
    clearAccessToken();
  });

  it("并发 401 共用一次 Refresh Token 轮换", async () => {
    let refreshCalls = 0;
    const adapter: AxiosAdapter = async (config) => {
      if (config.url === "/v1/auth/refresh") {
        refreshCalls += 1;
        await Promise.resolve();
        return {
          data: {
            code: 0,
            message: "ok",
            data: { access_token: "fresh-token" },
            request_id: "refresh",
          },
          status: 200,
          statusText: "OK",
          headers: new AxiosHeaders(),
          config,
        };
      }
      if (AxiosHeaders.from(config.headers).get("Authorization") !== "Bearer fresh-token") {
        return rejectWithStatus(config, 401);
      }
      return {
        data: { ok: true },
        status: 200,
        statusText: "OK",
        headers: new AxiosHeaders(),
        config,
      };
    };
    setAccessToken("expired-token");
    const client = createApiClient({ adapter });

    const responses = await Promise.all(
      Array.from({ length: 10 }, (_, index) => client.get(`/v1/protected/${index}`)),
    );

    expect(responses).toHaveLength(10);
    expect(refreshCalls).toBe(1);
    clearAccessToken();
  });
});
