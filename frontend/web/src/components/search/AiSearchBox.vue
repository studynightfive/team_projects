<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

import { getQuerySafetyMessage } from "../../services/query-safety";
import type {
  KnowledgeBaseOption,
  ModelOption,
  SearchMode,
  SearchRequest,
  SearchSourceType,
} from "../../types/ai-search";
import { Send, X } from "../icons";

const props = withDefaults(
  defineProps<{
    query: string;
    mode: SearchMode;
    sources: readonly SearchSourceType[];
    modelId: string;
    workspaceId?: string;
    modelOptions: readonly ModelOption[];
    knowledgeBaseOptions?: readonly KnowledgeBaseOption[];
    requiresWorkspace?: boolean;
    busy?: boolean;
    disabled?: boolean;
    compact?: boolean;
  }>(),
  {
    busy: false,
    disabled: false,
    compact: false,
    requiresWorkspace: true,
    workspaceId: undefined,
    knowledgeBaseOptions: () => [],
  },
);

const emit = defineEmits<{
  "update:query": [value: string];
  "update:sources": [value: SearchSourceType[]];
  "update:model-id": [value: string];
  "update:workspace-id": [value: string | undefined];
  submit: [request: SearchRequest];
  notice: [message: string];
}>();

const textareaRef = ref<HTMLTextAreaElement>();
const selectedKnowledgeBaseLabel = computed(() => {
  const selected = props.knowledgeBaseOptions.find(
    (item) => item.id === props.workspaceId,
  );
  return selected?.name ?? props.knowledgeBaseOptions[0]?.name ?? "暂无可用知识库";
});
const querySafetyMessage = computed(() => getQuerySafetyMessage(props.query));
const canSubmit = computed(
  () =>
    props.query.trim().length > 0 &&
    querySafetyMessage.value === undefined &&
    props.sources.length > 0 &&
    (!props.requiresWorkspace ||
      (props.workspaceId !== undefined && props.workspaceId !== "")) &&
    !props.busy &&
    !props.disabled,
);

const resizeTextarea = async (): Promise<void> => {
  await nextTick();
  const textarea = textareaRef.value;
  if (textarea === undefined) return;

  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, props.compact ? 132 : 180)}px`;
};

watch(() => props.query, resizeTextarea, { immediate: true });

watch(
  () => props.knowledgeBaseOptions,
  (options) => {
    if (options.length === 0) return;
    const exists = options.some((item) => item.id === props.workspaceId);
    if (!exists) emit("update:workspace-id", options[0]?.id);
  },
  { immediate: true },
);

const updateQuery = (event: Event): void => {
  emit("update:query", (event.target as HTMLTextAreaElement).value);
};

const clearQuery = (): void => {
  emit("update:query", "");
  textareaRef.value?.focus();
};

const submit = (): void => {
  if (querySafetyMessage.value !== undefined) {
    textareaRef.value?.focus();
    return;
  }
  if (!canSubmit.value) {
    if (props.query.trim().length === 0) {
      emit("notice", "请输入要查找的问题");
    } else if (
      props.requiresWorkspace &&
      (props.workspaceId === undefined || props.workspaceId === "")
    ) {
      emit("notice", "请选择要检索的知识库");
    }
    return;
  }

  emit("submit", {
    query: props.query.trim(),
    mode: props.mode,
    sources: [...props.sources],
    workspaceId:
      props.workspaceId !== undefined && props.workspaceId !== ""
        ? props.workspaceId
        : undefined,
    modelId: props.modelId,
  });
};

const handleKeydown = (event: KeyboardEvent): void => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  submit();
};

defineExpose({
  focus: (): void => textareaRef.value?.focus(),
});
</script>

<template>
  <form
    class="ai-search-box"
    :class="{
      compact,
      busy,
      disabled,
      invalid: querySafetyMessage !== undefined,
    }"
    aria-label="企业 AI 搜索"
    @submit.prevent="submit"
  >
    <label class="visually-hidden" for="ai-search-query">输入搜索问题</label>
    <div class="search-editor">
      <textarea
        id="ai-search-query"
        ref="textareaRef"
        :value="query"
        rows="2"
        :disabled="disabled || busy"
        :aria-invalid="querySafetyMessage !== undefined"
        :aria-describedby="
          querySafetyMessage === undefined ? undefined : 'ai-search-query-error'
        "
        placeholder="输入问题，例如：公司最新的差旅报销标准是什么？"
        @input="updateQuery"
        @keydown="handleKeydown"
      />
      <button
        v-if="query.length > 0 && !busy"
        class="search-clear-button"
        type="button"
        aria-label="清空搜索内容"
        title="清空搜索内容"
        @click="clearQuery"
      >
        <X :size="18" aria-hidden="true" />
      </button>
    </div>

    <p
      v-if="querySafetyMessage !== undefined"
      id="ai-search-query-error"
      class="search-input-error"
      role="alert"
    >
      {{ querySafetyMessage }}
    </p>

    <div class="search-toolbar">
      <div class="search-toolbar-options">
        <label
          v-if="knowledgeBaseOptions.length > 0"
          class="search-select-label"
        >
          <span class="visually-hidden">选择知识库</span>
          <select
            :value="workspaceId ?? ''"
            :disabled="disabled || busy"
            :title="`选择知识库：${selectedKnowledgeBaseLabel}`"
            @change="
              emit(
                'update:workspace-id',
                ($event.target as HTMLSelectElement).value || undefined,
              )
            "
          >
            <option
              v-for="knowledgeBase in knowledgeBaseOptions"
              :key="knowledgeBase.id"
              :value="knowledgeBase.id"
            >
              {{ knowledgeBase.name }}（{{
                knowledgeBase.readyDocumentCount
              }}/{{ knowledgeBase.documentCount }}）
            </option>
          </select>
        </label>
        <span v-else class="search-empty-knowledge" aria-live="polite">
          暂无可用知识库
        </span>

        <label class="search-select-label">
          <span class="visually-hidden">选择 AI 模型</span>
          <select
            :value="modelId"
            :disabled="disabled || busy"
            title="选择 AI 模型"
            @change="
              emit(
                'update:model-id',
                ($event.target as HTMLSelectElement).value,
              )
            "
          >
            <option
              v-for="model in modelOptions"
              :key="model.value"
              :value="model.value"
            >
              {{ model.label }}
            </option>
          </select>
        </label>
      </div>

      <button
        class="search-submit-button"
        type="submit"
        :disabled="!canSubmit"
        :aria-label="busy ? '正在检索企业知识' : '发送搜索问题'"
      >
        <span>{{ busy ? "正在检索" : "开始搜索" }}</span>
        <Send :size="17" aria-hidden="true" />
      </button>
    </div>

    <div v-if="busy" class="search-box-meta" aria-live="polite">
      <span>正在检索已选知识库，请稍候</span>
    </div>
  </form>
</template>

<style scoped>
.ai-search-box {
  position: relative;
  display: grid;
  width: 100%;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-16);
  background: var(--color-surface);
  box-shadow: var(--shadow-md);
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.ai-search-box:focus-within {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-focus), var(--shadow-md);
}

.ai-search-box.busy {
  border-color: var(--blue-300);
}

.ai-search-box.invalid {
  border-color: var(--color-danger);
}

.search-mode-list {
  display: flex;
  width: fit-content;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin: 0;
  padding: var(--space-1);
  border: 0;
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.search-mode-list button {
  min-height: 34px;
  padding: 0 var(--space-3);
  border-radius: 6px;
  color: var(--color-text-muted);
  background: transparent;
  font-size: var(--font-size-13);
}

.search-mode-list button.active {
  color: var(--color-primary);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  font-weight: var(--font-weight-medium);
}

.search-editor {
  position: relative;
}

.search-editor textarea {
  display: block;
  width: 100%;
  min-height: 72px;
  max-height: 180px;
  padding: var(--space-2) 40px var(--space-2) var(--space-1);
  resize: none;
  overflow-y: auto;
  border: 0;
  outline: 0;
  color: var(--color-text);
  background: transparent;
  font: inherit;
  font-size: var(--font-size-16);
  line-height: 1.65;
}

.search-editor textarea::placeholder {
  color: var(--color-text-subtle);
}

.search-editor textarea:focus-visible {
  box-shadow: none;
}

.search-input-error {
  margin: calc(var(--space-2) * -1) 0 0;
  color: var(--color-danger-text);
  font-size: var(--font-size-13);
}

.search-clear-button {
  position: absolute;
  top: var(--space-1);
  right: 0;
  display: grid;
  width: 32px;
  height: 32px;
  padding: 0;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: transparent;
}

.attachment-list,
.search-toolbar,
.search-toolbar-options,
.search-box-meta,
.attachment-chip {
  display: flex;
  align-items: center;
}

.attachment-list {
  flex-wrap: wrap;
  gap: var(--space-2);
}

.attachment-chip {
  max-width: 240px;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface-subtle);
  font-size: var(--font-size-12);
}

.attachment-chip > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-chip button {
  display: grid;
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  padding: 0;
  place-items: center;
  border-radius: var(--radius-4);
  color: var(--color-text-muted);
  background: transparent;
}

.search-toolbar {
  justify-content: space-between;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.search-toolbar-options {
  min-width: 0;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.search-tool-button,
.search-select-label select {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  font-size: var(--font-size-13);
}

.search-select-label select {
  appearance: auto;
  min-width: 136px;
}

.search-empty-knowledge {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  font-size: var(--font-size-13);
}

.search-submit-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border-radius: var(--radius-8);
  color: var(--white);
  background: var(--color-primary);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.search-box-meta {
  justify-content: space-between;
  gap: var(--space-3);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.compact .search-mode-list {
  display: none;
}

.compact .search-editor textarea {
  min-height: 52px;
  max-height: 132px;
}

@media (max-width: 767px) {
  .ai-search-box {
    padding: var(--space-3);
    border-radius: var(--radius-12);
  }

  .search-mode-list {
    display: grid;
    width: 100%;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .search-mode-list button,
  .search-tool-button,
  .search-select-label select,
  .search-submit-button {
    min-height: 44px;
  }

  .search-toolbar,
  .search-box-meta {
    align-items: stretch;
    flex-direction: column;
  }

  .search-toolbar-options {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .search-tool-button,
  .search-select-label select,
  .search-select-label,
  .search-empty-knowledge {
    width: 100%;
  }

  .search-submit-button {
    width: 100%;
  }
}
</style>
