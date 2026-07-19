import { apiClient } from "../api/client";
import type { Favorite, FavoriteType } from "../types/ai-search";

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

interface FavoriteRecord {
  readonly id: string;
  readonly type: FavoriteType;
  readonly title: string;
  readonly summary: string;
  readonly tags: readonly string[];
  readonly note: string;
  readonly source_id: string | null;
  readonly source_payload: Record<string, unknown>;
  readonly saved_at: string | null;
}

export interface FavoriteCreatePayload {
  readonly type: FavoriteType;
  readonly title: string;
  readonly summary: string;
  readonly tags?: readonly string[];
  readonly note?: string;
  readonly source_id?: string | null;
  readonly source_payload?: Record<string, unknown>;
}

const unwrap = <T>(response: ApiResponse<T>): T => {
  if (response.code !== 0 || response.data === null) {
    throw new Error(response.message || "请求失败，请稍后重试");
  }
  return response.data;
};

const toFavorite = (record: FavoriteRecord): Favorite => ({
  id: record.id,
  type: record.type,
  title: record.title,
  summary: record.summary,
  tags: record.tags,
  note: record.note,
  sourceId: record.source_id ?? "",
  savedAt: record.saved_at ?? new Date().toISOString(),
});

export const listFavorites = async (
  signal?: AbortSignal,
): Promise<readonly Favorite[]> => {
  const response = await apiClient.get<ApiResponse<PaginatedData<FavoriteRecord>>>(
    "/v1/favorites",
    { params: { page: 1, page_size: 100 }, signal },
  );
  return unwrap(response.data).items.map(toFavorite);
};

export const createFavorite = async (
  payload: FavoriteCreatePayload,
): Promise<Favorite> => {
  const response = await apiClient.post<ApiResponse<FavoriteRecord>>(
    "/v1/favorites",
    payload,
  );
  return toFavorite(unwrap(response.data));
};

export const updateFavorite = async (
  favoriteId: string,
  payload: { readonly note?: string; readonly tags?: readonly string[] },
): Promise<Favorite> => {
  const response = await apiClient.patch<ApiResponse<FavoriteRecord>>(
    `/v1/favorites/${favoriteId}`,
    payload,
  );
  return toFavorite(unwrap(response.data));
};

export const deleteFavorite = async (favoriteId: string): Promise<void> => {
  await apiClient.delete(`/v1/favorites/${favoriteId}`);
};
