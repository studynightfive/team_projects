/**
 * 真实 API 服务层 - 对接员工5 后端检索和流式问答接口
 *
 * 后端接口（事实来源）：
 *   POST /api/v1/retrieval/search  -> APIResponse<SearchResponse>
 *   POST /api/v1/retrieval/answer/stream  -> 生成带引用的流式 RAG 答案
 *
 * 前端需要的数据模型在 ../types/ai-search.ts
 */

import {
  apiClient,
  FetchApiError,
  getAccessToken,
  setAccessToken,
} from "../api/client";
import {
  unwrapApiData as unwrap,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";
import type {
  AiAnswer,
  AiSearchHomeData,
  AiSearchResponse,
  AiSearchStreamObserver,
  CitationSource,
  ModelOption,
  QuickAction,
  RagProcessingStage,
  SearchModeOption,
  SearchRequest,
  SearchResultItem,
  SearchScopeOption,
} from "../types/ai-search";

/** 真实模式下仍由前端提供的 UI 选项（无对应后端配置接口） */
const REAL_MODE_OPTIONS = [
  {
    value: "smart",
    label: "智能搜索",
    description: "综合多个企业数据源生成带引用的答案。",
  },
  {
    value: "precise",
    label: "精确检索",
    description: "优先返回原始文档和高匹配度内容。",
  },
  {
    value: "document",
    label: "文档问答",
    description: "仅依据当前选择或上传的文档回答。",
  },
] as const satisfies readonly SearchModeOption[];

const REAL_SCOPE_OPTIONS = [
  {
    value: "knowledge",
    label: "企业知识库",
    description: "检索经过整理和维护的企业知识内容。",
    sources: ["knowledge"],
  },
] as const satisfies readonly SearchScopeOption[];

const REAL_SUGGESTIONS = [
  "查询最新的员工差旅报销标准。",
  "汇总本季度重点项目进展。",
  "查找产品上线流程和负责人。",
  "对比两个版本的合同条款。",
  "整理最近一个月的客户反馈。",
  "查找信息安全相关管理制度。",
] as const;

const REAL_QUICK_ACTIONS = [
  {
    id: "quick-upload",
    label: "上传文档并提问",
    description: "选择本地文档并限定问答范围。",
    to: "/knowledge?action=upload",
    icon: "upload",
  },
  {
    id: "quick-space",
    label: "进入知识空间",
    description: "按部门和主题浏览维护中的知识。",
    to: "/spaces",
    icon: "space",
  },
  {
    id: "quick-favorite",
    label: "查看收藏内容",
    description: "集中查看答案、文档、问题和空间。",
    to: "/favorites",
    icon: "favorite",
  },
] as const satisfies readonly QuickAction[];

// ============================================================
// 后端请求/响应类型（与 backend/app/rag/search/schemas.py 对齐）
// ============================================================
type BackendSearchMode = ApiSchema<"RagAnswerRequest">["mode"];
type BackendSearchRequest = ApiSchema<"RagAnswerRequest">;

interface BackendAvailableModelItem {
  readonly id: string;
  readonly provider_code: string;
  readonly model_name: string;
  readonly kind: string;
}

interface BackendSearchHit {
  doc_id: string;
  chunk_id: string;
  doc_title: string | null;
  page: number | null;
  score: number;
  vector_score: number | null;
  keyword_score: number | null;
  rerank_score: number | null;
  text: string;
  highlights: string[] | null;
  kb_id: string | null;
}

interface BackendRagAnswerResponse {
  answer: string;
  hits: BackendSearchHit[];
  mode: BackendSearchMode;
  took_ms: number;
  model: string | null;
  conversation_id: string | null;
  generated: boolean;
  from_cache?: boolean;
  cache_match?: "exact" | "similar" | null;
  cache_similarity?: number | null;
}

interface BackendStreamStage {
  readonly stage: string;
  readonly label: string;
  readonly status: "running" | "completed";
  readonly detail: string;
  readonly elapsed_ms: number;
}

interface BackendStreamDone {
  readonly took_ms: number;
  readonly mode: BackendSearchMode;
  readonly model: string | null;
  readonly generated: boolean;
  readonly from_cache: boolean;
  readonly cache_match: "exact" | "similar" | null;
  readonly cache_similarity: number | null;
}

interface ParsedSseEvent {
  readonly event: string;
  readonly data: unknown;
}

interface RefreshTokenData {
  readonly access_token: string;
}

// ============================================================
// 前端 SearchMode -> 后端 SearchMode 映射
// ============================================================
const FRONTEND_TO_BACKEND_MODE: Record<string, BackendSearchMode> = {
  smart: "hybrid",
  precise: "keyword",
  document: "keyword",
};

const toBackendMode = (mode: string): BackendSearchMode =>
  FRONTEND_TO_BACKEND_MODE[mode] ?? "hybrid";

const providerLabel = (code: string): string =>
  ({ deepseek: "DeepSeek", dashscope: "阿里云 DashScope", openai: "OpenAI" })[
    code
  ] ?? code;

const DEFAULT_CHAT_MODEL_OPTIONS = [
  {
    value: "env-deepseek",
    label: "DeepSeek / 环境默认模型",
    description: "模型列表暂不可用，后端将使用环境默认模型。",
  },
] as const satisfies readonly ModelOption[];

const toModelOption = (model: BackendAvailableModelItem): ModelOption => ({
  value: model.id,
  label: `${providerLabel(model.provider_code)} / ${model.model_name}`,
  description: "管理员已启用，可用于真实 RAG 回答。",
});

export const listRealChatModelOptions = async (
  signal?: AbortSignal,
): Promise<readonly ModelOption[]> => {
  const response = await apiClient.get<
    ApiResponse<readonly BackendAvailableModelItem[]>
  >("/v1/models/available", { params: { kind: "chat" }, signal });
  const models = unwrap(response.data);
  const options = models.map(toModelOption);
  return options.length > 0 ? options : DEFAULT_CHAT_MODEL_OPTIONS;
};

// ============================================================
// 将后端 SearchHit 转为前端 SearchResult
// ============================================================
const extractKeywords = (query: string): readonly string[] => {
  const keywords = query
    .split(/\s+/u)
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
    .slice(0, 5);
  return keywords.length > 0 ? keywords : [query.slice(0, 20)];
};

const toFrontendHit = (
  hit: BackendSearchHit,
  index: number,
  query: string,
): SearchResultItem => ({
  id: hit.chunk_id || `hit-${index}`,
  title: hit.doc_title ?? "未知文档",
  snippet: hit.text?.slice(0, 300) ?? "",
  sourceName: "知识库文档",
  sourceType: "knowledge" as const,
  fileType: "文档片段",
  spaceName: hit.kb_id ?? "已授权知识库",
  department: "未提供",
  owner: "未提供",
  updatedAt: "",
  relevance: hit.score ?? 0,
  scoreLabel: (hit.score ?? 0).toFixed(4),
  scoreDescription: "RRF 排序分",
  permissionStatus: "available",
  verifiedStatus: "pending",
  matchedKeywords: extractKeywords(query),
  documentContent: hit.text ? [hit.text] : [],
  documentId: hit.doc_id,
  knowledgeBaseId: hit.kb_id ?? undefined,
});

const toCitation = (hit: SearchResultItem): CitationSource => ({
  id: hit.id,
  title: hit.title,
  sourceName: hit.sourceName,
  sourceType: hit.sourceType,
  fileType: hit.fileType,
  snippet: hit.snippet,
  spaceName: hit.spaceName,
  owner: hit.owner,
  updatedAt: hit.updatedAt,
  relevance: hit.relevance,
  verifiedStatus: hit.verifiedStatus,
  permissionStatus: hit.permissionStatus,
  documentContent: hit.documentContent,
  documentId: hit.documentId,
  knowledgeBaseId: hit.knowledgeBaseId,
});

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const parseSseBlock = (block: string): ParsedSseEvent | undefined => {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.replace(/\r\n/gu, "\n").split("\n")) {
    if (line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }
  if (dataLines.length === 0) return undefined;
  const rawData = dataLines.join("\n");
  try {
    return { event, data: JSON.parse(rawData) as unknown };
  } catch {
    return { event, data: rawData };
  }
};

export async function* parseSseStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<ParsedSseEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/gu, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const parsed = parseSseBlock(block);
        if (parsed !== undefined) yield parsed;
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
    const trailing = parseSseBlock(buffer);
    if (trailing !== undefined) yield trailing;
  } finally {
    reader.releaseLock();
  }
}

const refreshAccessTokenForStream = async (): Promise<string> => {
  const response = await apiClient.post<ApiResponse<RefreshTokenData>>(
    "/v1/auth/refresh",
  );
  const token = unwrap(response.data).access_token;
  setAccessToken(token);
  return token;
};

const streamRequest = async (
  body: BackendSearchRequest,
  signal?: AbortSignal,
): Promise<Response> => {
  const send = (token: string | undefined): Promise<Response> =>
    fetch("/api/v1/retrieval/answer/stream", {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        ...(token === undefined || token === ""
          ? {}
          : { Authorization: `Bearer ${token}` }),
      },
      body: JSON.stringify(body),
      signal,
    });

  let response = await send(getAccessToken());
  if (response.status === 401) {
    response = await send(await refreshAccessTokenForStream());
  }
  if (!response.ok) {
    let message = "流式回答请求失败，请稍后重试。";
    try {
      const payload = (await response.json()) as unknown;
      if (
        isRecord(payload) &&
        typeof payload.message === "string" &&
        payload.message.trim() !== ""
      ) {
        message = payload.message;
      }
    } catch {
      // 非 JSON 错误响应使用稳定的公开提示。
    }
    throw new FetchApiError(message, response.status);
  }
  if (response.body === null) {
    throw new FetchApiError("浏览器未收到可读取的流式响应。", 502);
  }
  return response;
};

const buildFrontendResponse = (
  request: SearchRequest,
  query: string,
  searchData: BackendRagAnswerResponse,
): AiSearchResponse => {
  const hits = (searchData.hits ?? []).map((hit, index) =>
    toFrontendHit(hit, index, query),
  );
  const citations = hits.map(toCitation);
  const cacheDescription =
    searchData.cache_match === "similar"
      ? `复用高置信度相似问题答案（相似度 ${Math.round(
          (searchData.cache_similarity ?? 0) * 100,
        )}%）。`
      : "命中完全相同问题的答案缓存。";
  const answer: AiAnswer = {
    id: searchData.conversation_id ?? `answer-${Date.now()}`,
    query,
    title: `关于"${query}"的知识库回答`,
    summary:
      hits.length > 0
        ? `基于 ${hits.length} 条引用生成，耗时 ${searchData.took_ms}ms。`
        : "未找到相关结果，请尝试其他关键词。",
    markdown: searchData.answer,
    sections: [],
    citations,
    relatedQuestions: [],
    disclaimer: searchData.from_cache
      ? cacheDescription
      : searchData.generated && searchData.model
        ? `答案由 ${searchData.model} 基于当前账号有权访问的知识库引用生成。`
        : "正在基于当前账号有权访问的知识库引用生成答案。",
    createdAt: new Date().toISOString(),
    status: hits.length > 0 ? "success" : "partial",
  };
  return {
    request: { ...request, query, sources: [...request.sources] },
    status: hits.length > 0 ? "success" : "partial",
    answer,
    results: hits,
    sourceCount: new Set(hits.map((hit) => hit.documentId ?? hit.id)).size,
    isMock: false,
    notice: "",
    elapsedLabel: `${searchData.took_ms ?? 0}ms`,
  };
};

// ============================================================
// 调用真实后端流式 RAG 接口
// POST /api/v1/retrieval/answer/stream
// ============================================================
export const runRealSearch = async (
  request: SearchRequest,
  signal?: AbortSignal,
  observer?: AiSearchStreamObserver,
): Promise<AiSearchResponse> => {
  const query = request.query.trim();
  if (query.length === 0) {
    throw new TypeError("请输入搜索问题。");
  }

  const backendReq: BackendSearchRequest = {
    query,
    mode: toBackendMode(request.mode),
    kb_id: request.workspaceId,
    top_k: 10,
    threshold: 0.0,
    rerank: true,
    chat_model_id:
      request.modelId !== undefined && request.modelId !== "env-deepseek"
        ? request.modelId
        : null,
  };

  const response = await streamRequest(backendReq, signal);
  const hits: BackendSearchHit[] = [];
  let answer = "";
  let done: BackendStreamDone | undefined;
  const publish = (): AiSearchResponse => {
    const next = buildFrontendResponse(request, query, {
      answer,
      hits,
      mode: done?.mode ?? backendReq.mode,
      took_ms: done?.took_ms ?? 0,
      model: done?.model ?? null,
      conversation_id: null,
      generated: done?.generated ?? false,
      from_cache: done?.from_cache ?? false,
      cache_match: done?.cache_match ?? null,
      cache_similarity: done?.cache_similarity ?? null,
    });
    observer?.onResponse?.(next);
    return next;
  };

  for await (const event of parseSseStream(response.body!)) {
    if (!isRecord(event.data)) continue;
    if (event.event === "stage") {
      const stage = event.data as unknown as BackendStreamStage;
      const frontendStage: RagProcessingStage = {
        id: stage.stage,
        label: stage.label,
        status: stage.status,
        detail: stage.detail,
        elapsedMs: stage.elapsed_ms,
      };
      observer?.onStage?.(frontendStage);
    } else if (event.event === "citation") {
      hits.push(event.data as unknown as BackendSearchHit);
      publish();
    } else if (event.event === "delta") {
      const text = event.data.text;
      if (typeof text === "string") {
        answer += text;
        publish();
      }
    } else if (event.event === "done") {
      done = event.data as unknown as BackendStreamDone;
    } else if (event.event === "error") {
      const message =
        typeof event.data.message === "string"
          ? event.data.message
          : "流式回答暂时不可用，请稍后重试。";
      throw new FetchApiError(message, 502);
    }
  }
  if (done === undefined) {
    throw new FetchApiError("流式回答意外中断，请重新尝试。", 502);
  }
  return publish();
};

// ============================================================
// 首页数据 - 真实 API 模式下返回空骨架，数据由用户操作触发加载
// ============================================================
export const loadRealHome = async (
  signal?: AbortSignal,
): Promise<AiSearchHomeData> => {
  if (signal?.aborted === true) {
    throw new DOMException("加载已取消。", "AbortError");
  }
  let modelOptions: readonly ModelOption[];
  try {
    modelOptions = await listRealChatModelOptions(signal);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    modelOptions = DEFAULT_CHAT_MODEL_OPTIONS;
  }

  return {
    meta: {
      designOnly: false,
      apiRequestsAllowed: true,
      notice: "已接入真实后端 API，搜索结果来自当前账号有权访问的知识库。",
      lastUpdated: new Date().toISOString(),
    },
    modeOptions: REAL_MODE_OPTIONS,
    scopeOptions: REAL_SCOPE_OPTIONS,
    modelOptions,
    suggestions: REAL_SUGGESTIONS,
    quickActions: REAL_QUICK_ACTIONS,
    recentSearches: [],
    knowledgeSpaces: [],
    dataSources: [],
  };
};
