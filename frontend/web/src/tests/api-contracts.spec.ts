import { describe, expect, it } from "vitest";

import {
  assertApiSuccess,
  unwrapApiData,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";

describe("OpenAPI response helpers", () => {
  it("accepts a successful response without data", () => {
    const response: ApiSchema<"APIResponse_NoneType_"> = {
      code: 0,
      message: "success",
      data: null,
      request_id: "request-1",
    };

    expect(() => assertApiSuccess(response)).not.toThrow();
  });

  it("unwraps data and rejects missing data", () => {
    const response: ApiResponse<{ readonly id: string }> = {
      code: 0,
      message: "success",
      data: { id: "item-1" },
      request_id: "request-2",
    };

    expect(unwrapApiData(response)).toEqual({ id: "item-1" });
    expect(() =>
      unwrapApiData({
        code: 0,
        message: "success",
        request_id: "request-3",
      }),
    ).toThrow("请求失败，请稍后重试");
  });

  it("uses the API message for business failures", () => {
    expect(() => assertApiSuccess({ code: 409, message: "资源冲突" })).toThrow(
      "资源冲突",
    );
    expect(() =>
      assertApiSuccess({ code: 500, message: "" }, "操作失败"),
    ).toThrow("操作失败");
  });
});
