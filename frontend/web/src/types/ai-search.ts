export type SearchMode = "smart" | "precise" | "document";

export type SearchSourceType =
  | "knowledge"
  | "project"
  | "policy"
  | "meeting"
  | "business"
  | "personal"
  | "internet";

export type SearchScope = "all" | SearchSourceType;

export type SearchStatus =
  | "idle"
  | "searching"
  | "success"
  | "partial"
  | "error";

export type VerifiedStatus = "verified" | "pending" | "expired" | "restricted";

export type PermissionStatus = "available" | "restricted";

export type DataSourceConnectionStatus =
  | "connected"
  | "syncing"
  | "failed"
  | "disconnected"
  | "permission-error";

export type DataSourceType =
  | "knowledge-base"
  | "cloud-drive"
  | "project-management"
  | "code-repository"
  | "customer-management"
  | "ticketing"
  | "collaboration"
  | "internet";

export interface SearchRequest {
  readonly query: string;
  readonly mode: SearchMode;
  readonly sources: readonly SearchSourceType[];
  readonly workspaceId?: string;
  readonly attachmentIds?: readonly string[];
  readonly modelId?: string;
}

export interface SearchModeOption {
  readonly value: SearchMode;
  readonly label: string;
  readonly description: string;
}

export interface SearchScopeOption {
  readonly value: SearchScope;
  readonly label: string;
  readonly description: string;
  readonly sources: readonly SearchSourceType[];
}

export interface ModelOption {
  readonly value: string;
  readonly label: string;
  readonly description: string;
}

export interface KnowledgeBaseOption {
  readonly id: string;
  readonly name: string;
  readonly documentCount: number;
  readonly readyDocumentCount: number;
  readonly status: string;
}

export interface QuickAction {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  readonly to: string;
  readonly icon: "upload" | "space" | "favorite" | "data-source";
}

export interface CitationSource {
  readonly id: string;
  readonly title: string;
  readonly sourceName: string;
  readonly sourceType: SearchSourceType;
  readonly fileType: string;
  readonly snippet: string;
  readonly spaceName: string;
  readonly owner: string;
  readonly updatedAt: string;
  readonly relevance: number;
  readonly scoreLabel?: string;
  readonly scoreDescription?: string;
  readonly verifiedStatus: VerifiedStatus;
  readonly permissionStatus: PermissionStatus;
  readonly documentContent: readonly string[];
  readonly url?: string;
  readonly documentId?: string;
  readonly knowledgeBaseId?: string;
}

export type Citation = CitationSource;

export interface AnswerTable {
  readonly headers: readonly string[];
  readonly rows: readonly (readonly string[])[];
}

export interface AnswerSection {
  readonly id: string;
  readonly title: string;
  readonly body: string;
  readonly citationIds: readonly string[];
  readonly bullets?: readonly string[];
  readonly table?: AnswerTable;
}

export interface AiAnswer {
  readonly id: string;
  readonly query: string;
  readonly title: string;
  readonly summary: string;
  readonly markdown: string;
  readonly sections: readonly AnswerSection[];
  readonly citations: readonly CitationSource[];
  readonly relatedQuestions: readonly string[];
  readonly disclaimer: string;
  readonly createdAt: string;
  readonly status: SearchStatus;
}

export interface SearchResultItem {
  readonly id: string;
  readonly title: string;
  readonly snippet: string;
  readonly sourceName: string;
  readonly sourceType: SearchSourceType;
  readonly fileType: string;
  readonly spaceName: string;
  readonly department: string;
  readonly owner: string;
  readonly updatedAt: string;
  readonly relevance: number;
  readonly scoreLabel?: string;
  readonly scoreDescription?: string;
  readonly permissionStatus: PermissionStatus;
  readonly verifiedStatus: VerifiedStatus;
  readonly matchedKeywords: readonly string[];
  readonly documentContent: readonly string[];
  readonly documentId?: string;
  readonly knowledgeBaseId?: string;
}

export type SearchResult = SearchResultItem;

export interface KnowledgeSpace {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly department: string;
  readonly owner: string;
  readonly memberCount: number;
  readonly documentCount: number;
  readonly updatedAt: string;
  readonly permissionType: string;
  readonly commonSearches: readonly string[];
  readonly recentQuestions: readonly string[];
}

export interface DataSource {
  readonly id: string;
  readonly name: string;
  readonly type: DataSourceType;
  readonly description: string;
  readonly connectionStatus: DataSourceConnectionStatus;
  readonly contentCount: number;
  readonly lastSyncedAt: string;
  readonly syncProgress: number;
  readonly permissionStatus: PermissionStatus;
  readonly actionLabel: string;
  readonly isMock: true;
}

export interface SearchHistory {
  readonly id: string;
  readonly query: string;
  readonly mode: SearchMode;
  readonly sources: readonly SearchSourceType[];
  readonly createdAt: string;
  readonly resultCount: number;
  readonly isFavorite: boolean;
}

export type History = SearchHistory;

export type FavoriteType = "answer" | "document" | "space" | "query";

export interface Favorite {
  readonly id: string;
  readonly title: string;
  readonly type: FavoriteType;
  readonly summary: string;
  readonly tags: readonly string[];
  readonly note: string;
  readonly savedAt: string;
  readonly sourceId: string;
}

export type UiStateKind =
  | "initial"
  | "loading"
  | "empty"
  | "searching"
  | "success"
  | "partial"
  | "error"
  | "network"
  | "forbidden"
  | "not-found"
  | "expired"
  | "disconnected";

export interface UiStateExample {
  readonly id: string;
  readonly kind: UiStateKind;
  readonly title: string;
  readonly description: string;
  readonly actionLabel?: string;
}

export interface AiSearchMockMeta {
  readonly designOnly: boolean;
  readonly apiRequestsAllowed: boolean;
  readonly notice: string;
  readonly lastUpdated?: string;
}

export interface AiSearchMockData {
  readonly meta: AiSearchMockMeta;
  readonly modeOptions: readonly SearchModeOption[];
  readonly scopeOptions: readonly SearchScopeOption[];
  readonly modelOptions: readonly ModelOption[];
  readonly suggestions: readonly string[];
  readonly quickActions: readonly QuickAction[];
  readonly recentSearches: readonly SearchHistory[];
  readonly knowledgeSpaces: readonly KnowledgeSpace[];
  readonly dataSources: readonly DataSource[];
  readonly answer: AiAnswer;
  readonly results: readonly SearchResultItem[];
  readonly history: readonly SearchHistory[];
  readonly favorites: readonly Favorite[];
  readonly stateExamples: readonly UiStateExample[];
}

export type AiSearchHomeData = Pick<
  AiSearchMockData,
  | "meta"
  | "modeOptions"
  | "scopeOptions"
  | "modelOptions"
  | "suggestions"
  | "quickActions"
  | "recentSearches"
  | "knowledgeSpaces"
  | "dataSources"
>;

export interface AiSearchResponse {
  readonly request: SearchRequest;
  readonly status: Extract<SearchStatus, "success" | "partial">;
  readonly answer: AiAnswer;
  readonly results: readonly SearchResultItem[];
  readonly sourceCount: number;
  readonly isMock: boolean;
  readonly notice: string;
  readonly elapsedLabel: string;
}
