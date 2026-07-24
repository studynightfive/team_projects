import { App as AntApp } from "ant-design-vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import DocumentDetailView from "../views/user/DocumentDetailView.vue";

const serviceMocks = vi.hoisted(() => ({
  getDocument: vi.fn(),
  getDocumentOriginal: vi.fn(),
  getDocumentMarkdown: vi.fn(),
  getDocumentChunks: vi.fn(),
}));

vi.mock("../config/runtime", () => ({
  isRealApiMode: true,
  isMockApiMode: false,
}));
vi.mock("../services/knowledge", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/knowledge")>()),
  ...serviceMocks,
}));

const documentRecord = {
  id: "document-1",
  knowledge_base_id: "kb-1",
  title: "医疗信息化系统",
  original_filename: "医疗信息化系统.pdf",
  folder_path: "",
  extension: ".pdf",
  mime_type: "application/pdf",
  size_bytes: 1024,
  content_hash: "0".repeat(64),
  version: 1,
  status: "ready",
  parser_name: "pdf",
  chunk_strategy: "recursive",
  chunk_size: 800,
  chunk_overlap: 120,
  page_count: 3,
  error_code: null,
  error_message: null,
  created_at: "2026-07-24T00:00:00Z",
  updated_at: "2026-07-24T00:00:00Z",
  language: "chi_sim+eng",
  ocr_enabled: true,
  is_active_index: true,
  ocr: {
    status: "low_confidence",
    language: "chi_sim+eng",
    average_confidence: 0.62,
    review_required: true,
    message: "OCR 置信度偏低，建议人工核对 Markdown 与原文。",
  },
} as const;

const renderDocument = async () => {
  serviceMocks.getDocument.mockResolvedValue(documentRecord);
  serviceMocks.getDocumentOriginal.mockResolvedValue(
    new Blob(["pdf"], { type: "application/pdf" }),
  );
  serviceMocks.getDocumentMarkdown.mockResolvedValue({
    document_id: documentRecord.id,
    content: "# 医疗信息化系统\n\n标准化正文",
    manifest: {},
  });
  serviceMocks.getDocumentChunks.mockResolvedValue({
    items: [
      {
        id: "chunk-1",
        chunk_no: 1,
        section_no: 1,
        heading: "核心模块",
        page_no: 2,
        content: "HIS、EMR、LIS 是核心业务系统。",
        char_start: 0,
        char_end: 22,
        token_estimate: 12,
        index_generation: 2,
        is_active: true,
        embedding_status: "vector",
      },
    ],
    page: 1,
    page_size: 20,
    total: 1,
  });
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:document-preview");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/knowledge/:kb_id/documents/:document_id",
        component: DocumentDetailView,
      },
    ],
  });
  await router.push("/knowledge/kb-1/documents/document-1");
  await router.isReady();
  const Harness = defineComponent({
    setup: () => () =>
      h(AntApp, null, {
        default: () => h(DocumentDetailView),
      }),
  });
  const wrapper = mount(Harness, {
    attachTo: window.document.body,
    global: { plugins: [router] },
  });
  await flushPromises();
  return wrapper;
};

describe("真实文档三视图", () => {
  it("默认展示鉴权原文，并可切换 Markdown 与分页分块", async () => {
    const wrapper = await renderDocument();

    expect(serviceMocks.getDocumentOriginal).toHaveBeenCalledWith(
      "document-1",
      expect.any(AbortSignal),
    );
    expect(wrapper.find('object[type="application/pdf"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("OCR 需复核");
    expect(wrapper.text()).toContain("平均置信度 62%");

    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs).toHaveLength(3);
    await tabs[1]?.trigger("click");
    await flushPromises();
    expect(serviceMocks.getDocumentMarkdown).toHaveBeenCalled();
    expect(wrapper.text()).toContain("标准化正文");

    await tabs[2]?.trigger("click");
    await flushPromises();
    expect(serviceMocks.getDocumentChunks).toHaveBeenCalledWith(
      "document-1",
      1,
      20,
      expect.any(AbortSignal),
    );
    expect(wrapper.text()).toContain("核心模块");
    expect(wrapper.text()).toContain("向量就绪");
    expect(wrapper.text()).toContain("字符范围");
  });
});
