import { apiClient } from "../api/client";
import { unwrapApiData, type ApiResponse } from "../api/contracts";
import type { paths } from "../api/generated/openapi";
import type { Favorite, FavoriteType } from "../types/ai-search";

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

type FavoriteCreateRequest =
  paths["/favorites"]["post"]["requestBody"]["content"]["application/json"];

export type FavoriteCreatePayload = Readonly<
  Omit<FavoriteCreateRequest, "tags" | "note" | "source_payload"> & {
    readonly tags?: readonly string[];
    readonly note?: FavoriteCreateRequest["note"];
    readonly source_payload?: Readonly<Record<string, unknown>>;
  }
>;

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
  const items: FavoriteRecord[] = [];
  let page = 1;
  let total = 0;

  do {
    const response = await apiClient.get<
      ApiResponse<PaginatedData<FavoriteRecord>>
    >("/v1/favorites", { params: { page, page_size: 100 }, signal });
    const data = unwrapApiData(response.data);
    items.push(...data.items);
    total = data.total;
    page += 1;
    if (data.items.length === 0) break;
  } while (items.length < total);

  return items.map(toFavorite);
};

export const createFavorite = async (
  payload: FavoriteCreatePayload,
): Promise<Favorite> => {
  const request: FavoriteCreateRequest = {
    ...payload,
    tags: payload.tags === undefined ? undefined : [...payload.tags],
    note: payload.note ?? "",
  };
  const response = await apiClient.post<ApiResponse<FavoriteRecord>>(
    "/v1/favorites",
    request,
  );
  return toFavorite(unwrapApiData(response.data));
};

export const updateFavorite = async (
  favoriteId: string,
  payload: { readonly note?: string; readonly tags?: readonly string[] },
): Promise<Favorite> => {
  const request: paths["/favorites/{favorite_id}"]["patch"]["requestBody"]["content"]["application/json"] =
    {
      ...payload,
      tags: payload.tags === undefined ? undefined : [...payload.tags],
    };
  const response = await apiClient.patch<ApiResponse<FavoriteRecord>>(
    `/v1/favorites/${favoriteId}`,
    request,
  );
  return toFavorite(unwrapApiData(response.data));
};

export const deleteFavorite = async (favoriteId: string): Promise<void> => {
  await apiClient.delete(`/v1/favorites/${favoriteId}`);
};
