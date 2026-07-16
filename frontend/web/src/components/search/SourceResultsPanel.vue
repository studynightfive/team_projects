<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

import type { SearchResultItem, SearchSourceType } from "../../types/ai-search";
import {
  Bookmark,
  ExternalLink,
  LayoutList,
  ListFilter,
  Search,
  SlidersHorizontal,
  X,
} from "../icons";
import InlineState from "../InlineState.vue";
import SearchStatusBadge from "./SearchStatusBadge.vue";

const props = defineProps<{
  results: readonly SearchResultItem[];
  currentTime?: number;
}>();

const emit = defineEmits<{
  preview: [result: SearchResultItem, trigger: HTMLElement];
  favorite: [resultId: string];
}>();

type TimeFilter = "all" | "30" | "90";
type SortMode = "relevance" | "updated";

const keyword = ref("");
const typeFilter = ref<"all" | SearchSourceType>("all");
const sourceFilter = ref("all");
const departmentFilter = ref("all");
const timeFilter = ref<TimeFilter>("all");
const sortMode = ref<SortMode>("relevance");
const compact = ref(false);
const isFilterPanelOpen = ref(false);
const favoriteIds = ref<ReadonlySet<string>>(new Set());
const filterPanelRef = ref<HTMLElement>();
const filterToggleRef = ref<HTMLButtonElement>();
const filterCloseRef = ref<HTMLButtonElement>();
let mobileViewportQuery: MediaQueryList | undefined;

const sourceOptions = computed(() => [
  ...new Set(props.results.map((item) => item.sourceName)),
]);
const departmentOptions = computed(() => [
  ...new Set(props.results.map((item) => item.department)),
]);
const activeFilterCount = computed(
  () =>
    Number(typeFilter.value !== "all") +
    Number(sourceFilter.value !== "all") +
    Number(departmentFilter.value !== "all") +
    Number(timeFilter.value !== "all"),
);

const filteredResults = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase("zh-CN");
  const now = props.currentTime ?? Date.now();
  const maximumAge =
    timeFilter.value === "all"
      ? Number.POSITIVE_INFINITY
      : Number(timeFilter.value) * 24 * 60 * 60 * 1000;

  return props.results
    .filter((item) => {
      const haystack =
        `${item.title}${item.snippet}${item.matchedKeywords.join("")}`.toLocaleLowerCase(
          "zh-CN",
        );
      return (
        (normalizedKeyword.length === 0 ||
          haystack.includes(normalizedKeyword)) &&
        (typeFilter.value === "all" || item.sourceType === typeFilter.value) &&
        (sourceFilter.value === "all" ||
          item.sourceName === sourceFilter.value) &&
        (departmentFilter.value === "all" ||
          item.department === departmentFilter.value) &&
        now - new Date(item.updatedAt).getTime() <= maximumAge
      );
    })
    .sort((left, right) =>
      sortMode.value === "relevance"
        ? right.relevance - left.relevance
        : new Date(right.updatedAt).getTime() -
          new Date(left.updatedAt).getTime(),
    );
});

const sourceTypeLabel: Readonly<Record<SearchSourceType, string>> = {
  knowledge: "企业知识库",
  project: "项目文档",
  policy: "规章制度",
  meeting: "会议记录",
  business: "业务数据",
  personal: "个人文件",
  internet: "互联网信息",
};

const formatDate = (value: string): string =>
  new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));

const resetFilters = (): void => {
  keyword.value = "";
  typeFilter.value = "all";
  sourceFilter.value = "all";
  departmentFilter.value = "all";
  timeFilter.value = "all";
  sortMode.value = "relevance";
};

const isFavorite = (resultId: string): boolean =>
  favoriteIds.value.has(resultId);

const toggleFavorite = (resultId: string): void => {
  const nextFavoriteIds = new Set(favoriteIds.value);
  const willFavorite = !nextFavoriteIds.has(resultId);

  if (willFavorite) nextFavoriteIds.add(resultId);
  else nextFavoriteIds.delete(resultId);

  favoriteIds.value = nextFavoriteIds;
  if (willFavorite) emit("favorite", resultId);
};

const openFilterPanel = (): void => {
  isFilterPanelOpen.value = true;
};

const closeFilterPanel = async (restoreFocus = true): Promise<void> => {
  isFilterPanelOpen.value = false;
  if (!restoreFocus) return;

  await nextTick();
  filterToggleRef.value?.focus();
};

const getFilterPanelFocusableElements = (): HTMLElement[] => {
  if (filterPanelRef.value === undefined) return [];
  return Array.from(
    filterPanelRef.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
};

const handleFilterPanelKeydown = (event: KeyboardEvent): void => {
  if (!isFilterPanelOpen.value) return;

  if (event.key === "Escape") {
    event.preventDefault();
    void closeFilterPanel();
    return;
  }
  if (event.key !== "Tab") return;

  const focusable = getFilterPanelFocusableElements();
  const first = focusable.at(0);
  const last = focusable.at(-1);
  if (first === undefined || last === undefined) {
    event.preventDefault();
  } else if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
};

const handleMobileViewportChange = (
  viewport: MediaQueryListEvent | MediaQueryList,
): void => {
  if (!viewport.matches && isFilterPanelOpen.value) {
    void closeFilterPanel(false);
  }
};

watch(isFilterPanelOpen, async (open) => {
  document.body.classList.toggle("source-filter-drawer-open", open);
  if (!open) return;

  await nextTick();
  filterCloseRef.value?.focus();
});

onMounted(() => {
  if (typeof window.matchMedia !== "function") return;

  mobileViewportQuery = window.matchMedia("(max-width: 767px)");
  mobileViewportQuery.addEventListener?.("change", handleMobileViewportChange);
});

onBeforeUnmount(() => {
  document.body.classList.remove("source-filter-drawer-open");
  mobileViewportQuery?.removeEventListener?.(
    "change",
    handleMobileViewportChange,
  );
});
</script>

<template>
  <section class="source-results-panel" aria-labelledby="source-results-title">
    <header class="source-results-heading">
      <div>
        <span>可核验的原始依据</span>
        <h2 id="source-results-title">原始搜索结果</h2>
      </div>
      <div class="result-density" aria-label="结果显示密度">
        <button
          type="button"
          :class="{ active: !compact }"
          :aria-pressed="!compact"
          @click="compact = false"
        >
          <LayoutList :size="16" aria-hidden="true" />
          列表
        </button>
        <button
          type="button"
          :class="{ active: compact }"
          :aria-pressed="compact"
          @click="compact = true"
        >
          <ListFilter :size="16" aria-hidden="true" />
          紧凑
        </button>
      </div>
    </header>

    <div class="mobile-result-filter-bar">
      <label class="filter-search">
        <span class="visually-hidden">在结果中搜索</span>
        <Search :size="16" aria-hidden="true" />
        <input v-model="keyword" type="search" placeholder="在结果中搜索" />
      </label>
      <button
        ref="filterToggleRef"
        class="mobile-filter-toggle"
        type="button"
        aria-controls="source-results-filter-panel"
        :aria-expanded="isFilterPanelOpen"
        @click="openFilterPanel"
      >
        <SlidersHorizontal :size="16" aria-hidden="true" />
        筛选
        <span v-if="activeFilterCount > 0" class="mobile-filter-count">
          {{ activeFilterCount }}
        </span>
      </button>
    </div>

    <button
      v-if="isFilterPanelOpen"
      class="mobile-filter-backdrop"
      type="button"
      aria-label="关闭结果筛选面板"
      @click="closeFilterPanel()"
    />

    <div
      id="source-results-filter-panel"
      ref="filterPanelRef"
      class="result-filters"
      :class="{ 'mobile-open': isFilterPanelOpen }"
      aria-label="原始结果筛选器"
      :role="isFilterPanelOpen ? 'dialog' : undefined"
      :aria-modal="isFilterPanelOpen ? 'true' : undefined"
      @keydown="handleFilterPanelKeydown"
    >
      <header class="mobile-filter-heading">
        <div>
          <strong>高级筛选</strong>
          <span>
            {{ activeFilterCount > 0 ? `已启用 ${activeFilterCount} 项` : "尚未启用筛选" }}
          </span>
        </div>
        <button
          ref="filterCloseRef"
          type="button"
          aria-label="关闭结果筛选面板"
          @click="closeFilterPanel()"
        >
          <X :size="19" aria-hidden="true" />
        </button>
      </header>

      <label class="filter-search desktop-filter-search">
        <span class="visually-hidden">在结果中搜索</span>
        <Search :size="16" aria-hidden="true" />
        <input v-model="keyword" type="search" placeholder="在结果中搜索" />
      </label>
      <label class="advanced-filter-field">
        <span class="mobile-filter-label">内容类型</span>
        <span class="visually-hidden">内容类型</span>
        <select v-model="typeFilter" aria-label="按内容类型筛选">
          <option value="all">全部类型</option>
          <option
            v-for="(label, value) in sourceTypeLabel"
            :key="value"
            :value="value"
          >
            {{ label }}
          </option>
        </select>
      </label>
      <label class="advanced-filter-field">
        <span class="mobile-filter-label">数据源</span>
        <span class="visually-hidden">数据源</span>
        <select v-model="sourceFilter" aria-label="按数据源筛选">
          <option value="all">全部数据源</option>
          <option v-for="source in sourceOptions" :key="source" :value="source">
            {{ source }}
          </option>
        </select>
      </label>
      <label class="advanced-filter-field">
        <span class="mobile-filter-label">所属部门</span>
        <span class="visually-hidden">所属部门</span>
        <select v-model="departmentFilter" aria-label="按所属部门筛选">
          <option value="all">全部部门</option>
          <option
            v-for="department in departmentOptions"
            :key="department"
            :value="department"
          >
            {{ department }}
          </option>
        </select>
      </label>
      <label class="advanced-filter-field">
        <span class="mobile-filter-label">更新时间</span>
        <span class="visually-hidden">更新时间</span>
        <select v-model="timeFilter" aria-label="按更新时间筛选">
          <option value="all">不限时间</option>
          <option value="30">最近 30 天</option>
          <option value="90">最近 90 天</option>
        </select>
      </label>
      <label class="advanced-filter-field">
        <span class="mobile-filter-label">排序方式</span>
        <span class="visually-hidden">排序方式</span>
        <select v-model="sortMode" aria-label="选择排序方式">
          <option value="relevance">按相关度排序</option>
          <option value="updated">按更新时间排序</option>
        </select>
      </label>

      <footer class="mobile-filter-actions">
        <button
          class="secondary-button"
          type="button"
          @click="resetFilters"
        >
          重置筛选
        </button>
        <button
          class="primary-button"
          type="button"
          @click="closeFilterPanel()"
        >
          查看 {{ filteredResults.length }} 条结果
        </button>
      </footer>
    </div>

    <p class="result-count" aria-live="polite">
      共 {{ filteredResults.length }} 条模拟结果，内容按当前账号权限状态展示
    </p>

    <div
      v-if="filteredResults.length > 0"
      class="source-result-list"
      :class="{ compact }"
    >
      <article
        v-for="result in filteredResults"
        :key="result.id"
        class="source-result-item"
      >
        <div class="source-result-main">
          <div class="source-result-meta">
            <span>{{ sourceTypeLabel[result.sourceType] }}</span>
            <span>{{ result.fileType }}</span>
            <span>{{ result.sourceName }}</span>
            <span>{{ formatDate(result.updatedAt) }}</span>
          </div>
          <h3>{{ result.title }}</h3>
          <p>{{ result.snippet }}</p>
          <div class="matched-keywords" aria-label="命中关键词">
            <span
              v-for="matchedKeyword in result.matchedKeywords"
              :key="matchedKeyword"
            >
              {{ matchedKeyword }}
            </span>
          </div>
          <div class="source-result-details">
            <span>{{ result.spaceName }}</span>
            <span>{{ result.department }}</span>
            <span>负责人：{{ result.owner }}</span>
            <SearchStatusBadge :status="result.verifiedStatus" />
            <SearchStatusBadge :status="result.permissionStatus" />
          </div>
        </div>
        <div class="source-result-side">
          <strong>{{ result.relevance }}%</strong>
          <span>相关度</span>
          <button
            type="button"
            :class="{ 'favorite-active': isFavorite(result.id) }"
            :aria-pressed="isFavorite(result.id)"
            :aria-label="
              isFavorite(result.id)
                ? `取消收藏结果 ${result.title}`
                : `收藏结果 ${result.title}`
            "
            :title="isFavorite(result.id) ? '取消收藏结果' : '收藏结果'"
            @click="toggleFavorite(result.id)"
          >
            <Bookmark :size="16" aria-hidden="true" />
          </button>
          <button
            type="button"
            :aria-label="`预览原文 ${result.title}`"
            title="预览原文"
            @click="
              emit('preview', result, $event.currentTarget as HTMLElement)
            "
          >
            <ExternalLink :size="16" aria-hidden="true" />
          </button>
        </div>
      </article>
    </div>

    <InlineState
      v-else
      kind="empty"
      title="没有符合条件的结果"
      description="请减少筛选条件、缩短关键词或恢复全部数据源。"
    />

    <button
      v-if="filteredResults.length === 0"
      class="secondary-button reset-filters"
      type="button"
      @click="resetFilters"
    >
      重置筛选条件
    </button>
  </section>
</template>

<style scoped>
.source-results-panel {
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.source-results-heading,
.result-density,
.result-filters,
.filter-search,
.source-result-item,
.source-result-meta,
.source-result-details,
.source-result-side,
.matched-keywords {
  display: flex;
  align-items: center;
}

.source-results-heading,
.source-result-item {
  justify-content: space-between;
  gap: var(--space-4);
}

.source-results-heading > div:first-child > span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.source-results-heading h2 {
  margin: var(--space-1) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-20);
}

.result-density {
  gap: var(--space-1);
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.result-density button {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-2);
  border-radius: 6px;
  color: var(--color-text-muted);
  background: transparent;
  font-size: var(--font-size-12);
}

.result-density button.active {
  color: var(--color-primary);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.mobile-result-filter-bar,
.mobile-filter-backdrop,
.mobile-filter-heading,
.mobile-filter-actions,
.mobile-filter-label {
  display: none;
}

.result-filters {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) repeat(5, minmax(132px, 1fr));
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding: var(--space-3);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.result-filters label,
.result-filters select,
.result-filters input {
  width: 100%;
  min-width: 0;
}

.result-filters select,
.filter-search {
  min-height: 38px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  font-size: var(--font-size-12);
}

.result-filters select {
  padding: 0 var(--space-2);
}

.filter-search {
  gap: var(--space-2);
  padding: 0 var(--space-3);
}

.filter-search input {
  border: 0;
  outline: 0;
  background: transparent;
}

.filter-search input:focus-visible {
  box-shadow: none;
}

.result-count {
  margin: var(--space-4) 0 var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.source-result-list {
  display: grid;
}

.source-result-item {
  padding: var(--space-5) 0;
  border-top: 1px solid var(--color-border);
  align-items: flex-start;
}

.source-result-main {
  min-width: 0;
  flex: 1;
}

.source-result-meta,
.source-result-details,
.matched-keywords {
  flex-wrap: wrap;
  gap: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.source-result-meta span:not(:last-child)::after,
.source-result-details > span:not(:last-of-type)::after {
  margin-left: var(--space-2);
  color: var(--color-border-strong);
  content: "·";
}

.source-result-item h3 {
  margin: var(--space-2) 0;
  color: var(--color-text);
  font-size: var(--font-size-16);
}

.source-result-item p {
  margin-bottom: var(--space-3);
  color: var(--color-text-secondary);
  line-height: 1.65;
}

.matched-keywords {
  margin-bottom: var(--space-3);
}

.matched-keywords span {
  padding: 2px var(--space-2);
  border-radius: var(--radius-4);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.source-result-side {
  flex: 0 0 92px;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
  text-align: right;
}

.source-result-side strong {
  width: 100%;
  color: var(--color-primary);
  font-size: var(--font-size-18);
}

.source-result-side > span {
  width: 100%;
}

.source-result-side button {
  display: grid;
  width: 34px;
  height: 34px;
  margin-top: var(--space-2);
  padding: 0;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface);
}

.source-result-side button.favorite-active {
  border-color: var(--blue-300);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.source-result-list.compact .source-result-item {
  padding: var(--space-3) 0;
}

.source-result-list.compact .source-result-item p,
.source-result-list.compact .matched-keywords {
  display: none;
}

.reset-filters {
  margin: var(--space-4) auto 0;
}

@media (max-width: 1180px) {
  .result-filters {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .source-results-panel {
    padding: var(--space-4);
  }

  .source-results-heading,
  .source-result-item {
    align-items: stretch;
    flex-direction: column;
  }

  .mobile-result-filter-bar {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--space-2);
    margin-top: var(--space-4);
  }

  .mobile-filter-toggle {
    display: inline-flex;
    min-height: 44px;
    align-items: center;
    justify-content: center;
    gap: var(--space-1);
    padding: 0 var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-8);
    color: var(--color-text-secondary);
    background: var(--color-surface);
    white-space: nowrap;
  }

  .mobile-filter-count {
    display: inline-grid;
    min-width: 20px;
    height: 20px;
    padding: 0 var(--space-1);
    place-items: center;
    border-radius: var(--radius-pill);
    color: var(--white);
    background: var(--color-primary);
    font-size: var(--font-size-12);
  }

  .mobile-filter-backdrop {
    position: fixed;
    inset: 0;
    z-index: 89;
    display: block;
    width: 100%;
    height: 100%;
    padding: 0;
    background: var(--color-overlay);
  }

  .result-filters {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 90;
    display: none;
    max-height: min(80vh, 640px);
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-3);
    margin: 0;
    padding: var(--space-4);
    overflow-y: auto;
    border: 1px solid var(--color-border);
    border-bottom: 0;
    border-radius: var(--radius-16) var(--radius-16) 0 0;
    background: var(--color-surface);
    box-shadow: var(--shadow-lg);
  }

  .result-filters.mobile-open {
    display: grid;
  }

  .result-filters .desktop-filter-search {
    display: none;
  }

  .mobile-filter-heading {
    position: sticky;
    top: calc(-1 * var(--space-4));
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    margin: calc(-1 * var(--space-4)) calc(-1 * var(--space-4)) 0;
    padding: var(--space-4);
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface);
  }

  .mobile-filter-heading > div {
    display: grid;
    gap: var(--space-1);
  }

  .mobile-filter-heading strong {
    color: var(--color-text);
    font-size: var(--font-size-18);
  }

  .mobile-filter-heading span {
    color: var(--color-text-muted);
    font-size: var(--font-size-12);
  }

  .mobile-filter-heading button {
    display: grid;
    flex: 0 0 44px;
    width: 44px;
    height: 44px;
    padding: 0;
    place-items: center;
    border-radius: var(--radius-8);
    color: var(--color-text-secondary);
    background: var(--color-surface-subtle);
  }

  .advanced-filter-field,
  .mobile-filter-label {
    display: grid;
  }

  .advanced-filter-field {
    gap: var(--space-2);
  }

  .mobile-filter-label {
    color: var(--color-text-secondary);
    font-size: var(--font-size-13);
    font-weight: var(--font-weight-medium);
  }

  .mobile-filter-actions {
    position: sticky;
    bottom: calc(-1 * var(--space-4));
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-2);
    margin: var(--space-1) calc(-1 * var(--space-4))
      calc(-1 * var(--space-4));
    padding: var(--space-3) var(--space-4) var(--space-4);
    border-top: 1px solid var(--color-border);
    background: var(--color-surface);
  }

  .result-filters select,
  .mobile-result-filter-bar .filter-search,
  .filter-search,
  .result-density button {
    min-height: 44px;
  }

  .source-result-side {
    flex-basis: auto;
    justify-content: flex-start;
    text-align: left;
  }

  .source-result-side strong,
  .source-result-side > span {
    width: auto;
  }
}
</style>
