import { App as AntApp } from "ant-design-vue";
import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import { describe, expect, it, vi } from "vitest";

import DownloadsView from "../views/user/DownloadsView.vue";

const serviceMocks = vi.hoisted(() => ({
  listAllExportTasks: vi.fn(),
  convertAnswerExport: vi.fn(),
  downloadExportBlob: vi.fn(),
  prepareFileSave: vi.fn(),
  save: vi.fn(),
}));

vi.mock("../config/runtime", () => ({
  isRealApiMode: true,
  isMockApiMode: false,
}));
vi.mock("../services/downloads", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/downloads")>()),
  listAllExportTasks: serviceMocks.listAllExportTasks,
  convertAnswerExport: serviceMocks.convertAnswerExport,
  downloadExportBlob: serviceMocks.downloadExportBlob,
}));
vi.mock("../services/file-save", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/file-save")>()),
  prepareFileSave: serviceMocks.prepareFileSave,
}));

describe("我的下载问答格式", () => {
  it("可从 Markdown、Word、PDF 中选择并调用真实转换接口", async () => {
    serviceMocks.listAllExportTasks.mockResolvedValue({
      items: [
        {
          id: "export-1",
          user_id: "user-1",
          format: "markdown",
          document_ids: [],
          options: {
            include_citations: true,
            include_assets: false,
            include_toc: false,
            template: "default",
            page_size: "A4",
            font_size: 12,
            language: "zh-CN",
          },
          status: "done",
          progress: 100,
          source_type: "answer",
          filename: "RAG-answer.md",
          file_size: 100,
          download_url: "/api/v1/exports/export-1/download",
          expires_at: "2026-07-27T00:00:00Z",
          error_code: null,
          error_message: null,
          created_at: "2026-07-26T00:00:00Z",
          finished_at: "2026-07-26T00:00:01Z",
        },
      ],
      page: 1,
      pageSize: 1,
      total: 1,
    });
    serviceMocks.prepareFileSave.mockResolvedValue({ save: serviceMocks.save });
    serviceMocks.convertAnswerExport.mockResolvedValue({
      blob: new Blob(["docx"]),
      filename: "RAG-answer.docx",
      exportId: "export-2",
    });
    const Harness = defineComponent({
      setup: () => () =>
        h(AntApp, null, {
          default: () => h(DownloadsView),
        }),
    });
    const wrapper = mount(Harness, { attachTo: document.body });
    await flushPromises();

    const formatSelect = wrapper.get<HTMLSelectElement>(
      'select[aria-label^="下载 RAG-answer.md 的格式"]',
    );
    expect(
      formatSelect.findAll("option").map((option) => option.text()),
    ).toEqual(["Markdown", "Word", "PDF"]);

    await formatSelect.setValue("docx");
    const downloadButton = wrapper
      .findAll("button")
      .find((button) => button.text().trim() === "下载");
    if (downloadButton === undefined) throw new Error("缺少下载按钮");
    await downloadButton.trigger("click");
    await flushPromises();

    expect(serviceMocks.convertAnswerExport).toHaveBeenCalledWith(
      "export-1",
      "docx",
    );
    expect(serviceMocks.downloadExportBlob).not.toHaveBeenCalled();
    expect(serviceMocks.save).toHaveBeenCalled();
  });
});
