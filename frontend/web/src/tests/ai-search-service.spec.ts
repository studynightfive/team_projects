import { describe, expect, it, vi } from "vitest";

import { aiSearchMockData } from "../mocks/ai-search";
import { loadAiSearchHome, runAiSearch } from "../services/ai-search";
import type { SearchRequest } from "../types/ai-search";

const request: SearchRequest = {
  query: "  公司最新的差旅报销标准是什么？  ",
  mode: "smart",
  sources: [
    "knowledge",
    "project",
    "policy",
    "meeting",
    "business",
    "personal",
    "internet",
  ],
  modelId: "enterprise-general",
};

describe("AI 搜索本地数据服务", () => {
  it("提供规定数量的设计验证数据且明确禁止业务 API", () => {
    expect(aiSearchMockData.meta).toMatchObject({
      designOnly: true,
      apiRequestsAllowed: false,
    });
    expect(aiSearchMockData.suggestions).toHaveLength(6);
    expect(aiSearchMockData.history).toHaveLength(8);
    expect(aiSearchMockData.knowledgeSpaces).toHaveLength(6);
    expect(aiSearchMockData.dataSources).toHaveLength(8);
    expect(aiSearchMockData.results).toHaveLength(10);
    expect(aiSearchMockData.answer.citations).toHaveLength(6);
    expect(aiSearchMockData.answer.relatedQuestions).toHaveLength(4);
    expect(aiSearchMockData.stateExamples.length).toBeGreaterThanOrEqual(3);
  });

  it("拒绝空查询", async () => {
    await expect(runAiSearch({ ...request, query: " \n\t " })).rejects.toThrow(
      "请输入搜索问题。",
    );
  });

  it("返回确定性副本且不发送网络请求", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const first = await runAiSearch(request);
    const second = await runAiSearch(request);

    expect(first).toEqual(second);
    expect(first.answer.query).toBe("公司最新的差旅报销标准是什么？");
    expect(first.results).toHaveLength(10);
    expect(first.answer.citations).toHaveLength(6);
    expect(first.elapsedLabel).toBe("本地模拟，无真实耗时");
    expect(first).not.toBe(second);
    expect(first.results).not.toBe(second.results);
    expect(fetchSpy).not.toHaveBeenCalled();

    vi.unstubAllGlobals();
  });

  it("响应已取消的加载任务", async () => {
    const controller = new AbortController();
    const pending = loadAiSearchHome(controller.signal);

    controller.abort();

    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });
});
