import { App as AntApp } from "ant-design-vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { defineComponent, h } from "vue";
import { describe, expect, it, vi } from "vitest";

import { useSessionStore } from "../stores/session";
import KnowledgeDetailView from "../views/user/KnowledgeDetailView.vue";

const serviceMocks = vi.hoisted(() => ({
  listKnowledgeBases: vi.fn(),
  listDocuments: vi.fn(),
  uploadDocuments: vi.fn(),
}));

vi.mock("../config/runtime", () => ({
  isRealApiMode: true,
  isMockApiMode: false,
}));
vi.mock("../services/knowledge", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/knowledge")>()),
  ...serviceMocks,
}));

const personalKnowledgeBase = {
  id: "personal-kb",
  name: "我的个人知识库",
  description: "个人文档检索空间",
  department_id: "department-1",
  department_name: "医疗信息化部",
  kind: "personal",
  owner_user_id: "user-1",
  status: "active",
  document_count: 1,
  ready_document_count: 1,
  chunk_count: 2,
  created_at: "2026-07-24T00:00:00Z",
  updated_at: "2026-07-24T00:00:00Z",
} as const;

const documentRecord = {
  id: "document-1",
  knowledge_base_id: "personal-kb",
  title: "医疗信息化建设方案",
  original_filename: "医疗信息化建设方案.pdf",
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
} as const;

const renderKnowledgeDetail = async () => {
  serviceMocks.listKnowledgeBases.mockResolvedValue([personalKnowledgeBase]);
  serviceMocks.listDocuments.mockResolvedValue([documentRecord]);
  serviceMocks.uploadDocuments.mockResolvedValue([]);

  const pinia = createPinia();
  setActivePinia(pinia);
  useSessionStore().setUser({
    id: "user-1",
    username: "liuhaiwang",
    display_name: "刘海旺",
    department: { id: "department-1", name: "医疗信息化部" },
    roles: [{ id: "role-1", name: "普通用户" }],
    permissions: ["personal.document.upload"],
    knowledge_base_access: [
      { kb_id: "personal-kb", access_level: "admin" },
    ],
  });

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/knowledge/:kb_id",
        component: KnowledgeDetailView,
      },
      {
        path: "/knowledge/:kb_id/documents/:document_id",
        component: { render: () => h("div") },
      },
      {
        path: "/knowledge",
        component: { render: () => h("div") },
      },
      {
        path: "/downloads",
        component: { render: () => h("div") },
      },
    ],
  });
  await router.push("/knowledge/personal-kb");
  await router.isReady();

  const Harness = defineComponent({
    setup: () => () =>
      h(AntApp, null, {
        default: () => h(KnowledgeDetailView),
      }),
  });
  const wrapper = mount(Harness, {
    attachTo: window.document.body,
    global: { plugins: [pinia, router] },
  });
  await flushPromises();
  return wrapper;
};

describe("个人知识库移动上传流程", () => {
  it("展示可点击上传区、单文档操作列标识并提交所选切分配置", async () => {
    const wrapper = await renderKnowledgeDetail();

    const uploadZone = wrapper.get(".upload-drop-zone");
    expect(uploadZone.attributes("role")).toBe("button");
    expect(uploadZone.attributes("tabindex")).toBe("0");
    expect(wrapper.get(".chunk-options").findAll("label")).toHaveLength(3);
    expect(
      wrapper.get(".document-table").classes("mobile-sticky-actions"),
    ).toBe(true);

    await wrapper.get(".chunk-options select").setValue("semantic");
    const numericInputs = wrapper.findAll<HTMLInputElement>(
      '.chunk-options input[type="number"]',
    );
    await numericInputs[0]?.setValue(600);
    await numericInputs[1]?.setValue(80);

    const file = new File(["医疗信息化"], "方案.md", {
      type: "text/markdown",
    });
    const input = wrapper.get<HTMLInputElement>('input[type="file"]');
    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [file],
    });
    await input.trigger("change");
    await flushPromises();

    expect(serviceMocks.uploadDocuments).toHaveBeenCalledWith(
      "personal-kb",
      [file],
      {
        chunkStrategy: "semantic",
        chunkSize: 600,
        chunkOverlap: 80,
      },
    );
  });
});
