import {
  AxiosError,
  AxiosHeaders,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { describe, expect, it, vi } from "vitest";

import { createApiClient, toPublicApiError } from "../api/client";
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
});
