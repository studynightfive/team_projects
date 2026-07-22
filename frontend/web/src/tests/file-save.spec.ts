import { afterEach, describe, expect, it, vi } from "vitest";

import { prepareFileSave } from "../services/file-save";

const options = {
  suggestedName: "RAG问答结果.md",
  description: "Markdown 文档",
  mediaType: "text/markdown",
  extensions: [".md"],
} as const;

afterEach(() => {
  Object.defineProperty(window, "showSaveFilePicker", {
    configurable: true,
    value: undefined,
  });
});

describe("文件保存位置选择", () => {
  it("在支持的浏览器中写入用户选择的文件句柄", async () => {
    const write = vi.fn<(blob: Blob) => Promise<void>>().mockResolvedValue();
    const close = vi.fn<() => Promise<void>>().mockResolvedValue();
    const picker = vi.fn().mockResolvedValue({
      createWritable: vi.fn().mockResolvedValue({ write, close }),
    });
    Object.defineProperty(window, "showSaveFilePicker", {
      configurable: true,
      value: picker,
    });

    const destination = await prepareFileSave(options);
    const blob = new Blob(["answer"], { type: "text/markdown" });
    await destination?.save(blob);

    expect(picker).toHaveBeenCalledWith(
      expect.objectContaining({ suggestedName: "RAG问答结果.md" }),
    );
    expect(write).toHaveBeenCalledWith(blob);
    expect(close).toHaveBeenCalledOnce();
  });

  it("用户取消位置选择时不返回保存目标", async () => {
    Object.defineProperty(window, "showSaveFilePicker", {
      configurable: true,
      value: vi
        .fn()
        .mockRejectedValue(new DOMException("cancelled", "AbortError")),
    });

    await expect(prepareFileSave(options)).resolves.toBeUndefined();
  });

  it("不支持文件选择器时回退到标准浏览器下载", async () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    const destination = await prepareFileSave(options);

    await destination?.save(new Blob(["answer"]), "server-answer.md");

    expect(click).toHaveBeenCalledOnce();
  });
});
