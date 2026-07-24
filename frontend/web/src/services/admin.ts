import { apiClient } from "../api/client";
import {
  assertApiSuccess,
  unwrapApiData as unwrap,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";
import type { paths } from "../api/generated/openapi";
import type { KnowledgeBaseRecord } from "./knowledge";

interface PageData<T> {
  readonly items: readonly T[];
  readonly page: number;
  readonly page_size: number;
  readonly total: number;
}

type PageParams = Readonly<
  Record<string, string | number | boolean | undefined>
>;

const listAllPages = async <T>(
  path: string,
  params: PageParams = {},
): Promise<PageData<T>> => {
  const items: T[] = [];
  let page = 1;
  let total = 0;

  do {
    const response = await apiClient.get<ApiResponse<PageData<T>>>(path, {
      params: { ...params, page, page_size: 100 },
    });
    const data = unwrap(response.data);
    items.push(...data.items);
    total = data.total;
    page += 1;
    if (data.items.length === 0) break;
  } while (items.length < total);

  return { items, page: 1, page_size: 100, total };
};

type CreateUserRequest =
  paths["/users"]["post"]["requestBody"]["content"]["application/json"];
type UpdateUserRequest =
  paths["/users/{user_id}"]["patch"]["requestBody"]["content"]["application/json"];
type ResetPasswordRequest =
  paths["/users/{user_id}/reset-password"]["post"]["requestBody"]["content"]["application/json"];
type CreateRoleRequest =
  paths["/roles"]["post"]["requestBody"]["content"]["application/json"];
type UpdateRoleRequest =
  paths["/roles/{role_id}"]["patch"]["requestBody"]["content"]["application/json"];
type SetRolePermissionsRequest =
  paths["/roles/{role_id}/permissions"]["put"]["requestBody"]["content"]["application/json"];

type CreateAdminUserPayload = Readonly<
  Omit<CreateUserRequest, "role_ids"> & {
    readonly role_ids: readonly string[];
  }
>;

type UpdateAdminUserPayload = Readonly<
  Omit<UpdateUserRequest, "role_ids"> & {
    readonly role_ids?: readonly string[];
  }
>;

type CreateAdminRolePayload = Readonly<
  Omit<CreateRoleRequest, "description" | "permission_ids"> & {
    readonly description: string;
    readonly permission_ids: readonly string[];
  }
>;

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
  readonly department: DepartmentBrief | null;
  readonly last_login_at: string | null;
  readonly created_at: string | null;
}

export interface DepartmentBrief {
  readonly id: string;
  readonly name: string;
}

export interface DepartmentRecord {
  readonly id: string;
  readonly name: string;
  readonly description: string | null;
  readonly admin_user_id: string | null;
  readonly admin_username: string | null;
  readonly admin_display_name: string | null;
  readonly user_count: number;
  readonly knowledge_base_count: number;
  readonly created_at: string | null;
  readonly updated_at: string | null;
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

export type DashboardMetrics = Readonly<ApiSchema<"DashboardMetrics">>;
export type DepartmentLeaderboardItem = Readonly<
  ApiSchema<"DepartmentLeaderboardItem">
>;
export type DashboardDays = ApiSchema<"DashboardPeriod">["days"];

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

export type AdminDocument = Readonly<Required<ApiSchema<"AdminDocumentItem">>>;

export type AdminTask = Readonly<Required<ApiSchema<"AdminTaskItem">>>;

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

export type RetrievalDatasetQuery = Readonly<
  Omit<ApiSchema<"RetrievalTestQuery">, "relevant_chunk_ids"> & {
    readonly relevant_chunk_ids: readonly string[];
  }
>;

export type RetrievalTestMode = ApiSchema<"RetrievalTestConfig">["mode"];

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
  readonly config: Readonly<Required<ApiSchema<"RetrievalTestConfig">>>;
  readonly config_hash: string;
  readonly total: number;
  readonly metrics: RetrievalTestMetrics;
  readonly per_query: readonly RetrievalPerQueryResult[];
  readonly started_at: string | null;
  readonly finished_at: string | null;
}

export interface SingleRetrievalTestResult {
  readonly question: string;
  readonly hit: boolean;
  readonly hit_rate: number;
  readonly threshold: number;
  readonly hits: readonly RetrievalSearchHit[];
  readonly took_ms: number;
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

export const listAdminUsers = async (
  params: {
    readonly search?: string;
    readonly status?: string;
  } = {},
): Promise<PageData<AdminUser>> => {
  return listAllPages<AdminUser>("/v1/users", params);
};

export const createAdminUser = async (
  payload: CreateAdminUserPayload,
): Promise<AdminUser> => {
  const response = await apiClient.post<ApiResponse<AdminUser>>("/v1/users", {
    ...payload,
    role_ids: [...payload.role_ids],
  });
  return unwrap(response.data);
};

export const updateAdminUser = async (
  userId: string,
  payload: UpdateAdminUserPayload,
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

export const listDepartments = async (): Promise<readonly DepartmentRecord[]> => {
  const response = await apiClient.get<
    ApiResponse<{ readonly items: readonly DepartmentRecord[]; readonly total: number }>
  >("/v1/departments");
  return unwrap(response.data).items;
};

export const createDepartment = async (payload: {
  readonly name: string;
  readonly description?: string | null;
  readonly admin_user_id: string;
}): Promise<DepartmentRecord> => {
  const response = await apiClient.post<ApiResponse<DepartmentRecord>>(
    "/v1/departments",
    payload,
  );
  return unwrap(response.data);
};

export const updateDepartment = async (
  departmentId: string,
  payload: {
    readonly name?: string;
    readonly description?: string | null;
    readonly admin_user_id?: string;
  },
): Promise<DepartmentRecord> => {
  const response = await apiClient.patch<ApiResponse<DepartmentRecord>>(
    `/v1/departments/${departmentId}`,
    payload,
  );
  return unwrap(response.data);
};

export const resetAdminUserPassword = async (
  userId: string,
  newPassword: string,
): Promise<void> => {
  const request: ResetPasswordRequest = { new_password: newPassword };
  const response = await apiClient.post<ApiSchema<"APIResponse_NoneType_">>(
    `/v1/users/${userId}/reset-password`,
    request,
  );
  assertApiSuccess(response.data);
};

export const listAdminRoles = async (): Promise<PageData<AdminRole>> => {
  return listAllPages<AdminRole>("/v1/roles");
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

export const createAdminRole = async (
  payload: CreateAdminRolePayload,
): Promise<RoleDetail> => {
  const response = await apiClient.post<ApiResponse<RoleDetail>>("/v1/roles", {
    ...payload,
    permission_ids: [...payload.permission_ids],
  });
  return unwrap(response.data);
};

export const updateAdminRole = async (
  roleId: string,
  payload: Readonly<UpdateRoleRequest>,
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
  const request: SetRolePermissionsRequest = {
    permission_ids: [...permissionIds],
  };
  const response = await apiClient.put<ApiResponse<RoleDetail>>(
    `/v1/roles/${roleId}/permissions`,
    request,
  );
  return unwrap(response.data);
};

export const getDashboardMetrics = async (
  params: {
    readonly days?: DashboardDays;
    readonly department_id?: string;
    readonly leaderboard_page?: number;
    readonly leaderboard_page_size?: number;
  } = {},
): Promise<DashboardMetrics> => {
  const response = await apiClient.get<ApiResponse<DashboardMetrics>>(
    "/v1/admin/dashboard",
    { params },
  );
  return unwrap(response.data);
};

export const listAuditLogs = async (
  params: {
    readonly result?: string;
  } = {},
): Promise<PageData<AuditLogItem>> => {
  return listAllPages<AuditLogItem>("/v1/audit-logs", params);
};

export const listAdminDocuments = async (
  params: {
    readonly search?: string;
    readonly status?: string;
  } = {},
): Promise<PageData<AdminDocument>> => {
  return listAllPages<AdminDocument>("/v1/admin/documents", params);
};

export const listAdminTasks = async (
  params: {
    readonly search?: string;
    readonly status?: string;
  } = {},
): Promise<PageData<AdminTask>> => {
  return listAllPages<AdminTask>("/v1/admin/tasks", params);
};

export const listModelProviders = async (): Promise<
  readonly ModelProvider[]
> => {
  const response = await apiClient.get<ApiResponse<readonly ModelProvider[]>>(
    "/v1/models/providers",
  );
  return unwrap(response.data);
};

export const upsertModelProvider = async (
  payload: Readonly<
    paths["/models/providers"]["post"]["requestBody"]["content"]["application/json"]
  >,
): Promise<ModelProvider> => {
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
  const response = await apiClient.delete<ApiSchema<"APIResponse_NoneType_">>(
    `/v1/models/${modelId}`,
  );
  assertApiSuccess(response.data);
};

export interface TestModelResult {
  readonly ok: boolean;
  readonly latency_ms: number;
  readonly model_info: Readonly<Record<string, unknown>> | null;
  readonly error_code: string | null;
  readonly error_message: string | null;
}

export interface RetrievalRunSummary {
  readonly id: string;
  readonly status: "pending" | "running" | "done" | "failed";
  readonly progress: number;
  readonly result: RetrievalTestResult | null;
  readonly error_message: string | null;
}

export type RetrievalRunDetail = RetrievalTestResult | RetrievalRunSummary;

export const isRetrievalTestResult = (
  value: RetrievalRunDetail,
): value is RetrievalTestResult => "metrics" in value && "per_query" in value;

export const testModel = async (modelId: string): Promise<TestModelResult> => {
  const response = await apiClient.post<ApiResponse<TestModelResult>>(
    `/v1/models/${modelId}/test`,
  );
  return unwrap(response.data);
};

export const listRetrievalDatasets = async (): Promise<
  PageData<RetrievalDataset>
> => {
  return listAllPages<RetrievalDataset>("/v1/retrieval-tests/datasets");
};

export const createRetrievalDataset = async (payload: {
  readonly name: string;
  readonly description: string;
  readonly kb_id: string;
  readonly queries: readonly RetrievalDatasetQuery[];
}): Promise<RetrievalDataset> => {
  const request: ApiSchema<"RetrievalTestDatasetCreate"> = {
    ...payload,
    queries: payload.queries.map((query) => ({
      query: query.query,
      relevant_chunk_ids: [...query.relevant_chunk_ids],
      notes: query.notes ?? null,
    })),
  };
  const response = await apiClient.post<ApiResponse<RetrievalDataset>>(
    "/v1/retrieval-tests/datasets",
    request,
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
  const request: ApiSchema<"RetrievalTestDatasetUpdate"> = {
    name: payload.name,
    description: payload.description,
    queries: payload.queries.map((query) => ({
      query: query.query,
      relevant_chunk_ids: [...query.relevant_chunk_ids],
      notes: query.notes ?? null,
    })),
  };
  const response = await apiClient.patch<ApiResponse<RetrievalDataset>>(
    `/v1/retrieval-tests/datasets/${datasetId}`,
    request,
  );
  return unwrap(response.data);
};

export const listRetrievalRuns = async (): Promise<PageData<RetrievalRun>> => {
  return listAllPages<RetrievalRun>("/v1/retrieval-tests/runs");
};

export const getRetrievalRun = async (
  runId: string,
): Promise<RetrievalRunDetail> => {
  const response = await apiClient.get<ApiResponse<RetrievalRunDetail>>(
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
  const request: ApiSchema<"RetrievalTestRequest"> = {
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
  };
  const response = await apiClient.post<ApiResponse<RetrievalTestResult>>(
    "/v1/retrieval-tests/run",
    request,
  );
  return unwrap(response.data);
};

export const runSingleRetrievalTest = async (payload: {
  readonly kb_id: string;
  readonly question: string;
  readonly mode: RetrievalTestMode;
  readonly top_k: number;
  readonly threshold: number;
  readonly rerank: boolean;
}): Promise<SingleRetrievalTestResult> => {
  const response = await apiClient.post<ApiResponse<SingleRetrievalTestResult>>(
    "/v1/retrieval-tests/single",
    {
      kb_id: payload.kb_id,
      question: payload.question,
      config: {
        mode: payload.mode,
        top_k: payload.top_k,
        threshold: payload.threshold,
        rerank: payload.rerank,
        metadata_filter: {},
        embedding_model_id: null,
        rerank_model_id: null,
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
  const request: ApiSchema<"SearchRequest"> = {
    query: payload.query,
    mode: payload.mode,
    kb_id: payload.kb_id,
    top_k: payload.top_k,
    threshold: payload.threshold,
    metadata_filter: {},
    rerank: payload.rerank,
    rerank_model_id: null,
    embedding_model_id: null,
  };
  const response = await apiClient.post<
    ApiResponse<{ readonly hits: readonly RetrievalSearchHit[] }>
  >("/v1/retrieval/search", request);
  return unwrap(response.data).hits;
};

export type { KnowledgeBaseRecord };
