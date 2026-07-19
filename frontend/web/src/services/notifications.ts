import { apiClient } from "../api/client";
import type {
  NotificationAudience,
  NotificationItem,
} from "../data/account-support";

interface ApiResponse<T> {
  readonly code: number;
  readonly message: string;
  readonly data: T | null;
  readonly request_id: string;
}

interface NotificationActionResponse {
  readonly label: string;
  readonly to: string;
}

interface NotificationResponse {
  readonly id: string;
  readonly audience: NotificationAudience;
  readonly category: NotificationItem["category"];
  readonly title: string;
  readonly description: string;
  readonly read: boolean;
  readonly created_at: string;
  readonly action: NotificationActionResponse | null;
}

interface NotificationListResponse {
  readonly items: readonly NotificationResponse[];
  readonly total: number;
  readonly unread: number;
}

const unwrap = <T>(response: ApiResponse<T>): T => {
  if (response.code !== 0 || response.data === null) {
    throw new Error(response.message || "通知接口请求失败");
  }
  return response.data;
};

const formatTime = (value: string): string =>
  new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));

const mapNotification = (
  notification: NotificationResponse,
): NotificationItem => ({
  id: notification.id,
  category: notification.category,
  title: notification.title,
  description: notification.description,
  time: formatTime(notification.created_at),
  action:
    notification.action === null
      ? undefined
      : {
          label: notification.action.label,
          to: notification.action.to,
        },
  read: notification.read,
});

export const listNotifications = async (
  audience: NotificationAudience,
): Promise<readonly NotificationItem[]> => {
  const response = await apiClient.get<ApiResponse<NotificationListResponse>>(
    "/v1/notifications",
    { params: { audience } },
  );
  return unwrap(response.data).items.map(mapNotification);
};

export const markNotificationRead = async (
  notificationId: string,
): Promise<NotificationItem> => {
  const response = await apiClient.patch<ApiResponse<NotificationResponse>>(
    `/v1/notifications/${notificationId}/read`,
  );
  return mapNotification(unwrap(response.data));
};

export const markAllNotificationsRead = async (
  audience: NotificationAudience,
): Promise<void> => {
  const response = await apiClient.post<ApiResponse<unknown>>(
    "/v1/notifications/mark-all-read",
    undefined,
    { params: { audience } },
  );
  if (response.data.code !== 0) {
    throw new Error(response.data.message || "通知接口请求失败");
  }
};
