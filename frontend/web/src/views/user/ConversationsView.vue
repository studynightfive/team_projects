<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { MessageSquarePlus, X } from "../../components/icons";
import { localPageData } from "../../data/local-pages";

type ConversationItem = (typeof localPageData.conversations)[number];

const { message, modal } = AntApp.useApp();
const query = ref("");
const pinnedOnly = ref(false);
const visibleIds = ref<string[]>(
  localPageData.conversations.map((item) => item.id),
);
const titleOverrides = ref<Record<string, string>>({});
const editingId = ref<string>();
const editTitle = ref("");

const getConversationTitle = (item: ConversationItem): string =>
  titleOverrides.value[item.id] ?? item.title;

const filteredConversations = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase("zh-CN");

  return localPageData.conversations.filter((item) => {
    const isVisible = visibleIds.value.includes(item.id);
    const matchesPinned = !pinnedOnly.value || item.pinned;
    const matchesQuery =
      normalizedQuery.length === 0 ||
      `${getConversationTitle(item)}${item.preview}`
        .toLocaleLowerCase("zh-CN")
        .includes(normalizedQuery);

    return isVisible && matchesPinned && matchesQuery;
  });
});

const startRename = (item: ConversationItem): void => {
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
  void message.success("本地预览名称已更新，刷新后恢复固定数据");
};

const requestDelete = (conversationId: string): void => {
  editingId.value = undefined;
  modal.confirm({
    title: "确认从本地预览中删除这条会话？",
    content: "不会发送删除请求，刷新页面后固定数据会恢复。",
    okText: "确认删除",
    okType: "danger",
    cancelText: "取消",
    centered: true,
    autoFocusButton: "cancel",
    onOk: () => {
      visibleIds.value = visibleIds.value.filter((id) => id !== conversationId);
      void message.success("会话已从本地预览中移除");
    },
  });
};
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="用户工作区"
      title="历史会话"
      description="搜索、重命名、删除确认和继续提问均为当前页面的本地状态。"
    >
      <template #actions>
        <RouterLink class="primary-button" to="/chat">
          <MessageSquarePlus :size="17" aria-hidden="true" />
          新建问答
        </RouterLink>
      </template>
    </PageHeader>

    <ResourcePanel
      title="会话列表"
      description="固定数据不代表真实会话或分页契约。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
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

      <div v-if="filteredConversations.length > 0" class="conversation-list">
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
            <RouterLink class="primary-button compact" :to="`/chat/${item.id}`">
              继续提问
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
        <span>共 {{ filteredConversations.length }} 条本地记录</span>
        <span>第 1 / 1 页</span>
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
