/**
 * 真实 API 服务层 - 对接员工5 后端检索和流式问答接口
 *
 * 后端接口（事实来源）：
 *   POST /api/v1/retrieval/search  -> APIResponse<SearchResponse>
 *   POST /api/v1/retrieval/answer  -> 生成带引用的 RAG 答案
 *
 * 前端需要的数据模型在 ../types/ai-search.ts
 */

import { apiClient } from "../api/client";
import {
  unwrapApiData as unwrap,
  type ApiResponse,
  type ApiSchema,
} from "../api/contracts";
import type {
  AiAnswer,
  AiSearchHomeData,
  AiSearchResponse,
  CitationSource,
  ModelOption,
  QuickAction,
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

interface BackendModelItem {
  readonly id: string;
  readonly provider_code: string;
  readonly model_name: string;
  readonly kind: string;
  readonly parameters: Record<string, unknown>;
  readonly api_key_set: boolean;
  readonly enabled: boolean;
  readonly dimensions: number | null;
  readonly distance: string | null;
  readonly top_n: number | null;
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

const toModelOption = (model: BackendModelItem): ModelOption => ({
  value: model.id,
  label: `${providerLabel(model.provider_code)} / ${model.model_name}`,
  description: model.api_key_set
    ? "已配置密钥，可用于真实 RAG 回答。"
    : "未配置密钥；若直接选择，后端可能回退到环境配置或返回连通性错误。",
});

export const listRealChatModelOptions = async (
  signal?: AbortSignal,
): Promise<readonly ModelOption[]> => {
  const response = await apiClient.get<
    ApiResponse<readonly BackendModelItem[]>
  >("/v1/models", { params: { kind: "chat" }, signal });
  const models = unwrap(response.data).filter((model) => model.enabled);
  const options = models.map(toModelOption);
  return options.length > 0
    ? options
    : [
        {
          value: "env-deepseek",
          label: "DeepSeek / 环境默认模型",
          description: "后端将使用环境配置中的 DeepSeek RAG 模型。",
        },
      ];
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

// ============================================================
// 调用真实后端检索接口
// POST /api/v1/retrieval/search
// ============================================================
export const runRealSearch = async (
  request: SearchRequest,
  signal?: AbortSignal,
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

  const response = await apiClient.post<ApiResponse<BackendRagAnswerResponse>>(
    "/v1/retrieval/answer",
    backendReq,
    { signal },
  );

  const searchData = unwrap(response.data);

  const hits = (searchData.hits ?? []).map((hit, index) =>
    toFrontendHit(hit, index, query),
  );
  const citations = hits.map(toCitation);

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
      ? `命中问答缓存（未再次检索文档），原模型：${searchData.model ?? "未知"}。`
      : searchData.generated && searchData.model
        ? `答案由 ${searchData.model} 基于当前账号有权访问的知识库引用生成。`
        : "未调用生成模型；请确认知识库已有可检索内容。",
    createdAt: new Date().toISOString(),
    status: hits.length > 0 ? "success" : "partial",
  };

  return {
    request: { ...request, query, sources: [...request.sources] },
    status: hits.length > 0 ? "success" : "partial",
    answer,
    results: hits,
    sourceCount: new Set(hits.map((h) => h.sourceName)).size,
    isMock: false,
    notice: "",
    elapsedLabel: `${searchData.took_ms ?? 0}ms`,
  };
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
  const modelOptions = await listRealChatModelOptions(signal);

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
