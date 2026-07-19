<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { RouterLink } from "vue-router";

import type {
  NotificationAudience,
  NotificationItem,
} from "../data/account-support";
import { useNotificationStore } from "../stores/notifications";
import { Bell } from "./icons";

const { audience } = defineProps<{
  audience: NotificationAudience;
}>();

const notificationStore = useNotificationStore();
const notificationRoute = computed(() =>
  audience === "admin" ? "/admin/notifications" : "/notifications",
);
const previewHeading = computed(() =>
  audience === "admin" ? "管理通知" : "通知",
);
const previewNotifications = computed(() =>
  notificationStore.getNotifications(audience).slice(0, 4),
);
const unreadNotificationCount = computed(() =>
  notificationStore.unreadCount(audience),
);
const triggerLabel = computed(() => {
  if (audience === "admin") {
    return unreadNotificationCount.value > 0
      ? `查看通知，当前有 ${unreadNotificationCount.value} 项待处理`
      : "查看通知，当前没有待处理项";
  }

  return unreadNotificationCount.value > 0
    ? `查看通知，当前有 ${unreadNotificationCount.value} 条未读消息`
    : "查看通知，当前没有未读消息";
});

const getNotificationTarget = (notification: NotificationItem): string =>
  notification.action?.to ?? notificationRoute.value;

onMounted(() => {
  void notificationStore.loadNotifications(audience);
});

watch(
  () => audience,
  (nextAudience) => {
    void notificationStore.loadNotifications(nextAudience);
  },
);
</script>

<template>
  <div class="notification-preview">
    <RouterLink
      class="icon-button notification-button"
      :to="notificationRoute"
      :aria-label="triggerLabel"
    >
      <Bell :size="20" aria-hidden="true" />
      <span
        v-if="unreadNotificationCount > 0"
        class="notification-dot"
        aria-hidden="true"
      />
    </RouterLink>

    <div class="notification-popover">
      <section
        class="notification-popover-surface"
        :aria-label="`${previewHeading}预览`"
      >
        <header class="notification-preview-header">
          <strong>{{ previewHeading }}</strong>
          <button
            class="notification-preview-mark-all"
            type="button"
            :disabled="unreadNotificationCount === 0"
            :aria-label="
              unreadNotificationCount > 0
                ? `将 ${unreadNotificationCount} 条通知全部标为已读`
                : '所有通知均已读'
            "
            @click="notificationStore.markAllAsRead(audience)"
          >
            全部已读
          </button>
        </header>

        <div class="notification-preview-list">
          <RouterLink
            v-for="notification in previewNotifications"
            :key="notification.id"
            class="notification-preview-item"
            :class="{ unread: !notification.read }"
            :to="getNotificationTarget(notification)"
            @click="notificationStore.markAsRead(audience, notification.id)"
          >
            <span class="notification-preview-copy">
              <strong>{{ notification.title }}</strong>
              <span>{{ notification.category }} · {{ notification.time }}</span>
            </span>
            <span
              v-if="!notification.read"
              class="notification-preview-unread"
              aria-hidden="true"
            />
            <span v-if="!notification.read" class="visually-hidden">未读</span>
          </RouterLink>
        </div>

        <RouterLink class="notification-preview-footer" :to="notificationRoute">
          查看全部通知
        </RouterLink>
      </section>
    </div>
  </div>
</template>

<style scoped>
.notification-preview {
  --notification-accent: var(--color-primary);
  --notification-accent-soft: var(--color-primary-soft);

  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
}

:global(.variant-admin) .notification-preview {
  --notification-accent: var(--color-admin);
  --notification-accent-soft: var(--color-admin-soft);
}

.notification-popover {
  position: absolute;
  z-index: 30;
  top: 100%;
  left: 50%;
  display: none;
  width: min(352px, calc(100vw - 32px));
  padding-top: var(--space-2);
  transform: translateX(-50%);
}

.notification-preview:hover .notification-popover,
.notification-preview:focus-within .notification-popover {
  display: block;
}

.notification-popover-surface {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
  box-shadow: var(--shadow-lg);
}

.notification-preview-header {
  display: flex;
  min-height: 48px;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.notification-preview-header > strong {
  color: var(--color-text);
  font-size: var(--font-size-16);
}

.notification-preview-mark-all {
  min-height: 28px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-pill);
  color: var(--notification-accent);
  background: var(--notification-accent-soft);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
}

.notification-preview-mark-all:disabled {
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  cursor: default;
}

.notification-preview-list {
  display: grid;
}

.notification-preview-item {
  display: flex;
  min-width: 0;
  min-height: 64px;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  color: inherit;
  text-decoration: none;
}

.notification-preview-copy {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: var(--space-1);
}

.notification-preview-copy > strong {
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-preview-item.unread .notification-preview-copy > strong {
  color: var(--color-text);
  font-weight: var(--font-weight-semibold);
}

.notification-preview-copy > span {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.notification-preview-unread {
  flex: 0 0 8px;
  width: 8px;
  height: 8px;
  border-radius: var(--radius-pill);
  background: var(--notification-accent);
}

.notification-preview-footer {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  color: var(--notification-accent);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
}

@media (hover: hover) {
  .notification-preview-item:hover,
  .notification-preview-footer:hover,
  .notification-preview-mark-all:hover:not(:disabled) {
    background: var(--color-surface-subtle);
  }
}

@media (max-width: 767px), (hover: none) and (pointer: coarse) {
  .notification-preview:hover .notification-popover,
  .notification-preview:focus-within .notification-popover {
    display: none;
  }
}
</style>
