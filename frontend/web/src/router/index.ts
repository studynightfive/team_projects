import {
  createRouter,
  createWebHistory,
  type Router,
  type RouterHistory,
} from "vue-router";

import AdminWorkspaceLayout from "../layouts/AdminWorkspaceLayout.vue";
import UserWorkspaceLayout from "../layouts/UserWorkspaceLayout.vue";
import AdminHomeView from "../views/AdminHomeView.vue";
import ForbiddenView from "../views/ForbiddenView.vue";
import LoginView from "../views/LoginView.vue";
import NotFoundView from "../views/NotFoundView.vue";
import UserHomeView from "../views/UserHomeView.vue";

export const createAppRouter = (history: RouterHistory): Router =>
  createRouter({
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
            meta: { title: "工作台", parentTitle: "首页" },
          },
          {
            path: "knowledge",
            name: "knowledge-list",
            component: () => import("../views/user/KnowledgeListView.vue"),
            meta: { title: "知识库", parentTitle: "用户工作区" },
          },
          {
            path: "knowledge/:kb_id",
            name: "knowledge-detail",
            component: () => import("../views/user/KnowledgeDetailView.vue"),
            meta: { title: "文档目录", parentTitle: "知识库" },
          },
          {
            path: "knowledge/:kb_id/documents/:document_id",
            name: "document-detail",
            component: () => import("../views/user/DocumentDetailView.vue"),
            meta: { title: "文档预览", parentTitle: "知识库" },
          },
          {
            path: "search",
            name: "search",
            component: () => import("../views/user/SearchView.vue"),
            meta: { title: "知识检索", parentTitle: "用户工作区" },
          },
          {
            path: "chat",
            name: "chat-new",
            component: () => import("../views/user/ChatView.vue"),
            meta: { title: "新会话", parentTitle: "智能问答" },
          },
          {
            path: "chat/:conversation_id",
            name: "chat-detail",
            component: () => import("../views/user/ChatView.vue"),
            meta: { title: "会话详情", parentTitle: "智能问答" },
          },
          {
            path: "conversations",
            name: "conversations",
            component: () => import("../views/user/ConversationsView.vue"),
            meta: { title: "历史会话", parentTitle: "用户工作区" },
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
            meta: { title: "平台总览", parentTitle: "管理中心" },
          },
          {
            path: "users",
            name: "admin-users",
            component: () => import("../views/admin/UsersView.vue"),
            meta: { title: "用户管理", parentTitle: "管理中心" },
          },
          {
            path: "roles",
            name: "admin-roles",
            component: () => import("../views/admin/RolesView.vue"),
            meta: { title: "角色管理", parentTitle: "管理中心" },
          },
          {
            path: "models",
            name: "admin-models",
            component: () => import("../views/admin/ModelsView.vue"),
            meta: { title: "模型管理", parentTitle: "管理中心" },
          },
          {
            path: "knowledge-bases",
            name: "admin-knowledge-bases",
            component: () => import("../views/admin/KnowledgeBasesView.vue"),
            meta: { title: "知识库管理", parentTitle: "管理中心" },
          },
          {
            path: "documents",
            name: "admin-documents",
            component: () => import("../views/admin/DocumentsView.vue"),
            meta: { title: "文档管理", parentTitle: "管理中心" },
          },
          {
            path: "tasks",
            name: "admin-tasks",
            component: () => import("../views/admin/TasksView.vue"),
            meta: { title: "转换任务", parentTitle: "管理中心" },
          },
          {
            path: "retrieval-tests",
            name: "admin-retrieval-tests",
            component: () => import("../views/admin/RetrievalTestsView.vue"),
            meta: { title: "命中率测试", parentTitle: "管理中心" },
          },
          {
            path: "audit-logs",
            name: "admin-audit-logs",
            component: () => import("../views/admin/AuditLogsView.vue"),
            meta: { title: "审计日志", parentTitle: "管理中心" },
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

export const router = createAppRouter(
  createWebHistory(import.meta.env.BASE_URL),
);
