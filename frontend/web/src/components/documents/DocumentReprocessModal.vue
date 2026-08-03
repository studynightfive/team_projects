<script setup lang="ts">
import { Modal as AntModal } from "ant-design-vue";
import { computed, ref, watch } from "vue";

import type {
  ChunkStrategy,
  DocumentReprocessOptions,
} from "../../services/knowledge";

const props = withDefaults(
  defineProps<{
    open: boolean;
    documentCount: number;
    submitting?: boolean;
    initialStrategy?: ChunkStrategy;
    initialChunkSize?: number;
    initialChunkOverlap?: number;
  }>(),
  {
    submitting: false,
    initialStrategy: "recursive",
    initialChunkSize: 800,
    initialChunkOverlap: 120,
  },
);

const emit = defineEmits<{
  "update:open": [value: boolean];
  submit: [options: DocumentReprocessOptions];
}>();

const chunkStrategy = ref<ChunkStrategy>(props.initialStrategy);
const chunkSize = ref(props.initialChunkSize);
const chunkOverlap = ref(props.initialChunkOverlap);
const validationMessage = computed(() => {
  if (chunkSize.value < 200 || chunkSize.value > 4000) {
    return "切分大小必须在 200 到 4000 之间";
  }
  if (chunkOverlap.value < 0 || chunkOverlap.value > 1000) {
    return "重叠字符必须在 0 到 1000 之间";
  }
  if (chunkOverlap.value >= chunkSize.value) {
    return "重叠字符必须小于切分大小";
  }
  return undefined;
});

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    chunkStrategy.value = props.initialStrategy;
    chunkSize.value = props.initialChunkSize;
    chunkOverlap.value = props.initialChunkOverlap;
  },
);

const submit = (): void => {
  if (validationMessage.value !== undefined) return;
  emit("submit", {
    chunkStrategy: chunkStrategy.value,
    chunkSize: chunkSize.value,
    chunkOverlap: chunkOverlap.value,
  });
};
</script>

<template>
  <AntModal
    :open="open"
    title="重新处理文档"
    ok-text="开始重新处理"
    cancel-text="取消"
    :confirm-loading="submitting"
    :closable="!submitting"
    :mask-closable="!submitting"
    :cancel-button-props="{ disabled: submitting }"
    :ok-button-props="{ disabled: validationMessage !== undefined }"
    centered
    @update:open="emit('update:open', $event)"
    @ok="submit"
  >
    <div class="reprocess-form">
      <p>
        将对 {{ documentCount }} 个文档重新生成 Markdown、分块和向量索引。任务完成前不会混用新旧向量。
      </p>
      <label>
        <span>切分方法</span>
        <select v-model="chunkStrategy" :disabled="submitting">
          <option value="fixed">固定长度</option>
          <option value="semantic">语义</option>
          <option value="recursive">递归</option>
          <option value="format">格式</option>
        </select>
      </label>
      <div class="reprocess-number-grid">
        <label>
          <span>切分大小</span>
          <input
            v-model.number="chunkSize"
            type="number"
            min="200"
            max="4000"
            :disabled="submitting"
          />
        </label>
        <label>
          <span>重叠字符</span>
          <input
            v-model.number="chunkOverlap"
            type="number"
            min="0"
            max="1000"
            :disabled="submitting"
          />
        </label>
      </div>
      <p v-if="validationMessage" class="reprocess-error" role="alert">
        {{ validationMessage }}
      </p>
    </div>
  </AntModal>
</template>

<style scoped>
.reprocess-form {
  display: grid;
  gap: var(--space-4);
}

.reprocess-form > p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.reprocess-form label {
  display: grid;
  gap: var(--space-2);
  color: var(--color-text);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-medium);
}

.reprocess-form select,
.reprocess-form input {
  width: 100%;
  min-width: 0;
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-6);
  background: var(--color-surface);
}

.reprocess-number-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.reprocess-form .reprocess-error {
  color: var(--color-danger-text);
  font-size: var(--font-size-13);
}

@media (max-width: 575px) {
  .reprocess-number-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
