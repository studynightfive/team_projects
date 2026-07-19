import { apiClient } from "../api/client";

interface ApiResponse<T> {
  readonly code: number;
  readonly message: string;
  readonly data: T | null;
  readonly request_id: string;
}

interface PaginatedData<T> {
  readonly items: readonly T[];
  readonly page: number;
  readonly page_size: number;
  readonly total: number;
}

export type ExportFormat = "pdf" | "docx" | "markdown" | "csv" | "txt";

export type ExportStatus =
  | "pending"
  | "running"
  | "done"
  | "failed"
  | "expired"
  | "cancelled";

export interface ExportTaskRecord {
  readonly id: string;
  readonly user_id: string;
  readonly format: ExportFormat;
  readonly document_ids: readonly string[];
  readonly options: Record<string, unknown>;
  readonly status: ExportStatus;
  readonly progress: number;
  readonly file_path: string | null;
  readonly file_size: number | null;
  readonly download_url: string | null;
  readonly expires_at: string;
  readonly error_code: string | null;
  readonly error_message: string | null;
  readonly created_at: string | null;
  readonly finished_at: string | null;
}

export interface ExportCreatePayload {
  readonly format: ExportFormat;
  readonly document_ids: readonly string[];
}

export interface ExportTaskPage {
  readonly items: readonly ExportTaskRecord[];
  readonly page: number;
  readonly pageSize: number;
  readonly total: number;
}

const unwrap = <T>(response: ApiResponse<T>): T => {
  if (response.code !== 0 || response.data === null) {
    throw new Error(response.message || "请求失败，请稍后重试");
  }
  return response.data;
};

const toClientPath = (downloadUrl: string): string =>
  downloadUrl.startsWith("/api/")
    ? downloadUrl.slice("/api".length)
    : downloadUrl;

const getFilenameFromHeader = (header: string | undefined): string | undefined => {
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
  const response = await apiClient.get<
    ApiResponse<PaginatedData<ExportTaskRecord>>
  >("/v1/exports", {
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 50,
    },
    signal,
  });
  const data = unwrap(response.data);
  return {
    items: data.items,
    page: data.page,
    pageSize: data.page_size,
    total: data.total,
  };
};

export const createExportTask = async (
  payload: ExportCreatePayload,
): Promise<ExportTaskRecord> => {
  const response = await apiClient.post<ApiResponse<ExportTaskRecord>>(
    "/v1/exports",
    payload,
  );
  return unwrap(response.data);
};

export const deleteExportTask = async (exportId: string): Promise<void> => {
  await apiClient.delete(`/v1/exports/${exportId}`);
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
