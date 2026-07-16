import { aiSearchMockData } from "../mocks/ai-search";
import type {
  AiAnswer,
  AiSearchHomeData,
  AiSearchResponse,
  SearchRequest,
  SearchSourceType,
} from "../types/ai-search";

const MOCK_DELAY_MS = 24;

const createAbortError = (): DOMException =>
  new DOMException("搜索已取消。", "AbortError");

/** 保留真实异步边界，页面才能可靠验证加载态与离开页面时的取消清理。 */
const waitForMock = (signal?: AbortSignal): Promise<void> => {
  if (signal?.aborted === true) {
    return Promise.reject(createAbortError());
  }

  return new Promise((resolve, reject) => {
    const onAbort = (): void => {
      clearTimeout(timeoutId);
      reject(createAbortError());
    };
    const timeoutId = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, MOCK_DELAY_MS);

    signal?.addEventListener("abort", onAbort, { once: true });
  });
};

const clone = <Value>(value: Value): Value => structuredClone(value);

const escapeMarkdownText = (value: string): string =>
  value.replace(/[\\`*_[\]{}()#+\-.!|>]/gu, "\\$&");

const createQueryHash = (query: string): string => {
  let hash = 0;
  for (const character of query) {
    hash = (hash * 31 + (character.codePointAt(0) ?? 0)) >>> 0;
  }
  return hash.toString(36);
};

/** 非默认问题只生成明确的演示说明，避免把固定差旅答案伪装成真实检索结果。 */
const createScopedMockAnswer = (
  query: string,
  citations: readonly AiAnswer["citations"][number][],
  status: AiSearchResponse["status"],
): AiAnswer => {
  const safeQuery = escapeMarkdownText(query);
  const sourceList =
    citations.length === 0
      ? "当前所选范围没有可展示的固定来源。"
      : citations
          .map(
            (citation, index) =>
              `- [${index + 1}] **${escapeMarkdownText(citation.title)}**：${escapeMarkdownText(citation.snippet)}`,
          )
          .join("\n");

  return {
    id: `mock-answer-${createQueryHash(query)}`,
    query,
    title: `关于“${query}”的模拟检索说明`,
    summary:
      "当前前端尚未接入真实检索接口，本答案只用于验证搜索结构、来源筛选和引用交互，不代表企业事实结论。",
    markdown: `## 检索边界\n\n你搜索的是 **${safeQuery}**。当前页面不会发起真实业务请求，也不会依据固定样例推断新的事实。\n\n## 可核验的固定来源\n\n${sourceList}\n\n## 建议操作\n\n请在“原始结果”中核对来源、更新时间和权限状态；真实接口接入后，再根据同一问题生成正式答案。`,
    sections: [],
    citations: clone(citations),
    relatedQuestions: [
      `查看与“${query}”相关的原始结果`,
      `仅使用已验证来源重新检索“${query}”`,
      `按最近更新时间筛选“${query}”的依据`,
      `把“${query}”限定到企业知识库`,
    ],
    disclaimer:
      "这是固定模拟数据，不构成正式业务结论；请以真实系统中的权限、原文和最新发布时间为准。",
    createdAt: new Date("2026-07-16T12:00:00+08:00").toISOString(),
    status,
  };
};

export const loadAiSearchHome = async (
  signal?: AbortSignal,
): Promise<AiSearchHomeData> => {
  await waitForMock(signal);

  return clone({
    meta: aiSearchMockData.meta,
    modeOptions: aiSearchMockData.modeOptions,
    scopeOptions: aiSearchMockData.scopeOptions,
    modelOptions: aiSearchMockData.modelOptions,
    suggestions: aiSearchMockData.suggestions,
    quickActions: aiSearchMockData.quickActions,
    recentSearches: aiSearchMockData.recentSearches,
    knowledgeSpaces: aiSearchMockData.knowledgeSpaces,
    dataSources: aiSearchMockData.dataSources,
  });
};

export const runAiSearch = async (
  request: SearchRequest,
  signal?: AbortSignal,
): Promise<AiSearchResponse> => {
  const query = request.query.trim();
  if (query.length === 0) {
    throw new TypeError("请输入搜索问题。");
  }

  await waitForMock(signal);

  const selectedSources = [...new Set<SearchSourceType>(request.sources)];
  const includesSource = (source: SearchSourceType): boolean =>
    selectedSources.length === 0 || selectedSources.includes(source);
  const results = aiSearchMockData.results.filter((item) =>
    includesSource(item.sourceType),
  );
  const citations = aiSearchMockData.answer.citations.filter((item) =>
    includesSource(item.sourceType),
  );
  const citationIds = new Set(citations.map((item) => item.id));
  const status = results.length > 0 ? "success" : "partial";
  const useDefaultAnswer =
    query === aiSearchMockData.answer.query &&
    citations.length === aiSearchMockData.answer.citations.length;
  const answer: AiAnswer = useDefaultAnswer
    ? {
        ...clone(aiSearchMockData.answer),
        query,
        status,
        citations: clone(citations),
        sections: aiSearchMockData.answer.sections.map((section) => ({
          ...clone(section),
          citationIds: section.citationIds.filter((id) =>
            citationIds.has(id),
          ),
        })),
      }
    : createScopedMockAnswer(query, citations, status);
  const normalizedRequest: SearchRequest = {
    ...request,
    query,
    sources: selectedSources,
    attachmentIds:
      request.attachmentIds === undefined
        ? undefined
        : [...request.attachmentIds],
  };
  const sourceCount = new Set([
    ...results.map((item) => item.sourceName),
    ...citations.map((item) => item.sourceName),
  ]).size;

  return {
    request: normalizedRequest,
    status,
    answer,
    results: clone(results),
    sourceCount,
    isMock: true,
    notice: aiSearchMockData.meta.notice,
    elapsedLabel: "本地模拟，无真实耗时",
  };
};
