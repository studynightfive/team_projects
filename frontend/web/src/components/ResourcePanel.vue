<script setup lang="ts">
import { useId } from "vue";

defineProps<{
  title: string;
  description?: string;
}>();

const titleId = useId();
</script>

<template>
  <section class="resource-panel content-card" :aria-labelledby="titleId">
    <header class="resource-panel-header">
      <div>
        <h2 :id="titleId">{{ title }}</h2>
        <p v-if="description">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="resource-panel-actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="resource-panel-body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="resource-panel-footer">
      <slot name="footer" />
    </footer>
  </section>
</template>
