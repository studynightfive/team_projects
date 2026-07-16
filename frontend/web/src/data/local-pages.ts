import rawLocalPageData from "../../../../docs/design/m02-m14-local-pages/mock-data.json";

if (rawLocalPageData.meta.apiRequestsAllowed !== false) {
  throw new Error("M02-M14 本地页面数据不得启用业务 API 请求");
}

/** 这些数据只描述本地界面，不代表后端 DTO 或 OpenAPI 契约。 */
export const localPageData = rawLocalPageData;

export type LocalPageData = typeof localPageData;
