<script setup lang="ts">
import { App as AntApp, Modal as AntModal } from "ant-design-vue";
import { ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import {
  isNavigationItemActive,
  type NavigationItem,
} from "../data/foundation";
import AppSidebar from "./AppSidebar.vue";
import { Menu } from "./icons";
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

const showNotice = (notice: string): void => {
  void message.info(notice);
};

const openProfile = (): void => {
  isProfileOpen.value = true;
};
</script>

<template>
  <div
    :id="`${variant}-view`"
    class="workspace-shell"
    :class="[`variant-${variant}`, { 'sidebar-collapsed': isSidebarCollapsed }]"
    data-design-source="V2-Redesign-Prompt.md"
  >
    <AppSidebar
      :variant="variant"
      :collapsed="isSidebarCollapsed"
      :navigation="navigation"
      :navigation-label="navigationLabel"
      :identity-name="identityName"
      :identity-role="identityRole"
      :identity-initial="identityInitial"
      @toggle-collapse="isSidebarCollapsed = !isSidebarCollapsed"
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
      :width="480"
    >
      <div class="profile-preview">
        <span class="local-preview-badge">M02 本地预览</span>
        <div class="profile-preview-identity">
          <span class="avatar" aria-hidden="true">{{ identityInitial }}</span>
          <div>
            <strong>{{ identityName }}</strong>
            <span>{{ identityRole }}</span>
          </div>
        </div>
        <dl class="profile-preview-details">
          <div>
            <dt>当前区域</dt>
            <dd>{{ areaTitle }}</dd>
          </div>
          <div>
            <dt>会话状态</dt>
            <dd>等待认证 OpenAPI</dd>
          </div>
          <div>
            <dt>资料来源</dt>
            <dd>确定性 design-only 数据</dd>
          </div>
        </dl>
        <p class="profile-preview-note">
          独立个人资料路由不在正式路由表内；真实姓名、部门和权限将在 `/me`
          契约确认后接入。
        </p>
      </div>
    </AntModal>
  </div>
</template>
