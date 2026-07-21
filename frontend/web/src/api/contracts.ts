import type { components } from "./generated/openapi";

type ApiEnvelope = components["schemas"]["APIResponse_NoneType_"];

export type ApiSchema<Name extends keyof components["schemas"]> =
  components["schemas"][Name];

export type ApiResponse<T> = Readonly<
  Omit<ApiEnvelope, "data"> & { readonly data?: T | null }
>;

export class ApiResponseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiResponseError";
  }
}

export const assertApiSuccess = (
  response: Pick<ApiEnvelope, "code" | "message">,
  fallbackMessage = "请求失败，请稍后重试",
): void => {
  if (response.code !== 0) {
    throw new ApiResponseError(response.message || fallbackMessage);
  }
};

export const unwrapApiData = <T>(response: ApiResponse<T>): T => {
  assertApiSuccess(response);
  if (response.data === null || response.data === undefined) {
    throw new ApiResponseError("请求失败，请稍后重试");
  }
  return response.data;
};
