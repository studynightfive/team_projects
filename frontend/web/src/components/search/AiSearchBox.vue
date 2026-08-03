<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

import { isRealApiMode } from "../../config/runtime";
import {
  checkQuerySafety,
  classifyUnsafeQuery,
  getQuerySafetyMessage,
  INVALID_QUERY_MESSAGE,
} from "../../services/query-safety";
import type {
  KnowledgeBaseOption,
  ModelOption,
  SearchMode,
  SearchRequest,
  SearchSourceType,
} from "../../types/ai-search";
import { Plus, Send, X } from "../icons";

const props = withDefaults(
  defineProps<{
    query: string;
    mode: SearchMode;
    sources: readonly SearchSourceType[];
    modelId: string;
    workspaceIds?: readonly string[];
    modelOptions: readonly ModelOption[];
    knowledgeBaseOptions?: readonly KnowledgeBaseOption[];
    requiresWorkspace?: boolean;
    busy?: boolean;
    disabled?: boolean;
    compact?: boolean;
    scopeLocked?: boolean;
  }>(),
  {
    busy: false,
    disabled: false,
    compact: false,
    scopeLocked: false,
    requiresWorkspace: true,
    workspaceIds: () => [],
    knowledgeBaseOptions: () => [],
  },
);

const emit = defineEmits<{
  "update:query": [value: string];
  "update:sources": [value: SearchSourceType[]];
  "update:model-id": [value: string];
  "update:workspace-ids": [value: string[]];
  submit: [request: SearchRequest];
  notice: [message: string];
}>();

const textareaRef = ref<HTMLTextAreaElement>();
const knowledgeMenuOpen = ref(false);
const semanticSafetyState = ref<
  "idle" | "checking" | "allowed" | "blocked" | "unavailable"
>("idle");
const semanticSafetyMessage = ref<string>();
const submitSafetyPending = ref(false);
let safetyTimer: ReturnType<typeof setTimeout> | undefined;
let safetyController: AbortController | undefined;
let safetyPromise: Promise<boolean | undefined> | undefined;
let safetyRequestKey: string | undefined;
const selectedKnowledgeBases = computed(() =>
  props.workspaceIds
    .map((id) => props.knowledgeBaseOptions.find((item) => item.id === id))
    .filter((item): item is KnowledgeBaseOption => item !== undefined),
);
const availableKnowledgeBases = computed(() => {
  const selectedIds = new Set(props.workspaceIds);
  return props.knowledgeBaseOptions.filter((item) => !selectedIds.has(item.id));
});
const querySafetyMessage = computed(() =>
  isRealApiMode
    ? semanticSafetyMessage.value
    : getQuerySafetyMessage(props.query),
);
const semanticSafetyChecking = computed(
  () => isRealApiMode && semanticSafetyState.value === "checking",
);
const selectedScopeHasReadyDocument = computed(() =>
  selectedKnowledgeBases.value.some((item) => item.readyDocumentCount > 0),
);
const normalizeKnowledgeBaseName = (name: string): string =>
  name.normalize("NFKC").trim().toLocaleLowerCase("zh-CN").replace(/\s+/gu, " ");
const selectedScopeIsValid = computed(() => {
  if (!props.requiresWorkspace) return true;
  if (
    props.workspaceIds.length < 1 ||
    props.workspaceIds.length > 10 ||
    selectedKnowledgeBases.value.length !== props.workspaceIds.length
  ) {
    return false;
  }
  const names = selectedKnowledgeBases.value.map((item) =>
    normalizeKnowledgeBaseName(item.name),
  );
  return (
    new Set(names).size === names.length &&
    selectedScopeHasReadyDocument.value
  );
});
const baseCanSubmit = computed(
  () =>
    props.query.trim().length > 0 &&
    props.sources.length > 0 &&
    selectedScopeIsValid.value &&
    !props.busy &&
    !props.disabled,
);
const canSubmit = computed(
  () =>
    baseCanSubmit.value &&
    querySafetyMessage.value === undefined &&
    !submitSafetyPending.value,
);

const resizeTextarea = async (): Promise<void> => {
  await nextTick();
  const textarea = textareaRef.value;
  if (textarea === undefined) return;

  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, props.compact ? 132 : 180)}px`;
};

watch(() => props.query, resizeTextarea, { immediate: true });

const runSemanticSafetyCheck = (
  normalized: string,
  modelId: string,
): Promise<boolean | undefined> => {
  const requestKey = `${modelId}\u0000${normalized}`;
  if (safetyPromise !== undefined && safetyRequestKey === requestKey) {
    return safetyPromise;
  }

  safetyController?.abort();
  const controller = new AbortController();
  safetyController = controller;
  safetyRequestKey = requestKey;
  semanticSafetyState.value = "checking";
  semanticSafetyMessage.value = undefined;
  const pending = checkQuerySafety(normalized, modelId, controller.signal)
    .then((result) => {
      if (
        controller.signal.aborted ||
        props.query.trim() !== normalized ||
        props.modelId !== modelId
      ) {
        return undefined;
      }
      semanticSafetyState.value = result.allowed ? "allowed" : "blocked";
      semanticSafetyMessage.value = result.allowed
        ? undefined
        : (result.message ?? INVALID_QUERY_MESSAGE);
      return result.allowed;
    })
    .catch(() => {
      if (!controller.signal.aborted) {
        // 预检网络故障不锁死输入，最终提交仍由后端执行强制校验。
        semanticSafetyState.value = "unavailable";
        semanticSafetyMessage.value = undefined;
      }
      return undefined;
    })
    .finally(() => {
      if (safetyRequestKey === requestKey) {
        safetyPromise = undefined;
        safetyRequestKey = undefined;
      }
    });
  safetyPromise = pending;
  return pending;
};

watch(
  [() => props.query, () => props.modelId],
  ([queryValue, modelId]) => {
    if (safetyTimer !== undefined) clearTimeout(safetyTimer);
    safetyController?.abort();
    safetyPromise = undefined;
    safetyRequestKey = undefined;
    semanticSafetyMessage.value = undefined;

    const normalized = queryValue.trim();
    if (!isRealApiMode || normalized.length === 0) {
      semanticSafetyState.value = "idle";
      return;
    }

    semanticSafetyState.value = "checking";
    // 明显候选词较快送检；普通输入稍长防抖，减少连续打字产生的模型请求。
    const delay = classifyUnsafeQuery(normalized) === undefined ? 650 : 250;
    safetyTimer = setTimeout(() => {
      void runSemanticSafetyCheck(normalized, modelId);
    }, delay);
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (safetyTimer !== undefined) clearTimeout(safetyTimer);
  safetyController?.abort();
});

watch(
  [() => props.knowledgeBaseOptions, () => props.workspaceIds],
  ([options, workspaceIds]) => {
    // 真实列表尚未返回时保留跨页传入的 ID，避免加载过程把用户选择清空。
    if (options.length === 0) return;
    const names = new Set<string>();
    const validIds: string[] = [];
    for (const id of workspaceIds) {
      const option = options.find((item) => item.id === id);
      if (option === undefined) continue;
      const normalizedName = normalizeKnowledgeBaseName(option.name);
      if (names.has(normalizedName)) continue;
      names.add(normalizedName);
      validIds.push(id);
      if (validIds.length === 10) break;
    }
    const defaultOption =
      options.find((item) => item.readyDocumentCount > 0) ?? options[0];
    const nextIds =
      validIds.length === 0 && defaultOption !== undefined
        ? [defaultOption.id]
        : validIds;
    if (
      nextIds.length !== workspaceIds.length ||
      nextIds.some((id, index) => id !== workspaceIds[index])
    ) {
      emit("update:workspace-ids", nextIds);
    }
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

const addKnowledgeBase = (knowledgeBase: KnowledgeBaseOption): void => {
  if (props.workspaceIds.length >= 10) {
    emit("notice", "一次最多选择 10 个知识库");
    return;
  }
  const normalizedName = normalizeKnowledgeBaseName(knowledgeBase.name);
  if (
    selectedKnowledgeBases.value.some(
      (item) => normalizeKnowledgeBaseName(item.name) === normalizedName,
    )
  ) {
    emit("notice", "不能同时选择同名知识库");
    return;
  }
  emit("update:workspace-ids", [...props.workspaceIds, knowledgeBase.id]);
  knowledgeMenuOpen.value = false;
};

const removeKnowledgeBase = (knowledgeBaseId: string): void => {
  if (props.workspaceIds.length <= 1) {
    emit("notice", "至少保留一个知识库");
    return;
  }
  emit(
    "update:workspace-ids",
    props.workspaceIds.filter((id) => id !== knowledgeBaseId),
  );
};

const submit = async (): Promise<void> => {
  if (querySafetyMessage.value !== undefined) {
    textareaRef.value?.focus();
    return;
  }
  if (!baseCanSubmit.value || submitSafetyPending.value) {
    if (props.query.trim().length === 0) {
      emit("notice", "请输入要查找的问题");
    } else if (props.requiresWorkspace && props.workspaceIds.length === 0) {
      emit("notice", "请选择要检索的知识库");
    } else if (!selectedScopeIsValid.value) {
      emit(
        "notice",
        selectedKnowledgeBases.value.every(
          (item) => item.readyDocumentCount === 0,
        )
          ? "所选知识库暂无已处理文档，请更换知识库后再检索"
          : "知识库范围无效，请移除同名或失效的知识库",
      );
    }
    return;
  }

  const normalizedQuery = props.query.trim();
  const selectedModelId = props.modelId;
  if (isRealApiMode && semanticSafetyState.value !== "allowed") {
    if (safetyTimer !== undefined) clearTimeout(safetyTimer);
    submitSafetyPending.value = true;
    const allowed = await runSemanticSafetyCheck(
      normalizedQuery,
      selectedModelId,
    );
    submitSafetyPending.value = false;
    if (
      allowed === false ||
      props.query.trim() !== normalizedQuery ||
      props.modelId !== selectedModelId
    ) {
      textareaRef.value?.focus();
      return;
    }
  }
  if (querySafetyMessage.value !== undefined) return;

  emit("submit", {
    query: normalizedQuery,
    mode: props.mode,
    sources: [...props.sources],
    workspaceIds:
      props.workspaceIds.length > 0 ? [...props.workspaceIds] : undefined,
    modelId: props.modelId,
  });
};

const handleKeydown = (event: KeyboardEvent): void => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  void submit();
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
    <p
      v-else-if="semanticSafetyChecking"
      class="search-input-checking"
      role="status"
    >
      正在进行语义安全检查…
    </p>
    <p
      v-else-if="
        requiresWorkspace &&
          selectedKnowledgeBases.length > 0 &&
          !selectedScopeHasReadyDocument
      "
      class="search-scope-warning"
      role="status"
    >
      所选知识库暂无已处理文档，请更换知识库后再检索。
    </p>

    <div class="search-toolbar">
      <div class="search-toolbar-options">
        <div
          v-if="knowledgeBaseOptions.length > 0"
          class="knowledge-base-selector"
        >
          <div class="selected-knowledge-list" aria-label="已选知识库">
            <span
              v-for="knowledgeBase in selectedKnowledgeBases"
              :key="knowledgeBase.id"
              class="selected-knowledge-chip"
            >
              <span>{{ knowledgeBase.name }}</span>
              <button
                type="button"
                :title="`移除 ${knowledgeBase.name}`"
                :aria-label="`移除 ${knowledgeBase.name}`"
                :disabled="disabled || busy || workspaceIds.length <= 1"
                :hidden="scopeLocked"
                @click="removeKnowledgeBase(knowledgeBase.id)"
              >
                <X :size="13" aria-hidden="true" />
              </button>
            </span>
          </div>
          <div class="knowledge-add-wrap">
            <button
              class="knowledge-add-button"
              type="button"
              title="添加知识库"
              aria-label="添加知识库"
              :aria-expanded="knowledgeMenuOpen"
              :disabled="
                disabled ||
                  busy ||
                  scopeLocked ||
                  availableKnowledgeBases.length === 0 ||
                  workspaceIds.length >= 10
              "
              @click="knowledgeMenuOpen = !knowledgeMenuOpen"
            >
              <Plus :size="16" aria-hidden="true" />
            </button>
            <div
              v-if="knowledgeMenuOpen"
              class="knowledge-add-menu"
              role="menu"
            >
              <button
                v-for="knowledgeBase in availableKnowledgeBases"
                :key="knowledgeBase.id"
                type="button"
                role="menuitem"
                @click="addKnowledgeBase(knowledgeBase)"
              >
                <span>{{ knowledgeBase.name }}</span>
                <small>
                  {{ knowledgeBase.readyDocumentCount }}/{{
                    knowledgeBase.documentCount
                  }}
                  个文档
                </small>
              </button>
            </div>
          </div>
        </div>
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
        :aria-label="
          submitSafetyPending
            ? '正在检查输入内容'
            : busy
              ? '正在检索企业知识'
              : '发送搜索问题'
        "
      >
        <span>
          {{ submitSafetyPending ? "检查中" : busy ? "正在检索" : "开始搜索" }}
        </span>
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

.search-input-checking {
  margin: calc(var(--space-2) * -1) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
}

.search-scope-warning {
  margin: calc(var(--space-2) * -1) 0 0;
  color: var(--color-warning-text);
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

.knowledge-base-selector,
.selected-knowledge-list,
.selected-knowledge-chip {
  display: flex;
  align-items: center;
}

.knowledge-base-selector {
  min-width: 0;
  gap: var(--space-1);
}

.selected-knowledge-list {
  min-width: 0;
  max-width: min(52vw, 520px);
  flex-wrap: wrap;
  gap: var(--space-1);
}

.selected-knowledge-chip {
  max-width: 190px;
  min-height: 36px;
  gap: var(--space-1);
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  font-size: var(--font-size-13);
}

.selected-knowledge-chip > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-knowledge-chip button,
.knowledge-add-button {
  display: grid;
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  padding: 0;
  place-items: center;
  border-radius: var(--radius-4);
  color: var(--color-text-muted);
  background: transparent;
}

.knowledge-add-wrap {
  position: relative;
}

.knowledge-add-button {
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-surface);
}

.knowledge-add-menu {
  position: absolute;
  bottom: calc(100% + var(--space-2));
  left: 0;
  z-index: 12;
  display: grid;
  width: min(320px, calc(100vw - 32px));
  max-height: 240px;
  padding: var(--space-1);
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
  box-shadow: var(--shadow-lg);
}

.knowledge-add-menu button {
  display: grid;
  min-height: 44px;
  gap: 2px;
  padding: var(--space-2);
  border-radius: var(--radius-4);
  color: var(--color-text);
  background: transparent;
  text-align: left;
}

.knowledge-add-menu button:hover,
.knowledge-add-menu button:focus-visible {
  background: var(--color-surface-subtle);
}

.knowledge-add-menu small {
  color: var(--color-text-muted);
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
    grid-template-columns: minmax(0, 1fr);
  }

  .knowledge-base-selector,
  .selected-knowledge-list {
    width: 100%;
  }

  .selected-knowledge-list {
    max-width: none;
  }

  .knowledge-add-menu {
    right: 0;
    left: auto;
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
