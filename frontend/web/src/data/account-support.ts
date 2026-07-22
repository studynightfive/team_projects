export type NotificationAudience = "user" | "admin";
export type NotificationCategory = "任务" | "知识" | "系统" | "安全";

export interface NotificationItem {
  readonly id: string;
  readonly category: NotificationCategory;
  readonly title: string;
  readonly description: string;
  readonly time: string;
  readonly action?: {
    readonly label: string;
    readonly to: string;
  };
  read: boolean;
}

export const notificationSeeds = {
  user: [
    {
      id: "user-export-ready",
      category: "任务",
      title: "《发布流程手册》导出已完成",
      description:
        "PDF 与 Markdown 两种格式已进入我的下载，可在有效期内查看任务状态。",
      time: "10 分钟前",
      action: { label: "查看下载", to: "/downloads" },
      read: false,
    },
    {
      id: "user-space-update",
      category: "知识",
      title: "研发效能空间新增 4 篇文档",
      description: "本次更新包含前端质量门禁、发布检查和回滚说明。",
      time: "45 分钟前",
      action: { label: "进入知识空间", to: "/spaces" },
      read: false,
    },
    {
      id: "user-knowledge-ready",
      category: "知识",
      title: "企业知识库新增可检索文档",
      description: "上传后的文档已进入知识库目录，可在 AI 搜索中限定知识库检索。",
      time: "2 小时前",
      action: { label: "查看知识库", to: "/knowledge" },
      read: false,
    },
    {
      id: "user-security-review",
      category: "安全",
      title: "账号安全策略已更新",
      description: "企业会话将继续使用 HttpOnly Cookie，前端不会保存访问令牌。",
      time: "昨天 16:20",
      read: true,
    },
    {
      id: "user-knowledge-recommended",
      category: "知识",
      title: "为你推荐：统一发布流程与回滚指南",
      description: "该文档与最近的搜索主题相关，可直接进入企业知识库查看。",
      time: "周二 09:30",
      action: { label: "查看知识库", to: "/knowledge" },
      read: true,
    },
  ],
  admin: [
    {
      id: "admin-task-failed",
      category: "任务",
      title: "2 个文档处理任务需要复核",
      description:
        "固定样例中包含 OCR 失败和格式转换超时，请在任务中心查看失败阶段。",
      time: "5 分钟前",
      action: { label: "查看任务", to: "/admin/tasks" },
      read: false,
    },
    {
      id: "admin-user-review",
      category: "安全",
      title: "3 个用户状态变更等待确认",
      description: "请复核账号启停和角色调整是否符合最小权限原则。",
      time: "20 分钟前",
      action: { label: "查看用户", to: "/admin/users" },
      read: false,
    },
    {
      id: "admin-model-warning",
      category: "系统",
      title: "一个模型连通性检查未通过",
      description: "演示环境的备用模型返回超时，本通知不会触发真实重试。",
      time: "40 分钟前",
      action: { label: "查看模型", to: "/admin/models" },
      read: false,
    },
    {
      id: "admin-source-sync",
      category: "知识",
      title: "知识库同步存在权限差异",
      description: "研发效能手册的两条来源未通过当前授权范围检查。",
      time: "1 小时前",
      action: { label: "查看知识库", to: "/admin/knowledge-bases" },
      read: false,
    },
    {
      id: "admin-audit-failure",
      category: "安全",
      title: "审计日志出现一条失败操作",
      description: "失败记录已使用固定掩码标识，不包含真实请求或网络地址。",
      time: "2 小时前",
      action: { label: "查看审计", to: "/admin/audit-logs" },
      read: false,
    },
    {
      id: "admin-retrieval-baseline",
      category: "系统",
      title: "命中率基线需要重新验证",
      description: "索引配置样例发生变化，请使用固定测试集检查当前参数。",
      time: "昨天 18:10",
      action: { label: "运行测试", to: "/admin/retrieval-tests" },
      read: false,
    },
  ],
} satisfies Record<NotificationAudience, readonly NotificationItem[]>;

export type HelpCategory =
  | "开始使用"
  | "搜索与问答"
  | "知识与文档"
  | "账号与安全";

export interface HelpTopic {
  readonly id: string;
  readonly category: HelpCategory;
  readonly question: string;
  readonly answer: string;
}

export const helpCategories = [
  "开始使用",
  "搜索与问答",
  "知识与文档",
  "账号与安全",
] as const satisfies readonly HelpCategory[];

export const helpTopics = [
  {
    id: "start-search",
    category: "开始使用",
    question: "第一次使用时应该从哪里开始？",
    answer:
      "从 AI 搜索首页输入一个具体业务问题即可。需要按目录浏览时进入企业知识库，重要答案可直接导出或收藏。",
  },
  {
    id: "start-data-boundary",
    category: "开始使用",
    question: "当前页面里的数据是真实业务数据吗？",
    answer:
      "演示链路中的登录、企业知识库、文档上传、RAG 问答、收藏、历史、下载和通知已接入真实接口；帮助和偏好设置仍保留界面级样例。",
  },
  {
    id: "search-modes",
    category: "搜索与问答",
    question: "智能、关键词和向量搜索有什么区别？",
    answer:
      "智能搜索会综合问题和来源选择策略；关键词搜索适合精确术语；向量搜索更适合表达不同但语义接近的内容。",
  },
  {
    id: "search-citations",
    category: "搜索与问答",
    question: "如何核验 AI 答案的依据？",
    answer:
      "优先查看答案旁的引用编号和来源面板，再进入文档预览核对原文位置。没有可核验来源的结论不应直接用于高风险决策。",
  },
  {
    id: "knowledge-permissions",
    category: "知识与文档",
    question: "为什么有些知识库或文档不可见？",
    answer:
      "知识内容会按账号权限过滤。前端隐藏入口不能替代后端鉴权，真实可见范围最终以后端权限结果为准。",
  },
  {
    id: "knowledge-downloads",
    category: "知识与文档",
    question: "导出完成后在哪里查看？",
    answer:
      "导出任务会进入“我的下载”。真实模式下列表、删除和下载都会请求后端鉴权接口，不拼接公开静态文件地址。",
  },
  {
    id: "account-tokens",
    category: "账号与安全",
    question: "前端会把登录令牌保存在哪里？",
    answer:
      "不会写入 localStorage、URL 或日志。正式认证优先使用 HttpOnly Cookie，并由后端完成会话与权限校验。",
  },
  {
    id: "account-preferences",
    category: "账号与安全",
    question: "偏好设置会同步到其他设备吗？",
    answer:
      "当前不会。偏好页只验证本地表单与状态，刷新后恢复固定默认值；跨设备同步需要账号偏好契约和后端持久化。",
  },
] as const satisfies readonly HelpTopic[];

export type DefaultWorkspace = "ai-search" | "knowledge";
export type ContentDensity = "comfortable" | "compact";
export type LinkOpenMode = "same-tab" | "new-tab";
export type NotificationDigest = "realtime" | "daily" | "weekly";

export interface AccountPreferences {
  defaultWorkspace: DefaultWorkspace;
  contentDensity: ContentDensity;
  linkOpenMode: LinkOpenMode;
  notificationDigest: NotificationDigest;
  taskNotifications: boolean;
  knowledgeNotifications: boolean;
  securityNotifications: true;
}

export const defaultAccountPreferences = {
  defaultWorkspace: "ai-search",
  contentDensity: "comfortable",
  linkOpenMode: "same-tab",
  notificationDigest: "realtime",
  taskNotifications: true,
  knowledgeNotifications: true,
  securityNotifications: true,
} as const satisfies AccountPreferences;
