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

export interface KnowledgeBaseRecord {
  readonly id: string;
  readonly name: string;
  readonly description: string | null;
  readonly status: string;
  readonly chunk_size: number;
  readonly chunk_overlap: number;
  readonly document_count: number;
  readonly ready_document_count: number;
  readonly chunk_count: number;
  readonly created_at: string | null;
  readonly updated_at: string | null;
}

export interface DocumentRecord {
  readonly id: string;
  readonly knowledge_base_id: string;
  readonly title: string;
  readonly original_filename: string;
  readonly extension: string;
  readonly mime_type: string;
  readonly size_bytes: number;
  readonly status: string;
  readonly parser_name: string | null;
  readonly page_count: number | null;
  readonly error_message: string | null;
  readonly created_at: string | null;
  readonly updated_at: string | null;
}

export interface DocumentDetailRecord extends DocumentRecord {
  readonly language: string;
  readonly ocr_enabled: boolean;
  readonly markdown_path: string | null;
  readonly manifest_path: string | null;
  readonly is_active_index: boolean;
}

export interface MarkdownContent {
  readonly document_id: string;
  readonly content: string;
  readonly manifest: Record<string, unknown>;
}

export interface UploadResult {
  readonly document: DocumentRecord;
  readonly task_id: string;
  readonly skipped: boolean;
  readonly message: string | null;
}

const unwrap = <T>(response: ApiResponse<T>): T => {
  if (response.code !== 0 || response.data === null) {
    throw new Error(response.message || "请求失败，请稍后重试");
  }
  return response.data;
};

export const listKnowledgeBases = async (
  signal?: AbortSignal,
): Promise<readonly KnowledgeBaseRecord[]> => {
  const response = await apiClient.get<ApiResponse<PaginatedData<KnowledgeBaseRecord>>>(
    "/v1/knowledge-bases",
    { signal },
  );
  return unwrap(response.data).items;
};

export const createKnowledgeBase = async (
  payload: Pick<KnowledgeBaseRecord, "name"> & {
    readonly description?: string;
    readonly chunk_size?: number;
    readonly chunk_overlap?: number;
  },
): Promise<KnowledgeBaseRecord> => {
  const response = await apiClient.post<ApiResponse<KnowledgeBaseRecord>>(
    "/v1/knowledge-bases",
    payload,
  );
  return unwrap(response.data);
};

export const updateKnowledgeBase = async (
  kbId: string,
  payload: {
    readonly name?: string;
    readonly description?: string;
    readonly status?: string;
    readonly chunk_size?: number;
    readonly chunk_overlap?: number;
  },
): Promise<KnowledgeBaseRecord> => {
  const response = await apiClient.patch<ApiResponse<KnowledgeBaseRecord>>(
    `/v1/knowledge-bases/${kbId}`,
    payload,
  );
  return unwrap(response.data);
};

export const listDocuments = async (
  kbId: string,
  signal?: AbortSignal,
): Promise<readonly DocumentRecord[]> => {
  const response = await apiClient.get<ApiResponse<PaginatedData<DocumentRecord>>>(
    `/v1/knowledge-bases/${kbId}/documents`,
    { signal },
  );
  return unwrap(response.data).items;
};

export const getDocument = async (
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentDetailRecord> => {
  const response = await apiClient.get<ApiResponse<DocumentDetailRecord>>(
    `/v1/documents/${documentId}`,
    { signal },
  );
  return unwrap(response.data);
};

export const getDocumentMarkdown = async (
  documentId: string,
  signal?: AbortSignal,
): Promise<MarkdownContent> => {
  const response = await apiClient.get<ApiResponse<MarkdownContent>>(
    `/v1/documents/${documentId}/markdown`,
    { signal },
  );
  return unwrap(response.data);
};

export const uploadDocuments = async (
  kbId: string,
  files: readonly File[],
): Promise<readonly UploadResult[]> => {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  form.append("duplicate_policy", "new_version");
  form.append("ocr_enabled", "true");
  form.append("language", "chi_sim+eng");

  const response = await apiClient.post<
    ApiResponse<{ readonly items: readonly UploadResult[] }>
  >(`/v1/knowledge-bases/${kbId}/documents`, form);
  return unwrap(response.data).items;
};

export const reprocessDocument = async (documentId: string): Promise<void> => {
  const response = await apiClient.post<ApiResponse<unknown>>(
    `/v1/documents/${documentId}/reprocess`,
    {},
  );
  unwrap(response.data);
};

export const deleteDocument = async (documentId: string): Promise<void> => {
  const response = await apiClient.delete<ApiResponse<null>>(
    `/v1/documents/${documentId}`,
  );
  unwrap(response.data);
};
