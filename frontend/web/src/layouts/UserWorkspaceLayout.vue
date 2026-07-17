<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import NotificationPreview from "../components/NotificationPreview.vue";
import WorkspaceShell from "../components/WorkspaceShell.vue";
import { CircleHelp, Database, Search } from "../components/icons";
import {
  foundationData,
  userMobileNavigation,
  userNavigation,
} from "../data/foundation";
import { aiSearchMockData } from "../mocks/ai-search";

const route = useRoute();
const router = useRouter();
const searchInputRef = ref<HTMLInputElement>();
const globalSearch = ref("");
const dataSourceCount = aiSearchMockData.dataSources.length;
const connectedSourceCount = aiSearchMockData.dataSources.filter(
  (source) => source.connectionStatus === "connected",
).length;

const currentTitle = computed(() =>
  typeof route.meta.title === "string" ? route.meta.title : "工作台",
);
const currentParentTitle = computed(() =>
  typeof route.meta.parentTitle === "string" ? route.meta.parentTitle : "首页",
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
    :identity-name="foundationData.userView.profile.name"
    :identity-role="foundationData.userView.profile.department"
    :identity-initial="foundationData.userView.profile.initial"
    :workspace-switch="{
      label: '管理中心',
      mobileLabel: '进入管理中心',
      to: '/admin',
    }"
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
          <RouterLink
            class="topbar-source-status"
            to="/data-sources"
            :aria-label="`${connectedSourceCount} 个数据源连接正常，共 ${aiSearchMockData.dataSources.length} 个`"
          >
            <Database :size="16" aria-hidden="true" />
            <span>
              {{ connectedSourceCount }}/{{ dataSourceCount }} 数据源可用
            </span>
          </RouterLink>
          <NotificationPreview audience="user" />
          <RouterLink
            class="icon-button help-button"
            to="/help"
            aria-label="查看帮助"
          >
            <CircleHelp :size="20" aria-hidden="true" />
          </RouterLink>
          <span class="topbar-divider" aria-hidden="true" />
          <RouterLink class="topbar-workspace-link" to="/admin">
            管理中心
          </RouterLink>
          <button
            class="avatar topbar-avatar"
            type="button"
            :aria-label="`${foundationData.userView.profile.name}的账号菜单`"
            @click="openProfile"
          >
            {{ foundationData.userView.profile.initial }}
          </button>
        </div>
      </div>
    </template>

    <RouterView />
  </WorkspaceShell>
</template>
