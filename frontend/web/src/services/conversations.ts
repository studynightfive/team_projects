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

const unwrap = <T>(response: ApiResponse<T>): T => {
  if (response.code !== 0 || response.data === null) {
    throw new Error(response.message || "请求失败，请稍后重试");
  }
  return response.data;
};

export const listConversations = async (
  signal?: AbortSignal,
): Promise<readonly ConversationRecord[]> => {
  const response = await apiClient.get<ApiResponse<PaginatedData<ConversationRecord>>>(
    "/v1/conversations",
    { params: { page: 1, page_size: 50 }, signal },
  );
  return unwrap(response.data).items;
};

export const listConversationMessages = async (
  conversationId: string,
  signal?: AbortSignal,
): Promise<readonly MessageRecord[]> => {
  const response = await apiClient.get<
    ApiResponse<{
      readonly items: readonly MessageRecord[];
      readonly page: number;
      readonly page_size: number;
      readonly total: number;
      readonly has_more: boolean;
    }>
  >(`/v1/conversations/${conversationId}/messages`, { signal });
  return unwrap(response.data).items;
};

export const deleteConversation = async (
  conversationId: string,
): Promise<void> => {
  await apiClient.delete(`/v1/conversations/${conversationId}`);
};
