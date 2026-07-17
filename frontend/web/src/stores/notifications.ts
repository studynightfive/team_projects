import { defineStore } from "pinia";
import { ref } from "vue";

import {
  notificationSeeds,
  type NotificationAudience,
  type NotificationItem,
} from "../data/account-support";

const cloneSeed = (audience: NotificationAudience): NotificationItem[] =>
  notificationSeeds[audience].map((item) => ({ ...item }));

export const useNotificationStore = defineStore("notifications", () => {
  const notifications = ref<Record<NotificationAudience, NotificationItem[]>>({
    user: cloneSeed("user"),
    admin: cloneSeed("admin"),
  });

  const getNotifications = (
    audience: NotificationAudience,
  ): readonly NotificationItem[] => notifications.value[audience];

  const unreadCount = (audience: NotificationAudience): number =>
    notifications.value[audience].filter((item) => !item.read).length;

  const markAsRead = (audience: NotificationAudience, id: string): void => {
    const notification = notifications.value[audience].find(
      (item) => item.id === id,
    );
    if (notification !== undefined) notification.read = true;
  };

  const markAllAsRead = (audience: NotificationAudience): void => {
    notifications.value[audience].forEach((item) => {
      item.read = true;
    });
  };

  return {
    notifications,
    getNotifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
  };
});
