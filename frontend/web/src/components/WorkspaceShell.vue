<script setup lang="ts">
import { ref } from "vue";
import { RouterLink } from "vue-router";

import type { NavigationItem } from "../data/foundation";
import MobileDrawer from "./MobileDrawer.vue";

defineProps<{
  variant: "user" | "admin";
  areaTitle: string;
  navigation: readonly NavigationItem[];
  navigationLabel: string;
  navigationAriaLabel: string;
  mobileNavigation: readonly string[];
  identityName: string;
  identityRole: string;
  identityInitial: string;
  workspaceSwitch: {
    readonly label: string;
    readonly mobileLabel: string;
    readonly to: string;
  };
}>();

const isDrawerOpen = ref(false);
const menuButtonRef = ref<HTMLButtonElement>();
</script>

<template>
  <div
    :id="`${variant}-view`"
    class="app-shell"
    :class="{ 'admin-shell': variant === 'admin' }"
    data-design-source="mock-data.json"
  >
    <aside
      class="sidebar"
      :class="{ admin: variant === 'admin' }"
      :aria-label="navigationAriaLabel"
    >
      <div class="brand">智能知识库平台</div>
      <div class="nav-label">
        {{ navigationLabel }}
      </div>
      <nav :aria-label="`${navigationLabel}功能`">
        <ul class="nav-list">
          <li v-for="(item, index) in navigation" :key="item.label">
            <a
              class="nav-item"
              :class="{ active: index === 0 }"
              href="#"
              @click.prevent
            >
              <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
              {{ item.label }}
            </a>
          </li>
        </ul>
      </nav>
      <div class="sidebar-footer">
        <div class="identity">
          <span class="avatar" aria-hidden="true">{{ identityInitial }}</span>
          <div class="identity-copy">
            <div class="identity-name">
              {{ identityName }}
            </div>
            <div class="identity-role">
              {{ identityRole }}
            </div>
          </div>
        </div>
      </div>
    </aside>

    <div class="main-column">
      <header class="topbar">
        <div class="topbar-start">
          <button
            ref="menuButtonRef"
            class="mobile-menu"
            type="button"
            :aria-label="`打开${areaTitle}导航`"
            :aria-controls="`${variant}-mobile-drawer`"
            :aria-expanded="isDrawerOpen"
            @click="isDrawerOpen = true"
          >
            ☰
          </button>
          <span class="topbar-title">{{ areaTitle }}</span>
        </div>
        <div class="topbar-actions">
          <RouterLink class="button secondary" :to="workspaceSwitch.to">
            {{ workspaceSwitch.label }}
          </RouterLink>
          <span class="avatar" :aria-label="identityName">{{
            identityInitial
          }}</span>
        </div>
      </header>
      <main id="workspace-content" class="content">
        <slot />
      </main>
    </div>

    <nav class="mobile-nav" :aria-label="`移动端${areaTitle}导航`">
      <a
        v-for="(item, index) in mobileNavigation"
        :key="item"
        href="#"
        :class="{ active: index === 0 }"
        @click.prevent
      >
        {{ item }}
      </a>
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
    />
  </div>
</template>
