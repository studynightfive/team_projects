import { apiClient } from "../api/client";
import type { KnowledgeBaseRecord } from "./knowledge";

interface ApiResponse<T> {
  readonly code: number;
  readonly message: string;
  readonly data: T | null;
  readonly request_id: string;
}

interface PageData<T> {
  readonly items: readonly T[];
  readonly page: number;
  readonly page_size: number;
  readonly total: number;
}

const unwrap = <T>(response: ApiResponse<T>): T => {
  if (response.code !== 0 || response.data === null) {
    throw new Error(response.message || "请求失败，请稍后重试");
  }
  return response.data;
};

export interface RoleBrief {
  readonly id: string;
  readonly name: string;
}

export interface AdminUser {
  readonly id: string;
  readonly username: string;
  readonly display_name: string;
  readonly status: string;
  readonly roles: readonly RoleBrief[];
  readonly last_login_at: string | null;
  readonly created_at: string | null;
}

export interface AdminRole {
  readonly id: string;
  readonly name: string;
  readonly description: string | null;
  readonly status: string;
  readonly permissions_count: number;
  readonly created_at: string | null;
}

export interface RoleDetail {
  readonly id: string;
  readonly name: string;
  readonly description: string | null;
  readonly status: string;
  readonly permissions: readonly PermissionItem[];
  readonly created_at: string | null;
  readonly updated_at: string | null;
}

export interface PermissionItem {
  readonly id: string;
  readonly code: string;
  readonly name: string;
  readonly module: string;
  readonly action: string;
}

export interface DashboardMetrics {
  readonly total_users: number;
  readonly active_users: number;
  readonly disabled_users: number;
  readonly total_roles: number;
  readonly total_knowledge_bases: number;
  readonly total_documents: number;
  readonly total_conversations: number;
  readonly total_chats_today: number;
  readonly success_rate: number;
  readonly avg_response_time_ms: number;
  readonly total_tokens_used: number;
}

export interface AuditLogItem {
  readonly id: string;
  readonly user_id: string | null;
  readonly username: string | null;
  readonly action: string;
  readonly resource_type: string | null;
  readonly resource_id: string | null;
  readonly detail: string | null;
  readonly ip_address: string | null;
  readonly user_agent: string | null;
  readonly result: string;
  readonly request_id: string | null;
  readonly created_at: string | null;
}

export interface AdminDocument {
  readonly id: string;
  readonly knowledge_base_id: string;
  readonly knowledge_base_name: string;
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

export interface AdminTask {
  readonly task_id: string;
  readonly task_type: string;
  readonly status: string;
  readonly stage: string;
  readonly progress: number;
  readonly retry_count: number;
  readonly error_message: string | null;
  readonly request_id: string;
  readonly created_at: string | null;
  readonly finished_at: string | null;
  readonly started_at: string | null;
  readonly document_id: string;
  readonly document_title: string;
  readonly knowledge_base_id: string;
  readonly knowledge_base_name: string;
}

export interface ModelProvider {
  readonly code: string;
  readonly display_name: string;
  readonly base_url: string;
  readonly enabled: boolean;
}

export interface ModelItem {
  readonly id: string;
  readonly provider_code: string;
  readonly model_name: string;
  readonly kind: string;
  readonly parameters: Record<string, unknown>;
  readonly api_key_set: boolean;
  readonly enabled: boolean;
  readonly dimensions: number | null;
  readonly distance: string | null;
  readonly top_n: number | null;
  readonly created_at: string | null;
  readonly updated_at: string | null;
}

export interface RetrievalDataset {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly kb_id: string;
  readonly queries: readonly RetrievalDatasetQuery[];
  readonly created_by: string;
  readonly created_at: string | null;
  readonly updated_at: string | null;
}

export interface RetrievalDatasetQuery {
  readonly query: string;
  readonly relevant_chunk_ids: readonly string[];
  readonly notes?: string | null;
}

export type RetrievalTestMode = "keyword" | "vector" | "hybrid";

export interface RetrievalRun {
  readonly id: string;
  readonly dataset_id: string;
  readonly config_hash: string;
  readonly status: string;
  readonly progress: number;
  readonly total: number;
  readonly started_at: string | null;
  readonly finished_at: string | null;
}

export interface RetrievalTestMetrics {
  readonly hit_rate: number;
  readonly mrr: number;
  readonly ndcg_at_k: number;
  readonly recall_at_k: number;
  readonly precision_at_k: number;
  readonly map_at_k: number;
}

export interface RetrievalPerQueryResult {
  readonly query: string;
  readonly relevant_chunk_ids: readonly string[];
  readonly retrieved_chunk_ids: readonly string[];
  readonly hit: boolean;
  readonly reciprocal_rank: number;
  readonly ndcg: number;
  readonly recall: number;
  readonly precision: number;
  readonly latency_ms: number;
}

export interface RetrievalTestResult {
  readonly id: string;
  readonly dataset_id: string;
  readonly config: {
    readonly mode: RetrievalTestMode;
    readonly top_k: number;
    readonly rerank: boolean;
    readonly threshold: number;
    readonly embedding_model_id: string | null;
    readonly rerank_model_id: string | null;
    readonly metadata_filter: Record<string, unknown> | null;
  };
  readonly config_hash: string;
  readonly total: number;
  readonly metrics: RetrievalTestMetrics;
  readonly per_query: readonly RetrievalPerQueryResult[];
  readonly started_at: string | null;
  readonly finished_at: string | null;
}

export interface RetrievalSearchHit {
  readonly doc_id: string;
  readonly chunk_id: string;
  readonly doc_title: string | null;
  readonly page: number | null;
  readonly score: number;
  readonly vector_score: number | null;
  readonly keyword_score: number | null;
  readonly rerank_score: number | null;
  readonly text: string;
  readonly kb_id: string | null;
}

export const listAdminUsers = async (params: {
  readonly search?: string;
  readonly status?: string;
} = {}): Promise<PageData<AdminUser>> => {
  const response = await apiClient.get<ApiResponse<PageData<AdminUser>>>(
    "/v1/users",
    { params: { page_size: 100, ...params } },
  );
  return unwrap(response.data);
};

export const createAdminUser = async (payload: {
  readonly username: string;
  readonly display_name: string;
  readonly password: string;
  readonly role_ids: readonly string[];
}): Promise<AdminUser> => {
  const response = await apiClient.post<ApiResponse<AdminUser>>("/v1/users", {
    ...payload,
    role_ids: [...payload.role_ids],
  });
  return unwrap(response.data);
};

export const updateAdminUser = async (
  userId: string,
  payload: {
    readonly display_name?: string;
    readonly status?: string;
    readonly role_ids?: readonly string[];
  },
): Promise<AdminUser> => {
  const response = await apiClient.patch<ApiResponse<AdminUser>>(
    `/v1/users/${userId}`,
    {
      ...payload,
      role_ids:
        payload.role_ids === undefined ? undefined : [...payload.role_ids],
    },
  );
  return unwrap(response.data);
};

export const resetAdminUserPassword = async (
  userId: string,
  newPassword: string,
): Promise<void> => {
  const response = await apiClient.post<ApiResponse<null>>(
    `/v1/users/${userId}/reset-password`,
    { new_password: newPassword },
  );
  unwrap(response.data);
};

export const listAdminRoles = async (): Promise<PageData<AdminRole>> => {
  const response = await apiClient.get<ApiResponse<PageData<AdminRole>>>(
    "/v1/roles",
    { params: { page_size: 100 } },
  );
  return unwrap(response.data);
};

export const getAdminRole = async (roleId: string): Promise<RoleDetail> => {
  const response = await apiClient.get<ApiResponse<RoleDetail>>(
    `/v1/roles/${roleId}`,
  );
  return unwrap(response.data);
};

export const listPermissions = async (): Promise<readonly PermissionItem[]> => {
  const response =
    await apiClient.get<ApiResponse<readonly PermissionItem[]>>(
      "/v1/permissions",
    );
  return unwrap(response.data);
};

export const createAdminRole = async (payload: {
  readonly name: string;
  readonly description: string;
  readonly permission_ids: readonly string[];
}): Promise<RoleDetail> => {
  const response = await apiClient.post<ApiResponse<RoleDetail>>("/v1/roles", {
    ...payload,
    permission_ids: [...payload.permission_ids],
  });
  return unwrap(response.data);
};

export const updateAdminRole = async (
  roleId: string,
  payload: {
    readonly name?: string;
    readonly description?: string;
    readonly status?: string;
  },
): Promise<RoleDetail> => {
  const response = await apiClient.patch<ApiResponse<RoleDetail>>(
    `/v1/roles/${roleId}`,
    payload,
  );
  return unwrap(response.data);
};

export const setAdminRolePermissions = async (
  roleId: string,
  permissionIds: readonly string[],
): Promise<RoleDetail> => {
  const response = await apiClient.put<ApiResponse<RoleDetail>>(
    `/v1/roles/${roleId}/permissions`,
    { permission_ids: [...permissionIds] },
  );
  return unwrap(response.data);
};

export const getDashboardMetrics = async (): Promise<DashboardMetrics> => {
  const response = await apiClient.get<ApiResponse<DashboardMetrics>>(
    "/v1/admin/dashboard",
  );
  return unwrap(response.data);
};

export const listAuditLogs = async (params: {
  readonly result?: string;
} = {}): Promise<PageData<AuditLogItem>> => {
  const response = await apiClient.get<ApiResponse<PageData<AuditLogItem>>>(
    "/v1/audit-logs",
    { params: { page_size: 100, ...params } },
  );
  return unwrap(response.data);
};

export const listAdminDocuments = async (params: {
  readonly search?: string;
  readonly status?: string;
} = {}): Promise<PageData<AdminDocument>> => {
  const response = await apiClient.get<ApiResponse<PageData<AdminDocument>>>(
    "/v1/admin/documents",
    { params: { page_size: 100, ...params } },
  );
  return unwrap(response.data);
};

export const listAdminTasks = async (params: {
  readonly search?: string;
  readonly status?: string;
} = {}): Promise<PageData<AdminTask>> => {
  const response = await apiClient.get<ApiResponse<PageData<AdminTask>>>(
    "/v1/admin/tasks",
    { params: { page_size: 100, ...params } },
  );
  return unwrap(response.data);
};

export const listModelProviders = async (): Promise<
  readonly ModelProvider[]
> => {
  const response =
    await apiClient.get<ApiResponse<readonly ModelProvider[]>>(
      "/v1/models/providers",
    );
  return unwrap(response.data);
};

export const upsertModelProvider = async (payload: {
  readonly code: string;
  readonly display_name: string;
  readonly base_url: string;
  readonly enabled: boolean;
}): Promise<ModelProvider> => {
  const response = await apiClient.post<ApiResponse<ModelProvider>>(
    "/v1/models/providers",
    payload,
  );
  return unwrap(response.data);
};

export const listModels = async (): Promise<readonly ModelItem[]> => {
  const response =
    await apiClient.get<ApiResponse<readonly ModelItem[]>>("/v1/models");
  return unwrap(response.data);
};

export const createModel = async (payload: {
  readonly provider_code: string;
  readonly model_name: string;
  readonly kind: string;
  readonly parameters: Record<string, unknown>;
  readonly enabled: boolean;
  readonly api_key?: string;
  readonly dimensions?: number;
  readonly distance?: string;
  readonly top_n?: number;
}): Promise<ModelItem> => {
  const response = await apiClient.post<ApiResponse<ModelItem>>(
    "/v1/models",
    payload,
  );
  return unwrap(response.data);
};

export const updateModel = async (
  modelId: string,
  payload: {
    readonly model_name?: string;
    readonly parameters?: Record<string, unknown>;
    readonly enabled?: boolean;
    readonly api_key?: string;
    readonly dimensions?: number;
    readonly distance?: string;
    readonly top_n?: number;
  },
): Promise<ModelItem> => {
  const response = await apiClient.patch<ApiResponse<ModelItem>>(
    `/v1/models/${modelId}`,
    payload,
  );
  return unwrap(response.data);
};

export const deleteModel = async (modelId: string): Promise<void> => {
  const response = await apiClient.delete<ApiResponse<null>>(
    `/v1/models/${modelId}`,
  );
  unwrap(response.data);
};

export const testModel = async (modelId: string): Promise<void> => {
  const response = await apiClient.post<ApiResponse<unknown>>(
    `/v1/models/${modelId}/test`,
  );
  unwrap(response.data);
};

export const listRetrievalDatasets = async (): Promise<
  PageData<RetrievalDataset>
> => {
  const response = await apiClient.get<ApiResponse<PageData<RetrievalDataset>>>(
    "/v1/retrieval-tests/datasets",
    { params: { page_size: 100 } },
  );
  return unwrap(response.data);
};

export const createRetrievalDataset = async (payload: {
  readonly name: string;
  readonly description: string;
  readonly kb_id: string;
  readonly queries: readonly RetrievalDatasetQuery[];
}): Promise<RetrievalDataset> => {
  const response = await apiClient.post<ApiResponse<RetrievalDataset>>(
    "/v1/retrieval-tests/datasets",
    {
      ...payload,
      queries: payload.queries.map((query) => ({
        query: query.query,
        relevant_chunk_ids: [...query.relevant_chunk_ids],
        notes: query.notes ?? null,
      })),
    },
  );
  return unwrap(response.data);
};

export const updateRetrievalDataset = async (
  datasetId: string,
  payload: {
    readonly name: string;
    readonly description: string;
    readonly queries: readonly RetrievalDatasetQuery[];
  },
): Promise<RetrievalDataset> => {
  const response = await apiClient.patch<ApiResponse<RetrievalDataset>>(
    `/v1/retrieval-tests/datasets/${datasetId}`,
    {
      name: payload.name,
      description: payload.description,
      queries: payload.queries.map((query) => ({
        query: query.query,
        relevant_chunk_ids: [...query.relevant_chunk_ids],
        notes: query.notes ?? null,
      })),
    },
  );
  return unwrap(response.data);
};

export const listRetrievalRuns = async (): Promise<PageData<RetrievalRun>> => {
  const response = await apiClient.get<ApiResponse<PageData<RetrievalRun>>>(
    "/v1/retrieval-tests/runs",
    { params: { page_size: 100 } },
  );
  return unwrap(response.data);
};

export const getRetrievalRun = async (
  runId: string,
): Promise<RetrievalTestResult> => {
  const response = await apiClient.get<ApiResponse<RetrievalTestResult>>(
    `/v1/retrieval-tests/runs/${runId}`,
  );
  return unwrap(response.data);
};

export const runRetrievalTest = async (payload: {
  readonly dataset_id: string;
  readonly mode: RetrievalTestMode;
  readonly top_k: number;
  readonly threshold: number;
  readonly rerank: boolean;
  readonly embedding_model_id?: string | null;
  readonly rerank_model_id?: string | null;
}): Promise<RetrievalTestResult> => {
  const response = await apiClient.post<ApiResponse<RetrievalTestResult>>(
    "/v1/retrieval-tests/run",
    {
      dataset_id: payload.dataset_id,
      async_run: false,
      config: {
        mode: payload.mode,
        top_k: payload.top_k,
        threshold: payload.threshold,
        metadata_filter: {},
        rerank: payload.rerank,
        rerank_model_id: payload.rerank_model_id ?? null,
        embedding_model_id: payload.embedding_model_id ?? null,
      },
    },
  );
  return unwrap(response.data);
};

export const searchRetrievalCandidates = async (payload: {
  readonly query: string;
  readonly mode: RetrievalTestMode;
  readonly kb_id: string;
  readonly top_k: number;
  readonly threshold: number;
  readonly rerank: boolean;
}): Promise<readonly RetrievalSearchHit[]> => {
  const response = await apiClient.post<
    ApiResponse<{ readonly hits: readonly RetrievalSearchHit[] }>
  >("/v1/retrieval/search", {
    query: payload.query,
    mode: payload.mode,
    kb_id: payload.kb_id,
    top_k: payload.top_k,
    threshold: payload.threshold,
    metadata_filter: {},
    rerank: payload.rerank,
    rerank_model_id: null,
    embedding_model_id: null,
  });
  return unwrap(response.data).hits;
};

export type { KnowledgeBaseRecord };
