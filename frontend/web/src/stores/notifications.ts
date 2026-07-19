import { defineStore } from "pinia";
import { ref } from "vue";

import {
  notificationSeeds,
  type NotificationAudience,
  type NotificationItem,
} from "../data/account-support";
import { isRealApiMode } from "../config/runtime";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../services/notifications";

const cloneSeed = (audience: NotificationAudience): NotificationItem[] =>
  notificationSeeds[audience].map((item) => ({ ...item }));

export const useNotificationStore = defineStore("notifications", () => {
  const notifications = ref<Record<NotificationAudience, NotificationItem[]>>({
    user: cloneSeed("user"),
    admin: cloneSeed("admin"),
  });
  const loadState = ref<Record<NotificationAudience, "idle" | "loading" | "error">>({
    user: "idle",
    admin: "idle",
  });
  const loadError = ref<Record<NotificationAudience, string>>({
    user: "",
    admin: "",
  });

  const getNotifications = (
    audience: NotificationAudience,
  ): readonly NotificationItem[] => notifications.value[audience];

  const unreadCount = (audience: NotificationAudience): number =>
    notifications.value[audience].filter((item) => !item.read).length;

  const loadNotifications = async (
    audience: NotificationAudience,
  ): Promise<void> => {
    if (!isRealApiMode) return;
    loadState.value[audience] = "loading";
    loadError.value[audience] = "";
    try {
      notifications.value[audience] = [...(await listNotifications(audience))];
      loadState.value[audience] = "idle";
    } catch {
      loadError.value[audience] = "通知暂时无法加载，请稍后重试。";
      loadState.value[audience] = "error";
    }
  };

  const markAsRead = (audience: NotificationAudience, id: string): void => {
    const notification = notifications.value[audience].find(
      (item) => item.id === id,
    );
    if (notification !== undefined) notification.read = true;
    if (isRealApiMode) {
      void markNotificationRead(id).catch(() => {
        void loadNotifications(audience);
      });
    }
  };

  const markAllAsRead = (audience: NotificationAudience): void => {
    notifications.value[audience].forEach((item) => {
      item.read = true;
    });
    if (isRealApiMode) {
      void markAllNotificationsRead(audience).catch(() => {
        void loadNotifications(audience);
      });
    }
  };

  return {
    notifications,
    loadState,
    loadError,
    getNotifications,
    unreadCount,
    loadNotifications,
    markAsRead,
    markAllAsRead,
  };
});
