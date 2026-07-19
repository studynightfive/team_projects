<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

import type {
  KnowledgeBaseOption,
  ModelOption,
  SearchMode,
  SearchModeOption,
  SearchRequest,
  SearchSourceType,
} from "../../types/ai-search";
import { FileText, Paperclip, Send, X } from "../icons";

const props = withDefaults(
  defineProps<{
    query: string;
    mode: SearchMode;
    sources: readonly SearchSourceType[];
    modelId: string;
    workspaceId?: string;
    modeOptions: readonly SearchModeOption[];
    modelOptions: readonly ModelOption[];
    knowledgeBaseOptions?: readonly KnowledgeBaseOption[];
    busy?: boolean;
    disabled?: boolean;
    compact?: boolean;
  }>(),
  {
    busy: false,
    disabled: false,
    compact: false,
    workspaceId: undefined,
    knowledgeBaseOptions: () => [],
  },
);

const emit = defineEmits<{
  "update:query": [value: string];
  "update:mode": [value: SearchMode];
  "update:sources": [value: SearchSourceType[]];
  "update:model-id": [value: string];
  "update:workspace-id": [value: string | undefined];
  "attachments-change": [names: string[]];
  submit: [request: SearchRequest];
  notice: [message: string];
}>();

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const MAX_FILE_COUNT = 5;
const ALLOWED_FILE_EXTENSIONS = [
  ".pdf",
  ".doc",
  ".docx",
  ".txt",
  ".md",
  ".xls",
  ".xlsx",
] as const;

const textareaRef = ref<HTMLTextAreaElement>();
const fileInputRef = ref<HTMLInputElement>();
const attachments = ref<File[]>([]);

const activeMode = computed(
  () =>
    props.modeOptions.find((option) => option.value === props.mode) ??
    props.modeOptions[0],
);
const selectedKnowledgeBaseLabel = computed(() => {
  const selected = props.knowledgeBaseOptions.find(
    (item) => item.id === props.workspaceId,
  );
  return selected?.name ?? props.knowledgeBaseOptions[0]?.name ?? "暂无可用知识库";
});
const canSubmit = computed(
  () =>
    props.query.trim().length > 0 &&
    props.sources.length > 0 &&
    props.workspaceId !== undefined &&
    props.workspaceId !== "" &&
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
  if (!canSubmit.value) {
    if (props.query.trim().length === 0) emit("notice", "请输入要查找的问题");
    else if (props.workspaceId === undefined || props.workspaceId === "") {
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
    attachmentIds: attachments.value.map((file) => file.name),
    modelId: props.modelId,
  });
};

const handleKeydown = (event: KeyboardEvent): void => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  submit();
};

const openFilePicker = (): void => {
  if (!props.disabled && !props.busy) fileInputRef.value?.click();
};

const emitAttachmentNames = (): void => {
  emit(
    "attachments-change",
    attachments.value.map((file) => file.name),
  );
};

const addAttachments = (event: Event): void => {
  const input = event.target as HTMLInputElement;
  const selectedFiles = Array.from(input.files ?? []);
  input.value = "";

  const availableSlots = MAX_FILE_COUNT - attachments.value.length;
  if (availableSlots <= 0) {
    emit("notice", `最多添加 ${MAX_FILE_COUNT} 个附件`);
    return;
  }

  const acceptedFiles = selectedFiles
    .slice(0, availableSlots)
    .filter((file) => {
      const normalizedName = file.name.toLocaleLowerCase("zh-CN");
      const extensionAllowed = ALLOWED_FILE_EXTENSIONS.some((extension) =>
        normalizedName.endsWith(extension),
      );
      if (!extensionAllowed) {
        emit("notice", `${file.name} 的格式不受支持`);
        return false;
      }
      if (file.size > MAX_FILE_SIZE) {
        emit("notice", `${file.name} 超过 10 MB 限制`);
        return false;
      }
      return true;
    });

  attachments.value = [...attachments.value, ...acceptedFiles];
  emitAttachmentNames();
};

const removeAttachment = (name: string): void => {
  attachments.value = attachments.value.filter((file) => file.name !== name);
  emitAttachmentNames();
};

defineExpose({
  focus: (): void => textareaRef.value?.focus(),
  openFilePicker,
});
</script>

<template>
  <form
    class="ai-search-box"
    :class="{ compact, busy, disabled }"
    aria-label="企业 AI 搜索"
    @submit.prevent="submit"
  >
    <fieldset class="search-mode-list">
      <legend class="visually-hidden">搜索模式</legend>
      <button
        v-for="option in modeOptions"
        :key="option.value"
        type="button"
        :class="{ active: mode === option.value }"
        :aria-pressed="mode === option.value"
        :title="option.description"
        :disabled="disabled || busy"
        @click="emit('update:mode', option.value)"
      >
        {{ option.label }}
      </button>
    </fieldset>

    <label class="visually-hidden" for="ai-search-query">输入搜索问题</label>
    <div class="search-editor">
      <textarea
        id="ai-search-query"
        ref="textareaRef"
        :value="query"
        rows="2"
        :disabled="disabled || busy"
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

    <div
      v-if="attachments.length > 0"
      class="attachment-list"
      aria-label="已添加附件"
    >
      <span
        v-for="file in attachments"
        :key="file.name"
        class="attachment-chip"
      >
        <FileText :size="15" aria-hidden="true" />
        <span :title="file.name">{{ file.name }}</span>
        <button
          type="button"
          :aria-label="`移除附件 ${file.name}`"
          @click="removeAttachment(file.name)"
        >
          <X :size="14" aria-hidden="true" />
        </button>
      </span>
    </div>

    <div class="search-toolbar">
      <div class="search-toolbar-options">
        <input
          ref="fileInputRef"
          class="visually-hidden"
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.txt,.md,.xls,.xlsx"
          @change="addAttachments"
        />
        <button
          class="search-tool-button"
          type="button"
          title="添加附件，最多 5 个且单个不超过 10 MB"
          :disabled="disabled || busy"
          @click="openFilePicker"
        >
          <Paperclip :size="17" aria-hidden="true" />
          添加附件
        </button>

        <label v-if="compact" class="search-select-label">
          <span class="visually-hidden">选择搜索模式</span>
          <select
            :value="mode"
            :disabled="disabled || busy"
            title="选择搜索模式"
            @change="
              emit(
                'update:mode',
                ($event.target as HTMLSelectElement).value as SearchMode,
              )
            "
          >
            <option
              v-for="option in modeOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>

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

    <div class="search-box-meta">
      <span>{{ activeMode?.description }}</span>
      <span aria-live="polite">{{
        busy ? "正在检索已选知识库，请稍候" : "Enter 发送，Shift + Enter 换行"
      }}</span>
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
