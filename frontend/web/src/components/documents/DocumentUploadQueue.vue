<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { FileUp, Trash2, X } from "../icons";

const props = withDefaults(
  defineProps<{
    readonly uploading?: boolean;
    readonly maxFiles?: number;
    readonly resetToken?: number;
  }>(),
  {
    uploading: false,
    maxFiles: 20,
    resetToken: 0,
  },
);

const emit = defineEmits<{
  submit: [files: readonly File[]];
}>();

const inputRef = ref<HTMLInputElement>();
const queuedFiles = ref<readonly File[]>([]);
const dragging = ref(false);
const notice = ref("");
const canSubmit = computed(
  () => queuedFiles.value.length > 0 && !props.uploading,
);

const fileKey = (file: File): string =>
  `${file.name}:${file.size}:${file.lastModified}`;

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const appendFiles = (files: readonly File[]): void => {
  const existing = new Set(queuedFiles.value.map(fileKey));
  const additions = files.filter((file) => !existing.has(fileKey(file)));
  const next = [...queuedFiles.value, ...additions].slice(0, props.maxFiles);
  queuedFiles.value = next;

  if (next.length >= props.maxFiles && files.length > additions.length) {
    notice.value = `单次最多选择 ${props.maxFiles} 个文件，重复或超出部分未加入。`;
  } else if (additions.length < files.length) {
    notice.value = "重复文件已自动忽略。";
  } else {
    notice.value = "";
  }
};

const handleInput = (event: Event): void => {
  const input = event.target as HTMLInputElement;
  appendFiles(Array.from(input.files ?? []));
  input.value = "";
};

const handleDrop = (event: DragEvent): void => {
  dragging.value = false;
  appendFiles(Array.from(event.dataTransfer?.files ?? []));
};

const removeFile = (file: File): void => {
  const key = fileKey(file);
  queuedFiles.value = queuedFiles.value.filter(
    (candidate) => fileKey(candidate) !== key,
  );
};

const clearQueue = (): void => {
  queuedFiles.value = [];
  notice.value = "";
};

watch(
  () => props.resetToken,
  () => clearQueue(),
);
</script>

<template>
  <div class="document-upload-queue">
    <button
      class="upload-drop-zone"
      :class="{ dragging }"
      type="button"
      :disabled="uploading"
      @click="inputRef?.click()"
      @dragenter.prevent="dragging = true"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="handleDrop"
    >
      <FileUp :size="30" aria-hidden="true" />
      <strong>点击或拖拽文件加入上传队列</strong>
      <span>可连续添加文件，确认前不会上传</span>
    </button>
    <input
      ref="inputRef"
      class="visually-hidden"
      type="file"
      multiple
      accept=".pdf,.doc,.docx,.md,.markdown,.txt,.csv,.xlsx,.pptx,.html,.json,.jpg,.jpeg,.png,.webp"
      @change="handleInput"
    />

    <div v-if="queuedFiles.length > 0" class="queue-heading">
      <div>
        <strong>待上传文档</strong>
        <span>{{ queuedFiles.length }} / {{ maxFiles }}</span>
      </div>
      <button
        class="icon-button"
        type="button"
        title="清空上传队列"
        :disabled="uploading"
        @click="clearQueue"
      >
        <Trash2 :size="17" aria-hidden="true" />
        <span class="visually-hidden">清空上传队列</span>
      </button>
    </div>

    <ul v-if="queuedFiles.length > 0" class="queued-file-list">
      <li v-for="file in queuedFiles" :key="fileKey(file)">
        <div>
          <strong>{{ file.name }}</strong>
          <span>{{ formatBytes(file.size) }}</span>
        </div>
        <button
          class="icon-button"
          type="button"
          :title="`移除 ${file.name}`"
          :disabled="uploading"
          @click="removeFile(file)"
        >
          <X :size="16" aria-hidden="true" />
          <span class="visually-hidden">移除 {{ file.name }}</span>
        </button>
      </li>
    </ul>

    <p v-if="notice" class="queue-notice">{{ notice }}</p>

    <div class="queue-actions">
      <span>统一使用当前切分与 OCR 配置</span>
      <button
        class="primary-button"
        type="button"
        :disabled="!canSubmit"
        @click="emit('submit', queuedFiles)"
      >
        <FileUp :size="17" aria-hidden="true" />
        {{ uploading ? "正在上传" : `确认上传（${queuedFiles.length}）` }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.document-upload-queue {
  display: grid;
  gap: var(--space-3);
}

.upload-drop-zone {
  display: grid;
  min-height: 138px;
  place-items: center;
  align-content: center;
  gap: var(--space-2);
  padding: var(--space-4);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  cursor: pointer;
  text-align: center;
}

.upload-drop-zone:hover,
.upload-drop-zone:focus-visible,
.upload-drop-zone.dragging {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.upload-drop-zone:disabled {
  cursor: progress;
  opacity: 0.68;
}

.queue-heading,
.queue-heading > div,
.queue-actions,
.queued-file-list li,
.queued-file-list li > div {
  display: flex;
  align-items: center;
}

.queue-heading,
.queue-actions,
.queued-file-list li {
  justify-content: space-between;
  gap: var(--space-3);
}

.queue-heading > div,
.queued-file-list li > div {
  min-width: 0;
  gap: var(--space-2);
}

.queue-heading span,
.queued-file-list span,
.queue-actions > span,
.queue-notice {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.queued-file-list {
  display: grid;
  max-height: 260px;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.queued-file-list li {
  min-height: 44px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.queued-file-list strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-notice {
  margin: 0;
}

.queue-actions {
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

@media (max-width: 767px) {
  .queue-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .queue-actions .primary-button {
    width: 100%;
  }
}
</style>
