import { AxiosHeaders, type AxiosResponse } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../api/client";
import {
  downloadAnswerExport,
  type AnswerExportFormat,
} from "../services/downloads";

const formats = ["markdown", "docx", "pdf"] as const satisfies readonly AnswerExportFormat[];

describe("答案格式导出", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it.each(formats)("将所选 %s 格式传给真实导出接口", async (format) => {
    const blob = new Blob(["answer"]);
    const response: AxiosResponse<Blob> = {
      data: blob,
      status: 200,
      statusText: "OK",
      headers: {
        "content-disposition": `attachment; filename="answer.${format}"`,
        "x-export-id": `export-${format}`,
      },
      config: { headers: new AxiosHeaders() },
    };
    const post = vi.spyOn(apiClient, "post").mockResolvedValue(response);

    const result = await downloadAnswerExport({
      format,
      question: "医疗信息化平台如何规划？",
      answer: "分阶段建设。",
      citations: [],
    });

    expect(post).toHaveBeenCalledWith(
      "/v1/exports/answer",
      {
        format,
        question: "医疗信息化平台如何规划？",
        answer: "分阶段建设。",
        citations: [],
      },
      { responseType: "blob" },
    );
    expect(result.blob).toBe(blob);
    expect(result.exportId).toBe(`export-${format}`);
  });
});
