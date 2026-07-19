<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  Bell,
  BookOpen,
  CheckCircle2,
  Search,
  ShieldCheck,
  Workflow,
  type LucideIcon,
} from "../../components/icons";
import type {
  NotificationAudience,
  NotificationCategory,
} from "../../data/account-support";
import { isRealApiMode } from "../../config/runtime";
import { useNotificationStore } from "../../stores/notifications";

type ReadFilter = "all" | "unread" | "read";

const props = defineProps<{
  audience: NotificationAudience;
}>();

const notificationStore = useNotificationStore();
const keyword = ref("");
const readFilter = ref<ReadFilter>("all");
const categoryFilter = ref<"all" | NotificationCategory>("all");

const categoryIcons = {
  任务: Workflow,
  知识: BookOpen,
  系统: Bell,
  安全: ShieldCheck,
} satisfies Record<NotificationCategory, LucideIcon>;

const categories: readonly NotificationCategory[] = [
  "任务",
  "知识",
  "系统",
  "安全",
];
const readFilterOptions = [
  { value: "all", label: "全部" },
  { value: "unread", label: "未读" },
  { value: "read", label: "已读" },
] as const satisfies readonly { value: ReadFilter; label: string }[];

const currentNotifications = computed(() =>
  notificationStore.getNotifications(props.audience),
);
const unreadCount = computed(() =>
  notificationStore.unreadCount(props.audience),
);
const loadState = computed(() => notificationStore.loadState[props.audience]);
const loadError = computed(() => notificationStore.loadError[props.audience]);
const filteredNotifications = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase("zh-CN");

  return currentNotifications.value.filter((item) => {
    const matchesReadState =
      readFilter.value === "all" ||
      (readFilter.value === "unread" ? !item.read : item.read);
    const matchesCategory =
      categoryFilter.value === "all" || item.category === categoryFilter.value;
    const matchesKeyword =
      normalizedKeyword.length === 0 ||
      `${item.title}${item.description}`
        .toLocaleLowerCase("zh-CN")
        .includes(normalizedKeyword);

    return matchesReadState && matchesCategory && matchesKeyword;
  });
});

const reloadNotifications = (): void => {
  void notificationStore.loadNotifications(props.audience);
};

onMounted(reloadNotifications);

watch(
  () => props.audience,
  () => {
    reloadNotifications();
  },
);
</script>

<template>
  <div class="business-page notifications-page">
    <PageHeader
      eyebrow="账号与支持"
      title="通知中心"
      :description="
        audience === 'admin'
          ? '集中查看需要管理员关注的治理与运行提醒。'
          : '集中查看任务、知识更新、系统和安全提醒。'
      "
    >
      <template #actions>
        <span class="local-preview-badge" aria-live="polite">
          {{ unreadCount }} 条未读 · {{ isRealApiMode ? "真实接口" : "当前会话" }}
        </span>
        <button
          v-if="isRealApiMode"
          class="secondary-button"
          type="button"
          @click="reloadNotifications"
        >
          刷新
        </button>
        <button
          class="secondary-button"
          type="button"
          :disabled="unreadCount === 0"
          @click="notificationStore.markAllAsRead(audience)"
        >
          <CheckCircle2 :size="16" aria-hidden="true" />
          全部标为已读
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="全部通知"
      :description="
        isRealApiMode
          ? '通知列表和已读状态来自真实后端接口。'
          : '筛选和已读状态只保留在本次打开应用期间，不会发送保存请求。'
      "
    >
      <template #actions>
        <div class="segmented-control" aria-label="按阅读状态筛选">
          <button
            v-for="option in readFilterOptions"
            :key="option.value"
            type="button"
            :class="{ active: readFilter === option.value }"
            :aria-pressed="readFilter === option.value"
            @click="readFilter = option.value"
          >
            {{ option.label }}
          </button>
        </div>
      </template>

      <div class="notification-filter-bar">
        <label class="notification-search-field">
          <span class="visually-hidden">搜索通知</span>
          <Search :size="17" aria-hidden="true" />
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索通知标题或内容"
            autocomplete="off"
          />
        </label>
        <label class="notification-category-field">
          <span>通知类型</span>
          <select v-model="categoryFilter">
            <option value="all">全部类型</option>
            <option v-for="category in categories" :key="category">
              {{ category }}
            </option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="isRealApiMode && loadState === 'loading'"
        kind="loading"
        title="正在加载通知"
        description="正在读取当前账号的真实通知。"
      />
      <InlineState
        v-else-if="isRealApiMode && loadState === 'error'"
        kind="error"
        title="通知加载失败"
        :description="loadError"
      />
      <div
        v-else-if="filteredNotifications.length > 0"
        class="notification-list"
        aria-live="polite"
      >
        <article
          v-for="notification in filteredNotifications"
          :key="notification.id"
          :class="{ unread: !notification.read }"
        >
          <span class="notification-item-icon" aria-hidden="true">
            <component :is="categoryIcons[notification.category]" :size="20" />
          </span>

          <div class="notification-item-copy">
            <div class="notification-item-heading">
              <h3>{{ notification.title }}</h3>
              <span
                class="status-chip"
                :class="notification.read ? '' : 'info'"
              >
                {{ notification.read ? "已读" : "未读" }}
              </span>
              <span class="notification-category">{{
                notification.category
              }}</span>
            </div>
            <p>{{ notification.description }}</p>
            <time>{{ notification.time }}</time>
          </div>

          <div class="notification-item-actions">
            <RouterLink
              v-if="notification.action !== undefined"
              class="secondary-button compact"
              :to="notification.action.to"
              @click="notificationStore.markAsRead(audience, notification.id)"
            >
              {{ notification.action.label }}
            </RouterLink>
            <button
              v-if="!notification.read"
              class="text-button"
              type="button"
              @click="notificationStore.markAsRead(audience, notification.id)"
            >
              标为已读
            </button>
          </div>
        </article>
      </div>

      <InlineState
        v-else
        kind="empty"
        title="没有符合条件的通知"
        description="请清空关键词，或调整阅读状态与通知类型。"
      />

      <template #footer>
        <span>显示 {{ filteredNotifications.length }} 条通知</span>
        <span>{{
          isRealApiMode ? "已读状态会写入后端" : "刷新应用后恢复固定样例"
        }}</span>
      </template>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.notifications-page {
  gap: var(--space-5);
}

.notification-filter-bar,
.notification-search-field,
.notification-item-heading,
.notification-item-actions {
  display: flex;
  align-items: center;
}

.notification-filter-bar {
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.notification-search-field {
  min-height: 40px;
  flex: 1 1 360px;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
}

.notification-search-field input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
}

.notification-search-field input:focus-visible {
  box-shadow: none;
}

.notification-category-field {
  display: grid;
  min-width: 180px;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.notification-category-field select {
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text);
  background: var(--color-surface);
}

.notification-list {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
}

.notification-list article {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.notification-list article:first-child {
  border-top: 0;
}

.notification-list article.unread {
  background: color-mix(in srgb, var(--color-primary-soft) 42%, white);
}

.notification-item-icon {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.variant-admin .notification-item-icon {
  color: var(--color-admin);
  background: var(--color-admin-soft);
}

.notification-item-copy {
  min-width: 0;
}

.notification-item-heading {
  min-width: 0;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.notification-item-heading h3 {
  min-width: 0;
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-15);
  font-weight: var(--font-weight-semibold);
}

.notification-category {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.notification-item-copy p {
  margin: var(--space-2) 0 var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
  line-height: 1.65;
}

.notification-item-copy time {
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
}

.notification-item-actions {
  justify-content: flex-end;
  gap: var(--space-3);
}

@media (max-width: 767px) {
  .notifications-page :deep(.resource-panel-actions) {
    width: 100%;
    grid-template-columns: minmax(0, 1fr);
  }

  .notifications-page .segmented-control {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .notification-filter-bar {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }

  .notification-search-field,
  .notification-category-field {
    width: 100%;
    min-height: 44px;
  }

  .notification-category-field select {
    min-height: 44px;
  }

  .notification-list article {
    grid-template-columns: 44px minmax(0, 1fr);
    align-items: start;
  }

  .notification-item-actions {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .notification-item-actions > * {
    width: 100%;
    justify-content: center;
  }
}
</style>
