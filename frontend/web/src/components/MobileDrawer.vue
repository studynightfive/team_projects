<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import {
  isNavigationItemActive,
  type NavigationItem,
} from "../data/foundation";
import { X } from "./icons";
import PlatformLogo from "./PlatformLogo.vue";

const props = defineProps<{
  open: boolean;
  drawerId: string;
  title: string;
  dialogLabel: string;
  variant: "user" | "admin";
  navigation: readonly NavigationItem[];
  workspaceSwitch: {
    readonly label: string;
    readonly to: string;
  };
  returnFocusTo?: HTMLButtonElement;
}>();

const emit = defineEmits<{
  "update:open": [value: boolean];
  notice: [message: string];
}>();

const route = useRoute();
const panelRef = ref<HTMLElement>();
const closeButtonRef = ref<HTMLButtonElement>();

const close = (): void => {
  emit("update:open", false);
};

const notifyUpcoming = (label: string): void => {
  close();
  emit("notice", `${label}将在后续功能里程碑开放`);
};

const getFocusableElements = (): HTMLElement[] => {
  if (panelRef.value === undefined) return [];

  return Array.from(
    panelRef.value.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
};

const handleKeydown = (event: KeyboardEvent): void => {
  if (event.key === "Escape") {
    event.preventDefault();
    close();
    return;
  }

  if (event.key !== "Tab") return;

  const focusableElements = getFocusableElements();
  const firstElement = focusableElements.at(0);
  const lastElement = focusableElements.at(-1);

  if (firstElement === undefined || lastElement === undefined) {
    event.preventDefault();
    return;
  }

  if (event.shiftKey && document.activeElement === firstElement) {
    event.preventDefault();
    lastElement.focus();
  } else if (!event.shiftKey && document.activeElement === lastElement) {
    event.preventDefault();
    firstElement.focus();
  }
};

watch(
  () => props.open,
  async (isOpen) => {
    document.body.classList.toggle("drawer-open", isOpen);

    if (isOpen) {
      await nextTick();
      closeButtonRef.value?.focus();
    } else {
      props.returnFocusTo?.focus();
    }
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  document.body.classList.remove("drawer-open");
});
</script>

<template>
  <div
    v-if="open"
    :id="drawerId"
    class="mobile-drawer"
    :class="`variant-${variant}`"
    @keydown="handleKeydown"
  >
    <button
      class="mobile-drawer-backdrop"
      type="button"
      :aria-label="`关闭${dialogLabel}`"
      @click="close"
    />
    <aside
      ref="panelRef"
      class="mobile-drawer-panel"
      role="dialog"
      aria-modal="true"
      :aria-label="dialogLabel"
    >
      <div class="mobile-drawer-header">
        <PlatformLogo
          :name="variant === 'user' ? '企业 AI 搜索工作台' : '智能知识库平台'"
        />
        <button
          ref="closeButtonRef"
          class="mobile-drawer-close icon-button"
          type="button"
          aria-label="关闭导航"
          @click="close"
        >
          <X :size="20" aria-hidden="true" />
        </button>
      </div>
      <div class="mobile-drawer-title">{{ title }}</div>
      <nav :aria-label="`${title}全部功能`">
        <ul class="mobile-drawer-list">
          <li v-for="item in navigation" :key="item.label">
            <RouterLink
              v-if="item.to !== undefined"
              class="mobile-drawer-link"
              :class="{ active: isNavigationItemActive(item, route.path) }"
              :to="item.to"
              @click="close"
            >
              <component :is="item.icon" :size="20" aria-hidden="true" />
              {{ item.label }}
            </RouterLink>
            <button
              v-else
              class="mobile-drawer-link"
              type="button"
              @click="notifyUpcoming(item.label)"
            >
              <component :is="item.icon" :size="20" aria-hidden="true" />
              {{ item.label }}
            </button>
            <ul
              v-if="item.children !== undefined"
              class="mobile-drawer-subnavigation"
              :aria-label="`${item.label}子导航`"
            >
              <li v-for="child in item.children" :key="child.to">
                <RouterLink
                  class="mobile-drawer-link mobile-drawer-sublink"
                  :class="{ active: route.path === child.to }"
                  :to="child.to"
                  @click="close"
                >
                  {{ child.label }}
                </RouterLink>
              </li>
            </ul>
          </li>
        </ul>
      </nav>
      <div class="mobile-drawer-footer">
        <RouterLink
          class="mobile-drawer-link workspace-switch"
          :to="workspaceSwitch.to"
          @click="close"
        >
          {{ workspaceSwitch.label }}
        </RouterLink>
      </div>
    </aside>
  </div>
</template>
