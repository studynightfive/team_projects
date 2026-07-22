import { apiClient } from "../api/client";
import {
  assertApiSuccess,
  unwrapApiData,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";
import type { paths } from "../api/generated/openapi";

type ExportOptions = Readonly<Required<ApiSchema<"ExportOptions">>>;
type ExportCreateRequest =
  paths["/exports"]["post"]["requestBody"]["content"]["application/json"];

export type ExportFormat = ExportCreateRequest["format"];
export type ExportStatus = ApiSchema<"ExportTaskResponse">["status"];

export type ExportTaskRecord = Readonly<
  Omit<
    Required<ApiSchema<"ExportTaskResponse">>,
    "document_ids" | "options"
  > & {
    readonly document_ids: readonly string[];
    readonly options: ExportOptions;
  }
>;

export type ExportCreatePayload = Readonly<
  Omit<ExportCreateRequest, "document_ids" | "options"> & {
    readonly document_ids: readonly string[];
    readonly options?: ExportOptions;
  }
>;

export type ExportTaskPage = Readonly<{
  items: readonly ExportTaskRecord[];
  page: number;
  pageSize: number;
  total: number;
}>;

type ExportTaskPageResponse = Readonly<
  Omit<ApiSchema<"PaginatedData_ExportTaskResponse_">, "items"> & {
    readonly items: readonly ExportTaskRecord[];
  }
>;

const toClientPath = (downloadUrl: string): string =>
  downloadUrl.startsWith("/api/")
    ? downloadUrl.slice("/api".length)
    : downloadUrl;

const getFilenameFromHeader = (
  header: string | undefined,
): string | undefined => {
  if (header === undefined || header.trim() === "") return undefined;

  const encoded = /filename\*=UTF-8''([^;]+)/iu.exec(header)?.[1];
  if (encoded !== undefined) {
    try {
      return decodeURIComponent(encoded);
    } catch {
      return encoded;
    }
  }

  return /filename="?([^";]+)"?/iu.exec(header)?.[1];
};

export const listExportTasks = async (
  params: { readonly page?: number; readonly pageSize?: number } = {},
  signal?: AbortSignal,
): Promise<ExportTaskPage> => {
  const response = await apiClient.get<ApiResponse<ExportTaskPageResponse>>(
    "/v1/exports",
    {
      params: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 50,
      },
      signal,
    },
  );
  const data = unwrapApiData(response.data);
  return {
    items: data.items,
    page: data.page,
    pageSize: data.page_size,
    total: data.total,
  };
};

export const listAllExportTasks = async (
  signal?: AbortSignal,
): Promise<ExportTaskPage> => {
  const items: ExportTaskRecord[] = [];
  let page = 1;
  let total = 0;
  do {
    const current = await listExportTasks({ page, pageSize: 100 }, signal);
    items.push(...current.items);
    total = current.total;
    page += 1;
    if (current.items.length === 0) break;
  } while (items.length < total);
  return { items, page: 1, pageSize: Math.max(items.length, 1), total };
};

export const createExportTask = async (
  payload: ExportCreatePayload,
): Promise<ExportTaskRecord> => {
  const response = await apiClient.post<ApiResponse<ExportTaskRecord>>(
    "/v1/exports",
    payload,
  );
  return unwrapApiData(response.data);
};

export const downloadAnswerExport = async (payload: {
  readonly question: string;
  readonly answer: string;
  readonly format?: "markdown" | "txt" | "docx";
  readonly citations?: readonly Readonly<Record<string, string | number | null>>[];
}): Promise<Blob> => {
  const response = await apiClient.post<Blob>(
    "/v1/exports/answer",
    {
      format: payload.format ?? "markdown",
      question: payload.question,
      answer: payload.answer,
      citations: payload.citations ?? [],
    },
    { responseType: "blob" },
  );
  return response.data;
};

export const deleteExportTask = async (exportId: string): Promise<void> => {
  const response = await apiClient.delete<ApiSchema<"APIResponse_NoneType_">>(
    `/v1/exports/${exportId}`,
  );
  assertApiSuccess(response.data);
};

export const downloadExportBlob = async (
  downloadUrl: string,
): Promise<{ readonly blob: Blob; readonly filename?: string }> => {
  const response = await apiClient.get<Blob>(toClientPath(downloadUrl), {
    responseType: "blob",
  });
  return {
    blob: response.data,
    filename: getFilenameFromHeader(response.headers["content-disposition"]),
  };
};
