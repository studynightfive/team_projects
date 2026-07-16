<script setup lang="ts">
import { computed } from "vue";

import { CircleAlert, Inbox, LoaderCircle, TriangleAlert } from "./icons";

const props = defineProps<{
  kind: "loading" | "empty" | "error" | "info";
  title: string;
  description: string;
}>();

const stateIcon = computed(
  () =>
    ({
      loading: LoaderCircle,
      empty: Inbox,
      error: TriangleAlert,
      info: CircleAlert,
    })[props.kind],
);
</script>

<template>
  <div
    class="inline-state"
    :class="`kind-${kind}`"
    :role="kind === 'error' ? 'alert' : 'status'"
  >
    <component
      :is="stateIcon"
      :size="22"
      :class="{ spinning: kind === 'loading' }"
      aria-hidden="true"
    />
    <div>
      <strong>{{ title }}</strong>
      <p>{{ description }}</p>
    </div>
  </div>
</template>
