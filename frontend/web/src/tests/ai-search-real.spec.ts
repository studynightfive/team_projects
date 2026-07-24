import { AxiosHeaders, type AxiosResponse } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";
import type { ApiResponse } from "../api/contracts";
import {
  listRealChatModelOptions,
  loadRealHome,
} from "../services/ai-search-real";

interface AvailableModelFixture {
  readonly id: string;
  readonly provider_code: string;
  readonly model_name: string;
  readonly kind: string;
}

const createResponse = <T>(data: ApiResponse<T>): AxiosResponse<ApiResponse<T>> => ({
  data,
  status: 200,
  statusText: "OK",
  headers: new AxiosHeaders(),
  config: { headers: new AxiosHeaders() },
});

describe("AI 搜索真实工作台", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("普通用户通过可用模型接口读取聊天模型", async () => {
    const get = vi.spyOn(apiClient, "get").mockResolvedValue(
      createResponse<readonly AvailableModelFixture[]>({
        code: 0,
        message: "success",
        data: [
          {
            id: "chat-model",
            provider_code: "deepseek",
            model_name: "deepseek-chat",
            kind: "chat",
          },
        ],
        request_id: "request-id",
      }),
    );

    const options = await listRealChatModelOptions();

    expect(get).toHaveBeenCalledWith("/v1/models/available", {
      params: { kind: "chat" },
      signal: undefined,
    });
    expect(options).toEqual([
      {
        value: "chat-model",
        label: "DeepSeek / deepseek-chat",
        description: "管理员已启用，可用于真实 RAG 回答。",
      },
    ]);
  });

  it("模型列表失败时工作台使用环境默认模型继续加载", async () => {
    vi.spyOn(apiClient, "get").mockRejectedValue(new Error("forbidden"));

    const home = await loadRealHome();

    expect(home.modelOptions).toEqual([
      {
        value: "env-deepseek",
        label: "DeepSeek / 环境默认模型",
        description: "模型列表暂不可用，后端将使用环境默认模型。",
      },
    ]);
    expect(home.meta.apiRequestsAllowed).toBe(true);
  });
});
