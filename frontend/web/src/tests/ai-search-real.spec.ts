import { AxiosHeaders, type AxiosResponse } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient, clearAccessToken, setAccessToken } from "../api/client";
import type { ApiResponse } from "../api/contracts";
import {
  listRealChatModelOptions,
  loadRealHome,
  parseSseStream,
  runRealSearch,
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
    clearAccessToken();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
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

  it("解析跨网络分片的 SSE 事件", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: delta\ndata: {"text":"第一'));
        controller.enqueue(
          encoder.encode('段"}\n\nevent: done\ndata: {"generated":true}\n\n'),
        );
        controller.close();
      },
    });

    const events = [];
    for await (const event of parseSseStream(stream)) {
      events.push(event);
    }

    expect(events).toEqual([
      { event: "delta", data: { text: "第一段" } },
      { event: "done", data: { generated: true } },
    ]);
  });

  it("流式接收处理阶段、引用与答案增量", async () => {
    setAccessToken("access-token");
    const eventStream = [
      'event: start\ndata: {"event":"start","request_id":"request-1"}\n\n',
      'event: stage\ndata: {"event":"stage","stage":"retrieval","label":"检索知识库","status":"running","detail":"正在检索","elapsed_ms":3}\n\n',
      'event: citation\ndata: {"event":"citation","doc_id":"doc-1","chunk_id":"chunk-1","doc_title":"医疗信息化方案","page":1,"score":0.95,"vector_score":0.9,"keyword_score":0.8,"rerank_score":0.95,"text":"电子病历建设内容","highlights":null,"kb_id":"kb-1"}\n\n',
      'event: delta\ndata: {"event":"delta","text":"电子病历"}\n\n',
      'event: delta\ndata: {"event":"delta","text":"是核心模块。"}\n\n',
      'event: done\ndata: {"event":"done","took_ms":88,"mode":"hybrid","model":"deepseek-chat","generated":true,"from_cache":false,"cache_match":null,"cache_similarity":null}\n\n',
    ].join("");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(eventStream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      ),
    );
    const onStage = vi.fn();
    const onResponse = vi.fn();

    const result = await runRealSearch(
      {
        query: "电子病历有哪些核心模块",
        mode: "smart",
        sources: ["knowledge"],
        workspaceIds: ["kb-1"],
        modelId: "chat-1",
      },
      undefined,
      { onStage, onResponse },
    );

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/retrieval/answer/stream",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: expect.objectContaining({
          Authorization: "Bearer access-token",
        }),
      }),
    );
    expect(onStage).toHaveBeenCalledWith(
      expect.objectContaining({ id: "retrieval", status: "running" }),
    );
    expect(onResponse).toHaveBeenCalled();
    expect(result.answer.markdown).toBe("电子病历是核心模块。");
    expect(result.answer.citations).toHaveLength(1);
    expect(result.elapsedLabel).toBe("88ms");
  });
});
