<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { MessageSquarePlus, X } from "../../components/icons";
import { isRealApiMode } from "../../config/runtime";
import { localPageData } from "../../data/local-pages";
import {
  deleteConversation,
  listConversations,
  type ConversationRecord,
} from "../../services/conversations";

interface DisplayConversation {
  readonly id: string;
  readonly title: string;
  readonly preview: string;
  readonly updated: string;
  readonly messages: number;
  readonly pinned: boolean;
}

const { message, modal } = AntApp.useApp();
const query = ref("");
const pinnedOnly = ref(false);
const visibleIds = ref<string[]>(
  localPageData.conversations.map((item) => item.id),
);
const titleOverrides = ref<Record<string, string>>({});
const editingId = ref<string>();
const editTitle = ref("");
const realConversations = ref<readonly ConversationRecord[]>([]);
const loadState = ref<"idle" | "loading" | "success" | "error">("idle");
const loadError = ref("");
let loadController: AbortController | undefined;

const toDisplayConversation = (item: ConversationRecord): DisplayConversation => ({
  id: item.id,
  title: item.title || "知识库问答",
  preview: item.title || "查看会话消息了解提问与回答。",
  updated: new Date(
    item.last_message_at ?? item.updated_at ?? item.created_at ?? Date.now(),
  ).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }),
  messages: item.message_count,
  pinned: item.is_pinned,
});

const conversations = computed<readonly DisplayConversation[]>(() =>
  isRealApiMode
    ? realConversations.value.map(toDisplayConversation)
    : localPageData.conversations,
);

const getConversationTitle = (item: DisplayConversation): string =>
  titleOverrides.value[item.id] ?? item.title;

const filteredConversations = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase("zh-CN");

  return conversations.value.filter((item) => {
    const isVisible = isRealApiMode || visibleIds.value.includes(item.id);
    const matchesPinned = !pinnedOnly.value || item.pinned;
    const matchesQuery =
      normalizedQuery.length === 0 ||
      `${getConversationTitle(item)}${item.preview}`
        .toLocaleLowerCase("zh-CN")
        .includes(normalizedQuery);

    return isVisible && matchesPinned && matchesQuery;
  });
});

const loadRealConversations = async (): Promise<void> => {
  if (!isRealApiMode) return;

  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loadState.value = "loading";
  loadError.value = "";

  try {
    realConversations.value = await listConversations(controller.signal);
    loadState.value = "success";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = toPublicApiError(error).message;
    loadState.value = "error";
  }
};

const startRename = (item: DisplayConversation): void => {
  editingId.value = item.id;
  editTitle.value = getConversationTitle(item);
};

const saveRename = (): void => {
  if (!editingId.value) return;

  const nextTitle = editTitle.value.trim();
  if (nextTitle.length === 0) {
    void message.warning("会话名称不能为空");
    return;
  }

  titleOverrides.value = {
    ...titleOverrides.value,
    [editingId.value]: nextTitle,
  };
  editingId.value = undefined;
  void message.success(
    isRealApiMode ? "当前版本暂不支持重命名真实会话" : "本地预览名称已更新，刷新后恢复固定数据",
  );
};

const requestDelete = (conversationId: string): void => {
  editingId.value = undefined;
  modal.confirm({
    title: isRealApiMode ? "确认删除这条真实会话？" : "确认从本地预览中删除这条会话？",
    content: isRealApiMode
      ? "删除后该会话不会再出现在历史记录中。"
      : "不会发送删除请求，刷新页面后固定数据会恢复。",
    okText: "确认删除",
    okType: "danger",
    cancelText: "取消",
    centered: true,
    autoFocusButton: "cancel",
    onOk: async () => {
      if (isRealApiMode) {
        try {
          await deleteConversation(conversationId);
          realConversations.value = realConversations.value.filter(
            (item) => item.id !== conversationId,
          );
          void message.success("真实会话已删除");
        } catch (error: unknown) {
          void message.error(toPublicApiError(error).message);
        }
        return;
      }

      visibleIds.value = visibleIds.value.filter((id) => id !== conversationId);
      void message.success("会话已从本地预览中移除");
    },
  });
};

onMounted(() => {
  void loadRealConversations();
});

onBeforeUnmount(() => {
  loadController?.abort();
});
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="用户工作区"
      title="历史会话"
      :description="
        isRealApiMode
          ? '展示真实 RAG 问答生成后的历史会话。'
          : '搜索、重命名、删除确认和继续提问均为当前页面的本地状态。'
      "
    >
      <template #actions>
        <RouterLink class="primary-button" to="/">
          <MessageSquarePlus :size="17" aria-hidden="true" />
          新建问答
        </RouterLink>
      </template>
    </PageHeader>

    <ResourcePanel
      title="会话列表"
      :description="
        isRealApiMode
          ? '记录来自后端会话表；RAG 问答完成后会自动新增。'
          : '固定数据不代表真实会话或分页契约。'
      "
    >
      <template #actions>
        <span class="local-preview-badge">
          {{ isRealApiMode ? "真实记录" : "本地预览" }}
        </span>
      </template>

      <div class="filter-bar">
        <label class="filter-field grow">
          <span>搜索历史会话</span>
          <input
            v-model="query"
            type="search"
            placeholder="搜索标题或摘要"
            autocomplete="off"
          />
        </label>
        <label class="checkbox-filter">
          <input v-model="pinnedOnly" type="checkbox" />
          只看置顶
        </label>
      </div>

      <InlineState
        v-if="isRealApiMode && loadState === 'loading'"
        kind="loading"
        title="正在加载真实会话"
        description="系统正在读取当前账号的 RAG 问答记录。"
      />
      <InlineState
        v-else-if="isRealApiMode && loadState === 'error'"
        kind="error"
        title="真实会话加载失败"
        :description="loadError"
      />

      <div v-else-if="filteredConversations.length > 0" class="conversation-list">
        <article v-for="item in filteredConversations" :key="item.id">
          <div class="conversation-copy">
            <span v-if="item.pinned" class="status-chip success">已置顶</span>
            <template v-if="editingId === item.id">
              <label :for="`conversation-title-${item.id}`">会话名称</label>
              <input
                :id="`conversation-title-${item.id}`"
                v-model="editTitle"
                class="title-editor"
                type="text"
                @keyup.enter="saveRename"
                @keyup.escape="editingId = undefined"
              />
              <div class="inline-actions">
                <button
                  class="primary-button compact"
                  type="button"
                  @click="saveRename"
                >
                  保存本地名称
                </button>
                <button
                  class="secondary-button compact"
                  type="button"
                  @click="editingId = undefined"
                >
                  取消
                </button>
              </div>
            </template>
            <template v-else>
              <h3>{{ getConversationTitle(item) }}</h3>
              <p>{{ item.preview }}</p>
              <span class="conversation-meta">
                {{ item.updated }} · {{ item.messages }} 条消息
              </span>
            </template>
          </div>
          <div v-if="editingId !== item.id" class="conversation-actions">
            <RouterLink class="primary-button compact" to="/">
              发起新问答
            </RouterLink>
            <button
              class="secondary-button compact"
              type="button"
              @click="startRename(item)"
            >
              重命名
            </button>
            <button
              class="icon-action"
              type="button"
              :aria-label="`删除${getConversationTitle(item)}`"
              @click="requestDelete(item.id)"
            >
              <X :size="17" aria-hidden="true" />
            </button>
          </div>
        </article>
      </div>

      <InlineState
        v-else
        kind="empty"
        title="没有匹配的会话"
        description="请调整关键词或关闭“只看置顶”。"
      />

      <template #footer>
        <span>
          共 {{ filteredConversations.length }} 条{{
            isRealApiMode ? "真实记录" : "本地记录"
          }}
        </span>
        <span>已加载全部记录</span>
      </template>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.local-page,
.conversation-list {
  display: grid;
  gap: var(--space-6);
}

.filter-bar {
  margin-bottom: var(--space-4);
}

.checkbox-filter {
  display: inline-flex;
  min-width: auto;
  min-height: 40px;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-14);
  white-space: nowrap;
}

.checkbox-filter input {
  width: 14px;
  height: 14px;
  min-height: 14px;
  margin: 0;
  padding: 0;
  accent-color: var(--color-primary);
}

.inline-actions,
.conversation-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.conversation-list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
}

.conversation-copy {
  min-width: 0;
}

.conversation-copy h3 {
  margin: var(--space-2) 0;
  overflow: hidden;
  font-size: var(--font-size-16);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-copy p {
  margin-bottom: var(--space-2);
  overflow: hidden;
  color: var(--color-text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-meta,
.conversation-copy label {
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
}

.title-editor {
  width: 100%;
  min-height: 40px;
  margin: var(--space-2) 0;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
}

.icon-action {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-danger-text);
  background: var(--color-danger-soft);
}

@media (max-width: 820px) {
  .conversation-list article {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }

  .conversation-actions {
    flex-wrap: wrap;
  }
}

@media (max-width: 767px) {
  .conversation-list article {
    padding: var(--space-4);
  }

  .conversation-actions .primary-button,
  .conversation-actions .secondary-button {
    min-height: 44px;
  }
}
</style>
