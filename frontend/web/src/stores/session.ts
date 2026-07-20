import { computed, ref } from "vue";
import { defineStore } from "pinia";

import type { AuthenticatedUser } from "../services/auth";

const ADMIN_PERMISSION_PREFIX = "admin.";

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
    return permissions.some((permission) =>
      permission.startsWith(ADMIN_PERMISSION_PREFIX),
    );
  });
  const hasAnyPermission = (requiredPermissions: readonly string[]): boolean => {
    if (requiredPermissions.length === 0) return true;
    const permissions = new Set(currentUser.value?.permissions ?? []);
    return requiredPermissions.some((permission) => permissions.has(permission));
  };

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
    hasAnyPermission,
    setUser,
    clearUser,
  };
});
