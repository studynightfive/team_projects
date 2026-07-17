import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

import SafeMarkdown from "../components/common/SafeMarkdown.vue";
import { aiSearchMockData } from "../mocks/ai-search";
import { runAiSearch } from "../services/ai-search";
import { renderAppAt } from "./renderApp";

const getButton = (wrapper: VueWrapper, label: string) => {
  const button = wrapper
    .findAll("button")
    .find((candidate) => candidate.text().includes(label));
  if (button === undefined) throw new Error(`未找到按钮：${label}`);
  return button;
};

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

  it("非默认问题不会复用差旅结论，筛选后的引用编号与来源一致", async () => {
    const query = "本季度重点项目进展如何？";
    const response = await runAiSearch({
      query,
      mode: "research",
      sources: ["project"],
      modelId: "enterprise-general",
    });
    const citationNumbers = [...response.answer.markdown.matchAll(/\[(\d+)\]/gu)].map(
      (match) => Number(match[1]),
    );

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

  it("附件名称随搜索进入上下文，但不写入查询字符串", async () => {
    const { wrapper, router } = await renderAppAt("/");
    await vi.waitFor(() => {
      expect(wrapper.find("form.ai-search-box").exists()).toBe(true);
    });

    await wrapper.get("#ai-search-query").setValue("总结附件中的发布风险");
    const fileInput = wrapper.get<HTMLInputElement>('input[type="file"]');
    Object.defineProperty(fileInput.element, "files", {
      configurable: true,
      value: [new File(["demo"], "发布风险清单.pdf", { type: "application/pdf" })],
    });
    await fileInput.trigger("change");
    expect(wrapper.get(".attachment-chip").text()).toContain("发布风险清单.pdf");

    await wrapper.get("form.ai-search-box").trigger("submit");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/search");
    expect(router.currentRoute.value.fullPath).not.toContain("发布风险清单");

    await getButton(wrapper, "搜索上下文").trigger("click");
    expect(wrapper.get(".context-file-list").text()).toContain(
      "发布风险清单.pdf",
    );
  });

  it("空间深链接选中目标空间，历史重命名不改变原始查询", async () => {
    const targetSpace = aiSearchMockData.knowledgeSpaces[2];
    if (targetSpace === undefined) throw new Error("缺少知识空间模拟数据");

    const spaces = await renderAppAt(`/spaces?space=${targetSpace.id}`);
    expect(spaces.wrapper.get(".knowledge-space-grid article.selected").text()).toContain(
      targetSpace.name,
    );
    expect(
      spaces.wrapper.get(".space-browser-layout > .space-detail-panel").text(),
    ).toContain(targetSpace.name);
    expect(spaces.wrapper.find(".lucide-arrow-up-right").exists()).toBe(false);
    expect(
      spaces.wrapper.findAll(
        ".knowledge-space-grid .lucide-chevron-right",
      ),
    ).toHaveLength(aiSearchMockData.knowledgeSpaces.length);
    spaces.wrapper.unmount();

    const history = await renderAppAt("/history");
    const originalQuery = history.wrapper.get(".history-list article h3").text();
    await history.wrapper
      .get('.history-list article button[aria-label^="重命名"]')
      .trigger("click");
    await history.wrapper.get(".title-editor").setValue("季度项目检查");
    await getButton(history.wrapper, "保存").trigger("click");
    expect(history.wrapper.text()).toContain("季度项目检查");

    await getButton(history.wrapper, "再次搜索").trigger("click");
    await flushPromises();
    await vi.waitFor(() => {
      expect(history.router.currentRoute.value.query.q).toBe(originalQuery);
    });
  });
});
