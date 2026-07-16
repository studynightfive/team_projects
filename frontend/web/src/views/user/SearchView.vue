<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import AiAnswerPanel from "../../components/search/AiAnswerPanel.vue";
import AiSearchBox from "../../components/search/AiSearchBox.vue";
import DocumentPreviewDrawer from "../../components/search/DocumentPreviewDrawer.vue";
import SearchContextPanel from "../../components/search/SearchContextPanel.vue";
import SearchStatusBadge from "../../components/search/SearchStatusBadge.vue";
import SourceResultsPanel from "../../components/search/SourceResultsPanel.vue";
import {
  Bookmark,
  Copy,
  Download,
  PanelRightOpen,
  RefreshCw,
  SlidersHorizontal,
} from "../../components/icons";
import { aiSearchMockData } from "../../mocks/ai-search";
import { runAiSearch } from "../../services/ai-search";
import type {
  AiSearchResponse,
  CitationSource,
  SearchMode,
  SearchRequest,
  SearchResultItem,
  SearchSourceType,
  SearchStatus,
} from "../../types/ai-search";

const { message } = AntApp.useApp();
const route = useRoute();
const router = useRouter();

const allowedModes: readonly SearchMode[] = [
  "smart",
  "precise",
  "research",
  "document",
];
const allowedSources: readonly SearchSourceType[] = [
  "knowledge",
  "project",
  "policy",
  "meeting",
  "business",
  "personal",
  "internet",
];

const query = ref<string>(aiSearchMockData.answer.query);
const mode = ref<SearchMode>("smart");
const sources = ref<SearchSourceType[]>([...allowedSources]);
const modelId = ref("enterprise-general");
const status = ref<SearchStatus>("idle");
const response = ref<AiSearchResponse>();
const errorMessage = ref("");
const activeTab = ref<"answer" | "results">("answer");
const isContextOpen = ref(false);
const previewDocument = ref<CitationSource | SearchResultItem>();
const isPreviewOpen = ref(false);
const previewTrigger = ref<HTMLElement>();
const answerFavorite = ref(false);
const attachmentNames = ref<string[]>([]);
const contextTrigger = ref<HTMLElement>();
const answerTabRef = ref<HTMLButtonElement>();
const resultsTabRef = ref<HTMLButtonElement>();

let searchController: AbortController | undefined;
let desktopContextQuery: MediaQueryList | undefined;

const modeLabel = computed(
  () =>
    aiSearchMockData.modeOptions.find((option) => option.value === mode.value)
      ?.label ?? "智能搜索",
);
const scopeLabel = computed(() => {
  const exactScope = aiSearchMockData.scopeOptions.find(
    (option) =>
      option.sources.length === sources.value.length &&
      option.sources.every((source) => sources.value.includes(source)),
  );
  return exactScope?.label ?? `已选 ${sources.value.length} 类范围`;
});
const modelLabel = computed(
  () =>
    aiSearchMockData.modelOptions.find(
      (option) => option.value === modelId.value,
    )?.label ?? "企业通用模型",
);

const parseMode = (value: unknown): SearchMode =>
  typeof value === "string" && allowedModes.includes(value as SearchMode)
    ? (value as SearchMode)
    : "smart";

const parseSources = (value: unknown): SearchSourceType[] => {
  if (typeof value !== "string") return [...allowedSources];
  const parsed = value
    .split(",")
    .filter((source): source is SearchSourceType =>
      allowedSources.includes(source as SearchSourceType),
    );
  return parsed.length > 0 ? [...new Set(parsed)] : [...allowedSources];
};

const readAttachmentNames = (): string[] => {
  const state: unknown = router.options.history.state;
  if (typeof state !== "object" || state === null) return [];

  const names = (state as Record<string, unknown>).attachmentNames;
  if (!Array.isArray(names)) return [];
  return names
    .filter((name): name is string => typeof name === "string")
    .slice(0, 5);
};

const syncFromRoute = (): void => {
  query.value =
    typeof route.query.q === "string" && route.query.q.trim().length > 0
      ? route.query.q.trim()
      : aiSearchMockData.answer.query;
  mode.value = parseMode(route.query.mode);
  sources.value = parseSources(route.query.sources);
  modelId.value =
    typeof route.query.model === "string" &&
    aiSearchMockData.modelOptions.some(
      (option) => option.value === route.query.model,
    )
      ? route.query.model
      : "enterprise-general";
  attachmentNames.value = readAttachmentNames();
};

const executeSearch = async (): Promise<void> => {
  searchController?.abort();
  searchController = new AbortController();
  status.value = "searching";
  errorMessage.value = "";
  activeTab.value = "answer";
  answerFavorite.value = false;

  try {
    const nextResponse = await runAiSearch(
      {
        query: query.value,
        mode: mode.value,
        sources: sources.value,
        modelId: modelId.value,
        attachmentIds: attachmentNames.value,
      },
      searchController.signal,
    );
    response.value = nextResponse;
    status.value = nextResponse.status;
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    errorMessage.value =
      error instanceof Error
        ? error.message
        : "搜索暂时无法完成，请保留问题后重新尝试。";
    status.value = "error";
  }
};

const submitSearch = (request: SearchRequest): void => {
  attachmentNames.value = [...(request.attachmentIds ?? [])];
  const nextQuery = {
    q: request.query,
    mode: request.mode,
    sources: request.sources.join(","),
    model: request.modelId,
  };
  const unchanged =
    route.query.q === nextQuery.q &&
    route.query.mode === nextQuery.mode &&
    route.query.sources === nextQuery.sources &&
    route.query.model === nextQuery.model;

  if (unchanged) {
    void executeSearch();
  } else {
    void router.push({
      path: "/search",
      query: nextQuery,
      state: { attachmentNames: attachmentNames.value },
    });
  }
};

const openPreview = (
  document: CitationSource | SearchResultItem,
  trigger: HTMLElement,
): void => {
  previewDocument.value = document;
  previewTrigger.value = trigger;
  isPreviewOpen.value = true;
};

const copyAnswer = async (): Promise<void> => {
  if (response.value === undefined) return;
  try {
    await navigator.clipboard.writeText(response.value.answer.markdown);
    void message.success("答案已复制");
  } catch {
    void message.warning("浏览器未允许复制，请手动选择答案内容");
  }
};

const exportAnswer = (): void => {
  if (response.value === undefined) return;
  const blob = new Blob([response.value.answer.markdown], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "AI搜索结果-模拟数据.md";
  anchor.click();
  URL.revokeObjectURL(url);
  void message.info("已导出本地模拟答案");
};

const runRelatedSearch = (question: string): void => {
  query.value = question;
  submitSearch({
    query: question,
    mode: mode.value,
    sources: sources.value,
    modelId: modelId.value,
  });
};

const showFeedback = (value: string): void => {
  void message.success(`已记录“${value}”反馈，本地刷新后将清除`);
};

const toggleAnswerFavorite = (): void => {
  answerFavorite.value = !answerFavorite.value;
  void message.success(
    answerFavorite.value ? "答案已加入本地收藏" : "已取消本地收藏",
  );
};

const showLocalNotice = (notice: string): void => {
  void message.info(notice);
};

const openContext = (trigger: HTMLElement): void => {
  contextTrigger.value = trigger;
  isContextOpen.value = true;
};

const selectResultTab = (
  tab: "answer" | "results",
  focus = false,
): void => {
  activeTab.value = tab;
  if (focus) {
    const target = tab === "answer" ? answerTabRef.value : resultsTabRef.value;
    target?.focus();
  }
};

const handleResultTabKeydown = (event: KeyboardEvent): void => {
  if (event.key === "ArrowLeft" || event.key === "Home") {
    event.preventDefault();
    selectResultTab("answer", true);
  } else if (event.key === "ArrowRight" || event.key === "End") {
    event.preventDefault();
    selectResultTab("results", true);
  }
};

const syncDesktopContext = (
  event: MediaQueryListEvent | MediaQueryList,
): void => {
  isContextOpen.value = event.matches;
};

watch(
  () => route.fullPath,
  () => {
    syncFromRoute();
    void executeSearch();
  },
  { immediate: true },
);

onMounted(() => {
  if (typeof window.matchMedia !== "function") return;
  desktopContextQuery = window.matchMedia("(min-width: 1440px)");
  syncDesktopContext(desktopContextQuery);
  desktopContextQuery.addEventListener("change", syncDesktopContext);
});

onBeforeUnmount(() => {
  searchController?.abort();
  desktopContextQuery?.removeEventListener("change", syncDesktopContext);
});
</script>

<template>
  <div class="business-page ai-search-results-page">
    <header class="search-result-header">
      <div class="search-result-title">
        <span>企业 AI 搜索工作台</span>
        <h1>AI 搜索结果</h1>
        <p>{{ query }}</p>
      </div>
      <div class="search-result-actions">
        <span class="mock-result-badge">模拟数据</span>
        <button
          class="secondary-button compact"
          type="button"
          :disabled="status === 'searching'"
          @click="executeSearch"
        >
          <RefreshCw :size="16" aria-hidden="true" />
          重新生成
        </button>
        <button
          class="secondary-button compact"
          type="button"
          :disabled="response === undefined"
          @click="copyAnswer"
        >
          <Copy :size="16" aria-hidden="true" />
          复制答案
        </button>
        <button
          class="secondary-button compact"
          type="button"
          :disabled="response === undefined"
          @click="exportAnswer"
        >
          <Download :size="16" aria-hidden="true" />
          导出结果
        </button>
        <button
          class="secondary-button compact"
          type="button"
          :aria-pressed="answerFavorite"
          :disabled="response === undefined"
          @click="toggleAnswerFavorite"
        >
          <Bookmark :size="16" aria-hidden="true" />
          {{ answerFavorite ? "已收藏" : "收藏结果" }}
        </button>
      </div>
    </header>

    <div class="search-query-meta" aria-label="查询摘要">
      <SearchStatusBadge :status="status" />
      <span>{{ modeLabel }}</span>
      <span>{{ scopeLabel }}</span>
      <span>{{ response?.sourceCount ?? 0 }} 个数据源</span>
      <span>{{ response?.elapsedLabel ?? "等待检索" }}</span>
      <button
        v-if="!isContextOpen"
        type="button"
        @click="openContext($event.currentTarget as HTMLElement)"
      >
        <PanelRightOpen :size="16" aria-hidden="true" />
        搜索上下文
      </button>
    </div>

    <AiSearchBox
      v-model:query="query"
      v-model:mode="mode"
      v-model:sources="sources"
      v-model:model-id="modelId"
      compact
      :busy="status === 'searching'"
      :mode-options="aiSearchMockData.modeOptions"
      :scope-options="aiSearchMockData.scopeOptions"
      :model-options="aiSearchMockData.modelOptions"
      @attachments-change="attachmentNames = $event"
      @submit="submitSearch"
      @notice="showLocalNotice"
    />

    <div
      class="search-result-layout"
      :class="{ 'context-open': isContextOpen }"
    >
      <main class="search-result-main" aria-live="polite">
        <div v-if="status === 'searching'" class="search-progress-state">
          <InlineState
            kind="loading"
            title="正在检索企业知识"
            description="正在整理匹配内容、验证来源并生成结构化答案。"
          />
          <div class="search-skeleton" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </div>

        <div v-else-if="status === 'error'" class="search-error-state">
          <InlineState
            kind="error"
            title="本次搜索未完成"
            :description="errorMessage"
          />
          <button class="primary-button" type="button" @click="executeSearch">
            重新搜索
          </button>
        </div>

        <template v-else-if="response !== undefined">
          <div
            v-if="response.status === 'partial'"
            class="partial-result-notice"
            role="status"
          >
            <SlidersHorizontal :size="18" aria-hidden="true" />
            <span>部分所选范围暂无可用来源，当前答案仅依据已返回内容生成。</span>
          </div>

          <div class="result-tabs" role="tablist" aria-label="搜索结果视图">
            <button
              id="answer-tab"
              ref="answerTabRef"
              type="button"
              role="tab"
              :aria-selected="activeTab === 'answer'"
              :tabindex="activeTab === 'answer' ? 0 : -1"
              aria-controls="answer-panel"
              @click="selectResultTab('answer')"
              @keydown="handleResultTabKeydown"
            >
              AI 答案
            </button>
            <button
              id="results-tab"
              ref="resultsTabRef"
              type="button"
              role="tab"
              :aria-selected="activeTab === 'results'"
              :tabindex="activeTab === 'results' ? 0 : -1"
              aria-controls="results-panel"
              @click="selectResultTab('results')"
              @keydown="handleResultTabKeydown"
            >
              原始结果
              <span>{{ response.results.length }}</span>
            </button>
          </div>

          <div
            v-if="activeTab === 'answer'"
            id="answer-panel"
            role="tabpanel"
            aria-labelledby="answer-tab"
          >
            <AiAnswerPanel
              :answer="response.answer"
              :favorite="answerFavorite"
              @preview="openPreview"
              @related="runRelatedSearch"
              @feedback="showFeedback"
              @toggle-favorite="toggleAnswerFavorite"
            />
          </div>

          <div
            v-else
            id="results-panel"
            role="tabpanel"
            aria-labelledby="results-tab"
          >
            <SourceResultsPanel
              :results="response.results"
              @preview="openPreview"
              @favorite="showLocalNotice('文档已加入本地收藏')"
            />
          </div>
        </template>
      </main>

      <SearchContextPanel
        :open="isContextOpen"
        :query="query"
        :selected-sources="sources"
        :source-options="aiSearchMockData.scopeOptions"
        :model-label="modelLabel"
        :citations="response?.answer.citations ?? []"
        :data-sources="aiSearchMockData.dataSources"
        :attachment-names="attachmentNames"
        :return-focus-to="contextTrigger"
        @close="isContextOpen = false"
        @preview="openPreview"
      />
    </div>

    <DocumentPreviewDrawer
      v-model:open="isPreviewOpen"
      :document="previewDocument"
      :return-focus-to="previewTrigger"
      @favorite="showLocalNotice('文档已加入本地收藏')"
      @notice="showLocalNotice"
    />
  </div>
</template>

<style scoped>
.ai-search-results-page {
  gap: var(--space-5);
}

.search-result-header,
.search-result-actions,
.search-query-meta,
.search-query-meta button,
.partial-result-notice,
.result-tabs {
  display: flex;
  align-items: center;
}

.search-result-header {
  justify-content: space-between;
  gap: var(--space-5);
}

.search-result-title {
  min-width: 0;
}

.search-result-title > span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.search-result-title h1 {
  margin: var(--space-1) 0 var(--space-2);
  color: var(--color-text);
  font-size: var(--font-size-24);
  font-weight: var(--font-weight-semibold);
}

.search-result-title p {
  max-width: 720px;
  margin: 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--font-size-15, 15px);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-result-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}

.mock-result-badge {
  min-height: 28px;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-4);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
}

.search-query-meta {
  min-height: 36px;
  flex-wrap: wrap;
  gap: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.search-query-meta > span:not(:first-child) {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-4);
  background: var(--color-surface);
}

.search-query-meta button {
  min-height: 30px;
  gap: var(--space-1);
  padding: 0 var(--space-2);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: transparent;
}

.search-result-layout,
.search-result-main {
  min-width: 0;
}

.search-result-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-4);
}

.search-progress-state,
.search-error-state {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
  justify-items: start;
}

.search-skeleton {
  display: grid;
  width: 100%;
  gap: var(--space-3);
}

.search-skeleton span {
  height: 14px;
  border-radius: var(--radius-4);
  background: var(--color-surface-subtle);
}

.search-skeleton span:nth-child(2) {
  width: 84%;
}

.search-skeleton span:nth-child(3) {
  width: 68%;
}

.partial-result-notice {
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--amber-100);
  border-radius: var(--radius-8);
  color: var(--color-warning-text);
  background: var(--amber-50);
  font-size: var(--font-size-13);
}

.result-tabs {
  gap: var(--space-1);
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
  justify-self: start;
}

.result-tabs button {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border-radius: 6px;
  color: var(--color-text-muted);
  background: transparent;
}

.result-tabs button[aria-selected="true"] {
  color: var(--color-primary);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  font-weight: var(--font-weight-medium);
}

.result-tabs button span {
  min-width: 20px;
  padding: 1px var(--space-1);
  border-radius: var(--radius-pill);
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  font-size: var(--font-size-12);
}

@media (min-width: 1440px) {
  .search-result-layout.context-open {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 320px;
    gap: var(--space-5);
  }
}

@media (max-width: 1180px) {
  .search-result-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .search-result-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 767px) {
  .search-result-title h1 {
    font-size: var(--font-size-24);
  }

  .search-result-title p {
    overflow: visible;
    text-overflow: clip;
    white-space: normal;
  }

  .search-result-actions {
    display: grid;
    width: 100%;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .search-result-actions > * {
    width: 100%;
    min-height: 44px;
  }

  .mock-result-badge {
    display: grid;
    place-items: center;
  }

  .result-tabs,
  .result-tabs button {
    width: 100%;
  }

  .result-tabs button {
    min-height: 44px;
    justify-content: center;
  }

  .search-query-meta button {
    min-height: 44px;
  }
}
</style>
