import { App as AntApp } from "ant-design-vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { defineComponent, h } from "vue";
import { describe, expect, it, vi } from "vitest";

import AdminDocumentPreviewDrawer from "../components/documents/AdminDocumentPreviewDrawer.vue";

const serviceMocks = vi.hoisted(() => ({
  getDocument: vi.fn(),
  getDocumentOriginal: vi.fn(),
  getDocumentMarkdown: vi.fn(),
  getDocumentChunks: vi.fn(),
}));

vi.mock("../services/knowledge", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/knowledge")>()),
  ...serviceMocks,
}));

const adminDocument = {
  id: "document-1",
  knowledge_base_id: "kb-1",
  knowledge_base_name: "医疗知识库",
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
  created_at: "2026-07-26T00:00:00Z",
  updated_at: "2026-07-26T00:00:00Z",
  deleted_at: null,
  purge_after: null,
} as const;

describe("管理端文档原地预览", () => {
  it("留在管理页面并读取原文、Markdown 与分块", async () => {
    serviceMocks.getDocument.mockResolvedValue({
      ...adminDocument,
      language: "chi_sim+eng",
      ocr_enabled: true,
      is_active_index: true,
      ocr: {
        status: "completed",
        language: "chi_sim+eng",
        average_confidence: 0.96,
        review_required: false,
        message: "OCR 已完成",
      },
    });
    serviceMocks.getDocumentOriginal.mockResolvedValue(
      new Blob(["pdf"], { type: "application/pdf" }),
    );
    serviceMocks.getDocumentMarkdown.mockResolvedValue({
      document_id: "document-1",
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
          page_no: 1,
          content: "HIS、EMR、LIS 是核心业务系统。",
          char_start: 0,
          char_end: 22,
          token_estimate: 12,
          index_generation: 1,
          is_active: true,
          embedding_status: "vector",
        },
      ],
      page: 1,
      page_size: 20,
      total: 1,
    });
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:admin-preview");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: "/admin/documents",
          component: { template: "<div />" },
        },
      ],
    });
    await router.push("/admin/documents");
    await router.isReady();
    const Harness = defineComponent({
      setup: () => () =>
        h(AntApp, null, {
          default: () =>
            h(AdminDocumentPreviewDrawer, {
              open: true,
              document: adminDocument,
            }),
        }),
    });
    mount(Harness, {
      attachTo: document.body,
      global: { plugins: [router] },
    });
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/admin/documents");
    expect(serviceMocks.getDocumentOriginal).toHaveBeenCalled();
    expect(document.querySelector('object[type="application/pdf"]')).not.toBeNull();

    const tabButtons = Array.from(
      document.querySelectorAll<HTMLButtonElement>('[role="tab"]'),
    );
    const markdownTab = tabButtons.find((button) =>
      button.textContent?.includes("Markdown"),
    );
    const chunksTab = tabButtons.find((button) =>
      button.textContent?.includes("分块"),
    );
    if (markdownTab === undefined || chunksTab === undefined) {
      throw new Error("缺少文档预览标签");
    }
    markdownTab.click();
    await flushPromises();
    expect(serviceMocks.getDocumentMarkdown).toHaveBeenCalledWith(
      "document-1",
      expect.any(AbortSignal),
    );
    expect(document.body.textContent).toContain("标准化正文");

    chunksTab.click();
    await flushPromises();
    expect(serviceMocks.getDocumentChunks).toHaveBeenCalled();
    expect(document.body.textContent).toContain("核心模块");
  });
});
