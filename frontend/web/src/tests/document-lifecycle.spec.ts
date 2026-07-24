import { App as AntApp } from "ant-design-vue";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { defineComponent, h } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import DocumentsView from "../views/admin/DocumentsView.vue";

const adminMocks = vi.hoisted(() => ({
  listAdminDocuments: vi.fn(),
}));
const knowledgeMocks = vi.hoisted(() => ({
  batchDeleteDocuments: vi.fn(),
  batchReprocessDocuments: vi.fn(),
  getDocumentTask: vi.fn(),
  listRecycleBin: vi.fn(),
  restoreDocuments: vi.fn(),
}));

vi.mock("../services/admin", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/admin")>()),
  ...adminMocks,
}));
vi.mock("../services/knowledge", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/knowledge")>()),
  ...knowledgeMocks,
}));

const documentRecord = (index: number) => ({
  id: `document-${index}`,
  knowledge_base_id: "kb-1",
  knowledge_base_name: "医疗知识库",
  title: `医疗文档 ${index}`,
  original_filename: `医疗文档-${index}.md`,
  folder_path: "",
  extension: ".md",
  mime_type: "text/markdown",
  size_bytes: 1024,
  content_hash: String(index).padStart(64, "0"),
  version: 1,
  status: "ready",
  parser_name: "markdown",
  chunk_strategy: "recursive",
  chunk_size: 800,
  chunk_overlap: 120,
  page_count: 1,
  error_code: null,
  error_message: null,
  created_at: "2026-07-24T00:00:00Z",
  updated_at: "2026-07-24T00:00:00Z",
  deleted_at: null,
  purge_after: null,
});

const taskItem = {
  document_id: "document-1",
  document_title: "医疗文档 1",
  task: {
    task_id: "task-1",
    task_type: "document_convert",
    status: "succeeded",
    stage: "ready",
    progress: 100,
    retry_count: 1,
    error_code: null,
    error_message: null,
    request_id: "request-1",
    created_at: "2026-07-24T00:00:00Z",
    finished_at: "2026-07-24T00:00:01Z",
  },
} as const;

const findButton = (wrapper: VueWrapper, label: string) => {
  const button = wrapper
    .findAll("button")
    .find((candidate) => candidate.text().includes(label));
  if (button === undefined) throw new Error(`未找到按钮：${label}`);
  return button;
};

const renderView = async () => {
  const active = Array.from({ length: 12 }, (_, index) =>
    documentRecord(index + 1),
  );
  const recycled = [
    {
      ...documentRecord(20),
      status: "cancelled",
      deleted_at: "2026-07-24T00:00:00Z",
      purge_after: "2026-08-23T00:00:00Z",
      deleted_by: "admin-1",
    },
  ];
  adminMocks.listAdminDocuments.mockResolvedValue({
    items: active,
    page: 1,
    page_size: 100,
    total: active.length,
  });
  knowledgeMocks.listRecycleBin.mockResolvedValue(recycled);
  knowledgeMocks.batchDeleteDocuments.mockResolvedValue(10);
  knowledgeMocks.restoreDocuments.mockResolvedValue([taskItem]);
  knowledgeMocks.getDocumentTask.mockResolvedValue(taskItem.task);

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/admin/documents", component: DocumentsView },
      {
        path: "/knowledge/:kb_id/documents/:document_id",
        component: { render: () => h("div") },
      },
    ],
  });
  await router.push("/admin/documents");
  await router.isReady();

  const Harness = defineComponent({
    setup: () => () =>
      h(AntApp, null, {
        default: () => h(DocumentsView),
      }),
  });
  const wrapper = mount(Harness, {
    attachTo: document.body,
    global: { plugins: [router] },
  });
  await flushPromises();
  return wrapper;
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("文档批量生命周期", () => {
  it("一次选择十个文档软删除，并从回收站恢复后展示任务进度", async () => {
    const wrapper = await renderView();
    const rowCheckboxes = wrapper.findAll<HTMLInputElement>(
      'tbody input[type="checkbox"]',
    );
    expect(rowCheckboxes.length).toBeGreaterThanOrEqual(10);

    for (const checkbox of rowCheckboxes.slice(0, 10)) {
      await checkbox.setValue(true);
    }
    await findButton(wrapper, "批量删除").trigger("click");
    await flushPromises();

    const confirmButton = Array.from(
      document.querySelectorAll<HTMLButtonElement>("button"),
    ).find((button) => button.textContent?.includes("移入回收站"));
    expect(confirmButton).toBeDefined();
    confirmButton?.click();
    await flushPromises();

    expect(knowledgeMocks.batchDeleteDocuments).toHaveBeenCalledWith(
      Array.from({ length: 10 }, (_, index) => `document-${index + 1}`),
    );

    await findButton(wrapper, "回收站").trigger("click");
    await flushPromises();
    await wrapper
      .get<HTMLInputElement>('tbody input[type="checkbox"]')
      .setValue(true);
    await findButton(wrapper, "批量恢复").trigger("click");
    await flushPromises();

    expect(knowledgeMocks.restoreDocuments).toHaveBeenCalledWith([
      "document-20",
    ]);
    expect(wrapper.text()).toContain("重新处理进度");
    expect(wrapper.text()).toContain("100%");
    wrapper.unmount();
  });
});
