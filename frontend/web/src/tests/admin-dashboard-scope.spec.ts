import { App as AntApp } from "ant-design-vue";
import { createPinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  DashboardMetrics,
  DepartmentRecord,
} from "../services/admin";
import { useSessionStore } from "../stores/session";
import AdminHomeView from "../views/AdminHomeView.vue";

const serviceMocks = vi.hoisted(() => ({
  getDashboardMetrics: vi.fn(),
  listDepartments: vi.fn(),
}));

vi.mock("../services/admin", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../services/admin")>()),
  ...serviceMocks,
}));

const departments = [
  {
    id: "department-a",
    name: "部门 A",
    description: null,
    admin_user_id: null,
    admin_username: null,
    admin_display_name: null,
    user_count: 2,
    knowledge_base_count: 1,
    created_at: null,
    updated_at: null,
  },
  {
    id: "department-b",
    name: "部门 B",
    description: null,
    admin_user_id: null,
    admin_username: null,
    admin_display_name: null,
    user_count: 1,
    knowledge_base_count: 1,
    created_at: null,
    updated_at: null,
  },
] satisfies readonly DepartmentRecord[];

const dashboard = (
  departmentId: string | null,
  departmentName: string,
): DashboardMetrics => ({
  total_users: 2,
  active_users: 2,
  disabled_users: 0,
  total_roles: 3,
  total_knowledge_bases: 1,
  total_documents: 2,
  total_conversations: 1,
  total_chats_today: 1,
  total_tokens_used: 128,
  success_rate: 100,
  avg_response_time_ms: 120,
  period: {
    days: 30,
    started_at: "2026-07-01T00:00:00Z",
    ended_at: "2026-07-31T00:00:00Z",
  },
  scope: { department_id: departmentId, department_name: departmentName },
  knowledge_coverage: { rate: 100, numerator: 1, denominator: 1 },
  active_searches: 2,
  product_queries: 2,
  product_match: { rate: 100, numerator: 2, denominator: 2 },
  effective_answers: 2,
  unanswered_queries: 0,
  document_processing: { rate: 100, numerator: 2, denominator: 2 },
  answer_cache: { rate: 50, numerator: 1, denominator: 2 },
  retrieval_evaluation: { rate: 100, numerator: 1, denominator: 1 },
  evaluation_run_count: 1,
  response_time: { average_ms: 120, sample_count: 2 },
  popular_products: [],
  department_leaderboard: {
    items: [],
    page: 1,
    page_size: 10,
    total: 0,
  },
});

const renderDashboard = async (roleName: string) => {
  const pinia = createPinia();
  useSessionStore(pinia).setUser({
    id: "admin-1",
    username: "admin",
    display_name: "管理员",
    department: { id: "department-a", name: "部门 A" },
    roles: [{ id: "role-1", name: roleName }],
    permissions: ["admin.dashboard.view", "admin.department.view"],
    knowledge_base_access: [],
  });
  const Harness = defineComponent({
    setup: () => () => h(AntApp, null, { default: () => h(AdminHomeView) }),
  });
  const wrapper = mount(Harness, {
    attachTo: document.body,
    global: { plugins: [pinia] },
  });
  await flushPromises();
  return wrapper;
};

afterEach(() => {
  vi.clearAllMocks();
  document.body.innerHTML = "";
});

describe("业务看板部门范围", () => {
  it("超级管理员切换部门后按选中部门重新请求并展示响应范围", async () => {
    serviceMocks.listDepartments.mockResolvedValue(departments);
    serviceMocks.getDashboardMetrics.mockImplementation(
      (params: { readonly department_id?: string }) => {
        const selected = departments.find(
          (item) => item.id === params.department_id,
        );
        return Promise.resolve(
          dashboard(selected?.id ?? null, selected?.name ?? "全部部门"),
        );
      },
    );
    const wrapper = await renderDashboard("超级管理员");

    await wrapper
      .get<HTMLSelectElement>('select[aria-label="部门范围"]')
      .setValue("department-b");
    await flushPromises();

    expect(serviceMocks.getDashboardMetrics).toHaveBeenLastCalledWith(
      expect.objectContaining({ department_id: "department-b" }),
    );
    expect(wrapper.text()).toContain("部门 B · 最近 30 天");
    wrapper.unmount();
  });

  it("非超级管理员即使有部门查看权限也不能选择其他部门", async () => {
    serviceMocks.getDashboardMetrics.mockResolvedValue(
      dashboard("department-a", "部门 A"),
    );
    const wrapper = await renderDashboard("知识库编辑者");

    expect(wrapper.find('select[aria-label="部门范围"]').exists()).toBe(false);
    expect(serviceMocks.listDepartments).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
