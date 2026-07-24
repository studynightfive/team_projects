<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import NotificationPreview from "../components/NotificationPreview.vue";
import WorkspaceShell from "../components/WorkspaceShell.vue";
import { CircleHelp, Search } from "../components/icons";
import {
  adminNavigation,
  userMobileNavigation,
  userNavigation,
} from "../data/foundation";
import { useSessionStore } from "../stores/session";

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();
const searchInputRef = ref<HTMLInputElement>();
const globalSearch = ref("");

const currentTitle = computed(() =>
  typeof route.meta.title === "string" ? route.meta.title : "工作台",
);
const currentParentTitle = computed(() =>
  typeof route.meta.parentTitle === "string" ? route.meta.parentTitle : "首页",
);
const adminEntryPath = computed(
  () =>
    adminNavigation.find((item) =>
      sessionStore.hasAnyPermission(item.requiredPermissions),
    )?.to,
);
const handleSearchShortcut = (event: KeyboardEvent): void => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    searchInputRef.value?.focus();
  }
};

const openSearch = (): void => {
  const query = globalSearch.value.trim();
  void router.push({
    path: "/search",
    query: query.length > 0 ? { q: query } : undefined,
  });
};

onMounted(() => window.addEventListener("keydown", handleSearchShortcut));
onBeforeUnmount(() =>
  window.removeEventListener("keydown", handleSearchShortcut),
);
</script>

<template>
  <WorkspaceShell
    variant="user"
    area-title="企业 AI 搜索工作台"
    :navigation="userNavigation"
    navigation-label="工作区"
    :mobile-navigation="userMobileNavigation"
    :identity-name="sessionStore.displayName"
    :identity-role="sessionStore.roleLabel"
    :identity-initial="sessionStore.initial"
    :workspace-switch="
      adminEntryPath !== undefined
        ? {
          label: '管理中心',
          mobileLabel: '进入管理中心',
          to: adminEntryPath,
        }
        : undefined
    "
  >
    <template #topbar="{ openProfile }">
      <div class="topbar-layout user-topbar-layout">
        <nav class="topbar-breadcrumb" aria-label="面包屑">
          <span>{{ currentParentTitle }}</span>
          <span aria-hidden="true">/</span>
          <strong>{{ currentTitle }}</strong>
        </nav>

        <label class="global-search" for="global-search-input">
          <Search :size="18" aria-hidden="true" />
          <input
            id="global-search-input"
            ref="searchInputRef"
            v-model="globalSearch"
            type="search"
            placeholder="搜索知识、文档、问题"
            autocomplete="off"
            @keydown.enter.prevent="openSearch"
          />
          <kbd>Ctrl K</kbd>
        </label>

        <div class="topbar-actions">
          <NotificationPreview audience="user" />
          <RouterLink
            class="icon-button help-button"
            to="/help"
            aria-label="查看帮助"
          >
            <CircleHelp :size="20" aria-hidden="true" />
          </RouterLink>
          <span class="topbar-divider" aria-hidden="true" />
          <RouterLink
            v-if="adminEntryPath !== undefined"
            class="topbar-workspace-link"
            :to="adminEntryPath"
          >
            管理中心
          </RouterLink>
          <button
            class="avatar topbar-avatar"
            type="button"
            :aria-label="`${sessionStore.displayName}的账号菜单`"
            @click="openProfile"
          >
            {{ sessionStore.initial }}
          </button>
        </div>
      </div>
    </template>

    <RouterView />
  </WorkspaceShell>
</template>
