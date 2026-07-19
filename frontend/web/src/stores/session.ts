import { computed, ref } from "vue";
import { defineStore } from "pinia";

import type { AuthenticatedUser } from "../services/auth";

const ADMIN_PERMISSION_PREFIX = "admin.";
const ADMIN_PERMISSION_NAMES = new Set([
  "admin.dashboard.view",
  "admin.user.view",
  "admin.role.view",
]);

const firstVisibleChar = (value: string): string => {
  const normalized = value.trim();
  return normalized === "" ? "用" : Array.from(normalized)[0] ?? "用";
};

export const useSessionStore = defineStore("session", () => {
  const currentUser = ref<AuthenticatedUser | null>(null);

  const displayName = computed(
    () => currentUser.value?.display_name ?? "未登录用户",
  );
  const username = computed(() => currentUser.value?.username ?? "");
  const roleLabel = computed(() => {
    const names = currentUser.value?.roles.map((role) => role.name) ?? [];
    return names.length > 0 ? names.join("、") : "普通用户";
  });
  const initial = computed(() => firstVisibleChar(displayName.value));
  const isAdmin = computed(() => {
    const permissions = currentUser.value?.permissions ?? [];
    return (
      permissions.some(
        (permission) =>
          permission.startsWith(ADMIN_PERMISSION_PREFIX) ||
          ADMIN_PERMISSION_NAMES.has(permission),
      ) ||
      (currentUser.value?.roles ?? []).some((role) =>
        role.name.includes("管理员"),
      )
    );
  });

  const setUser = (user: AuthenticatedUser): void => {
    currentUser.value = user;
  };

  const clearUser = (): void => {
    currentUser.value = null;
  };

  return {
    currentUser,
    displayName,
    username,
    roleLabel,
    initial,
    isAdmin,
    setUser,
    clearUser,
  };
});
