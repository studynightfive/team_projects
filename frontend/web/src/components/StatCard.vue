<script setup lang="ts">
import type { LucideIcon } from "./icons";
import { ArrowUpRight, CircleAlert } from "./icons";
import Sparkline from "./Sparkline.vue";

defineProps<{
  label: string;
  value: string;
  trend: string;
  tone: "blue" | "green" | "amber" | "violet" | "red";
  icon: LucideIcon;
  admin?: boolean;
  series?: readonly number[];
}>();
</script>

<template>
  <article class="stat-card" :class="[{ admin }, `tone-${tone}`]">
    <div class="stat-icon" aria-hidden="true">
      <component :is="icon" :size="22" :stroke-width="1.8" />
    </div>
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }}</div>
    <div class="stat-trend">
      <component
        :is="tone === 'red' ? CircleAlert : ArrowUpRight"
        :size="14"
        :stroke-width="2"
        aria-hidden="true"
      />
      <span>{{ trend }}</span>
    </div>
    <Sparkline
      v-if="series !== undefined"
      :points="series"
      :tone="tone"
      :label="`${label}最近七天趋势`"
    />
  </article>
</template>
