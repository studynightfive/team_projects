<script setup lang="ts">
import { App as AntApp, Modal as AntModal, Segmented } from "ant-design-vue";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import AiAnswerPanel from "../../components/search/AiAnswerPanel.vue";
import AiSearchBox from "../../components/search/AiSearchBox.vue";
import DocumentPreviewDrawer from "../../components/search/DocumentPreviewDrawer.vue";
import RagProcessingTimeline from "../../components/search/RagProcessingTimeline.vue";
import SourceResultsPanel from "../../components/search/SourceResultsPanel.vue";
import {
  Bookmark,
  Copy,
  Download,
  MessageSquarePlus,
  SlidersHorizontal,
  Square,
} from "../../components/icons";
import { isRealApiMode } from "../../config/runtime";
import { aiSearchMockData } from "../../mocks/ai-search";
import { runAiSearch } from "../../services/ai-search";
import { listRealChatModelOptions } from "../../services/ai-search-real";
import {
  getQuerySafetyMessage,
  INVALID_QUERY_MESSAGE,
} from "../../services/query-safety";
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
import {
  getConversation,
  listConversationMessages,
  type MessageRecord,
} from "../../services/conversations";
import type {
  AiSearchResponse,
  CitationSource,
  KnowledgeBaseOption,
  ModelOption,
  RagProcessingStage,
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

const defaultQuery = "";

const query = ref<string>(defaultQuery);
const currentQuestion = ref("");
const activeConversationId = ref<string>();
const mode = ref<SearchMode>("smart");
const sources = ref<SearchSourceType[]>([...defaultSources]);
const workspaceIds = ref<string[]>([]);
const modelId = ref("enterprise-general");
const modelOptions = ref<readonly ModelOption[]>(aiSearchMockData.modelOptions);
const knowledgeBaseOptions = ref<readonly KnowledgeBaseOption[]>([]);
const status = ref<SearchStatus>("idle");
const response = ref<AiSearchResponse>();
const processingStages = ref<readonly RagProcessingStage[]>([]);
const errorMessage = ref("");
const activeTab = ref<"answer" | "results">("answer");
const previewDocument = ref<CitationSource | SearchResultItem>();
const isPreviewOpen = ref(false);
const previewTrigger = ref<HTMLElement>();
const answerFavorite = ref(false);
const answerFavoriteId = ref<string>();
const answerTabRef = ref<HTMLButtonElement>();
const resultsTabRef = ref<HTMLButtonElement>();
const isExportDialogOpen = ref(false);
const isExporting = ref(false);
const searchOptionsReady = ref(!isRealApiMode);
const pendingAutomaticSearch = ref(false);
const pendingConversationId = ref<string>();
const conversationEndRef = ref<HTMLElement>();
const shouldFollowAnswer = ref(true);
const previousTurns = ref<readonly ConversationTurn[]>([]);
const conversationLoadState = ref<"idle" | "loading" | "error">("idle");
let conversationController: AbortController | undefined;

interface ConversationTurn {
  readonly id: string;
  readonly question: string;
  readonly response: AiSearchResponse;
}

type VisibleAnswerExportFormat = Exclude<AnswerExportFormat, "txt">;

const answerExportFormat = ref<VisibleAnswerExportFormat>("markdown");
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
  { label: "Markdown", value: "markdown" },
  { label: "Word", value: "docx" },
  { label: "PDF", value: "pdf" },
];

let searchController: AbortController | undefined;
let skipNextRouteSync = false;

const selectedKnowledgeBaseLabel = computed(() => {
  const names = workspaceIds.value
    .map(
      (id) => knowledgeBaseOptions.value.find((item) => item.id === id)?.name,
    )
    .filter((name): name is string => name !== undefined);
  if (names.length === 0) {
    return knowledgeBaseOptions.value[0]?.name ?? "暂无可用知识库";
  }
  if (names.length <= 2) return names.join("、");
  return `${names.slice(0, 2).join("、")}等 ${names.length} 个知识库`;
});
const apiModeLabel = computed(() =>
  isRealApiMode || response.value?.isMock === false ? "真实接口" : "模拟数据",
);
const hasConversationContent = computed(
  () =>
    previousTurns.value.length > 0 ||
    currentQuestion.value.trim().length > 0 ||
    response.value !== undefined,
);

const parseSources = (value: unknown): SearchSourceType[] => {
  if (typeof value !== "string") return [...defaultSources];
  return value.split(",").includes("knowledge")
    ? [...defaultSources]
    : [...defaultSources];
};

const readInitialSearch = ():
  | {
      readonly q?: string;
      readonly sources?: string;
      readonly workspaceIds?: readonly string[];
      readonly modelId?: string;
      readonly autoSubmit: boolean;
    }
  | undefined => {
  const historyState = router.options.history.state;
  const state: unknown = historyState;
  if (typeof state !== "object" || state === null) return undefined;
  const stateRecord = state as Record<string, unknown>;
  const initialSearch = stateRecord.initialSearch;
  const searchSetup = stateRecord.searchSetup;
  const setup =
    typeof initialSearch === "object" && initialSearch !== null
      ? initialSearch
      : typeof searchSetup === "object" && searchSetup !== null
        ? searchSetup
        : undefined;
  if (setup === undefined) {
    return undefined;
  }
  const value = setup as Record<string, unknown>;
  const q =
    typeof value.q === "string" && value.q.trim().length > 0
      ? value.q.trim()
      : undefined;
  const result = {
    q,
    sources: typeof value.sources === "string" ? value.sources : undefined,
    workspaceIds: Array.isArray(value.workspaceIds)
      ? value.workspaceIds.filter(
          (item): item is string => typeof item === "string" && item !== "",
        )
      : undefined,
    modelId:
      typeof value.modelId === "string" && value.modelId !== ""
        ? value.modelId
        : undefined,
    autoSubmit: q !== undefined && initialSearch === setup,
  };
  // 导航状态只消费一次，刷新页面既不会重复搜索，也不会遗留空间预选指令。
  const remainingState = { ...historyState };
  delete remainingState.initialSearch;
  delete remainingState.searchSetup;
  router.options.history.replace(route.fullPath, remainingState);
  return result;
};

const syncFromRoute = (): boolean => {
  const initialSearch = isRealApiMode ? readInitialSearch() : undefined;
  if (initialSearch?.q !== undefined) {
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
  workspaceIds.value = [...(initialSearch?.workspaceIds ?? [])];
  modelId.value = isRealApiMode
    ? (initialSearch?.modelId ?? "")
    : (initialSearch?.modelId ??
      (typeof route.query.model === "string"
        ? route.query.model
        : modelOptions.value[0]?.value) ??
      "enterprise-general");
  return initialSearch?.autoSubmit === true || (!isRealApiMode && query.value !== "");
};

const isNearPageBottom = (): boolean =>
  typeof window === "undefined" ||
  window.scrollY + window.innerHeight >=
    document.documentElement.scrollHeight - 180;

const syncAnswerFollowFromWheel = (event: WheelEvent): void => {
  if (status.value !== "searching") return;
  if (event.deltaY < 0) {
    shouldFollowAnswer.value = false;
    return;
  }
  if (isNearPageBottom()) {
    shouldFollowAnswer.value = true;
  }
};

const syncAnswerFollowFromKeyboard = (event: KeyboardEvent): void => {
  if (status.value !== "searching") return;
  if (["ArrowUp", "PageUp", "Home"].includes(event.key)) {
    shouldFollowAnswer.value = false;
  } else if (event.key === "End") {
    shouldFollowAnswer.value = true;
  }
};

const scrollToConversationEnd = async (force = false): Promise<void> => {
  if (!force && !shouldFollowAnswer.value) return;
  await nextTick();
  conversationEndRef.value?.scrollIntoView?.({
    block: "end",
    behavior: status.value === "searching" ? "auto" : "smooth",
  });
};

const syncConversationRoute = (conversationId: string): void => {
  if (route.query.conversation === conversationId) return;
  skipNextRouteSync = true;
  void router.replace({
    path: "/",
    query: { conversation: conversationId },
  });
};

const executeSearch = async (
  questionOverride?: string,
  preserveCompletedTurn = true,
): Promise<void> => {
  searchController?.abort();
  const submittedQuestion = (questionOverride ?? query.value).trim();
  if (submittedQuestion.length === 0) {
    void message.info("请输入搜索问题");
    return;
  }
  const safetyMessage = getQuerySafetyMessage(submittedQuestion);
  if (safetyMessage !== undefined) {
    searchController = undefined;
    status.value = "idle";
    response.value = undefined;
    errorMessage.value = "";
    void message.warning(safetyMessage);
    return;
  }
  if (
    preserveCompletedTurn &&
    currentQuestion.value.trim().length > 0 &&
    response.value !== undefined
  ) {
    previousTurns.value = [
      ...previousTurns.value,
      {
        id: response.value.answer.id,
        question: currentQuestion.value,
        response: response.value,
      },
    ];
  }
  currentQuestion.value = submittedQuestion;
  query.value = "";
  searchController = new AbortController();
  status.value = "searching";
  response.value = undefined;
  processingStages.value = [];
  errorMessage.value = "";
  activeTab.value = "answer";
  answerFavorite.value = false;
  answerFavoriteId.value = undefined;
  shouldFollowAnswer.value = true;
  void scrollToConversationEnd(true);

  try {
    const nextResponse = await runAiSearch(
      {
        query: submittedQuestion,
        mode: mode.value,
        sources: sources.value,
        workspaceIds: workspaceIds.value,
        modelId: modelId.value,
        conversationId: activeConversationId.value,
      },
      searchController.signal,
      {
        onStage: (stage) => {
          const existingIndex = processingStages.value.findIndex(
            (item) => item.id === stage.id,
          );
          processingStages.value =
            existingIndex < 0
              ? [...processingStages.value, stage]
              : processingStages.value.map((item, index) =>
                  index === existingIndex ? stage : item,
                );
        },
        onResponse: (streamedResponse) => {
          response.value = streamedResponse;
          if (streamedResponse.conversationId !== undefined) {
            activeConversationId.value = streamedResponse.conversationId;
          }
          void scrollToConversationEnd();
        },
      },
    );
    response.value = nextResponse;
    if (nextResponse.conversationId !== undefined) {
      activeConversationId.value = nextResponse.conversationId;
      syncConversationRoute(nextResponse.conversationId);
    }
    status.value = nextResponse.status;
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    const publicError = toPublicApiError(error);
    if (
      publicError.status === 422 &&
      /输入内容|提示词注入|禁止主题/u.test(publicError.message)
    ) {
      response.value = undefined;
      errorMessage.value = "";
      status.value = "idle";
      void message.warning(INVALID_QUERY_MESSAGE);
      return;
    }
    errorMessage.value = publicError.message;
    status.value = "error";
  }
};

const cancelSearch = (): void => {
  searchController?.abort();
  searchController = undefined;
  status.value = response.value?.status ?? "idle";
  void message.info("已停止生成");
};

const submitSearch = (request: SearchRequest): void => {
  if (isRealApiMode && !searchOptionsReady.value) {
    void message.info("知识库和模型仍在加载，请稍候再试");
    return;
  }
  mode.value = "smart";
  sources.value = [...request.sources];
  workspaceIds.value = [...(request.workspaceIds ?? [])];
  modelId.value = request.modelId ?? modelId.value ?? "enterprise-general";
  void executeSearch(request.query);
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
  const content = `# RAG 问答结果\n\n## 问题\n\n${currentQuestion.value}\n\n## 答案\n\n${response.value.answer.markdown}\n`;
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
      question: currentQuestion.value,
      answer: response.value.answer.markdown,
      citations: response.value.answer.citations.map((citation) => ({
        doc_id: citation.documentId ?? citation.id,
        chunk_id: citation.id,
        score: citation.relevance,
      })),
    });
    await destination.save(result.blob, result.filename);
    isExportDialogOpen.value = false;
    void message.success("答案已下载，并已记录到「我的下载」");
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
  submitSearch({
    query: question,
    mode: mode.value,
    sources: sources.value,
    modelId: modelId.value,
    workspaceIds: workspaceIds.value,
  });
};

const toHistoricalCitation = (
  citation: MessageRecord["citations"][number],
): CitationSource => ({
  id: citation.chunk_id,
  title: citation.doc_title ?? "知识库文档",
  sourceName: "知识库文档",
  sourceType: "knowledge",
  fileType: "文档片段",
  snippet: citation.text?.slice(0, 300) ?? "",
  spaceName: citation.kb_id ?? "已授权知识库",
  owner: "未提供",
  updatedAt: "",
  relevance: citation.score ?? 0,
  scoreLabel: (citation.score ?? 0).toFixed(4),
  scoreDescription: "历史检索相关度",
  verifiedStatus: "verified",
  permissionStatus: "available",
  documentContent: citation.text === null ? [] : [citation.text ?? ""],
  documentId: citation.doc_id,
  knowledgeBaseId: citation.kb_id ?? undefined,
});

const buildHistoricalResponse = (
  conversationId: string,
  question: MessageRecord,
  assistant: MessageRecord,
): AiSearchResponse => {
  const citations = assistant.citations.map(toHistoricalCitation);
  const results: SearchResultItem[] = citations.map((citation) => ({
    ...citation,
    department: "未提供",
    matchedKeywords: [],
  }));
  return {
    request: {
      query: question.content,
      mode: "smart",
      sources: ["knowledge"],
      workspaceIds: [...workspaceIds.value],
      modelId: modelId.value,
      conversationId,
    },
    status: citations.length > 0 ? "success" : "partial",
    answer: {
      id: assistant.id,
      query: question.content,
      title: `关于"${question.content}"的知识库回答`,
      summary:
        citations.length > 0
          ? `历史回答包含 ${citations.length} 条引用。`
          : "该历史回答没有可恢复的引用。",
      markdown: assistant.content,
      sections: [],
      citations,
      relatedQuestions: [],
      disclaimer: "这是已保存的历史回答，内容以生成时的知识库版本为准。",
      createdAt: assistant.created_at ?? new Date().toISOString(),
      status: citations.length > 0 ? "success" : "partial",
    },
    results,
    sourceCount: new Set(citations.map((item) => item.documentId ?? item.id))
      .size,
    isMock: false,
    notice: "",
    elapsedLabel: "历史记录",
    conversationId,
  };
};

const loadConversation = async (conversationId: string): Promise<void> => {
  if (!isRealApiMode) return;
  conversationController?.abort();
  const controller = new AbortController();
  conversationController = controller;
  conversationLoadState.value = "loading";
  errorMessage.value = "";
  try {
    const [conversation, messages] = await Promise.all([
      getConversation(conversationId, controller.signal),
      listConversationMessages(conversationId, controller.signal),
    ]);
    const scope =
      conversation.knowledge_base_ids.length > 0
        ? conversation.knowledge_base_ids
        : [conversation.kb_id];
    workspaceIds.value = scope.filter((id) =>
      knowledgeBaseOptions.value.some((item) => item.id === id),
    );

    const turns: ConversationTurn[] = [];
    let pendingQuestion: MessageRecord | undefined;
    for (const item of messages) {
      if (item.role === "user") {
        pendingQuestion = item;
      } else if (item.role === "assistant" && pendingQuestion !== undefined) {
        turns.push({
          id: item.id,
          question: pendingQuestion.content,
          response: buildHistoricalResponse(
            conversationId,
            pendingQuestion,
            item,
          ),
        });
        pendingQuestion = undefined;
      }
    }

    activeConversationId.value = conversationId;
    query.value = "";
    if (turns.length > 0) {
      const latest = turns.at(-1)!;
      previousTurns.value = turns.slice(0, -1);
      currentQuestion.value = latest.question;
      response.value = latest.response;
      status.value = latest.response.status;
    } else {
      previousTurns.value = [];
      currentQuestion.value = pendingQuestion?.content ?? "";
      response.value = undefined;
      status.value = pendingQuestion === undefined ? "idle" : "error";
      errorMessage.value =
        pendingQuestion === undefined ? "" : "该问题尚未生成完整答案。";
    }
    conversationLoadState.value = "idle";
    void scrollToConversationEnd(true);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    conversationLoadState.value = "error";
    status.value = "error";
    errorMessage.value = toPublicApiError(error).message;
  }
};

const startNewConversation = (): void => {
  searchController?.abort();
  activeConversationId.value = undefined;
  previousTurns.value = [];
  currentQuestion.value = "";
  query.value = "";
  response.value = undefined;
  processingStages.value = [];
  errorMessage.value = "";
  status.value = "idle";
  answerFavorite.value = false;
  answerFavoriteId.value = undefined;
  skipNextRouteSync = true;
  void router.replace({ path: "/" });
};

const loadRealKnowledgeBaseOptions = async (): Promise<void> => {
  if (!isRealApiMode) return;
  const [knowledgeBaseResult, chatModelResult] = await Promise.allSettled([
    listKnowledgeBases(),
    listRealChatModelOptions(),
  ]);

  if (chatModelResult.status === "fulfilled") {
    const chatModels = chatModelResult.value;
    modelOptions.value = chatModels;
    if (
      modelOptions.value.length > 0 &&
      !modelOptions.value.some((item) => item.value === modelId.value)
    ) {
      modelId.value = modelOptions.value[0]?.value ?? "env-deepseek";
    }
  } else {
    modelOptions.value = [
      {
        value: "env-deepseek",
        label: "DeepSeek / 环境默认模型",
        description: "模型列表暂不可用，后端将使用环境默认模型。",
      },
    ];
    modelId.value = "env-deepseek";
    void message.warning("模型列表暂不可用，已使用环境默认模型");
  }

  if (knowledgeBaseResult.status === "fulfilled") {
    const knowledgeBases = knowledgeBaseResult.value;
    knowledgeBaseOptions.value = knowledgeBases.map((item) => ({
      id: item.id,
      name: item.name,
      documentCount: item.document_count,
      readyDocumentCount: item.ready_document_count,
      status: item.status,
    }));
    workspaceIds.value = workspaceIds.value.filter((id) =>
      knowledgeBaseOptions.value.some((item) => item.id === id),
    );
    if (workspaceIds.value.length === 0) {
      const defaultKnowledgeBase =
        knowledgeBaseOptions.value.find((item) => item.readyDocumentCount > 0) ??
        knowledgeBaseOptions.value[0];
      if (defaultKnowledgeBase !== undefined) {
        workspaceIds.value = [defaultKnowledgeBase.id];
      }
    }
  } else {
    knowledgeBaseOptions.value = [];
    workspaceIds.value = [];
    void message.warning(toPublicApiError(knowledgeBaseResult.reason).message);
  }
  searchOptionsReady.value = true;
  if (pendingConversationId.value !== undefined) {
    const conversationId = pendingConversationId.value;
    pendingConversationId.value = undefined;
    void loadConversation(conversationId);
    return;
  }
  if (pendingAutomaticSearch.value && query.value.trim().length > 0) {
    pendingAutomaticSearch.value = false;
    void executeSearch();
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

watch(
  () => route.fullPath,
  () => {
    if (skipNextRouteSync) {
      skipNextRouteSync = false;
      return;
    }
    const conversationId =
      typeof route.query.conversation === "string"
        ? route.query.conversation
        : undefined;
    if (isRealApiMode && conversationId !== undefined) {
      if (!searchOptionsReady.value) {
        pendingConversationId.value = conversationId;
      } else {
        void loadConversation(conversationId);
      }
      return;
    }

    const shouldAutoSubmit = syncFromRoute();
    if (!shouldAutoSubmit) {
      status.value = "idle";
      response.value = undefined;
      errorMessage.value = "";
      currentQuestion.value = "";
      previousTurns.value = [];
      activeConversationId.value = undefined;
      return;
    }
    if (isRealApiMode && !searchOptionsReady.value) {
      // 空间卡片会携带知识库 ID；必须等真实选项完成校验后再发起一次搜索。
      pendingAutomaticSearch.value = true;
      return;
    }
    pendingAutomaticSearch.value = false;
    void executeSearch(query.value);
  },
  { immediate: true },
);

watch(
  () => [
    response.value?.answer?.markdown.length ?? 0,
    processingStages.value.length,
  ],
  () => void scrollToConversationEnd(),
  { flush: "post" },
);

onMounted(() => {
  void loadRealKnowledgeBaseOptions();
  // 仅把用户明确的上翻动作视为“暂停跟随”，避免程序滚动误关自动跟随。
  window.addEventListener("wheel", syncAnswerFollowFromWheel, {
    passive: true,
  });
  window.addEventListener("keydown", syncAnswerFollowFromKeyboard);
});

onBeforeUnmount(() => {
  searchController?.abort();
  conversationController?.abort();
  window.removeEventListener("wheel", syncAnswerFollowFromWheel);
  window.removeEventListener("keydown", syncAnswerFollowFromKeyboard);
});
</script>

<template>
  <div class="business-page ai-search-results-page">
    <header class="conversation-header">
      <div class="search-result-title">
        <h1>AI 搜索</h1>
        <p>{{ selectedKnowledgeBaseLabel }}</p>
      </div>
      <div class="search-result-actions">
        <button
          v-if="status === 'searching'"
          class="secondary-button compact"
          type="button"
          @click="cancelSearch"
        >
          <Square :size="15" aria-hidden="true" />
          停止生成
        </button>
        <button
          class="secondary-button compact"
          type="button"
          :disabled="!hasConversationContent"
          @click="startNewConversation"
        >
          <MessageSquarePlus :size="16" aria-hidden="true" />
          新建对话
        </button>
        <button
          v-if="response !== undefined"
          class="icon-button conversation-action-icon"
          type="button"
          :disabled="status === 'searching'"
          aria-label="复制当前答案"
          title="复制答案"
          @click="copyAnswer"
        >
          <Copy :size="16" aria-hidden="true" />
        </button>
        <button
          v-if="response !== undefined"
          class="icon-button conversation-action-icon"
          type="button"
          :disabled="status === 'searching' || isExporting"
          aria-label="下载当前答案"
          title="下载答案"
          @click="openAnswerExport"
        >
          <Download :size="16" aria-hidden="true" />
        </button>
        <button
          v-if="response !== undefined"
          class="icon-button conversation-action-icon"
          type="button"
          :aria-pressed="answerFavorite"
          :disabled="status === 'searching'"
          :aria-label="answerFavorite ? '取消收藏当前答案' : '收藏当前答案'"
          :title="answerFavorite ? '取消收藏' : '收藏答案'"
          @click="toggleAnswerFavorite"
        >
          <Bookmark :size="16" aria-hidden="true" />
        </button>
      </div>
    </header>

    <div class="search-result-layout">
      <main class="search-result-main" aria-live="polite">
        <section
          v-for="turn in previousTurns"
          :key="turn.id"
          class="completed-conversation-turn"
        >
          <article class="conversation-user-turn">
            <span>你的问题</span>
            <p>{{ turn.question }}</p>
          </article>
          <AiAnswerPanel
            :answer="turn.response.answer"
            :id-prefix="`history-${turn.id}`"
            readonly-view
            @preview="openPreview"
            @related="runRelatedSearch"
            @feedback="showFeedback"
            @toggle-favorite="toggleAnswerFavorite"
          />
        </section>

        <article
          v-if="currentQuestion.trim().length > 0"
          class="conversation-user-turn"
        >
          <span>你的问题</span>
          <p>{{ currentQuestion }}</p>
        </article>

        <InlineState
          v-if="conversationLoadState === 'loading'"
          kind="loading"
          title="正在恢复对话"
          description="系统正在读取已保存的问题、答案和引用来源。"
        />

        <div
          v-else-if="status === 'searching' && response === undefined"
          class="search-progress-state"
        >
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
          <RagProcessingTimeline
            :stages="processingStages"
            :busy="status === 'searching'"
          />
        </div>

        <div v-else-if="status === 'error'" class="search-error-state">
          <InlineState
            kind="error"
            title="本次搜索未完成"
            :description="errorMessage"
          />
          <button
            class="primary-button"
            type="button"
            @click="executeSearch(currentQuestion, false)"
          >
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
          <RagProcessingTimeline
            :stages="processingStages"
            :busy="status === 'searching'"
          />

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
              :id-prefix="`current-${response.answer.id}`"
              :favorite="answerFavorite"
              :busy="status === 'searching'"
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
    </div>

    <div ref="conversationEndRef" class="conversation-end-anchor" />
    <div class="conversation-composer">
      <AiSearchBox
        v-model:query="query"
        v-model:sources="sources"
        v-model:workspace-ids="workspaceIds"
        v-model:model-id="modelId"
        :mode="mode"
        compact
        :busy="status === 'searching'"
        :disabled="!searchOptionsReady"
        :model-options="modelOptions"
        :knowledge-base-options="knowledgeBaseOptions"
        :requires-workspace="isRealApiMode"
        :scope-locked="activeConversationId !== undefined"
        @submit="submitSearch"
        @notice="showLocalNotice"
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
      title="下载问答答案"
      :ok-text="`下载 ${answerExportFormats[answerExportFormat].label}`"
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
          <div>
            <dt>文件名</dt>
            <dd>
              RAG问答结果{{ answerExportFormats[answerExportFormat].extension }}
            </dd>
          </div>
        </dl>
      </div>
    </AntModal>
  </div>
</template>

<style scoped>
.ai-search-results-page {
  display: grid;
  width: 100%;
  min-height: calc(100vh - 176px);
  grid-template-rows: auto minmax(320px, 1fr) auto auto;
  gap: var(--space-5);
}

.conversation-header,
.search-result-actions,
.partial-result-notice,
.result-tabs {
  display: flex;
  align-items: center;
}

.conversation-header {
  width: min(100%, 960px);
  margin: 0 auto;
  justify-content: space-between;
  gap: var(--space-5);
}

.search-result-title {
  min-width: 0;
}

.search-result-title h1 {
  margin: 0 0 var(--space-1);
  color: var(--color-text);
  font-size: var(--font-size-20);
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

.conversation-action-icon {
  width: 36px;
  height: 36px;
}

.search-result-layout,
.search-result-main {
  min-width: 0;
}

.search-result-layout {
  width: min(100%, 960px);
  margin: 0 auto;
}

.search-result-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-content: start;
  gap: var(--space-6);
}

.conversation-user-turn {
  width: fit-content;
  max-width: min(720px, 86%);
  margin-left: auto;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-8);
  color: var(--white);
  background: var(--slate-800);
}

.completed-conversation-turn {
  display: grid;
  gap: var(--space-4);
  padding-bottom: var(--space-8);
  border-bottom: 1px solid var(--color-border);
}

.conversation-user-turn span {
  color: var(--slate-300);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.conversation-user-turn p {
  margin: var(--space-1) 0 0;
  color: var(--white);
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.conversation-end-anchor {
  height: 1px;
}

.conversation-composer {
  position: sticky;
  bottom: var(--space-3);
  z-index: 8;
  width: min(100%, 960px);
  margin: 0 auto;
  padding: var(--space-2) 0;
  background: var(--color-canvas);
}

.search-result-main :deep(.ai-answer-panel) {
  padding: var(--space-2) 0 var(--space-5);
  border: 0;
  border-radius: 0;
  background: transparent;
}

.search-progress-state,
.search-error-state,
.search-empty-state {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-10) 0;
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

@media (max-width: 1180px) {
  .conversation-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .search-result-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 767px) {
  .conversation-user-turn {
    width: 100%;
  }

  .conversation-composer {
    bottom: calc(72px + env(safe-area-inset-bottom));
  }

  .search-result-title h1 {
    font-size: var(--font-size-24);
  }

  .search-result-title p {
    overflow: visible;
    text-overflow: clip;
    white-space: normal;
  }

  .search-result-actions {
    display: flex;
    width: 100%;
    flex-wrap: wrap;
  }

  .search-result-actions > * {
    min-height: 44px;
    min-width: 0;
    white-space: normal;
  }

  .conversation-action-icon {
    width: 44px;
  }

  .result-tabs,
  .result-tabs button {
    width: 100%;
  }

  .result-tabs button {
    min-height: 44px;
    justify-content: center;
  }

  .answer-export-summary > div {
    grid-template-columns: 64px minmax(0, 1fr);
  }

  .answer-export-summary dd {
    overflow-wrap: anywhere;
  }
}
</style>
