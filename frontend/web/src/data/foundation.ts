import rawFoundationData from "../../../../docs/design/m01-web-foundation/mock-data.json";

import {
  Bell,
  BookOpen,
  Bot,
  Database,
  Download,
  FilePlus2,
  Files,
  Gauge,
  History,
  LayoutDashboard,
  LibraryBig,
  ListChecks,
  MessageSquareText,
  Network,
  ScrollText,
  Search,
  ServerCog,
  TriangleAlert,
  UsersRound,
  Workflow,
  type LucideIcon,
} from "../components/icons";

export type VisualTone = "blue" | "green" | "amber" | "violet" | "red";

export interface NavigationItem {
  readonly label: string;
  readonly shortLabel: string;
  readonly icon: LucideIcon;
  readonly to?: string;
}

interface UserSummaryItem {
  readonly label: string;
  readonly value: string;
  readonly trend: string;
  readonly tone: VisualTone;
  readonly icon: "book" | "file-plus" | "bell" | "message";
}

interface KnowledgeCollection {
  readonly name: string;
  readonly type: string;
  readonly documents: number;
  readonly updated: string;
  readonly tone: VisualTone;
}

interface TeamActivity {
  readonly name: string;
  readonly initial: string;
  readonly action: string;
  readonly target: string;
  readonly time: string;
  readonly tone: VisualTone;
}

interface AdminSummaryItem {
  readonly label: string;
  readonly value: string;
  readonly trend: string;
  readonly tone: VisualTone;
  readonly icon: "users" | "database" | "workflow" | "alert";
  readonly series: readonly number[];
}

export type ServiceHealthStatus = "运行正常" | "降级" | "异常";

interface ServiceHealthItem {
  readonly name: string;
  readonly status: ServiceHealthStatus;
  readonly metricLabel: string;
  readonly metricValue: string;
  readonly icon: "files" | "network" | "server";
}

interface GovernanceQueueItem {
  readonly name: string;
  readonly priority: "高" | "中" | "低";
  readonly scope: string;
  readonly submitter: string;
  readonly time: string;
}

interface AuditLogItem {
  readonly time: string;
  readonly operator: string;
  readonly action: string;
  readonly target: string;
  readonly ip: string;
  readonly result: "成功" | "失败";
}

interface FoundationData {
  readonly userView: {
    readonly profile: {
      readonly name: string;
      readonly department: string;
      readonly initial: string;
    };
    readonly summary: readonly UserSummaryItem[];
    readonly knowledgeCollections: readonly KnowledgeCollection[];
    readonly teamActivities: readonly TeamActivity[];
  };
  readonly adminView: {
    readonly profile: {
      readonly name: string;
      readonly department: string;
      readonly initial: string;
    };
    readonly summary: readonly AdminSummaryItem[];
    readonly serviceHealth: readonly ServiceHealthItem[];
    readonly governanceQueue: readonly GovernanceQueueItem[];
    readonly auditLogs: readonly AuditLogItem[];
    readonly pagination: {
      readonly total: number;
      readonly page: number;
      readonly totalPages: number;
    };
  };
}

const allowedVisualTones: readonly VisualTone[] = [
  "blue",
  "green",
  "amber",
  "violet",
  "red",
];
const allowedUserSummaryIcons: readonly UserSummaryItem["icon"][] = [
  "book",
  "file-plus",
  "bell",
  "message",
];
const allowedAdminSummaryIcons: readonly AdminSummaryItem["icon"][] = [
  "users",
  "database",
  "workflow",
  "alert",
];
const allowedServiceStatuses: readonly ServiceHealthStatus[] = [
  "运行正常",
  "降级",
  "异常",
];
const allowedServiceIcons: readonly ServiceHealthItem["icon"][] = [
  "files",
  "network",
  "server",
];
const allowedPriorities: readonly GovernanceQueueItem["priority"][] = [
  "高",
  "中",
  "低",
];
const allowedAuditResults: readonly AuditLogItem["result"][] = ["成功", "失败"];

const assertAllowedValue = (
  field: string,
  value: string,
  allowedValues: readonly string[],
): void => {
  if (!allowedValues.includes(value)) {
    throw new Error(`Mock 数据字段 ${field} 包含不支持的值：${value}`);
  }
};

/** JSON 导入会拓宽字符串字面量，因此先校验全部联合字段再收窄。 */
const validateFoundationData = (
  data: typeof rawFoundationData,
): FoundationData => {
  data.userView.summary.forEach((item) => {
    assertAllowedValue("userView.summary.tone", item.tone, allowedVisualTones);
    assertAllowedValue(
      "userView.summary.icon",
      item.icon,
      allowedUserSummaryIcons,
    );
  });
  data.userView.knowledgeCollections.forEach((item) =>
    assertAllowedValue(
      "userView.knowledgeCollections.tone",
      item.tone,
      allowedVisualTones,
    ),
  );
  data.userView.teamActivities.forEach((item) =>
    assertAllowedValue(
      "userView.teamActivities.tone",
      item.tone,
      allowedVisualTones,
    ),
  );
  data.adminView.summary.forEach((item) => {
    assertAllowedValue("adminView.summary.tone", item.tone, allowedVisualTones);
    assertAllowedValue(
      "adminView.summary.icon",
      item.icon,
      allowedAdminSummaryIcons,
    );
  });
  data.adminView.serviceHealth.forEach((item) => {
    assertAllowedValue(
      "adminView.serviceHealth.status",
      item.status,
      allowedServiceStatuses,
    );
    assertAllowedValue(
      "adminView.serviceHealth.icon",
      item.icon,
      allowedServiceIcons,
    );
  });
  data.adminView.governanceQueue.forEach((item) =>
    assertAllowedValue(
      "adminView.governanceQueue.priority",
      item.priority,
      allowedPriorities,
    ),
  );
  data.adminView.auditLogs.forEach((item) =>
    assertAllowedValue(
      "adminView.auditLogs.result",
      item.result,
      allowedAuditResults,
    ),
  );

  return data as FoundationData;
};

export const foundationData = validateFoundationData(rawFoundationData);

export const userNavigation = [
  {
    label: "工作台",
    shortLabel: "工作台",
    icon: LayoutDashboard,
    to: "/",
  },
  { label: "知识库", shortLabel: "知识库", icon: BookOpen },
  { label: "检索", shortLabel: "检索", icon: Search },
  { label: "智能问答", shortLabel: "问答", icon: MessageSquareText },
  { label: "历史会话", shortLabel: "历史", icon: History },
  { label: "我的下载", shortLabel: "下载", icon: Download },
] as const satisfies readonly NavigationItem[];

export const adminNavigation = [
  {
    label: "管理中心",
    shortLabel: "概览",
    icon: Gauge,
    to: "/admin",
  },
  { label: "用户与角色", shortLabel: "身份", icon: UsersRound },
  { label: "模型管理", shortLabel: "模型", icon: Bot },
  { label: "知识库管理", shortLabel: "知识库", icon: LibraryBig },
  { label: "文档与任务", shortLabel: "任务", icon: Files },
  { label: "命中率测试", shortLabel: "测试", icon: ListChecks },
  { label: "审计日志", shortLabel: "审计", icon: ScrollText },
] as const satisfies readonly NavigationItem[];

export const userMobileNavigation = userNavigation.slice(0, 4);
export const adminMobileNavigation = [
  adminNavigation[0],
  adminNavigation[1],
  adminNavigation[3],
  adminNavigation[6],
] as const;

export const userMetricIcons = {
  book: BookOpen,
  "file-plus": FilePlus2,
  bell: Bell,
  message: MessageSquareText,
} as const satisfies Record<UserSummaryItem["icon"], LucideIcon>;

export const adminMetricIcons = {
  users: UsersRound,
  database: Database,
  workflow: Workflow,
  alert: TriangleAlert,
} as const satisfies Record<AdminSummaryItem["icon"], LucideIcon>;

export const serviceIcons = {
  files: Files,
  network: Network,
  server: ServerCog,
} as const satisfies Record<ServiceHealthItem["icon"], LucideIcon>;

export const serviceStatusTone = {
  运行正常: "success",
  降级: "warning",
  异常: "failed",
} as const satisfies Record<
  ServiceHealthStatus,
  "success" | "warning" | "failed"
>;
