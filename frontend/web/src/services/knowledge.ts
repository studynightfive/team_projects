import { apiClient } from "../api/client";
import {
  assertApiSuccess,
  unwrapApiData,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";
import type { paths } from "../api/generated/openapi";

export type KnowledgeBaseRecord = Readonly<
  Required<ApiSchema<"KnowledgeBaseSummary">>
>;

export type DocumentRecord = Readonly<Required<ApiSchema<"DocumentSummary">>>;
export type ChunkStrategy = "fixed" | "semantic" | "recursive" | "format";

export type DocumentUploadOptions = Readonly<{
  chunkStrategy: ChunkStrategy;
  chunkSize: number;
  chunkOverlap: number;
}>;

export type DocumentDetailRecord = Readonly<
  Required<ApiSchema<"DocumentDetail">>
>;

export type MarkdownContent = Readonly<Required<ApiSchema<"MarkdownContent">>>;

export type UploadResult = Readonly<
  Omit<Required<ApiSchema<"UploadResultItem">>, "document"> & {
    readonly document: DocumentRecord;
  }
>;

type KnowledgeBasePage = Readonly<
  Omit<ApiSchema<"PaginatedData_KnowledgeBaseSummary_">, "items"> & {
    readonly items: readonly KnowledgeBaseRecord[];
  }
>;

type DocumentPage = Readonly<
  Omit<ApiSchema<"PaginatedData_DocumentSummary_">, "items"> & {
    readonly items: readonly DocumentRecord[];
  }
>;

type UploadResponse = Readonly<
  Omit<ApiSchema<"UploadResponse">, "items"> & {
    readonly items: readonly UploadResult[];
  }
>;

type KnowledgeBaseCreateRequest =
  paths["/knowledge-bases"]["post"]["requestBody"]["content"]["application/json"];

type KnowledgeBaseCreatePayload = Readonly<KnowledgeBaseCreateRequest>;

type KnowledgeBaseUpdatePayload = Readonly<
  paths["/knowledge-bases/{kb_id}"]["patch"]["requestBody"]["content"]["application/json"]
>;

export const listKnowledgeBases = async (
  signal?: AbortSignal,
): Promise<readonly KnowledgeBaseRecord[]> => {
  const items: KnowledgeBaseRecord[] = [];
  let page = 1;
  let total = 0;
  do {
    const response = await apiClient.get<ApiResponse<KnowledgeBasePage>>(
      "/v1/knowledge-bases",
      { params: { page, page_size: 100 }, signal },
    );
    const data = unwrapApiData(response.data);
    items.push(...data.items);
    total = data.total;
    page += 1;
    if (data.items.length === 0) break;
  } while (items.length < total);
  return items;
};

export const createKnowledgeBase = async (
  payload: KnowledgeBaseCreatePayload,
): Promise<KnowledgeBaseRecord> => {
  const response = await apiClient.post<ApiResponse<KnowledgeBaseRecord>>(
    "/v1/knowledge-bases",
    payload,
  );
  return unwrapApiData(response.data);
};

export const updateKnowledgeBase = async (
  kbId: string,
  payload: KnowledgeBaseUpdatePayload,
): Promise<KnowledgeBaseRecord> => {
  const response = await apiClient.patch<ApiResponse<KnowledgeBaseRecord>>(
    `/v1/knowledge-bases/${kbId}`,
    payload,
  );
  return unwrapApiData(response.data);
};

export const listDocuments = async (
  kbId: string,
  signal?: AbortSignal,
): Promise<readonly DocumentRecord[]> => {
  const items: DocumentRecord[] = [];
  let page = 1;
  let total = 0;
  do {
    const response = await apiClient.get<ApiResponse<DocumentPage>>(
      `/v1/knowledge-bases/${kbId}/documents`,
      { params: { page, page_size: 100 }, signal },
    );
    const data = unwrapApiData(response.data);
    items.push(...data.items);
    total = data.total;
    page += 1;
    if (data.items.length === 0) break;
  } while (items.length < total);
  return items;
};

export const getDocument = async (
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentDetailRecord> => {
  const response = await apiClient.get<ApiResponse<DocumentDetailRecord>>(
    `/v1/documents/${documentId}`,
    { signal },
  );
  return unwrapApiData(response.data);
};

export const getDocumentMarkdown = async (
  documentId: string,
  signal?: AbortSignal,
): Promise<MarkdownContent> => {
  const response = await apiClient.get<ApiResponse<MarkdownContent>>(
    `/v1/documents/${documentId}/markdown`,
    { signal },
  );
  return unwrapApiData(response.data);
};

export const uploadDocuments = async (
  kbId: string,
  files: readonly File[],
  options: DocumentUploadOptions,
): Promise<readonly UploadResult[]> => {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  form.append("duplicate_policy", "new_version");
  form.append("ocr_enabled", "true");
  form.append("language", "chi_sim+eng");
  form.append("chunk_strategy", options.chunkStrategy);
  form.append("chunk_size", String(options.chunkSize));
  form.append("chunk_overlap", String(options.chunkOverlap));

  const response = await apiClient.post<ApiResponse<UploadResponse>>(
    `/v1/knowledge-bases/${kbId}/documents`,
    form,
  );
  return unwrapApiData(response.data).items;
};

export const reprocessDocument = async (documentId: string): Promise<void> => {
  const response = await apiClient.post<
    ApiResponse<Readonly<Required<ApiSchema<"TaskResponse">>>>
  >(`/v1/documents/${documentId}/reprocess`, {});
  unwrapApiData(response.data);
};

export const deleteDocument = async (documentId: string): Promise<void> => {
  const response = await apiClient.delete<ApiSchema<"APIResponse_NoneType_">>(
    `/v1/documents/${documentId}`,
  );
  assertApiSuccess(response.data);
};
