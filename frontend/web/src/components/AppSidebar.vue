<script setup lang="ts">
import { nextTick, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import type { NavigationItem } from "../data/foundation";
import {
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  UserRound,
} from "./icons";
import PlatformLogo from "./PlatformLogo.vue";

defineProps<{
  variant: "user" | "admin";
  collapsed: boolean;
  navigation: readonly NavigationItem[];
  navigationLabel: string;
  identityName: string;
  identityRole: string;
  identityInitial: string;
}>();

const emit = defineEmits<{
  "toggle-collapse": [];
  notice: [message: string];
}>();

const route = useRoute();
const isProfileMenuOpen = ref(false);
const profileTriggerRef = ref<HTMLButtonElement>();

const isActive = (item: NavigationItem): boolean =>
  item.to !== undefined && route.path === item.to;

const notifyUpcoming = (label: string): void => {
  emit("notice", `${label}将在后续功能里程碑开放`);
};

const closeProfileMenu = async (): Promise<void> => {
  if (!isProfileMenuOpen.value) return;

  isProfileMenuOpen.value = false;
  await nextTick();
  profileTriggerRef.value?.focus();
};

const runProfileAction = async (label: string): Promise<void> => {
  await closeProfileMenu();
  emit("notice", `${label}将在认证与个人中心里程碑开放`);
};
</script>

<template>
  <aside
    class="app-sidebar"
    :class="[{ collapsed }, `variant-${variant}`]"
    :aria-label="`${navigationLabel}主导航`"
    @keydown.escape="closeProfileMenu()"
  >
    <div class="sidebar-brand-row">
      <PlatformLogo :compact="collapsed" inverse />
      <button
        class="sidebar-collapse-button"
        type="button"
        :aria-label="collapsed ? '展开侧边栏' : '折叠侧边栏'"
        :aria-expanded="!collapsed"
        @click="emit('toggle-collapse')"
      >
        <component
          :is="collapsed ? PanelLeftOpen : PanelLeftClose"
          :size="18"
          :stroke-width="1.8"
          aria-hidden="true"
        />
      </button>
    </div>

    <div class="sidebar-group-label" :class="{ 'visually-hidden': collapsed }">
      {{ navigationLabel }}
    </div>
    <nav :aria-label="`${navigationLabel}功能`">
      <ul class="sidebar-navigation">
        <li v-for="item in navigation" :key="item.label">
          <RouterLink
            v-if="item.to !== undefined"
            class="sidebar-navigation-item"
            :class="{ active: isActive(item) }"
            :to="item.to"
            :title="collapsed ? item.label : undefined"
            :aria-label="collapsed ? item.label : undefined"
          >
            <component
              :is="item.icon"
              :size="20"
              :stroke-width="1.8"
              aria-hidden="true"
            />
            <span v-if="!collapsed">{{ item.label }}</span>
          </RouterLink>
          <button
            v-else
            class="sidebar-navigation-item"
            type="button"
            :title="collapsed ? item.label : undefined"
            :aria-label="collapsed ? item.label : undefined"
            @click="notifyUpcoming(item.label)"
          >
            <component
              :is="item.icon"
              :size="20"
              :stroke-width="1.8"
              aria-hidden="true"
            />
            <span v-if="!collapsed">{{ item.label }}</span>
          </button>
        </li>
      </ul>
    </nav>

    <div class="sidebar-profile">
      <button
        ref="profileTriggerRef"
        class="sidebar-profile-trigger"
        type="button"
        :aria-expanded="isProfileMenuOpen"
        aria-controls="sidebar-profile-menu"
        :title="collapsed ? identityName : undefined"
        :aria-label="collapsed ? identityName : undefined"
        @click="isProfileMenuOpen = !isProfileMenuOpen"
      >
        <span class="avatar sidebar-avatar" aria-hidden="true">
          {{ identityInitial }}
        </span>
        <span v-if="!collapsed" class="sidebar-profile-copy">
          <strong>{{ identityName }}</strong>
          <span>{{ identityRole }}</span>
        </span>
      </button>
      <div
        v-if="isProfileMenuOpen"
        id="sidebar-profile-menu"
        class="sidebar-profile-menu"
      >
        <button type="button" @click="runProfileAction('个人中心')">
          <UserRound :size="16" aria-hidden="true" />
          个人中心
        </button>
        <button type="button" @click="runProfileAction('系统设置')">
          <Settings :size="16" aria-hidden="true" />
          系统设置
        </button>
        <button type="button" @click="runProfileAction('退出登录')">
          <LogOut :size="16" aria-hidden="true" />
          退出登录
        </button>
      </div>
    </div>
  </aside>
</template>
