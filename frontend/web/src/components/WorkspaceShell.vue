<script setup lang="ts">
import { App as AntApp, Modal as AntModal } from "ant-design-vue";
import { onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import {
  isNavigationItemActive,
  type NavigationItem,
} from "../data/foundation";
import AppSidebar from "./AppSidebar.vue";
import {
  Building2,
  ChevronRight,
  CircleAlert,
  CircleDashed,
  Database,
  Menu,
  Settings,
} from "./icons";
import MobileDrawer from "./MobileDrawer.vue";

defineProps<{
  variant: "user" | "admin";
  areaTitle: string;
  navigation: readonly NavigationItem[];
  navigationLabel: string;
  mobileNavigation: readonly NavigationItem[];
  identityName: string;
  identityRole: string;
  identityInitial: string;
  workspaceSwitch: {
    readonly label: string;
    readonly mobileLabel: string;
    readonly to: string;
  };
}>();

defineSlots<{
  topbar(props: { openProfile: () => void }): unknown;
  default(): unknown;
}>();

const route = useRoute();
const { message } = AntApp.useApp();
const isDrawerOpen = ref(false);
const isSidebarCollapsed = ref(false);
const isProfileOpen = ref(false);
const menuButtonRef = ref<HTMLButtonElement>();
let tabletViewportQuery: MediaQueryList | undefined;
let desktopCollapsedPreference = false;

const showNotice = (notice: string): void => {
  void message.info(notice);
};

const openProfile = (): void => {
  isProfileOpen.value = true;
};

const syncSidebarForViewport = (
  viewport: MediaQueryListEvent | MediaQueryList,
): void => {
  isSidebarCollapsed.value = viewport.matches
    ? true
    : desktopCollapsedPreference;
};

const toggleSidebar = (): void => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
  if (tabletViewportQuery?.matches !== true) {
    desktopCollapsedPreference = isSidebarCollapsed.value;
  }
};

onMounted(() => {
  if (typeof window.matchMedia !== "function") return;

  tabletViewportQuery = window.matchMedia(
    "(min-width: 768px) and (max-width: 1180px)",
  );
  syncSidebarForViewport(tabletViewportQuery);
  tabletViewportQuery.addEventListener?.("change", syncSidebarForViewport);
});

onBeforeUnmount(() => {
  tabletViewportQuery?.removeEventListener?.("change", syncSidebarForViewport);
});
</script>

<template>
  <div
    :id="`${variant}-view`"
    class="workspace-shell"
    :class="[`variant-${variant}`, { 'sidebar-collapsed': isSidebarCollapsed }]"
    :data-design-source="
      variant === 'user'
        ? 'docs/design/ai-search-workbench/PRD.md'
        : 'V2-Redesign-Prompt.md'
    "
  >
    <AppSidebar
      :variant="variant"
      :collapsed="isSidebarCollapsed"
      :navigation="navigation"
      :navigation-label="navigationLabel"
      :identity-name="identityName"
      :identity-role="identityRole"
      :identity-initial="identityInitial"
      @toggle-collapse="toggleSidebar"
      @notice="showNotice"
      @open-profile="isProfileOpen = true"
    />

    <div class="workspace-main-column">
      <header class="workspace-topbar">
        <button
          ref="menuButtonRef"
          class="mobile-menu-button icon-button"
          type="button"
          :aria-label="`打开${areaTitle}导航`"
          :aria-controls="`${variant}-mobile-drawer`"
          :aria-expanded="isDrawerOpen"
          @click="isDrawerOpen = true"
        >
          <Menu :size="20" aria-hidden="true" />
        </button>
        <slot name="topbar" :open-profile="openProfile" />
      </header>
      <main id="workspace-content" class="workspace-content">
        <slot />
      </main>
    </div>

    <nav class="mobile-bottom-nav" :aria-label="`${areaTitle}快捷导航`">
      <template v-for="item in mobileNavigation" :key="item.label">
        <RouterLink
          v-if="item.to !== undefined"
          :to="item.to"
          :class="{ active: isNavigationItemActive(item, route.path) }"
        >
          <component :is="item.icon" :size="19" aria-hidden="true" />
          <span>{{ item.shortLabel }}</span>
        </RouterLink>
        <button
          v-else
          type="button"
          @click="showNotice(`${item.label}将在后续功能里程碑开放`)"
        >
          <component :is="item.icon" :size="19" aria-hidden="true" />
          <span>{{ item.shortLabel }}</span>
        </button>
      </template>
    </nav>

    <MobileDrawer
      :open="isDrawerOpen"
      :drawer-id="`${variant}-mobile-drawer`"
      :title="`${areaTitle}导航`"
      :dialog-label="`${areaTitle}完整导航`"
      :variant="variant"
      :navigation="navigation"
      :workspace-switch="{
        label: workspaceSwitch.mobileLabel,
        to: workspaceSwitch.to,
      }"
      :return-focus-to="menuButtonRef"
      @update:open="isDrawerOpen = $event"
      @notice="showNotice"
    />

    <AntModal
      v-model:open="isProfileOpen"
      title="个人资料"
      :footer="null"
      :width="520"
      :wrap-class-name="`profile-preview-modal profile-preview-modal-${variant}`"
      centered
    >
      <div class="profile-preview">
        <section class="profile-preview-hero" aria-label="身份信息">
          <span class="avatar profile-preview-avatar" aria-hidden="true">
            {{ identityInitial }}
          </span>
          <div class="profile-preview-identity">
            <div class="profile-preview-name-row">
              <strong>{{ identityName }}</strong>
              <span class="local-preview-badge">本地模拟资料</span>
            </div>
            <span>{{ identityRole }}</span>
          </div>
        </section>
        <dl class="profile-preview-details">
          <div class="profile-preview-detail-card">
            <span class="profile-preview-detail-icon" aria-hidden="true">
              <Building2 :size="18" />
            </span>
            <div class="profile-preview-detail-copy">
              <dt>当前工作区</dt>
              <dd>{{ areaTitle }}</dd>
            </div>
          </div>
          <div class="profile-preview-detail-card">
            <span class="profile-preview-detail-icon" aria-hidden="true">
              <CircleDashed :size="18" />
            </span>
            <div class="profile-preview-detail-copy">
              <dt>认证状态</dt>
              <dd>等待认证服务接入</dd>
            </div>
          </div>
          <div class="profile-preview-detail-card">
            <span class="profile-preview-detail-icon" aria-hidden="true">
              <Database :size="18" />
            </span>
            <div class="profile-preview-detail-copy">
              <dt>资料来源</dt>
              <dd>固定演示数据</dd>
            </div>
          </div>
        </dl>
        <div class="profile-preview-note" role="note">
          <CircleAlert :size="18" aria-hidden="true" />
          <div>
            <strong>资料接入说明</strong>
            <p>
              当前资料仅用于界面演示；真实姓名、部门和权限将在个人资料接口确认后接入。
            </p>
          </div>
        </div>
        <RouterLink
          v-if="variant === 'user'"
          class="primary-button profile-preview-action"
          to="/preferences"
          @click="isProfileOpen = false"
        >
          <Settings :size="18" aria-hidden="true" />
          <span>打开偏好设置</span>
          <ChevronRight
            class="profile-preview-action-arrow"
            :size="18"
            aria-hidden="true"
          />
        </RouterLink>
      </div>
    </AntModal>
  </div>
</template>
