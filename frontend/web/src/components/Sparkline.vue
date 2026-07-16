<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  points: readonly number[];
  tone: "blue" | "green" | "amber" | "violet" | "red";
  label: string;
}>();

const width = 240;
const height = 40;
const padding = 4;

const coordinates = computed(() => {
  const minimum = Math.min(...props.points);
  const maximum = Math.max(...props.points);
  const range = Math.max(maximum - minimum, 1);
  const step = (width - padding * 2) / Math.max(props.points.length - 1, 1);

  return props.points.map((point, index) => ({
    x: padding + index * step,
    y: height - padding - ((point - minimum) / range) * (height - padding * 2),
  }));
});

const path = computed(() => {
  const [first, ...rest] = coordinates.value;
  if (first === undefined) return "";

  return rest.reduce((value, point, index) => {
    const previous = coordinates.value[index];
    if (previous === undefined) return value;
    const midpoint = (previous.x + point.x) / 2;
    return `${value} C ${midpoint} ${previous.y}, ${midpoint} ${point.y}, ${point.x} ${point.y}`;
  }, `M ${first.x} ${first.y}`);
});
</script>

<template>
  <svg
    class="sparkline"
    :class="`tone-${tone}`"
    viewBox="0 0 240 40"
    role="img"
    :aria-label="label"
    preserveAspectRatio="none"
  >
    <path class="sparkline-path" :d="path" />
    <circle
      v-for="(point, index) in coordinates"
      :key="index"
      class="sparkline-point"
      :cx="point.x"
      :cy="point.y"
      r="1.8"
    />
  </svg>
</template>
