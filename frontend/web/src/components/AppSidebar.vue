<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import {
  isNavigationItemActive,
  type NavigationItem,
} from "../data/foundation";
import {
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Settings2,
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
  "open-profile": [];
  logout: [];
}>();

const route = useRoute();
const isProfileMenuOpen = ref(false);
const profileRootRef = ref<HTMLElement>();
const profileTriggerRef = ref<HTMLButtonElement>();

const isActive = (item: NavigationItem): boolean =>
  isNavigationItemActive(item, route.path);

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
  if (label === "个人中心") {
    emit("open-profile");
    return;
  }
  if (label === "退出登录") {
    emit("logout");
    return;
  }
  emit("notice", `${label}将在认证与个人中心里程碑开放`);
};

const closeProfileMenuOnOutsideClick = (event: MouseEvent): void => {
  if (
    !isProfileMenuOpen.value ||
    !(event.target instanceof Node) ||
    profileRootRef.value?.contains(event.target)
  ) {
    return;
  }

  isProfileMenuOpen.value = false;
};

onMounted(() => {
  document.addEventListener("click", closeProfileMenuOnOutsideClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", closeProfileMenuOnOutsideClick);
});
</script>

<template>
  <aside
    class="app-sidebar"
    :class="[{ collapsed }, `variant-${variant}`]"
    :aria-label="`${navigationLabel}主导航`"
    @keydown.escape="closeProfileMenu()"
  >
    <div class="sidebar-brand-row">
      <PlatformLogo
        :compact="collapsed"
        :name="variant === 'user' ? '企业 AI 搜索工作台' : '智能知识库平台'"
        inverse
      />
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
          <ul
            v-if="!collapsed && item.children !== undefined && isActive(item)"
            class="sidebar-subnavigation"
            :aria-label="`${item.label}子导航`"
          >
            <li v-for="child in item.children" :key="child.to">
              <RouterLink
                class="sidebar-subnavigation-item"
                :class="{ active: route.path === child.to }"
                :to="child.to"
              >
                {{ child.label }}
              </RouterLink>
            </li>
          </ul>
        </li>
      </ul>
    </nav>

    <div ref="profileRootRef" class="sidebar-profile">
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
        <RouterLink
          v-if="variant === 'user'"
          to="/preferences"
          @click="closeProfileMenu"
        >
          <Settings :size="16" aria-hidden="true" />
          偏好设置
        </RouterLink>
        <RouterLink
          v-if="variant === 'user'"
          to="/settings"
          @click="closeProfileMenu"
        >
          <Settings2 :size="16" aria-hidden="true" />
          搜索设置
        </RouterLink>
        <button v-else type="button" @click="runProfileAction('系统设置')">
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
