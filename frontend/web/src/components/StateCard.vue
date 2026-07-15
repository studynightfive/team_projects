<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

import {
  CircleAlert,
  FileQuestion,
  Inbox,
  LoaderCircle,
  ShieldX,
} from "./icons";

type StateKind = "loading" | "empty" | "error" | "forbidden" | "not-found";

const props = defineProps<{
  kind: StateKind;
  actionTo?: string;
}>();

const emit = defineEmits<{
  action: [];
}>();

const stateContent = {
  loading: {
    icon: LoaderCircle,
    title: "正在加载页面",
    description: "请稍候，正在准备工作区内容。",
    action: undefined,
    tone: "info",
  },
  empty: {
    icon: Inbox,
    title: "暂无内容",
    description: "当前范围内还没有可显示的内容。",
    action: "刷新页面",
    tone: "info",
  },
  error: {
    icon: CircleAlert,
    title: "暂时无法加载",
    description: "网络或服务暂时不可用，请稍后重试。",
    action: "重新加载",
    tone: "danger",
  },
  forbidden: {
    icon: ShieldX,
    title: "你没有访问权限",
    description: "当前账号不能查看此页面，数据不会被加载。",
    action: "返回工作区",
    tone: "warning",
  },
  "not-found": {
    icon: FileQuestion,
    title: "页面不存在",
    description: "地址可能已变化，或页面已被移除。",
    action: "返回工作区",
    tone: "warning",
  },
} as const;

const content = computed(() => stateContent[props.kind]);
</script>

<template>
  <section
    class="state-card standalone-state-card"
    :aria-live="kind === 'loading' ? 'polite' : undefined"
  >
    <div
      class="state-icon"
      :class="[
        content.tone === 'info' ? undefined : content.tone,
        { spinning: kind === 'loading' },
      ]"
      aria-hidden="true"
    >
      <component :is="content.icon" :size="20" />
    </div>
    <h1>{{ content.title }}</h1>
    <p>{{ content.description }}</p>
    <div v-if="kind === 'loading'" class="loading-line" aria-hidden="true" />
    <RouterLink
      v-else-if="content.action !== undefined && actionTo !== undefined"
      class="state-action state-link"
      :to="actionTo"
    >
      {{ content.action }}
    </RouterLink>
    <button
      v-else-if="content.action !== undefined"
      class="state-action"
      type="button"
      @click="emit('action')"
    >
      {{ content.action }}
    </button>
  </section>
</template>
