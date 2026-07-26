import { App as AntApp } from "ant-design-vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { defineComponent, h } from "vue";
import { describe, expect, it, vi } from "vitest";

import { aiSearchMockData } from "../mocks/ai-search";
import SearchView from "../views/user/SearchView.vue";

const serviceMocks = vi.hoisted(() => ({
  listKnowledgeBases: vi.fn(),
  listRealChatModelOptions: vi.fn(),
  runAiSearch: vi.fn(),
}));

vi.mock("../config/runtime", () => ({
  isRealApiMode: true,
  isMockApiMode: false,
}));
vi.mock("../services/knowledge", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/knowledge")>()),
  listKnowledgeBases: serviceMocks.listKnowledgeBases,
}));
vi.mock("../services/ai-search-real", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/ai-search-real")>()),
  listRealChatModelOptions: serviceMocks.listRealChatModelOptions,
}));
vi.mock("../services/ai-search", () => ({
  runAiSearch: serviceMocks.runAiSearch,
}));

describe("真实问答页工作流", () => {
  it("空间提问等待真实选项加载后只搜索一次，并保持底部输入框", async () => {
    let resolveKnowledgeBases:
      | ((value: readonly Record<string, unknown>[]) => void)
      | undefined;
    serviceMocks.listKnowledgeBases.mockReturnValue(
      new Promise<readonly Record<string, unknown>[]>((resolve) => {
        resolveKnowledgeBases = resolve;
      }),
    );
    serviceMocks.listRealChatModelOptions.mockResolvedValue([
      {
        value: "chat-model-1",
        label: "真实问答模型",
        description: "测试",
      },
    ]);
    serviceMocks.runAiSearch.mockResolvedValue({
      request: {
        query: "请总结医疗知识库",
        mode: "smart",
        sources: ["knowledge"],
        workspaceIds: ["kb-medical"],
        modelId: "chat-model-1",
      },
      isMock: false,
      status: "success",
      answer: aiSearchMockData.answer,
      results: aiSearchMockData.results,
      sourceCount: aiSearchMockData.results.length,
      notice: "",
      elapsedLabel: "100ms",
    });
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/search", component: SearchView }],
    });
    await router.push({
      path: "/search",
      state: {
        initialSearch: {
          q: "请总结医疗知识库",
          workspaceIds: ["kb-medical"],
          sources: "knowledge",
        },
      },
    });
    await router.isReady();
    const Harness = defineComponent({
      setup: () => () =>
        h(AntApp, null, {
          default: () => h(SearchView),
        }),
    });
    const wrapper = mount(Harness, {
      attachTo: document.body,
      global: { plugins: [router] },
    });
    await flushPromises();

    expect(serviceMocks.runAiSearch).not.toHaveBeenCalled();
    expect(router.options.history.state.initialSearch).toBeUndefined();

    resolveKnowledgeBases?.([
      {
        id: "kb-medical",
        name: "医疗知识库",
        description: "医疗资料",
        kind: "department",
        department_id: "department-1",
        department_name: "医疗部",
        status: "active",
        document_count: 3,
        ready_document_count: 3,
        chunk_count: 20,
      },
    ]);
    await flushPromises();

    expect(serviceMocks.runAiSearch).toHaveBeenCalledTimes(1);
    expect(serviceMocks.runAiSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        query: "请总结医疗知识库",
        workspaceIds: ["kb-medical"],
        modelId: "chat-model-1",
      }),
      expect.any(AbortSignal),
      expect.any(Object),
    );
    const resultLayout = wrapper.get(".search-result-layout").element;
    const composer = wrapper.get(".conversation-composer").element;
    expect(
      resultLayout.compareDocumentPosition(composer) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).not.toBe(0);
    expect(scrollIntoView).toHaveBeenCalled();
  });
});
