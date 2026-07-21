<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  Pencil,
  RotateCcw,
  Search,
  Star,
  Trash2,
} from "../../components/icons";
import { isRealApiMode } from "../../config/runtime";
import { aiSearchMockData } from "../../mocks/ai-search";
import {
  deleteConversation,
  listConversations,
  updateConversationTitle,
  type ConversationRecord,
} from "../../services/conversations";
import {
  createFavorite,
  deleteFavorite,
  listFavorites,
} from "../../services/favorites";
import type {
  SearchHistory,
  SearchMode,
  SearchSourceType,
} from "../../types/ai-search";

interface HistoryGroup {
  readonly label: string;
  readonly items: readonly SearchHistory[];
}

const modeLabels = {
  smart: "智能搜索",
  precise: "精准检索",
  document: "文档问答",
} satisfies Record<SearchMode, string>;

const sourceLabels = {
  knowledge: "企业知识库",
  project: "项目文档",
  policy: "规章制度",
  meeting: "会议记录",
  business: "业务数据",
  personal: "个人文件",
  internet: "互联网信息",
} satisfies Record<SearchSourceType, string>;

const router = useRouter();
const { message, modal } = AntApp.useApp();
const keyword = ref("");
const modeFilter = ref<"all" | SearchMode>("all");
const favoriteOnly = ref(false);
const hiddenIds = ref<ReadonlySet<string>>(new Set());
const titleOverrides = ref<Record<string, string>>({});
const favoriteOverrides = ref<Record<string, boolean>>({});
const favoriteIdBySource = ref<Record<string, string>>({});
const editingId = ref<string>();
const editTitle = ref("");
const realConversations = ref<readonly ConversationRecord[]>([]);
const loadState = ref<"idle" | "loading" | "success" | "error">("idle");
const loadError = ref("");
let loadController: AbortController | undefined;

const realHistory = computed<readonly SearchHistory[]>(() =>
  realConversations.value.map((item) => ({
    id: item.id,
    query: item.title || "知识库问答",
    mode: "smart",
    sources: ["knowledge"],
    createdAt: item.last_message_at ?? item.updated_at ?? item.created_at ?? new Date().toISOString(),
    resultCount: Math.max(0, item.message_count - 1),
    isFavorite: false,
  })),
);

const historyItems = computed<readonly SearchHistory[]>(() =>
  isRealApiMode ? realHistory.value : aiSearchMockData.history,
);

const getTitle = (item: SearchHistory): string =>
  titleOverrides.value[item.id] ?? item.query;

const isFavorite = (item: SearchHistory): boolean =>
  favoriteOverrides.value[item.id] ?? item.isFavorite;

const filteredHistory = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase("zh-CN");

  return historyItems.value.filter((item) => {
    const searchableText = `${getTitle(item)}${item.sources
      .map((source) => sourceLabels[source])
      .join("")}`.toLocaleLowerCase("zh-CN");

    return (
      !hiddenIds.value.has(item.id) &&
      (modeFilter.value === "all" || item.mode === modeFilter.value) &&
      (!favoriteOnly.value || isFavorite(item)) &&
      (normalizedKeyword.length === 0 ||
        searchableText.includes(normalizedKeyword))
    );
  });
});

const historyGroups = computed<readonly HistoryGroup[]>(() => {
  const groupedItems = new Map<string, SearchHistory[]>();

  for (const item of filteredHistory.value) {
    const label = new Date(item.createdAt).toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "short",
    });
    groupedItems.set(label, [...(groupedItems.get(label) ?? []), item]);
  }

  return Array.from(groupedItems, ([label, items]) => ({ label, items }));
});
const formatTime = (value: string): string =>
  new Date(value).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

const startRename = (item: SearchHistory): void => {
  editingId.value = item.id;
  editTitle.value = getTitle(item);
};

const saveRename = async (): Promise<void> => {
  if (!editingId.value) return;

  const nextTitle = editTitle.value.trim();
  if (nextTitle.length === 0) {
    void message.warning("搜索名称不能为空");
    return;
  }

  const targetId = editingId.value;
  if (isRealApiMode) {
    try {
      const updated = await updateConversationTitle(targetId, nextTitle);
      realConversations.value = realConversations.value.map((item) =>
        item.id === targetId ? updated : item,
      );
      editingId.value = undefined;
      void message.success("搜索名称已保存");
    } catch (error: unknown) {
      void message.error(toPublicApiError(error).message);
    }
    return;
  }
  titleOverrides.value = { ...titleOverrides.value, [targetId]: nextTitle };
  editingId.value = undefined;
  void message.success("搜索名称已在当前页面更新，刷新后恢复模拟数据");
};

const toggleFavorite = async (item: SearchHistory): Promise<void> => {
  if (isRealApiMode) {
    try {
      if (isFavorite(item)) {
        const favoriteId = favoriteIdBySource.value[item.id];
        if (favoriteId !== undefined) {
          await deleteFavorite(favoriteId);
          const nextIds = { ...favoriteIdBySource.value };
          delete nextIds[item.id];
          favoriteIdBySource.value = nextIds;
        }
        favoriteOverrides.value = {
          ...favoriteOverrides.value,
          [item.id]: false,
        };
        void message.success("已取消收藏");
        return;
      }

      const favorite = await createFavorite({
        type: "query",
        title: getTitle(item),
        summary: `搜索模式：${modeLabels[item.mode]}`,
        tags: ["搜索历史"],
        note: "",
        source_id: item.id,
        source_payload: {
          conversationId: item.id,
          mode: item.mode,
          sources: [...item.sources],
        },
      });
      favoriteIdBySource.value = {
        ...favoriteIdBySource.value,
        [item.id]: favorite.id,
      };
      favoriteOverrides.value = {
        ...favoriteOverrides.value,
        [item.id]: true,
      };
      void message.success("已保存到真实收藏");
    } catch (error: unknown) {
      void message.error(toPublicApiError(error).message);
    }
    return;
  }

  const nextValue = !isFavorite(item);
  favoriteOverrides.value = {
    ...favoriteOverrides.value,
    [item.id]: nextValue,
  };
  void message.success(nextValue ? "已加入本地收藏" : "已取消本地收藏");
};

const requestDelete = (historyId: string): void => {
  editingId.value = undefined;
  modal.confirm({
    title: "确认删除这条搜索记录？",
    content: isRealApiMode
      ? "删除后对应的真实历史会话也会被移除。"
      : "本操作只影响当前页面，刷新后会恢复固定模拟数据。",
    okText: "确认删除",
    okType: "danger",
    cancelText: "取消",
    centered: true,
    autoFocusButton: "cancel",
    onOk: async () => {
      if (isRealApiMode) {
        try {
          await deleteConversation(historyId);
          realConversations.value = realConversations.value.filter(
            (item) => item.id !== historyId,
          );
          void message.success("真实搜索记录已删除");
        } catch (error: unknown) {
          void message.error(toPublicApiError(error).message);
        }
        return;
      }

      hiddenIds.value = new Set([...hiddenIds.value, historyId]);
      void message.success("记录已从当前页面移除，刷新后恢复模拟数据");
    },
  });
};

const resetSearch = (): void => {
  keyword.value = "";
};

const requestBulkDeleteFiltered = (): void => {
  const visibleIds = filteredHistory.value.map((item) => item.id);
  if (visibleIds.length === 0) {
    void message.info("当前筛选条件下没有可删除的记录");
    return;
  }

  editingId.value = undefined;
  modal.confirm({
    title: `确认批量删除 ${visibleIds.length} 条筛选结果？`,
    content: isRealApiMode
      ? "将删除点击按钮时当前筛选出的真实历史会话；其他记录不受影响。"
      : "只删除点击按钮时当前筛选出的记录；其他记录不受影响，刷新后模拟数据会恢复。",
    okText: "确认批量删除",
    okType: "danger",
    cancelText: "取消",
    centered: true,
    autoFocusButton: "cancel",
    onOk: async () => {
      if (isRealApiMode) {
        const results = await Promise.allSettled(
          visibleIds.map((id) => deleteConversation(id)),
        );
        const deletedIds = new Set(
          visibleIds.filter((_, index) => results[index]?.status === "fulfilled"),
        );
        realConversations.value = realConversations.value.filter(
          (item) => !deletedIds.has(item.id),
        );
        const failed = visibleIds.length - deletedIds.size;
        if (failed > 0) {
          void message.warning(`已删除 ${deletedIds.size} 条，${failed} 条删除失败`);
        } else {
          void message.success(`已删除 ${deletedIds.size} 条真实搜索记录`);
        }
        return;
      }
      hiddenIds.value = new Set([...hiddenIds.value, ...visibleIds]);
      void message.success(
        `已从当前页面删除 ${visibleIds.length} 条筛选结果，刷新后恢复模拟数据`,
      );
    },
  });
};

const repeatSearch = (item: SearchHistory): void => {
  if (isRealApiMode) {
    void router.push({
      path: "/search",
      state: {
        initialSearch: {
          q: item.query,
          mode: item.mode,
          sources: item.sources.join(","),
        },
      },
    });
    return;
  }

  void router.push({
    path: "/search",
    query: {
      q: item.query,
      mode: item.mode,
      sources: item.sources.join(","),
    },
  });
};

const loadRealHistory = async (): Promise<void> => {
  if (!isRealApiMode) return;

  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loadState.value = "loading";
  loadError.value = "";

  try {
    const [conversations, favorites] = await Promise.all([
      listConversations(controller.signal),
      listFavorites(controller.signal),
    ]);
    realConversations.value = conversations;

    const nextFavoriteIds: Record<string, string> = {};
    const nextFavoriteOverrides: Record<string, boolean> = {};
    for (const favorite of favorites) {
      if (favorite.type !== "query" || favorite.sourceId.length === 0) continue;
      nextFavoriteIds[favorite.sourceId] = favorite.id;
      nextFavoriteOverrides[favorite.sourceId] = true;
    }
    favoriteIdBySource.value = nextFavoriteIds;
    favoriteOverrides.value = nextFavoriteOverrides;
    loadState.value = "success";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = toPublicApiError(error).message;
    loadState.value = "error";
  }
};

onMounted(() => {
  void loadRealHistory();
});

onBeforeUnmount(() => {
  loadController?.abort();
});
</script>

<template>
  <div class="business-page search-history-page">
    <PageHeader
      eyebrow="个人搜索资产"
      title="搜索历史"
      :description="
        isRealApiMode
          ? '展示真实 RAG 问答形成的搜索记录；刷新后仍可查看已落库记录。'
          : '筛选、整理并重新运行最近的搜索；所有编辑仅保留在当前页面。'
      "
    >
      <template #actions>
        <span class="local-preview-badge">
          {{ isRealApiMode ? "真实记录" : "本地模拟记录" }}
        </span>
      </template>
    </PageHeader>

    <ResourcePanel
      title="历史记录"
      :description="
        isRealApiMode
          ? '记录来自后端会话表；RAG 问答完成后会自动新增。'
          : '搜索名称、收藏和删除状态不会写入服务器。'
      "
    >
      <template #actions>
        <button
          class="secondary-button compact history-panel-action"
          type="button"
          :disabled="keyword.length === 0"
          @click="resetSearch"
        >
          <RotateCcw :size="15" aria-hidden="true" />
          重置搜索
        </button>
        <button
          class="secondary-button compact history-panel-action"
          type="button"
          :disabled="filteredHistory.length === 0"
          @click="requestBulkDeleteFiltered"
        >
          <Trash2 :size="15" aria-hidden="true" />
          批量删除当前筛选结果
        </button>
      </template>

      <div class="history-filter-bar">
        <label class="history-search-field">
          <span class="visually-hidden">搜索历史记录</span>
          <Search :size="17" aria-hidden="true" />
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索问题或来源"
            autocomplete="off"
          />
        </label>
        <select v-model="modeFilter" aria-label="按搜索模式筛选">
          <option value="all">全部搜索模式</option>
          <option
            v-for="option in aiSearchMockData.modeOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </select>
        <label class="favorite-filter">
          <input v-model="favoriteOnly" type="checkbox" />
          只看收藏
        </label>
      </div>

      <InlineState
        v-if="isRealApiMode && loadState === 'loading'"
        kind="loading"
        title="正在加载真实搜索历史"
        description="系统正在读取当前账号的 RAG 问答记录。"
      />
      <InlineState
        v-else-if="isRealApiMode && loadState === 'error'"
        kind="error"
        title="真实搜索历史加载失败"
        :description="loadError"
      />

      <div v-else-if="historyGroups.length > 0" class="history-groups">
        <section
          v-for="group in historyGroups"
          :key="group.label"
          class="history-group"
        >
          <h2>{{ group.label }}</h2>
          <div class="history-list">
            <article v-for="item in group.items" :key="item.id">
              <div class="history-copy">
                <template v-if="editingId === item.id">
                  <label :for="`history-title-${item.id}`">搜索名称</label>
                  <input
                    :id="`history-title-${item.id}`"
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
                      保存
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
                  <div class="history-title-row">
                    <h3>{{ getTitle(item) }}</h3>
                    <span>{{ modeLabels[item.mode] }}</span>
                  </div>
                  <p>
                    {{
                      item.sources
                        .map((source) => sourceLabels[source])
                        .join(" · ")
                    }}
                  </p>
                  <div class="history-meta">
                    {{ formatTime(item.createdAt) }} ·
                    {{ item.resultCount }} 条结果
                  </div>
                </template>
              </div>

              <div v-if="editingId !== item.id" class="history-actions">
                <button
                  class="primary-button compact"
                  type="button"
                  @click="repeatSearch(item)"
                >
                  <RotateCcw :size="15" aria-hidden="true" />
                  再次搜索
                </button>
                <button
                  class="icon-action"
                  :class="{ active: isFavorite(item) }"
                  type="button"
                  :aria-label="
                    isFavorite(item)
                      ? `取消收藏${getTitle(item)}`
                      : `收藏${getTitle(item)}`
                  "
                  :aria-pressed="isFavorite(item)"
                  @click="toggleFavorite(item)"
                >
                  <Star
                    :size="17"
                    :fill="isFavorite(item) ? 'currentColor' : 'none'"
                    aria-hidden="true"
                  />
                </button>
                <button
                  class="icon-action"
                  type="button"
                  :aria-label="`重命名${getTitle(item)}`"
                  @click="startRename(item)"
                >
                  <Pencil :size="17" aria-hidden="true" />
                </button>
                <button
                  class="icon-action danger"
                  type="button"
                  :aria-label="`删除${getTitle(item)}`"
                  @click="requestDelete(item.id)"
                >
                  <Trash2 :size="17" aria-hidden="true" />
                </button>
              </div>
            </article>
          </div>
        </section>
      </div>

      <InlineState
        v-else
        kind="empty"
        title="没有符合条件的搜索记录"
        description="请清空关键词、选择全部搜索模式或关闭只看收藏。"
      />

      <template #footer>
        <span>
          共 {{ filteredHistory.length }} 条{{
            isRealApiMode ? "真实记录" : "本地记录"
          }}
        </span>
        <span>
          {{
            isRealApiMode
              ? "收藏与重命名暂未接入真实持久化"
              : "刷新页面后编辑状态将恢复"
          }}
        </span>
      </template>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.search-history-page,
.history-groups,
.history-group,
.history-list {
  display: grid;
  gap: var(--space-5);
}

.history-filter-bar,
.history-search-field,
.favorite-filter,
.inline-actions,
.history-title-row,
.history-actions {
  display: flex;
  align-items: center;
}

.history-filter-bar {
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.history-search-field {
  min-height: 40px;
  flex: 1 1 320px;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: var(--color-surface);
}

.history-search-field input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
}

.history-filter-bar select {
  min-width: 190px;
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text);
  background: var(--color-surface);
}

.favorite-filter {
  min-height: 40px;
  gap: var(--space-2);
  color: var(--color-text-secondary);
}

.inline-actions,
.history-actions {
  gap: var(--space-2);
}

.history-group {
  gap: var(--space-3);
}

.history-group > h2 {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-semibold);
}

.history-list {
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.history-list article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: center;
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.history-list article:first-child {
  border-top: 0;
}

.history-copy {
  min-width: 0;
}

.history-copy > label {
  display: block;
  margin-bottom: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.title-editor {
  width: min(100%, 720px);
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-8);
}

.inline-actions {
  margin-top: var(--space-2);
}

.history-title-row {
  gap: var(--space-3);
}

.history-title-row h3 {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: var(--color-text);
  font-size: var(--font-size-15);
  font-weight: var(--font-weight-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-title-row span {
  flex: none;
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: var(--font-size-12);
}

.history-copy p {
  margin: var(--space-2) 0 var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}

.history-meta {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.icon-action {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: var(--color-surface);
}

.icon-action.active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.icon-action.danger {
  color: var(--color-danger-text);
}

@media (max-width: 767px) {
  .history-panel-action {
    grid-column: 1 / -1;
  }

  .history-filter-bar,
  .history-list article {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }

  .history-search-field,
  .history-filter-bar select,
  .favorite-filter,
  .history-actions {
    width: 100%;
  }

  .history-actions {
    flex-wrap: wrap;
  }

  .history-actions .primary-button {
    flex: 1;
  }

  .icon-action {
    width: 44px;
    height: 44px;
  }
}
</style>
