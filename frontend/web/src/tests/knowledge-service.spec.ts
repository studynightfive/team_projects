import { describe, expect, it, vi } from "vitest";

import {
  getUploadTaskItems,
  type UploadResult,
} from "../services/knowledge";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock("../api/client", () => ({
  apiClient: {
    get: apiMocks.get,
  },
}));

describe("知识库服务上传任务映射", () => {
  it("任务详情暂时不可用时保留上传成功结果并交给轮询恢复", async () => {
    apiMocks.get.mockRejectedValueOnce(new Error("temporary network error"));
    const uploadResult: UploadResult = {
      document: {
        id: "document-1",
        knowledge_base_id: "kb-1",
        title: "医疗接口规范",
        original_filename: "医疗接口规范.pdf",
        folder_path: "",
        extension: ".pdf",
        mime_type: "application/pdf",
        size_bytes: 1024,
        content_hash: "0".repeat(64),
        version: 1,
        status: "uploaded",
        parser_name: null,
        chunk_strategy: "recursive",
        chunk_size: 800,
        chunk_overlap: 120,
        page_count: null,
        error_code: null,
        error_message: null,
        created_at: "2026-07-25T00:00:00Z",
        updated_at: "2026-07-25T00:00:00Z",
        deleted_at: null,
        purge_after: null,
      },
      task_id: "task-1",
      skipped: false,
      message: null,
    };

    const items = await getUploadTaskItems([uploadResult]);

    expect(items).toHaveLength(1);
    expect(items[0]?.task).toMatchObject({
      task_id: "task-1",
      status: "queued",
      stage: "uploaded",
      progress: 5,
    });
  });
});
