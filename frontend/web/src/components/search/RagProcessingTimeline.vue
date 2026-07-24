<script setup lang="ts">
import type { RagProcessingStage } from "../../types/ai-search";
import { CheckCircle2, LoaderCircle } from "../icons";

defineProps<{
  stages: readonly RagProcessingStage[];
  busy: boolean;
}>();
</script>

<template>
  <section
    v-if="stages.length > 0"
    class="rag-processing-timeline"
    :aria-busy="busy"
    aria-labelledby="rag-processing-title"
  >
    <header>
      <div>
        <span>RAG PROCESS</span>
        <h2 id="rag-processing-title">回答处理过程</h2>
      </div>
      <small>{{ busy ? "正在处理" : "处理完成" }}</small>
    </header>
    <ol>
      <li
        v-for="stage in stages"
        :key="stage.id"
        :class="{ running: stage.status === 'running' }"
      >
        <component
          :is="stage.status === 'running' ? LoaderCircle : CheckCircle2"
          :size="18"
          aria-hidden="true"
        />
        <div>
          <strong>{{ stage.label }}</strong>
          <p>{{ stage.detail }}</p>
        </div>
        <time>{{ stage.elapsedMs }}ms</time>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.rag-processing-timeline {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.rag-processing-timeline header,
.rag-processing-timeline li {
  display: flex;
  align-items: center;
}

.rag-processing-timeline header {
  justify-content: space-between;
  gap: var(--space-3);
}

.rag-processing-timeline header span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.rag-processing-timeline h2 {
  margin: var(--space-1) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-16);
}

.rag-processing-timeline small {
  color: var(--color-text-muted);
}

.rag-processing-timeline ol {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.rag-processing-timeline li {
  min-width: 0;
  gap: var(--space-3);
  color: var(--color-success);
}

.rag-processing-timeline li.running {
  color: var(--color-primary);
}

.rag-processing-timeline li.running > svg {
  animation: rag-stage-spin 1s linear infinite;
}

.rag-processing-timeline li > div {
  min-width: 0;
  flex: 1;
}

.rag-processing-timeline strong {
  color: var(--color-text);
  font-size: var(--font-size-13);
}

.rag-processing-timeline p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.rag-processing-timeline time {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

@keyframes rag-stage-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 767px) {
  .rag-processing-timeline li {
    align-items: flex-start;
  }

  .rag-processing-timeline time {
    display: none;
  }
}
</style>
