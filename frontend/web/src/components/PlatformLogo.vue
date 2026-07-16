<script setup lang="ts">
import { BookOpenText } from "./icons";

withDefaults(
  defineProps<{
    compact?: boolean;
    inverse?: boolean;
    name?: string;
  }>(),
  {
    compact: false,
    inverse: false,
    name: "智能知识库平台",
  },
);
</script>

<template>
  <div class="platform-logo" :class="{ compact, inverse }">
    <span class="platform-logo-mark" aria-hidden="true">
      <BookOpenText :size="20" :stroke-width="1.8" />
    </span>
    <span v-if="!compact" class="platform-logo-name">{{ name }}</span>
  </div>
</template>
