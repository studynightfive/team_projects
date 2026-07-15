<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { NavigationItem } from "../data/foundation";
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

const route = useRoute();
const { message } = AntApp.useApp();
const isDrawerOpen = ref(false);
const isSidebarCollapsed = ref(false);
const menuButtonRef = ref<HTMLButtonElement>();

const showNotice = (notice: string): void => {
  void message.info(notice);
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
        <slot name="topbar" />
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
          :class="{ active: route.path === item.to }"
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
  </div>
</template>
