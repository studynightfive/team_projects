<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import NotificationPreview from "../components/NotificationPreview.vue";
import WorkspaceShell from "../components/WorkspaceShell.vue";
import { ChevronDown } from "../components/icons";
import { isRealApiMode } from "../config/runtime";
import { adminNavigation } from "../data/foundation";
import type { NavigationItem } from "../data/foundation";
import { useSessionStore } from "../stores/session";

const route = useRoute();
const sessionStore = useSessionStore();
const environment = ref("演示");
const currentTitle = computed(() =>
  typeof route.meta.title === "string" ? route.meta.title : "平台总览",
);
const visibleNavigation = computed<readonly NavigationItem[]>(() =>
  !isRealApiMode
    ? (adminNavigation as readonly NavigationItem[])
    : (adminNavigation as readonly NavigationItem[]).flatMap((item) => {
        const children = item.children?.filter((child) =>
          sessionStore.hasAnyPermission(child.requiredPermissions ?? []),
        );
        const visible = sessionStore.hasAnyPermission(
          item.requiredPermissions ?? [],
        );
        if (!visible && (children?.length ?? 0) === 0) return [];
        return [
          {
            ...item,
            to: children?.[0]?.to ?? item.to,
            children,
          },
        ];
      }),
);
const visibleMobileNavigation = computed(() => visibleNavigation.value.slice(0, 4));
</script>

<template>
  <WorkspaceShell
    variant="admin"
    area-title="管理中心"
    :navigation="visibleNavigation"
    navigation-label="管理中心"
    :mobile-navigation="visibleMobileNavigation"
    :identity-name="sessionStore.displayName"
    :identity-role="sessionStore.roleLabel"
    :identity-initial="sessionStore.initial"
    :workspace-switch="{
      label: '返回用户工作区',
      mobileLabel: '返回用户工作区',
      to: '/',
    }"
  >
    <template #topbar="{ openProfile }">
      <div class="topbar-layout admin-topbar-layout">
        <div class="admin-topbar-title">
          <strong class="admin-area-title">管理中心</strong>
          <span aria-hidden="true">/</span>
          <span class="admin-current-title">{{ currentTitle }}</span>
        </div>
        <div class="topbar-actions admin-topbar-actions">
          <label class="environment-select">
            <span class="visually-hidden">运行环境</span>
            <select v-model="environment" aria-label="运行环境">
              <option>演示</option>
              <option>生产</option>
            </select>
            <ChevronDown :size="14" aria-hidden="true" />
          </label>
          <NotificationPreview audience="admin" />
          <button
            class="avatar topbar-avatar admin-avatar"
            type="button"
            :aria-label="`${sessionStore.displayName}的账号菜单`"
            @click="openProfile"
          >
            {{ sessionStore.initial }}
          </button>
          <RouterLink class="secondary-button compact" to="/">
            返回用户工作区
          </RouterLink>
        </div>
      </div>
    </template>

    <RouterView />
  </WorkspaceShell>
</template>
