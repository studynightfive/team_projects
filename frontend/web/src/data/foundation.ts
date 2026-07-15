import rawFoundationData from "../../../../docs/design/m01-web-foundation/mock-data.json";

export interface NavigationItem {
  readonly label: string;
  readonly icon: string;
}

interface SummaryItem {
  readonly label: string;
  readonly value: string;
  readonly note: string;
}

interface KnowledgeCollection {
  readonly name: string;
  readonly type: string;
  readonly documents: number;
  readonly updated: string;
}

interface RecentDocument {
  readonly name: string;
  readonly context: string;
  readonly updated: string;
}

interface ServiceHealthItem {
  readonly name: string;
  readonly status: string;
  readonly detail: string;
}

interface GovernanceQueueItem {
  readonly name: string;
  readonly scope: string;
  readonly status: string;
  readonly time: string;
}

interface FoundationData {
  readonly userView: {
    readonly summary: readonly SummaryItem[];
    readonly knowledgeCollections: readonly KnowledgeCollection[];
    readonly recentDocuments: readonly RecentDocument[];
  };
  readonly adminView: {
    readonly summary: readonly SummaryItem[];
    readonly serviceHealth: readonly ServiceHealthItem[];
    readonly governanceQueue: readonly GovernanceQueueItem[];
  };
}

export const foundationData: FoundationData = rawFoundationData;

export const userNavigation = [
  { label: "工作台", icon: "首" },
  { label: "知识库", icon: "库" },
  { label: "检索", icon: "搜" },
  { label: "智能问答", icon: "问" },
  { label: "历史会话", icon: "史" },
  { label: "我的下载", icon: "下" },
] as const satisfies readonly NavigationItem[];

export const adminNavigation = [
  { label: "系统概览", icon: "览" },
  { label: "用户与角色", icon: "人" },
  { label: "模型管理", icon: "模" },
  { label: "知识库管理", icon: "库" },
  { label: "文档与任务", icon: "文" },
  { label: "命中率测试", icon: "测" },
  { label: "审计日志", icon: "审" },
] as const satisfies readonly NavigationItem[];

export const userMobileNavigation = [
  "工作台",
  "知识库",
  "问答",
  "我的",
] as const;
export const adminMobileNavigation = ["概览", "身份", "内容", "审计"] as const;
