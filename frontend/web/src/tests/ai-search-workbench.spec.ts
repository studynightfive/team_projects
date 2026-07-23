import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

import SafeMarkdown from "../components/common/SafeMarkdown.vue";
import SearchContextPanel from "../components/search/SearchContextPanel.vue";
import { aiSearchMockData } from "../mocks/ai-search";
import { runAiSearch } from "../services/ai-search";
import { classifyUnsafeQuery } from "../services/query-safety";
import { renderAppAt } from "./renderApp";

describe("AI 搜索工作台关键链路", () => {
  it("安全渲染 Markdown 并把有效引用标记转换为可点击按钮", async () => {
    const wrapper = mount(SafeMarkdown, {
      props: {
        content:
          '结论来自 [1]。<script>alert("xss")</script> [危险链接](javascript:alert(1))',
        citationIds: ["citation-1"],
      },
    });

    expect(wrapper.find("script").exists()).toBe(false);
    expect(wrapper.find('a[href^="javascript:"]').exists()).toBe(false);
    expect(wrapper.html()).not.toContain("<script");

    const citation = wrapper.get<HTMLButtonElement>(".markdown-citation");
    expect(citation.attributes("aria-label")).toBe("查看引用 1");
    await citation.trigger("click");
    expect(wrapper.emitted("citation")?.[0]?.[0]).toBe("citation-1");
  });

  it("引用来源概览按文档去重且不显示待确认状态", () => {
    const citation = aiSearchMockData.answer.citations[0];
    if (citation === undefined) throw new Error("缺少引用模拟数据");

    const wrapper = mount(SearchContextPanel, {
      props: {
        open: true,
        query: "医疗信息化系统有哪些核心模块？",
        knowledgeBaseOptions: [],
        modelLabel: "DeepSeek",
        citations: [citation, { ...citation, id: "duplicate-citation" }],
      },
    });

    expect(wrapper.findAll(".context-citation-list button")).toHaveLength(1);
    expect(wrapper.text()).not.toContain("待确认");
  });

  it("非默认问题不会复用差旅结论，筛选后的引用编号与来源一致", async () => {
    const query = "本季度重点项目进展如何？";
    const response = await runAiSearch({
      query,
      mode: "smart",
      sources: ["project"],
      modelId: "enterprise-general",
    });
    const citationNumbers = [
      ...response.answer.markdown.matchAll(/\[(\d+)\]/gu),
    ].map((match) => Number(match[1]));

    expect(response.answer.query).toBe(query);
    expect(response.answer.title).toContain(query);
    expect(response.answer.summary).toContain("尚未接入真实检索接口");
    expect(response.answer.title).not.toBe(aiSearchMockData.answer.title);
    expect(
      citationNumbers.every(
        (number) => number >= 1 && number <= response.answer.citations.length,
      ),
    ).toBe(true);
  });

  it("答案正文引用可打开文档预览，并通过 Escape 关闭后返回焦点", async () => {
    const { wrapper } = await renderAppAt("/search");
    await vi.waitFor(() => {
      expect(wrapper.find(".markdown-citation").exists()).toBe(true);
    });

    const citation = wrapper.get<HTMLButtonElement>(".markdown-citation");
    await citation.trigger("click");
    await nextTick();

    expect(wrapper.get(".document-preview-panel").attributes("role")).toBe(
      "dialog",
    );
    expect(document.activeElement).toBe(
      wrapper.get(".document-preview-header .icon-button").element,
    );

    await wrapper
      .get(".document-preview-drawer")
      .trigger("keydown", { key: "Escape" });
    await nextTick();
    expect(wrapper.find(".document-preview-drawer").exists()).toBe(false);
    expect(document.activeElement).toBe(citation.element);
  });

  it("统一搜索不再展示附件和搜索模式控件", async () => {
    const { wrapper, router } = await renderAppAt("/");
    await vi.waitFor(() => {
      expect(wrapper.find("form.ai-search-box").exists()).toBe(true);
    });

    expect(wrapper.find('input[type="file"]').exists()).toBe(false);
    expect(wrapper.find('[title="选择搜索模式"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("智能搜索");
    expect(wrapper.text()).not.toContain("附件检索");

    await wrapper.get("#ai-search-query").setValue("总结发布风险");

    await wrapper.get("form.ai-search-box").trigger("submit");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/search");
    expect(router.currentRoute.value.query).not.toHaveProperty("mode");
  });

  it("敏感词在输入阶段禁用搜索且合法医疗问题不会被误伤", async () => {
    const { wrapper, router } = await renderAppAt("/");
    await vi.waitFor(() => {
      expect(wrapper.find("#ai-search-query").exists()).toBe(true);
    });
    const query = wrapper.get("#ai-search-query");
    const submit = wrapper.get<HTMLButtonElement>(".search-submit-button");

    await query.setValue("如何寻找贩-毒渠道");
    expect(classifyUnsafeQuery("如何寻找贩-毒渠道")).toBe("涉毒");
    expect(query.attributes("aria-invalid")).toBe("true");
    expect(wrapper.get(".search-input-error").text()).toBe(
      "输入内容不合法，请修改后重试",
    );
    expect(submit.attributes("disabled")).toBeDefined();

    await wrapper.get("form.ai-search-box").trigger("submit");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/");

    await query.setValue("医院病毒防控系统如何建设？");
    expect(classifyUnsafeQuery("医院病毒防控系统如何建设？")).toBeUndefined();
    expect(query.attributes("aria-invalid")).toBe("false");
    expect(wrapper.find(".search-input-error").exists()).toBe(false);
    expect(submit.attributes("disabled")).toBeUndefined();
  });

  it("问答导出提供 PDF、Word 与 Markdown 格式", async () => {
    const { wrapper } = await renderAppAt("/search");
    await vi.waitFor(() => {
      expect(wrapper.find(".result-tabs").exists()).toBe(true);
    });
    const exportButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("下载答案"));
    if (exportButton === undefined) throw new Error("缺少下载答案按钮");

    await exportButton.trigger("click");
    await flushPromises();

    const modalText = document.body.textContent ?? "";
    expect(modalText).toContain("下载问答答案");
    expect(modalText).toContain("PDF");
    expect(modalText).toContain("Word");
    expect(modalText).toContain("Markdown");
    expect(modalText).toContain("RAG问答结果.md");
    expect(modalText).toContain("下载 Markdown");
  });

  it("空间深链接选中目标空间，已删除的历史页面返回 404", async () => {
    const targetSpace = aiSearchMockData.knowledgeSpaces[2];
    if (targetSpace === undefined) throw new Error("缺少知识空间模拟数据");

    const spaces = await renderAppAt(`/spaces?space=${targetSpace.id}`);
    expect(
      spaces.wrapper.get(".knowledge-space-grid article.selected").text(),
    ).toContain(targetSpace.name);
    expect(
      spaces.wrapper.get(".space-browser-layout > .space-detail-panel").text(),
    ).toContain(targetSpace.name);
    expect(spaces.wrapper.find(".lucide-arrow-up-right").exists()).toBe(false);
    expect(
      spaces.wrapper.findAll(".knowledge-space-grid .lucide-chevron-right"),
    ).toHaveLength(aiSearchMockData.knowledgeSpaces.length);
    spaces.wrapper.unmount();

    const history = await renderAppAt("/history");
    expect(history.router.currentRoute.value.name).toBe("not-found");
    expect(history.wrapper.text()).toContain("页面不存在");
  });
});
