<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import {
  getDocumentTask,
  type DocumentBatchTaskItem,
  type DocumentTaskRecord,
} from "../../services/knowledge";
import { CheckCircle2, CircleAlert, LoaderCircle } from "../icons";

const props = defineProps<{
  readonly items: readonly DocumentBatchTaskItem[];
}>();

const emit = defineEmits<{
  finished: [];
}>();

const terminalStatuses = new Set([
  "succeeded",
  "failed",
  "cancelled",
  "manual_review",
]);
const tasks = ref<Readonly<Record<string, DocumentTaskRecord>>>({});
const pollError = ref("");
let timer: ReturnType<typeof setTimeout> | undefined;
let controller: AbortController | undefined;

const rows = computed(() =>
  props.items.map((item) => ({
    ...item,
    task: tasks.value[item.task.task_id] ?? item.task,
  })),
);
const overallProgress = computed(() => {
  if (rows.value.length === 0) return 0;
  return Math.round(
    rows.value.reduce((total, item) => total + item.task.progress, 0) /
      rows.value.length,
  );
});
const completedCount = computed(
  () =>
    rows.value.filter((item) => terminalStatuses.has(item.task.status)).length,
);

const stopPolling = (): void => {
  if (timer !== undefined) clearTimeout(timer);
  timer = undefined;
  controller?.abort();
  controller = undefined;
};

const poll = async (): Promise<void> => {
  const pending = rows.value.filter(
    (item) => !terminalStatuses.has(item.task.status),
  );
  if (pending.length === 0) {
    stopPolling();
    emit("finished");
    return;
  }

  controller?.abort();
  controller = new AbortController();
  try {
    const updates = await Promise.all(
      pending.map((item) =>
        getDocumentTask(item.task.task_id, controller?.signal),
      ),
    );
    tasks.value = {
      ...tasks.value,
      ...Object.fromEntries(updates.map((task) => [task.task_id, task])),
    };
    pollError.value = "";
  } catch (error: unknown) {
    if (!(error instanceof DOMException && error.name === "AbortError")) {
      pollError.value = "进度刷新暂时失败，系统会自动重试。";
    }
  }
  timer = setTimeout(() => void poll(), 1000);
};

watch(
  () => props.items,
  (items) => {
    stopPolling();
    tasks.value = Object.fromEntries(
      items.map((item) => [item.task.task_id, item.task]),
    );
    if (items.length > 0) void poll();
  },
  { immediate: true },
);

onBeforeUnmount(stopPolling);
</script>

<template>
  <section class="task-progress-panel" aria-live="polite">
    <header>
      <div>
        <strong>重新处理进度</strong>
        <span>{{ completedCount }} / {{ rows.length }} 已完成</span>
      </div>
      <b>{{ overallProgress }}%</b>
    </header>
    <progress :value="overallProgress" max="100">
      {{ overallProgress }}%
    </progress>
    <ul>
      <li v-for="item in rows" :key="item.task.task_id">
        <component
          :is="
            item.task.status === 'succeeded'
              ? CheckCircle2
              : ['failed', 'manual_review', 'cancelled'].includes(
                item.task.status,
              )
                ? CircleAlert
                : LoaderCircle
          "
          :size="17"
          :class="{ spinning: !terminalStatuses.has(item.task.status) }"
          aria-hidden="true"
        />
        <div>
          <strong>{{ item.document_title }}</strong>
          <span>{{ item.task.stage }} · {{ Math.round(item.task.progress) }}%</span>
        </div>
        <progress :value="item.task.progress" max="100">
          {{ item.task.progress }}%
        </progress>
      </li>
    </ul>
    <p v-if="pollError">{{ pollError }}</p>
  </section>
</template>

<style scoped>
.task-progress-panel {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.task-progress-panel header,
.task-progress-panel header > div,
.task-progress-panel li {
  display: flex;
  align-items: center;
}

.task-progress-panel header {
  justify-content: space-between;
}

.task-progress-panel header > div {
  gap: var(--space-2);
}

.task-progress-panel header span,
.task-progress-panel li span,
.task-progress-panel p {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.task-progress-panel progress {
  width: 100%;
  accent-color: var(--color-primary);
}

.task-progress-panel ul {
  display: grid;
  max-height: 260px;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.task-progress-panel li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) minmax(80px, 140px);
  gap: var(--space-2);
}

.task-progress-panel li > div {
  display: grid;
  min-width: 0;
}

.task-progress-panel li strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-progress-panel p {
  margin: 0;
}

.spinning {
  animation: task-spin 1s linear infinite;
}

@keyframes task-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 767px) {
  .task-progress-panel header > div {
    align-items: flex-start;
    flex-direction: column;
  }

  .task-progress-panel li {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .task-progress-panel li progress {
    grid-column: 2;
  }
}
</style>
