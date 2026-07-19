import { AxiosError } from "axios";
import type { AxiosAdapter, AxiosResponse } from "axios";

export const MOCK_NOT_FOUND = "ERR_MOCK_NOT_FOUND";

interface ApiResponse<T> {
  readonly code: number;
  readonly message: string;
  readonly data: T;
  readonly request_id: string;
}

const now = "2026-07-19T12:00:00+08:00";

type PermissionSeed = readonly [string, string, string, string];

const permissionSeeds: readonly PermissionSeed[] = [
  ["perm-admin-dashboard", "admin.dashboard.view", "查看系统概览", "admin"],
  ["perm-admin-user-view", "admin.user.view", "查看用户列表", "admin"],
  ["perm-admin-user-create", "admin.user.create", "创建用户", "admin"],
  ["perm-admin-user-edit", "admin.user.edit", "编辑用户", "admin"],
  ["perm-admin-role-view", "admin.role.view", "查看角色列表", "admin"],
  ["perm-admin-role-edit", "admin.role.edit", "编辑角色", "admin"],
  ["perm-document-view", "document.view", "查看文档", "document"],
  ["perm-document-upload", "document.upload", "上传文档", "document"],
  ["perm-retrieval", "retrieval.search", "知识检索", "retrieval"],
  ["perm-model-read", "model:read", "读取模型配置", "model"],
  ["perm-model-write", "model:write", "维护模型配置", "model"],
  ["perm-retrieval-test-read", "retrieval_test:read", "读取命中率测试", "retrieval_test"],
  ["perm-retrieval-test-run", "retrieval_test:run", "运行命中率测试", "retrieval_test"],
];

const permissions = permissionSeeds.map(([id, code, name, module]) => ({
  id,
  code,
  name,
  module,
  action: code.split(".").at(-1) ?? code,
}));

const roles = [
  {
    id: "role-admin",
    name: "超级管理员",
    description: "拥有全部平台管理与业务权限的演示管理员角色",
    status: "active",
    permissions_count: permissions.length,
    created_at: now,
  },
  {
    id: "role-editor",
    name: "知识库编辑者",
    description: "维护知识库、文档和任务的演示角色",
    status: "active",
    permissions_count: 8,
    created_at: now,
  },
  {
    id: "role-user",
    name: "普通用户",
    description: "使用知识库、检索、问答、收藏和下载功能",
    status: "active",
    permissions_count: 6,
    created_at: now,
  },
];

const users = [
  {
    id: "user-admin",
    username: "admin",
    display_name: "系统管理员",
    status: "active",
    roles: [roles[0]],
    last_login_at: now,
    created_at: now,
  },
  {
    id: "user-editor",
    username: "qmxl",
    display_name: "知识库编辑者",
    status: "active",
    roles: [roles[1]],
    last_login_at: null,
    created_at: now,
  },
  {
    id: "user-normal",
    username: "liuhaiwang",
    display_name: "刘海旺",
    status: "active",
    roles: [roles[2]],
    last_login_at: null,
    created_at: now,
  },
];

const knowledgeBases = [
  {
    id: "kb-default",
    name: "默认知识库",
    description: "用于基础交付演示的默认知识集合",
    status: "active",
    chunk_size: 800,
    chunk_overlap: 120,
    document_count: 2,
    ready_document_count: 1,
    chunk_count: 24,
    created_at: now,
    updated_at: now,
  },
  {
    id: "kb-medical",
    name: "医疗信息化知识库",
    description: "演示医疗信息化 IT 系统分析文档",
    status: "active",
    chunk_size: 1000,
    chunk_overlap: 160,
    document_count: 1,
    ready_document_count: 1,
    chunk_count: 16,
    created_at: now,
    updated_at: now,
  },
];

const documents = [
  {
    id: "doc-medical",
    knowledge_base_id: "kb-medical",
    knowledge_base_name: "医疗信息化知识库",
    title: "医疗信息化IT系统分析文档",
    original_filename: "医疗信息化IT系统分析文档.md",
    extension: ".md",
    mime_type: "text/markdown",
    size_bytes: 24800,
    status: "ready",
    parser_name: "markdown",
    page_count: null,
    error_message: null,
    created_at: now,
    updated_at: now,
  },
  {
    id: "doc-failed",
    knowledge_base_id: "kb-default",
    knowledge_base_name: "默认知识库",
    title: "服务降级复盘模板",
    original_filename: "服务降级复盘模板.pdf",
    extension: ".pdf",
    mime_type: "application/pdf",
    size_bytes: 1200000,
    status: "failed",
    parser_name: null,
    page_count: null,
    error_message: "转换失败",
    created_at: now,
    updated_at: now,
  },
];

const tasks = [
  {
    task_id: "task-doc-failed",
    task_type: "document_convert",
    status: "failed",
    stage: "converting",
    progress: 100,
    retry_count: 1,
    error_message: "转换失败",
    request_id: "req-task-failed",
    created_at: now,
    finished_at: now,
    started_at: now,
    document_id: "doc-failed",
    document_title: "服务降级复盘模板",
    knowledge_base_id: "kb-default",
    knowledge_base_name: "默认知识库",
  },
];

const auditLogs = [
  {
    id: "audit-1",
    user_id: "user-admin",
    username: "admin",
    action: "model_create",
    resource_type: "model",
    resource_id: "model-deepseek",
    detail: "模型配置变更",
    ip_address: "203.0.113.9",
    user_agent: "Vitest",
    result: "success",
    request_id: "demo-req-4a82",
    created_at: now,
  },
  {
    id: "audit-2",
    user_id: "user-admin",
    username: "admin",
    action: "document_upload",
    resource_type: "document",
    resource_id: "doc-medical",
    detail: "上传演示文档",
    ip_address: "203.0.113.10",
    user_agent: "Vitest",
    result: "failure",
    request_id: "demo-req-4b91",
    created_at: now,
  },
  {
    id: "audit-3",
    user_id: "user-editor",
    username: "qmxl",
    action: "knowledge_base_update",
    resource_type: "knowledge_base",
    resource_id: "kb-default",
    detail: "更新知识库",
    ip_address: "203.0.113.11",
    user_agent: "Vitest",
    result: "success",
    request_id: "demo-req-4c73",
    created_at: now,
  },
  {
    id: "audit-4",
    user_id: "user-normal",
    username: "liuhaiwang",
    action: "retrieval_answer",
    resource_type: "conversation",
    resource_id: "conv-1",
    detail: "RAG 问答",
    ip_address: "203.0.113.12",
    user_agent: "Vitest",
    result: "success",
    request_id: "demo-req-4d64",
    created_at: now,
  },
];

const providers = [
  {
    code: "deepseek",
    display_name: "DeepSeek",
    base_url: "https://api.deepseek.com",
    enabled: true,
  },
];

const models = [
  {
    id: "model-deepseek",
    provider_code: "deepseek",
    model_name: "deepseek-v4-pro",
    kind: "chat",
    parameters: { temperature: 0.2, max_tokens: 4096 },
    api_key_set: true,
    enabled: true,
    dimensions: null,
    distance: null,
    top_n: null,
    created_at: now,
    updated_at: now,
  },
];

const datasets = [
  {
    id: "dataset-medical",
    name: "医疗信息化验收测试集",
    kb_id: "kb-medical",
    queries: [],
    created_at: now,
    updated_at: now,
  },
];

const runs = [
  {
    id: "run-1",
    dataset_id: "dataset-medical",
    config_hash: "hash-demo",
    status: "done",
    progress: 100,
    total: 3,
    started_at: now,
    finished_at: now,
  },
];

const ok = <T>(config: Parameters<AxiosAdapter>[0], data: T): AxiosResponse<ApiResponse<T>> => ({
  data: { code: 0, message: "success", data, request_id: "mock-request" },
  status: 200,
  statusText: "OK",
  headers: {},
  config,
});

const page = <T>(items: readonly T[]) => ({
  items,
  page: 1,
  page_size: 100,
  total: items.length,
});

export const mockAdapter: AxiosAdapter = (config) => {
  const method = (config.method ?? "get").toLowerCase();
  const url = config.url ?? "";

  if (method === "get" && url === "/v1/users") return Promise.resolve(ok(config, page(users)));
  if (method === "get" && url === "/v1/roles") return Promise.resolve(ok(config, page(roles)));
  if (method === "get" && url.startsWith("/v1/roles/")) {
    const role = roles.find((item) => url.endsWith(item.id)) ?? roles[0];
    return Promise.resolve(ok(config, { ...role, permissions }));
  }
  if (method === "get" && url === "/v1/permissions") return Promise.resolve(ok(config, permissions));
  if (method === "get" && url === "/v1/admin/dashboard") {
    return Promise.resolve(ok(config, {
      total_users: users.length,
      active_users: users.length,
      disabled_users: 0,
      total_roles: roles.length,
      total_knowledge_bases: knowledgeBases.length,
      total_documents: documents.length,
      total_conversations: 1,
      total_chats_today: 2,
      success_rate: 0,
      avg_response_time_ms: 0,
      total_tokens_used: 0,
    }));
  }
  if (method === "get" && url === "/v1/audit-logs") return Promise.resolve(ok(config, page(auditLogs)));
  if (method === "get" && url === "/v1/knowledge-bases") return Promise.resolve(ok(config, page(knowledgeBases)));
  if (method === "get" && url === "/v1/admin/documents") return Promise.resolve(ok(config, page(documents)));
  if (method === "get" && url === "/v1/admin/tasks") return Promise.resolve(ok(config, page(tasks)));
  if (method === "get" && url === "/v1/models/providers") return Promise.resolve(ok(config, providers));
  if (method === "get" && url === "/v1/models") return Promise.resolve(ok(config, models));
  if (method === "get" && url === "/v1/retrieval-tests/datasets") return Promise.resolve(ok(config, page(datasets)));
  if (method === "get" && url === "/v1/retrieval-tests/runs") return Promise.resolve(ok(config, page(runs)));
  if (["post", "patch", "put", "delete"].includes(method)) {
    return Promise.resolve(ok(config, null));
  }

  return Promise.reject(
    new AxiosError("当前 Mock 未注册此请求。", MOCK_NOT_FOUND, config),
  );
};
