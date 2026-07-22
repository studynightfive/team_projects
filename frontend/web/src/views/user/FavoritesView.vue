<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { useListPagination } from "../../composables/useListPagination";
import { ExternalLink, Plus, Search, Trash2, X } from "../../components/icons";
import { isRealApiMode } from "../../config/runtime";
import { aiSearchMockData } from "../../mocks/ai-search";
import {
  deleteFavorite,
  listFavorites,
  updateFavorite,
} from "../../services/favorites";
import type { Favorite, FavoriteType } from "../../types/ai-search";

const typeLabels = {
  answer: "AI 答案",
  document: "文档",
  space: "知识空间",
  query: "搜索问题",
} satisfies Record<FavoriteType, string>;

const router = useRouter();
const { message, modal } = AntApp.useApp();
const keyword = ref("");
const typeFilter = ref<"all" | FavoriteType>("all");
const tagFilter = ref("all");
const hiddenIds = ref<ReadonlySet<string>>(new Set());
const noteDrafts = ref<Record<string, string>>(
  Object.fromEntries(
    aiSearchMockData.favorites.map((item) => [item.id, item.note]),
  ),
);
const tagsById = ref<Record<string, string[]>>(
  Object.fromEntries(
    aiSearchMockData.favorites.map((item) => [item.id, [...item.tags]]),
  ),
);
const tagDrafts = ref<Record<string, string>>({});
const realFavorites = ref<readonly Favorite[]>([]);
const loadState = ref<"idle" | "loading" | "success" | "error">("idle");
const loadError = ref("");
let loadController: AbortController | undefined;

const favorites = computed<readonly Favorite[]>(() =>
  isRealApiMode ? realFavorites.value : aiSearchMockData.favorites,
);

const getTags = (item: Favorite): readonly string[] =>
  tagsById.value[item.id] ?? item.tags;

const allTags = computed(() =>
  Array.from(
    new Set(favorites.value.flatMap((item) => getTags(item))),
  ).sort((left, right) => left.localeCompare(right, "zh-CN")),
);

const filteredFavorites = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase("zh-CN");

  return favorites.value.filter((item) => {
    const searchableText = `${item.title}${item.summary}${
      noteDrafts.value[item.id] ?? item.note
    }${getTags(item).join("")}`.toLocaleLowerCase("zh-CN");

    return (
      !hiddenIds.value.has(item.id) &&
      (typeFilter.value === "all" || item.type === typeFilter.value) &&
      (tagFilter.value === "all" || getTags(item).includes(tagFilter.value)) &&
      (normalizedKeyword.length === 0 ||
        searchableText.includes(normalizedKeyword))
    );
  });
});
const {
  page: favoritesPage,
  pageSize: favoritesPageSize,
  pagedItems: pagedFavorites,
  setPage: setFavoritesPage,
} = useListPagination(filteredFavorites);

const formatSavedAt = (value: string): string =>
  new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

const loadRealFavorites = async (): Promise<void> => {
  if (!isRealApiMode) return;

  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loadState.value = "loading";
  loadError.value = "";

  try {
    realFavorites.value = await listFavorites(controller.signal);
    noteDrafts.value = Object.fromEntries(
      realFavorites.value.map((item) => [item.id, item.note]),
    );
    tagsById.value = Object.fromEntries(
      realFavorites.value.map((item) => [item.id, [...item.tags]]),
    );
    loadState.value = "success";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = toPublicApiError(error).message;
    loadState.value = "error";
  }
};

const replaceFavorite = (nextFavorite: Favorite): void => {
  realFavorites.value = realFavorites.value.map((item) =>
    item.id === nextFavorite.id ? nextFavorite : item,
  );
};

const saveNote = async (item: Favorite): Promise<void> => {
  noteDrafts.value = {
    ...noteDrafts.value,
    [item.id]: (noteDrafts.value[item.id] ?? "").trim(),
  };
  if (isRealApiMode) {
    try {
      replaceFavorite(
        await updateFavorite(item.id, { note: noteDrafts.value[item.id] ?? "" }),
      );
      void message.success("备注已保存到服务器");
    } catch (error: unknown) {
      void message.error(toPublicApiError(error).message);
    }
    return;
  }
  void message.success("备注已在当前页面保存，刷新后恢复模拟数据");
};

const addTag = async (item: Favorite): Promise<void> => {
  const nextTag = (tagDrafts.value[item.id] ?? "").trim();
  if (nextTag.length === 0) return;

  const currentTags = getTags(item);
  if (currentTags.includes(nextTag)) {
    void message.warning("该标签已存在");
    return;
  }

  const nextTags = [...currentTags, nextTag];
  tagsById.value = { ...tagsById.value, [item.id]: nextTags };
  tagDrafts.value = { ...tagDrafts.value, [item.id]: "" };
  if (isRealApiMode) {
    try {
      replaceFavorite(await updateFavorite(item.id, { tags: nextTags }));
      void message.success("标签已保存到服务器");
    } catch (error: unknown) {
      void message.error(toPublicApiError(error).message);
    }
    return;
  }
  void message.success("标签已添加到当前页面");
};

const removeTag = async (item: Favorite, tag: string): Promise<void> => {
  const nextTags = getTags(item).filter((itemTag) => itemTag !== tag);
  tagsById.value = {
    ...tagsById.value,
    [item.id]: nextTags,
  };
  if (tagFilter.value === tag) tagFilter.value = "all";
  if (isRealApiMode) {
    try {
      replaceFavorite(await updateFavorite(item.id, { tags: nextTags }));
    } catch (error: unknown) {
      void message.error(toPublicApiError(error).message);
    }
  }
};

const requestDelete = (favoriteId: string): void => {
  modal.confirm({
    title: "确认删除这条收藏？",
    content: isRealApiMode
      ? "删除后这条收藏会从服务器移除。"
      : "本操作只影响当前页面，刷新后会恢复固定模拟数据。",
    okText: "确认删除",
    okType: "danger",
    cancelText: "取消",
    centered: true,
    autoFocusButton: "cancel",
    onOk: async () => {
      if (isRealApiMode) {
        try {
          await deleteFavorite(favoriteId);
          realFavorites.value = realFavorites.value.filter(
            (item) => item.id !== favoriteId,
          );
          void message.success("收藏已删除");
        } catch (error: unknown) {
          void message.error(toPublicApiError(error).message);
        }
        return;
      }

      hiddenIds.value = new Set([...hiddenIds.value, favoriteId]);
      void message.success("收藏已从当前页面移除，刷新后恢复模拟数据");
    },
  });
};

const openFavorite = (item: Favorite): void => {
  if (item.type === "space") {
    void router.push({ path: "/spaces", query: { space: item.sourceId } });
    return;
  }

  if (item.type === "document") {
    void message.info(
      `“${item.title}”的文档预览仅作本地交互说明，未请求真实文件`,
    );
    return;
  }

  void router.push({
    path: "/search",
    state: {
      initialSearch: {
        q: item.title,
        mode: "smart",
        sources: "knowledge",
      },
    },
  });
};

onMounted(() => {
  void loadRealFavorites();
});

onBeforeUnmount(() => {
  loadController?.abort();
});
</script>

<template>
  <div class="business-page favorites-page">
    <PageHeader
      eyebrow="个人知识资产"
      title="收藏内容"
      :description="
        isRealApiMode
          ? '集中管理已保存到服务器的答案、文档、知识空间和常用问题。'
          : '集中管理答案、文档、知识空间和常用问题；备注与标签仅保留在当前页面。'
      "
    >
      <template #actions>
        <span class="local-preview-badge">
          {{ isRealApiMode ? "真实收藏" : "本地模拟收藏" }}
        </span>
      </template>
    </PageHeader>

    <ResourcePanel
      title="全部收藏"
      :description="
        isRealApiMode
          ? '备注、标签和删除会写入后端收藏接口。'
          : '按类型和标签定位内容，打开操作不会访问未接入的业务服务。'
      "
    >
      <div class="favorite-filter-bar">
        <label class="favorite-search-field">
          <span class="visually-hidden">搜索收藏内容</span>
          <Search :size="17" aria-hidden="true" />
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索标题、摘要、标签或备注"
            autocomplete="off"
          />
        </label>
        <select v-model="typeFilter" aria-label="按收藏类型筛选">
          <option value="all">全部类型</option>
          <option value="answer">AI 答案</option>
          <option value="document">文档</option>
          <option value="space">知识空间</option>
          <option value="query">搜索问题</option>
        </select>
        <select v-model="tagFilter" aria-label="按标签筛选">
          <option value="all">全部标签</option>
          <option v-for="tag in allTags" :key="tag" :value="tag">
            {{ tag }}
          </option>
        </select>
      </div>

      <InlineState
        v-if="isRealApiMode && loadState === 'loading'"
        kind="loading"
        title="正在加载真实收藏"
        description="系统正在读取当前账号已保存的收藏。"
      />
      <InlineState
        v-else-if="isRealApiMode && loadState === 'error'"
        kind="error"
        title="真实收藏加载失败"
        :description="loadError"
      />

      <div v-else-if="filteredFavorites.length > 0" class="favorite-grid">
        <article v-for="item in pagedFavorites" :key="item.id">
          <header>
            <span class="favorite-type">{{ typeLabels[item.type] }}</span>
            <button
              class="icon-action danger"
              type="button"
              :aria-label="`删除收藏${item.title}`"
              @click="requestDelete(item.id)"
            >
              <Trash2 :size="17" aria-hidden="true" />
            </button>
          </header>

          <div class="favorite-copy">
            <h2>{{ item.title }}</h2>
            <p>{{ item.summary }}</p>
            <small>收藏于 {{ formatSavedAt(item.savedAt) }}</small>
          </div>

          <div class="tag-editor">
            <span class="field-label">标签</span>
            <div class="tag-list">
              <span
                v-for="tag in getTags(item)"
                :key="tag"
                class="favorite-tag"
              >
                {{ tag }}
                <button
                  type="button"
                  :aria-label="`移除标签${tag}`"
                  @click="removeTag(item, tag)"
                >
                  <X :size="12" aria-hidden="true" />
                </button>
              </span>
            </div>
            <div class="tag-input-row">
              <input
                v-model="tagDrafts[item.id]"
                type="text"
                maxlength="12"
                placeholder="添加标签"
                :aria-label="`为${item.title}添加标签`"
                @keyup.enter="addTag(item)"
              />
              <button
                type="button"
                :aria-label="`确认添加${item.title}的标签`"
                @click="addTag(item)"
              >
                <Plus :size="16" aria-hidden="true" />
              </button>
            </div>
          </div>

          <label class="note-editor">
            <span class="field-label">个人备注</span>
            <textarea
              v-model="noteDrafts[item.id]"
              rows="2"
              maxlength="160"
              placeholder="添加使用提醒或上下文"
            />
          </label>

          <footer>
            <button
              class="secondary-button compact"
              type="button"
              @click="saveNote(item)"
            >
              保存备注
            </button>
            <button
              class="primary-button compact"
              type="button"
              @click="openFavorite(item)"
            >
              <ExternalLink :size="15" aria-hidden="true" />
              {{ item.type === "document" ? "预览说明" : "打开内容" }}
            </button>
          </footer>
        </article>
      </div>
      <ListPagination
        v-if="filteredFavorites.length > 0"
        :page="favoritesPage"
        :page-size="favoritesPageSize"
        :total="filteredFavorites.length"
        @change="setFavoritesPage"
      />

      <InlineState
        v-else
        kind="empty"
        title="没有符合条件的收藏"
        description="请清空关键词，或选择全部类型和全部标签。"
      />

      <template #footer>
        <span>
          共 {{ filteredFavorites.length }} 条{{
            isRealApiMode ? "真实收藏" : "本地收藏"
          }}
        </span>
        <span>
          {{
            isRealApiMode
              ? "备注和标签会写入服务器"
              : "备注和标签不会写入服务器"
          }}
        </span>
      </template>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.favorites-page {
  gap: var(--space-5);
}

.favorite-filter-bar,
.favorite-search-field,
.favorite-grid article > header,
.favorite-grid article > footer,
.tag-list,
.favorite-tag,
.tag-input-row {
  display: flex;
  align-items: center;
}

.favorite-filter-bar {
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.favorite-search-field {
  min-height: 40px;
  flex: 1 1 340px;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: var(--color-surface);
}

.favorite-search-field:focus-within {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-focus);
}

.favorite-search-field input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
}

.favorite-search-field input:focus-visible {
  box-shadow: none;
}

.favorite-filter-bar select {
  min-width: 160px;
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text);
  background: var(--color-surface);
}

.favorite-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.favorite-grid article {
  display: grid;
  min-width: 0;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.favorite-grid article > header,
.favorite-grid article > footer {
  justify-content: space-between;
  gap: var(--space-3);
}

.favorite-type {
  padding: 3px var(--space-2);
  border-radius: var(--radius-pill);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
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

.icon-action.danger {
  color: var(--color-danger-text);
}

.favorite-copy h2 {
  margin: 0 0 var(--space-2);
  color: var(--color-text);
  font-size: var(--font-size-16);
  line-height: 1.5;
}

.favorite-copy p {
  margin: 0 0 var(--space-2);
  color: var(--color-text-secondary);
  line-height: 1.65;
}

.favorite-copy small,
.field-label {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.tag-editor,
.note-editor {
  display: grid;
  gap: var(--space-2);
}

.tag-list {
  flex-wrap: wrap;
  gap: var(--space-2);
}

.favorite-tag {
  gap: 3px;
  padding: 3px 4px 3px var(--space-2);
  border-radius: var(--radius-pill);
  color: var(--color-text-secondary);
  background: var(--color-surface-subtle);
  font-size: var(--font-size-12);
}

.favorite-tag button,
.tag-input-row button {
  display: inline-grid;
  width: 24px;
  height: 24px;
  padding: 0;
  place-items: center;
  color: var(--color-text-muted);
  background: transparent;
}

.tag-input-row {
  gap: var(--space-2);
}

.tag-input-row input,
.note-editor textarea {
  width: 100%;
  min-width: 0;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text);
  background: var(--color-surface);
}

.tag-input-row input {
  min-height: 36px;
  padding: 0 var(--space-3);
}

.tag-input-row button {
  width: 36px;
  height: 36px;
  flex: none;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
}

.note-editor textarea {
  min-height: 68px;
  padding: var(--space-2) var(--space-3);
  resize: vertical;
  line-height: 1.5;
}

@media (max-width: 1180px) {
  .favorite-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .favorite-filter-bar,
  .favorite-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }

  .favorite-search-field,
  .favorite-filter-bar select {
    width: 100%;
  }

  .favorite-grid article > footer > * {
    flex: 1;
    min-height: 44px;
  }

  .icon-action {
    width: 44px;
    height: 44px;
  }
}
</style>
