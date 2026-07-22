import { apiClient, clearAccessToken, setAccessToken } from "../api/client";
import {
  assertApiSuccess,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";
import type { paths } from "../api/generated/openapi";

interface UserRole {
  readonly id: string;
  readonly name: string;
}

interface KnowledgeBaseAccess {
  readonly kb_id: string;
  readonly access_level: string;
}

interface DepartmentBrief {
  readonly id: string;
  readonly name: string;
}

export interface AuthenticatedUser {
  readonly id: string;
  readonly username: string;
  readonly display_name: string;
  readonly department: DepartmentBrief | null;
  readonly roles: readonly UserRole[];
  readonly permissions: readonly string[];
  readonly knowledge_base_access: readonly KnowledgeBaseAccess[];
}

interface LoginData {
  readonly access_token: string;
  readonly token_type: string;
  readonly user: AuthenticatedUser;
}

export type LoginCredentials = Readonly<
  paths["/auth/login"]["post"]["requestBody"]["content"]["application/json"]
>;

export type RegisterPayload = Readonly<
  paths["/auth/register"]["post"]["requestBody"]["content"]["application/json"]
>;

export const loginWithPassword = async (
  credentials: LoginCredentials,
): Promise<AuthenticatedUser> => {
  const response = await apiClient.post<ApiResponse<LoginData>>(
    "/v1/auth/login",
    credentials,
  );
  const data = response.data.data;

  if (
    response.data.code !== 0 ||
    data === null ||
    data === undefined ||
    data.access_token === ""
  ) {
    throw new Error(response.data.message || "登录失败，请重试");
  }

  setAccessToken(data.access_token);
  return data.user;
};

export const refreshSession = async (): Promise<AuthenticatedUser> => {
  const response =
    await apiClient.post<ApiResponse<LoginData>>("/v1/auth/refresh");
  const data = response.data.data;

  if (
    response.data.code !== 0 ||
    data === null ||
    data === undefined ||
    data.access_token === ""
  ) {
    throw new Error(response.data.message || "登录状态已失效，请重新登录");
  }

  setAccessToken(data.access_token);
  return data.user;
};

export const logoutCurrentUser = async (): Promise<void> => {
  try {
    const response =
      await apiClient.post<ApiSchema<"APIResponse_NoneType_">>(
        "/v1/auth/logout",
      );
    assertApiSuccess(response.data);
  } finally {
    clearAccessToken();
  }
};

export const getCurrentUser = async (): Promise<AuthenticatedUser> => {
  const response =
    await apiClient.get<ApiResponse<AuthenticatedUser>>("/v1/me");
  const data = response.data.data;
  if (response.data.code !== 0 || data === null || data === undefined) {
    throw new Error(response.data.message || "获取当前用户失败");
  }
  return data;
};

export const checkUsernameAvailable = async (
  username: string,
): Promise<boolean> => {
  const response = await apiClient.get<
    ApiResponse<{ readonly username: string; readonly available: boolean }>
  >("/v1/auth/check-username", { params: { username } });
  if (
    response.data.code !== 0 ||
    response.data.data === null ||
    response.data.data === undefined
  ) {
    throw new Error(response.data.message || "账号检查失败");
  }
  return response.data.data.available;
};

export const registerAccount = async (
  payload: RegisterPayload,
): Promise<void> => {
  const response = await apiClient.post<
    ApiSchema<"APIResponse_dict_str__object__">
  >("/v1/auth/register", payload);
  assertApiSuccess(response.data, "注册失败，请重试");
};
