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
