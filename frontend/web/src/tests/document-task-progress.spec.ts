import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import DocumentTaskProgress from "../components/documents/DocumentTaskProgress.vue";
import type { DocumentBatchTaskItem } from "../services/knowledge";

const serviceMocks = vi.hoisted(() => ({
  getDocumentTask: vi.fn(),
}));

vi.mock("../services/knowledge", () => ({
  getDocumentTask: serviceMocks.getDocumentTask,
}));

const queuedItem: DocumentBatchTaskItem = {
  document_id: "document-1",
  document_title: "医疗接口规范",
  task: {
    task_id: "task-1",
    task_type: "document_convert",
    status: "queued",
    stage: "uploaded",
    progress: 5,
    retry_count: 0,
    request_id: "request-1",
    error_code: null,
    error_message: null,
    created_at: "2026-07-25T00:00:00Z",
    finished_at: null,
  },
};

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("文档任务进度轮询", () => {
  it("任务进入终态后更新进度并停止轮询", async () => {
    vi.useFakeTimers();
    serviceMocks.getDocumentTask.mockResolvedValue({
      ...queuedItem.task,
      status: "succeeded",
      stage: "ready",
      progress: 100,
      finished_at: "2026-07-25T00:00:01Z",
    });

    const wrapper = mount(DocumentTaskProgress, {
      props: { items: [queuedItem], title: "上传处理进度" },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("100%");
    await vi.advanceTimersByTimeAsync(1000);
    expect(wrapper.emitted("finished")).toHaveLength(1);
    expect(serviceMocks.getDocumentTask).toHaveBeenCalledTimes(1);
  });

  it("组件卸载后已中止请求不能重新创建定时器", async () => {
    vi.useFakeTimers();
    serviceMocks.getDocumentTask.mockImplementation(
      (_taskId: string, signal?: AbortSignal) =>
        new Promise((_resolve, reject) => {
          signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        }),
    );

    const wrapper = mount(DocumentTaskProgress, {
      props: { items: [queuedItem] },
    });
    expect(serviceMocks.getDocumentTask).toHaveBeenCalledTimes(1);

    wrapper.unmount();
    await flushPromises();
    await vi.advanceTimersByTimeAsync(2000);

    expect(serviceMocks.getDocumentTask).toHaveBeenCalledTimes(1);
  });
});
