import { apiClient } from "../api/client";
import {
  assertApiSuccess,
  unwrapApiData,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";
import type { paths } from "../api/generated/openapi";

interface PaginatedData<T> {
  readonly items: readonly T[];
  readonly page: number;
  readonly page_size: number;
  readonly total: number;
}

export interface ConversationRecord {
  readonly id: string;
  readonly user_id: string;
  readonly kb_id: string;
  readonly title: string;
  readonly is_pinned: boolean;
  readonly is_archived: boolean;
  readonly message_count: number;
  readonly last_message_at: string | null;
  readonly created_at: string | null;
  readonly updated_at: string | null;
}

export interface MessageRecord {
  readonly id: string;
  readonly conversation_id: string;
  readonly role: "system" | "user" | "assistant" | "tool";
  readonly content: string;
  readonly created_at: string | null;
}

export const listConversations = async (
  signal?: AbortSignal,
): Promise<readonly ConversationRecord[]> => {
  const items: ConversationRecord[] = [];
  let page = 1;
  let total = 0;
  do {
    const response = await apiClient.get<
      ApiResponse<PaginatedData<ConversationRecord>>
    >("/v1/conversations", { params: { page, page_size: 100 }, signal });
    const data = unwrapApiData(response.data);
    items.push(...data.items);
    total = data.total;
    page += 1;
    if (data.items.length === 0) break;
  } while (items.length < total);
  return items;
};

export const listConversationMessages = async (
  conversationId: string,
  signal?: AbortSignal,
): Promise<readonly MessageRecord[]> => {
  const items: MessageRecord[] = [];
  let page = 1;
  let hasMore = false;
  do {
    const response = await apiClient.get<
      ApiResponse<{
        readonly items: readonly MessageRecord[];
        readonly page: number;
        readonly page_size: number;
        readonly total: number;
        readonly has_more: boolean;
      }>
    >(`/v1/conversations/${conversationId}/messages`, {
      params: { page, page_size: 200 },
      signal,
    });
    const data = unwrapApiData(response.data);
    items.push(...data.items);
    hasMore = data.has_more;
    page += 1;
    if (data.items.length === 0) break;
  } while (hasMore);
  return items;
};

export const deleteConversation = async (
  conversationId: string,
): Promise<void> => {
  const response = await apiClient.delete<ApiSchema<"APIResponse_NoneType_">>(
    `/v1/conversations/${conversationId}`,
  );
  assertApiSuccess(response.data);
};

export const updateConversationTitle = async (
  conversationId: string,
  title: string,
): Promise<ConversationRecord> => {
  const request: paths["/conversations/{conversation_id}"]["patch"]["requestBody"]["content"]["application/json"] =
    { title };
  const response = await apiClient.patch<ApiResponse<ConversationRecord>>(
    `/v1/conversations/${conversationId}`,
    request,
  );
  return unwrapApiData(response.data);
};
