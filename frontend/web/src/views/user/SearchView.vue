<script setup lang="ts">
import { App as AntApp, Modal as AntModal, Segmented } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { toPublicApiError } from "../../api/client";
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
import { isRealApiMode } from "../../config/runtime";
import { aiSearchMockData } from "../../mocks/ai-search";
import { runAiSearch } from "../../services/ai-search";
import { listRealChatModelOptions } from "../../services/ai-search-real";
import {
  downloadAnswerExport,
  type AnswerExportFormat,
} from "../../services/downloads";
import {
  prepareFileSave,
  type PreparedFileSave,
} from "../../services/file-save";
import { createFavorite, deleteFavorite } from "../../services/favorites";
import { listKnowledgeBases } from "../../services/knowledge";
import type {
  AiSearchResponse,
  CitationSource,
  KnowledgeBaseOption,
  ModelOption,
  SearchMode,
  SearchRequest,
  SearchResultItem,
  SearchSourceType,
  SearchStatus,
} from "../../types/ai-search";

const { message } = AntApp.useApp();
const route = useRoute();
const router = useRouter();

const defaultSources: readonly SearchSourceType[] = ["knowledge"];

const defaultQuery = isRealApiMode ? "" : aiSearchMockData.answer.query;

const query = ref<string>(defaultQuery);
const mode = ref<SearchMode>("smart");
const sources = ref<SearchSourceType[]>([...defaultSources]);
const workspaceId = ref<string>();
const modelId = ref("enterprise-general");
const modelOptions = ref<readonly ModelOption[]>(aiSearchMockData.modelOptions);
const knowledgeBaseOptions = ref<readonly KnowledgeBaseOption[]>([]);
const status = ref<SearchStatus>("idle");
const response = ref<AiSearchResponse>();
const errorMessage = ref("");
const activeTab = ref<"answer" | "results">("answer");
const isContextOpen = ref(false);
const previewDocument = ref<CitationSource | SearchResultItem>();
const isPreviewOpen = ref(false);
const previewTrigger = ref<HTMLElement>();
const answerFavorite = ref(false);
const answerFavoriteId = ref<string>();
const contextTrigger = ref<HTMLElement>();
const answerTabRef = ref<HTMLButtonElement>();
const resultsTabRef = ref<HTMLButtonElement>();
const isExportDialogOpen = ref(false);
const isExporting = ref(false);

type VisibleAnswerExportFormat = Exclude<AnswerExportFormat, "txt">;

const answerExportFormat = ref<VisibleAnswerExportFormat>("pdf");
const answerExportFormats = {
  pdf: {
    label: "PDF",
    extension: ".pdf",
    description: "PDF 文档",
    mediaType: "application/pdf",
  },
  docx: {
    label: "Word",
    extension: ".docx",
    description: "Word 文档",
    mediaType:
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  },
  markdown: {
    label: "Markdown",
    extension: ".md",
    description: "Markdown 文档",
    mediaType: "text/markdown",
  },
} as const satisfies Record<
  VisibleAnswerExportFormat,
  {
    readonly label: string;
    readonly extension: string;
    readonly description: string;
    readonly mediaType: string;
  }
>;
const answerExportOptions: Array<{
  label: string;
  value: VisibleAnswerExportFormat;
}> = [
  { label: "PDF", value: "pdf" },
  { label: "Word", value: "docx" },
  { label: "Markdown", value: "markdown" },
];

let searchController: AbortController | undefined;
let desktopContextQuery: MediaQueryList | undefined;
let skipNextRouteSync = false;

const modelLabel = computed(
  () =>
    modelOptions.value.find((option) => option.value === modelId.value)
      ?.label ?? "企业通用模型",
);
const selectedKnowledgeBaseLabel = computed(() => {
  const selected = knowledgeBaseOptions.value.find(
    (item) => item.id === workspaceId.value,
  );
  return (
    selected?.name ?? knowledgeBaseOptions.value[0]?.name ?? "暂无可用知识库"
  );
});
const selectedKnowledgeBase = computed(() =>
  knowledgeBaseOptions.value.find((item) => item.id === workspaceId.value),
);
const apiModeLabel = computed(() =>
  isRealApiMode || response.value?.isMock === false ? "真实接口" : "模拟数据",
);

const parseSources = (value: unknown): SearchSourceType[] => {
  if (typeof value !== "string") return [...defaultSources];
  return value.split(",").includes("knowledge")
    ? [...defaultSources]
    : [...defaultSources];
};

const readInitialSearch = ():
  | {
      readonly q: string;
      readonly sources?: string;
      readonly workspaceId?: string;
      readonly modelId?: string;
    }
  | undefined => {
  const state: unknown = router.options.history.state;
  if (typeof state !== "object" || state === null) return undefined;
  const initialSearch = (state as Record<string, unknown>).initialSearch;
  if (typeof initialSearch !== "object" || initialSearch === null) {
    return undefined;
  }
  const value = initialSearch as Record<string, unknown>;
  if (typeof value.q !== "string" || value.q.trim().length === 0) {
    return undefined;
  }
  return {
    q: value.q.trim(),
    sources: typeof value.sources === "string" ? value.sources : undefined,
    workspaceId:
      typeof value.workspaceId === "string" && value.workspaceId !== ""
        ? value.workspaceId
        : undefined,
    modelId:
      typeof value.modelId === "string" && value.modelId !== ""
        ? value.modelId
        : undefined,
  };
};

const syncFromRoute = (): void => {
  const initialSearch = isRealApiMode ? readInitialSearch() : undefined;
  if (initialSearch !== undefined) {
    query.value = initialSearch.q;
  } else if (
    !isRealApiMode &&
    typeof route.query.q === "string" &&
    route.query.q.trim().length > 0
  ) {
    query.value = route.query.q.trim();
  } else {
    query.value = defaultQuery;
  }
  mode.value = "smart";
  sources.value = parseSources(initialSearch?.sources ?? route.query.sources);
  workspaceId.value = initialSearch?.workspaceId;
  modelId.value =
    initialSearch?.modelId ??
    (typeof route.query.model === "string"
      ? route.query.model
      : modelOptions.value[0]?.value) ??
    "enterprise-general";
};

const executeSearch = async (): Promise<void> => {
  searchController?.abort();
  searchController = new AbortController();
  status.value = "searching";
  errorMessage.value = "";
  activeTab.value = "answer";
  answerFavorite.value = false;
  answerFavoriteId.value = undefined;

  try {
    const nextResponse = await runAiSearch(
      {
        query: query.value,
        mode: mode.value,
        sources: sources.value,
        workspaceId: workspaceId.value,
        modelId: modelId.value,
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
  if (isRealApiMode) {
    query.value = request.query;
    mode.value = "smart";
    sources.value = [...request.sources];
    workspaceId.value = request.workspaceId;
    modelId.value = request.modelId ?? modelId.value ?? "enterprise-general";
    if (Object.keys(route.query).length > 0) {
      skipNextRouteSync = true;
      void router.replace({ path: "/search" });
    }
    void executeSearch();
    return;
  }

  const nextQuery = {
    q: request.query,
    sources: request.sources.join(","),
    model: request.modelId,
  };
  const unchanged =
    route.query.q === nextQuery.q &&
    route.query.sources === nextQuery.sources &&
    route.query.model === nextQuery.model;

  if (unchanged) {
    void executeSearch();
  } else {
    void router.push({
      path: "/search",
      query: nextQuery,
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

const downloadAnswerMarkdownLocally = (): void => {
  if (response.value === undefined) return;
  const content = `# RAG 问答结果\n\n## 问题\n\n${query.value}\n\n## 答案\n\n${response.value.answer.markdown}\n`;
  const blob = new Blob([content], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `AI搜索结果-${apiModeLabel.value}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
};

const openAnswerExport = (): void => {
  if (response.value === undefined) return;
  answerExportFormat.value = isRealApiMode ? "pdf" : "markdown";
  isExportDialogOpen.value = true;
};

const confirmAnswerExport = async (): Promise<void> => {
  if (response.value === undefined) return;

  if (!isRealApiMode) {
    downloadAnswerMarkdownLocally();
    isExportDialogOpen.value = false;
    void message.info("已导出本地预览答案");
    return;
  }

  const format = answerExportFormats[answerExportFormat.value];
  let destination: PreparedFileSave | undefined;
  try {
    destination = await prepareFileSave({
      suggestedName: `RAG问答结果${format.extension}`,
      description: format.description,
      mediaType: format.mediaType,
      extensions: [format.extension],
    });
  } catch (error: unknown) {
    void message.error(toPublicApiError(error).message);
    return;
  }
  if (destination === undefined) return;

  isExporting.value = true;
  try {
    const result = await downloadAnswerExport({
      format: answerExportFormat.value,
      question: query.value,
      answer: response.value.answer.markdown,
      citations: response.value.answer.citations.map((citation) => ({
        doc_id: citation.documentId ?? citation.id,
        chunk_id: citation.id,
        score: citation.relevance,
      })),
    });
    await destination.save(result.blob, result.filename);
    isExportDialogOpen.value = false;
    void message.success("答案已保存，并已记录到「我的下载」");
  } catch (error: unknown) {
    void message.error(toPublicApiError(error).message);
  } finally {
    isExporting.value = false;
  }
};

const favoriteDocumentResult = async (
  result: SearchResultItem | CitationSource,
): Promise<void> => {
  if (!isRealApiMode) {
    void message.info("文档已加入本地收藏");
    return;
  }

  const documentId =
    "documentId" in result && typeof result.documentId === "string"
      ? result.documentId
      : result.id;
  if (documentId.length === 0) {
    void message.warning("当前结果缺少文档标识，无法收藏");
    return;
  }

  try {
    await createFavorite({
      type: "document",
      title: result.title,
      summary: result.snippet,
      tags: ["文档", "搜索结果"],
      note: "",
      source_id: documentId,
      source_payload: {
        documentId,
        knowledgeBaseId:
          "knowledgeBaseId" in result ? result.knowledgeBaseId : undefined,
        sourceName: result.sourceName,
      },
    });
    void message.success("文档已保存到真实收藏");
  } catch (error: unknown) {
    void message.error(toPublicApiError(error).message);
  }
};

const favoriteResultById = async (resultId: string): Promise<void> => {
  const result = response.value?.results.find((item) => item.id === resultId);
  if (result === undefined) {
    void message.warning("未找到对应检索结果");
    return;
  }
  await favoriteDocumentResult(result);
};

const favoritePreviewDocument = async (documentId: string): Promise<void> => {
  const preview = previewDocument.value;
  if (preview === undefined) {
    void message.warning("当前没有可收藏的预览文档");
    return;
  }
  await favoriteDocumentResult({
    ...preview,
    documentId:
      "documentId" in preview && typeof preview.documentId === "string"
        ? preview.documentId
        : documentId,
  });
};

const runRelatedSearch = (question: string): void => {
  query.value = question;
  submitSearch({
    query: question,
    mode: mode.value,
    sources: sources.value,
    modelId: modelId.value,
    workspaceId: workspaceId.value,
  });
};

const loadRealKnowledgeBaseOptions = async (): Promise<void> => {
  if (!isRealApiMode) return;
  try {
    const [knowledgeBases, chatModels] = await Promise.all([
      listKnowledgeBases(),
      listRealChatModelOptions(),
    ]);
    modelOptions.value = chatModels;
    if (
      modelOptions.value.length > 0 &&
      !modelOptions.value.some((item) => item.value === modelId.value)
    ) {
      modelId.value = modelOptions.value[0]?.value ?? "env-deepseek";
    }
    knowledgeBaseOptions.value = knowledgeBases.map((item) => ({
      id: item.id,
      name: item.name,
      documentCount: item.document_count,
      readyDocumentCount: item.ready_document_count,
      status: item.status,
    }));
    if (
      knowledgeBaseOptions.value.length > 0 &&
      !knowledgeBaseOptions.value.some((item) => item.id === workspaceId.value)
    ) {
      workspaceId.value = knowledgeBaseOptions.value[0]?.id;
    }
  } catch (error: unknown) {
    void message.warning(toPublicApiError(error).message);
  }
};

const showFeedback = (value: string): void => {
  void message.success(`已记录“${value}”反馈，本地刷新后将清除`);
};

const toggleAnswerFavorite = async (): Promise<void> => {
  if (response.value === undefined) return;

  if (isRealApiMode) {
    try {
      if (answerFavorite.value && answerFavoriteId.value !== undefined) {
        await deleteFavorite(answerFavoriteId.value);
        answerFavorite.value = false;
        answerFavoriteId.value = undefined;
        void message.success("已取消收藏");
        return;
      }

      const favorite = await createFavorite({
        type: "answer",
        title: response.value.answer.title,
        summary: response.value.answer.summary,
        tags: ["RAG", "AI 答案"],
        note: "",
        source_id: response.value.answer.id,
        source_payload: {
          query: response.value.answer.query,
          markdown: response.value.answer.markdown,
          citations: response.value.answer.citations.map((citation) => ({
            id: citation.id,
            title: citation.title,
            snippet: citation.snippet,
          })),
        },
      });
      answerFavorite.value = true;
      answerFavoriteId.value = favorite.id;
      void message.success("答案已保存到真实收藏");
    } catch (error: unknown) {
      void message.error(toPublicApiError(error).message);
    }
    return;
  }

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

const selectResultTab = (tab: "answer" | "results", focus = false): void => {
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
    if (skipNextRouteSync) {
      skipNextRouteSync = false;
      return;
    }
    syncFromRoute();
    if (isRealApiMode && query.value.trim().length === 0) {
      if (Object.keys(route.query).length > 0) {
        skipNextRouteSync = true;
        void router.replace({ path: "/search" });
      }
      status.value = "idle";
      response.value = undefined;
      errorMessage.value = "";
      return;
    }
    void executeSearch();
  },
  { immediate: true },
);

onMounted(() => {
  void loadRealKnowledgeBaseOptions();
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
        <span class="mock-result-badge">{{ apiModeLabel }}</span>
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
          :disabled="response === undefined || isExporting"
          @click="openAnswerExport"
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
      <span>{{ selectedKnowledgeBaseLabel }}</span>
      <span>{{ response?.sourceCount ?? 0 }} 个知识来源</span>
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
      v-model:sources="sources"
      v-model:workspace-id="workspaceId"
      v-model:model-id="modelId"
      :mode="mode"
      compact
      :busy="status === 'searching'"
      :model-options="modelOptions"
      :knowledge-base-options="knowledgeBaseOptions"
      :requires-workspace="isRealApiMode"
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

        <div v-else-if="response === undefined" class="search-empty-state">
          <InlineState
            kind="empty"
            title="输入问题开始 RAG 检索"
            description="系统会先检索你有权限访问的知识库文档，再基于引用内容生成回答。"
          />
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
              @favorite="favoriteResultById"
            />
          </div>
        </template>
      </main>

      <SearchContextPanel
        :open="isContextOpen"
        :query="query"
        :selected-knowledge-base="selectedKnowledgeBase"
        :knowledge-base-options="knowledgeBaseOptions"
        :model-label="modelLabel"
        :citations="response?.answer.citations ?? []"
        :return-focus-to="contextTrigger"
        @close="isContextOpen = false"
        @preview="openPreview"
      />
    </div>

    <DocumentPreviewDrawer
      v-model:open="isPreviewOpen"
      :document="previewDocument"
      :return-focus-to="previewTrigger"
      @favorite="favoritePreviewDocument"
      @notice="showLocalNotice"
    />

    <AntModal
      v-model:open="isExportDialogOpen"
      title="导出问答结果"
      ok-text="导出并选择位置"
      cancel-text="取消"
      :confirm-loading="isExporting"
      :closable="!isExporting"
      :mask-closable="!isExporting"
      :cancel-button-props="{ disabled: isExporting }"
      centered
      @ok="confirmAnswerExport"
    >
      <div class="answer-export-form">
        <label for="answer-export-format">文件格式</label>
        <Segmented
          id="answer-export-format"
          v-model:value="answerExportFormat"
          :options="answerExportOptions"
          :disabled="isExporting || !isRealApiMode"
          block
        />
        <dl class="answer-export-summary">
          <div>
            <dt>内容</dt>
            <dd>当前问题、生成答案与引用摘要</dd>
          </div>
          <div>
            <dt>格式</dt>
            <dd>{{ answerExportFormats[answerExportFormat].label }}</dd>
          </div>
        </dl>
      </div>
    </AntModal>
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
.search-error-state,
.search-empty-state {
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

.answer-export-form {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-2) 0;
}

.answer-export-form > label {
  color: var(--color-text);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-medium);
}

.answer-export-summary {
  display: grid;
  margin: 0;
  border-top: 1px solid var(--color-border);
}

.answer-export-summary > div {
  display: grid;
  min-height: 42px;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
  grid-template-columns: 72px minmax(0, 1fr);
}

.answer-export-summary dt,
.answer-export-summary dd {
  margin: 0;
  font-size: var(--font-size-13);
}

.answer-export-summary dt {
  color: var(--color-text-muted);
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
