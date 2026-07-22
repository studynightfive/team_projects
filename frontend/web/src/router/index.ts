import {
  createRouter,
  createWebHistory,
  type Router,
  type RouterHistory,
} from "vue-router";

import { getAccessToken } from "../api/client";
import { isRealApiMode } from "../config/runtime";
import AdminWorkspaceLayout from "../layouts/AdminWorkspaceLayout.vue";
import UserWorkspaceLayout from "../layouts/UserWorkspaceLayout.vue";
import { getCurrentUser, refreshSession } from "../services/auth";
import { useSessionStore } from "../stores/session";
import AdminHomeView from "../views/AdminHomeView.vue";
import ForbiddenView from "../views/ForbiddenView.vue";
import LoginView from "../views/LoginView.vue";
import NotFoundView from "../views/NotFoundView.vue";
import UserHomeView from "../views/UserHomeView.vue";

const publicRouteNames = new Set(["login", "forbidden", "not-found"]);

export const createAppRouter = (history: RouterHistory): Router => {
  const router = createRouter({
    history,
    routes: [
      {
        path: "/",
        component: UserWorkspaceLayout,
        children: [
          {
            path: "",
            name: "user-home",
            component: UserHomeView,
            meta: { title: "AI 搜索", parentTitle: "企业知识中心" },
          },
          {
            path: "notifications",
            name: "user-notifications",
            component: () => import("../views/user/NotificationsView.vue"),
            props: { audience: "user" },
            meta: { title: "通知中心", parentTitle: "用户工作区" },
          },
          {
            path: "help",
            name: "help-center",
            component: () => import("../views/user/HelpCenterView.vue"),
            meta: { title: "帮助中心", parentTitle: "用户工作区" },
          },
          {
            path: "preferences",
            name: "account-preferences",
            component: () => import("../views/user/PreferencesView.vue"),
            meta: { title: "偏好设置", parentTitle: "用户工作区" },
          },
          {
            path: "knowledge",
            name: "knowledge-list",
            component: () => import("../views/user/KnowledgeListView.vue"),
            meta: { title: "企业知识库", parentTitle: "用户工作区" },
          },
          {
            path: "knowledge/:kb_id",
            name: "knowledge-detail",
            component: () => import("../views/user/KnowledgeDetailView.vue"),
            meta: { title: "文档目录", parentTitle: "企业知识库" },
          },
          {
            path: "knowledge/:kb_id/documents/:document_id",
            name: "document-detail",
            component: () => import("../views/user/DocumentDetailView.vue"),
            meta: { title: "文档预览", parentTitle: "企业知识库" },
          },
          {
            path: "search",
            name: "search",
            component: () => import("../views/user/SearchView.vue"),
            meta: { title: "搜索结果", parentTitle: "AI 搜索" },
          },
          {
            path: "spaces",
            name: "knowledge-spaces",
            component: () => import("../views/user/KnowledgeSpacesView.vue"),
            meta: { title: "我的空间", parentTitle: "企业知识中心" },
          },
          {
            path: "favorites",
            name: "search-favorites",
            component: () => import("../views/user/FavoritesView.vue"),
            meta: { title: "收藏内容", parentTitle: "企业知识中心" },
          },
          {
            path: "settings",
            name: "search-settings",
            component: () => import("../views/user/SearchSettingsView.vue"),
            meta: { title: "搜索设置", parentTitle: "AI 搜索" },
          },
          {
            path: "downloads",
            name: "downloads",
            component: () => import("../views/user/DownloadsView.vue"),
            meta: { title: "我的下载", parentTitle: "用户工作区" },
          },
        ],
      },
      {
        path: "/admin",
        component: AdminWorkspaceLayout,
        children: [
          {
            path: "",
            name: "admin-home",
            component: AdminHomeView,
            meta: {
              title: "平台总览",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.dashboard.view"],
            },
          },
          {
            path: "users",
            name: "admin-users",
            component: () => import("../views/admin/UsersView.vue"),
            meta: {
              title: "用户管理",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.user.view"],
            },
          },
          {
            path: "notifications",
            name: "admin-notifications",
            component: () => import("../views/user/NotificationsView.vue"),
            props: { audience: "admin" },
            meta: { title: "通知中心", parentTitle: "管理中心" },
          },
          {
            path: "departments",
            name: "admin-departments",
            component: () => import("../views/admin/DepartmentsView.vue"),
            meta: {
              title: "部门管理",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.department.view"],
            },
          },
          {
            path: "roles",
            name: "admin-roles",
            component: () => import("../views/admin/RolesView.vue"),
            meta: {
              title: "角色管理",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.role.view"],
            },
          },
          {
            path: "models",
            name: "admin-models",
            component: () => import("../views/admin/ModelsView.vue"),
            meta: {
              title: "模型管理",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.model.view"],
            },
          },
          {
            path: "knowledge-bases",
            name: "admin-knowledge-bases",
            component: () => import("../views/admin/KnowledgeBasesView.vue"),
            meta: {
              title: "知识库管理",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.knowledge_base.view"],
            },
          },
          {
            path: "documents",
            name: "admin-documents",
            component: () => import("../views/admin/DocumentsView.vue"),
            meta: {
              title: "文档管理",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.document.view"],
            },
          },
          {
            path: "tasks",
            name: "admin-tasks",
            component: () => import("../views/admin/TasksView.vue"),
            meta: {
              title: "任务中心",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.task.view"],
            },
          },
          {
            path: "retrieval-tests",
            name: "admin-retrieval-tests",
            component: () => import("../views/admin/RetrievalTestsView.vue"),
            meta: {
              title: "命中率测试",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.retrieval_test.run"],
            },
          },
          {
            path: "audit-logs",
            name: "admin-audit-logs",
            component: () => import("../views/admin/AuditLogsView.vue"),
            meta: {
              title: "审计日志",
              parentTitle: "管理中心",
              requiredPermissions: ["admin.audit.view"],
            },
          },
        ],
      },
      {
        path: "/login",
        name: "login",
        component: LoginView,
      },
      {
        path: "/403",
        name: "forbidden",
        component: ForbiddenView,
      },
      {
        path: "/:pathMatch(.*)*",
        name: "not-found",
        component: NotFoundView,
      },
    ],
  });

  router.beforeEach(async (to) => {
    if (!isRealApiMode || publicRouteNames.has(String(to.name))) {
      return true;
    }

    const sessionStore = useSessionStore();

    try {
      if (getAccessToken() === undefined) {
        sessionStore.setUser(await refreshSession());
      } else if (sessionStore.currentUser === null) {
        sessionStore.setUser(await getCurrentUser());
      }
    } catch {
      return {
        name: "login",
        query: { redirect: to.fullPath },
      };
    }

    if (to.path.startsWith("/admin") && !sessionStore.isAdmin) {
      return { name: "forbidden" };
    }
    const requiredPermissions = to.meta.requiredPermissions;
    if (
      Array.isArray(requiredPermissions) &&
      requiredPermissions.length > 0 &&
      !sessionStore.hasAnyPermission(requiredPermissions as string[])
    ) {
      return { name: "forbidden" };
    }

    return true;
  });

  return router;
};

export const router = createAppRouter(
  createWebHistory(import.meta.env.BASE_URL),
);
