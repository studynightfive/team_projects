<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import SafeMarkdown from "../../components/common/SafeMarkdown.vue";
import { ExternalLink, Search, Trash2 } from "../../components/icons";
import { useListPagination } from "../../composables/useListPagination";
import { isRealApiMode } from "../../config/runtime";
import {
  deleteConversation,
  listConversationMessages,
  listConversations,
  type ConversationRecord,
  type MessageRecord,
} from "../../services/conversations";

const router = useRouter();
const { message, modal } = AntApp.useApp();
const conversations = ref<readonly ConversationRecord[]>([]);
const selectedConversationId = ref("");
const selectedMessages = ref<readonly MessageRecord[]>([]);
const keyword = ref("");
const loadState = ref<"loading" | "success" | "error">("loading");
const messageState = ref<"idle" | "loading" | "success" | "error">("idle");
const loadError = ref("");
const messageError = ref("");
let loadController: AbortController | undefined;
let messageController: AbortController | undefined;

const mockConversations: readonly ConversationRecord[] = [
  {
    id: "mock-conversation-1",
    user_id: "mock-user",
    kb_id: "kb-medical",
    knowledge_base_ids: ["kb-medical"],
    title: "医疗信息化平台包含哪些核心模块",
    is_pinned: false,
    is_archived: false,
    message_count: 2,
    last_message_at: "2026-07-26T09:30:00+08:00",
    created_at: "2026-07-26T09:29:00+08:00",
    updated_at: "2026-07-26T09:30:00+08:00",
  },
];

const mockMessages: readonly MessageRecord[] = [
  {
    id: "mock-user-message",
    conversation_id: "mock-conversation-1",
    role: "user",
    content: "医疗信息化平台包含哪些核心模块？",
    citations: [],
    finish_reason: null,
    created_at: "2026-07-26T09:29:00+08:00",
  },
  {
    id: "mock-assistant-message",
    conversation_id: "mock-conversation-1",
    role: "assistant",
    content:
      "演示会话会在这里展示完整答案。真实 API 模式下，页面读取服务端保存的问答和引用。",
    citations: [],
    finish_reason: "stop",
    created_at: "2026-07-26T09:30:00+08:00",
  },
];

const visibleConversations = computed(() => {
  const normalized = keyword.value.trim().toLocaleLowerCase("zh-CN");
  if (normalized.length === 0) return conversations.value;
  return conversations.value.filter((item) =>
    item.title.toLocaleLowerCase("zh-CN").includes(normalized),
  );
});

const selectedConversation = computed(() =>
  conversations.value.find(
    (item) => item.id === selectedConversationId.value,
  ),
);

const {
  page,
  pageSize,
  pagedItems,
  setPage,
} = useListPagination(visibleConversations);

const formatTime = (value: string | null): string => {
  if (value === null) return "暂无时间";
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
};

const openConversation = async (conversationId: string): Promise<void> => {
  selectedConversationId.value = conversationId;
  messageController?.abort();
  if (!isRealApiMode) {
    selectedMessages.value = mockMessages;
    messageState.value = "success";
    return;
  }

  const controller = new AbortController();
  messageController = controller;
  messageState.value = "loading";
  messageError.value = "";
  try {
    selectedMessages.value = await listConversationMessages(
      conversationId,
      controller.signal,
    );
    messageState.value = "success";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    messageError.value = toPublicApiError(error).message;
    messageState.value = "error";
  }
};

const loadHistory = async (): Promise<void> => {
  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loadState.value = "loading";
  loadError.value = "";
  try {
    conversations.value = isRealApiMode
      ? await listConversations(controller.signal)
      : mockConversations;
    loadState.value = "success";
    const first = conversations.value[0];
    if (first !== undefined) await openConversation(first.id);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = toPublicApiError(error).message;
    loadState.value = "error";
  }
};

const continueConversation = (): void => {
  if (selectedConversationId.value === "") return;
  void router.push({
    path: "/",
    query: { conversation: selectedConversationId.value },
  });
};

const requestDelete = (item: ConversationRecord): void => {
  modal.confirm({
    title: "删除这段对话？",
    content: "删除后，这段问答将不再出现在对话历史中。",
    okText: "删除",
    okType: "danger",
    cancelText: "取消",
    centered: true,
    autoFocusButton: "cancel",
    onOk: async () => {
      try {
        if (isRealApiMode) await deleteConversation(item.id);
        conversations.value = conversations.value.filter(
          (conversation) => conversation.id !== item.id,
        );
        if (selectedConversationId.value === item.id) {
          selectedConversationId.value = "";
          selectedMessages.value = [];
          const first = conversations.value[0];
          if (first !== undefined) await openConversation(first.id);
        }
        void message.success("对话已删除");
      } catch (error: unknown) {
        void message.error(toPublicApiError(error).message);
      }
    },
  });
};

onMounted(() => void loadHistory());

onBeforeUnmount(() => {
  loadController?.abort();
  messageController?.abort();
});
</script>

<template>
  <div class="business-page conversation-history-page">
    <PageHeader
      eyebrow="个人知识资产"
      title="对话历史"
      description="回看已保存的知识库问答，或从任意一段对话继续提问。"
    />

    <div class="conversation-history-layout">
      <aside class="conversation-list-panel" aria-label="历史会话列表">
        <label class="conversation-search">
          <Search :size="17" aria-hidden="true" />
          <span class="visually-hidden">搜索对话</span>
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索对话标题"
            autocomplete="off"
          />
        </label>

        <InlineState
          v-if="loadState === 'loading'"
          kind="loading"
          title="正在加载对话历史"
          description="系统正在读取当前账号保存的问答。"
        />
        <InlineState
          v-else-if="loadState === 'error'"
          kind="error"
          title="对话历史加载失败"
          :description="loadError"
        />
        <div v-else-if="visibleConversations.length > 0" class="conversation-list">
          <article
            v-for="item in pagedItems"
            :key="item.id"
            :class="{ active: item.id === selectedConversationId }"
          >
            <button
              class="conversation-select"
              type="button"
              @click="openConversation(item.id)"
            >
              <strong>{{ item.title || "未命名对话" }}</strong>
              <span>
                {{ item.message_count }} 条消息 ·
                {{ formatTime(item.last_message_at ?? item.updated_at) }}
              </span>
            </button>
            <button
              class="conversation-delete"
              type="button"
              :aria-label="`删除对话${item.title}`"
              @click="requestDelete(item)"
            >
              <Trash2 :size="16" aria-hidden="true" />
            </button>
          </article>
          <ListPagination
            :page="page"
            :page-size="pageSize"
            :total="visibleConversations.length"
            @change="setPage"
          />
        </div>
        <InlineState
          v-else
          kind="empty"
          title="暂无对话历史"
          description="在 AI 搜索中完成一次问答后，对话会自动保存在这里。"
        />
      </aside>

      <main class="conversation-detail" aria-live="polite">
        <header v-if="selectedConversation !== undefined">
          <div>
            <span>已保存的问答</span>
            <h2>{{ selectedConversation.title || "未命名对话" }}</h2>
          </div>
          <button class="primary-button compact" type="button" @click="continueConversation">
            <ExternalLink :size="16" aria-hidden="true" />
            继续对话
          </button>
        </header>

        <InlineState
          v-if="messageState === 'loading'"
          kind="loading"
          title="正在加载消息"
          description="正在恢复问题、答案和引用信息。"
        />
        <InlineState
          v-else-if="messageState === 'error'"
          kind="error"
          title="消息加载失败"
          :description="messageError"
        />
        <div v-else-if="selectedMessages.length > 0" class="history-message-list">
          <article
            v-for="item in selectedMessages"
            :key="item.id"
            :class="`history-message ${item.role}`"
          >
            <span>{{ item.role === "user" ? "你的问题" : "AI 回答" }}</span>
            <p v-if="item.role === 'user'">{{ item.content }}</p>
            <SafeMarkdown v-else :content="item.content" />
          </article>
        </div>
        <InlineState
          v-else
          kind="empty"
          title="请选择一段对话"
          description="从左侧列表选择后，可在这里查看完整问答。"
        />
      </main>
    </div>
  </div>
</template>

<style scoped>
.conversation-history-layout {
  display: grid;
  min-height: 620px;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
  overflow: hidden;
}

.conversation-list-panel {
  padding: var(--space-5);
  border-right: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.conversation-search {
  display: flex;
  min-height: 42px;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.conversation-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
}

.conversation-list {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.conversation-list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 36px;
  border: 1px solid transparent;
  border-radius: var(--radius-8);
}

.conversation-list article.active {
  border-color: var(--color-primary);
  background: var(--color-surface);
}

.conversation-select {
  min-width: 0;
  padding: var(--space-3);
  border: 0;
  color: var(--color-text);
  background: transparent;
  text-align: left;
}

.conversation-select strong,
.conversation-select span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-select span {
  margin-top: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.conversation-delete {
  width: 36px;
  height: 36px;
  align-self: center;
  border: 0;
  color: var(--color-danger);
  background: transparent;
}

.conversation-detail {
  min-width: 0;
  padding: var(--space-6);
}

.conversation-detail > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.conversation-detail header span,
.history-message > span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.conversation-detail h2 {
  margin: var(--space-2) 0 0;
  font-size: var(--font-size-22);
}

.history-message-list {
  display: grid;
  gap: var(--space-5);
  margin-top: var(--space-5);
}

.history-message {
  max-width: min(860px, 92%);
}

.history-message.user {
  justify-self: end;
  padding: var(--space-4);
  border-radius: var(--radius-8);
  background: var(--color-primary-soft);
}

.history-message.assistant {
  justify-self: start;
}

.history-message p {
  margin: var(--space-2) 0 0;
  white-space: pre-wrap;
}

@media (max-width: 767px) {
  .conversation-history-layout {
    grid-template-columns: 1fr;
  }

  .conversation-list-panel {
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }

  .conversation-detail {
    padding: var(--space-4);
  }

  .conversation-detail > header {
    flex-direction: column;
  }

  .history-message {
    max-width: 100%;
  }
}
</style>
