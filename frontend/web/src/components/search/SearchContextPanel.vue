<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import type {
  CitationSource,
  KnowledgeBaseOption,
} from "../../types/ai-search";
import { BookOpen, FileText, Settings2, X } from "../icons";

const props = defineProps<{
  open: boolean;
  query: string;
  selectedKnowledgeBase?: KnowledgeBaseOption;
  knowledgeBaseOptions: readonly KnowledgeBaseOption[];
  modelLabel: string;
  citations: readonly CitationSource[];
  returnFocusTo?: HTMLElement;
}>();

const totalDocumentCount = computed(() =>
  props.knowledgeBaseOptions.reduce(
    (sum, item) => sum + item.documentCount,
    0,
  ),
);
const totalReadyDocumentCount = computed(() =>
  props.knowledgeBaseOptions.reduce(
    (sum, item) => sum + item.readyDocumentCount,
    0,
  ),
);
const uniqueCitations = computed(() => {
  const seenDocuments = new Set<string>();

  return props.citations.filter((citation) => {
    const documentId = citation.documentId?.trim();
    const key =
      documentId === undefined || documentId === ""
        ? `${citation.sourceName.trim()}::${citation.title.trim()}`
        : documentId;
    if (seenDocuments.has(key)) return false;

    seenDocuments.add(key);
    return true;
  });
});

const emit = defineEmits<{
  close: [];
  preview: [citation: CitationSource, trigger: HTMLElement];
}>();

const panelRef = ref<HTMLElement>();
const closeButtonRef = ref<HTMLButtonElement>();
const isOverlay = ref(
  typeof window !== "undefined" && window.innerWidth < 1440,
);
let previousFocus: HTMLElement | undefined;

const syncOverlay = (): void => {
  isOverlay.value = window.innerWidth < 1440;
};

const getFocusableElements = (): HTMLElement[] => {
  if (panelRef.value === undefined) return [];
  return Array.from(
    panelRef.value.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );
};

const handleGlobalKeydown = (event: KeyboardEvent): void => {
  if (!props.open || event.defaultPrevented) return;
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
    return;
  }
  if (!isOverlay.value || event.key !== "Tab") return;

  const activeModal =
    document.activeElement instanceof HTMLElement
      ? document.activeElement.closest<HTMLElement>(
          '[role="dialog"][aria-modal="true"]',
        )
      : null;
  if (activeModal !== null && activeModal !== panelRef.value) return;

  const focusable = getFocusableElements();
  const first = focusable.at(0);
  const last = focusable.at(-1);
  if (first === undefined || last === undefined) {
    event.preventDefault();
  } else if (!panelRef.value?.contains(document.activeElement)) {
    event.preventDefault();
    first.focus();
  } else if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
};

watch(
  [() => props.open, isOverlay],
  async ([open, overlay], [wasOpen, wasOverlay]) => {
    document.body.classList.toggle("search-context-open", open && overlay);
    if (open && !wasOpen) {
      previousFocus =
        document.activeElement instanceof HTMLElement
          ? document.activeElement
          : undefined;
    }
    if (open && overlay && (!wasOpen || !wasOverlay)) {
      await nextTick();
      closeButtonRef.value?.focus();
    } else if (!open && wasOpen) {
      (props.returnFocusTo ?? previousFocus)?.focus();
      previousFocus = undefined;
    }
  },
  { flush: "post", immediate: true },
);

onMounted(() => {
  syncOverlay();
  window.addEventListener("resize", syncOverlay);
  window.addEventListener("keydown", handleGlobalKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", syncOverlay);
  window.removeEventListener("keydown", handleGlobalKeydown);
  document.body.classList.remove("search-context-open");
});
</script>

<template>
  <div v-if="open" class="search-context-wrap">
    <button
      class="context-panel-backdrop"
      type="button"
      aria-label="关闭搜索上下文"
      @click="emit('close')"
    />
    <aside
      ref="panelRef"
      class="search-context-panel"
      :role="isOverlay ? 'dialog' : undefined"
      :aria-modal="isOverlay ? 'true' : undefined"
      aria-label="当前搜索上下文"
    >
      <header>
        <div>
          <span>辅助信息</span>
          <h2>搜索上下文</h2>
        </div>
        <button
          ref="closeButtonRef"
          class="icon-button"
          type="button"
          aria-label="收起搜索上下文"
          @click="emit('close')"
        >
          <X :size="19" aria-hidden="true" />
        </button>
      </header>

      <section>
        <h3><BookOpen :size="16" aria-hidden="true" />当前问题</h3>
        <p class="context-query">{{ query }}</p>
      </section>

      <section>
        <h3><Settings2 :size="16" aria-hidden="true" />模型与来源</h3>
        <dl class="context-definition-list">
          <div>
            <dt>当前知识库</dt>
            <dd>{{ selectedKnowledgeBase?.name ?? "未选择" }}</dd>
          </div>
          <div>
            <dt>AI 模型</dt>
            <dd>{{ modelLabel }}</dd>
          </div>
          <div>
            <dt>可访问知识库</dt>
            <dd>{{ knowledgeBaseOptions.length }} 个</dd>
          </div>
          <div>
            <dt>已就绪文档</dt>
            <dd>{{ totalReadyDocumentCount }} / {{ totalDocumentCount }} 个</dd>
          </div>
        </dl>
      </section>

      <section v-if="uniqueCitations.length > 0">
        <h3><FileText :size="16" aria-hidden="true" />引用来源概览</h3>
        <div class="context-citation-list">
          <button
            v-for="citation in uniqueCitations"
            :key="citation.id"
            type="button"
            @click="
              emit('preview', citation, $event.currentTarget as HTMLElement)
            "
          >
            <span>{{ citation.title }}</span>
          </button>
        </div>
      </section>
      <section v-else>
        <h3><FileText :size="16" aria-hidden="true" />引用来源概览</h3>
        <p class="context-query">检索完成后会显示真实命中文档引用。</p>
      </section>
    </aside>
  </div>
</template>

<style scoped>
:global(body.search-context-open) {
  overflow: hidden;
}

.search-context-wrap {
  min-width: 0;
}

.context-panel-backdrop {
  display: none;
}

.search-context-panel {
  position: sticky;
  top: calc(var(--topbar-height) + var(--space-6));
  max-height: calc(100vh - var(--topbar-height) - var(--space-12));
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.search-context-panel > header,
.search-context-panel > section,
.context-definition-list > div,
.search-context-panel h3,
.context-citation-list button {
  display: flex;
  align-items: center;
}

.search-context-panel > header {
  position: sticky;
  top: 0;
  z-index: 2;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.search-context-panel > header span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.search-context-panel h2 {
  margin: var(--space-1) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-18);
}

.search-context-panel > section {
  display: block;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.search-context-panel h3 {
  gap: var(--space-2);
  margin: 0 0 var(--space-3);
  color: var(--color-text);
  font-size: var(--font-size-13);
}

.search-context-panel h3 svg {
  color: var(--color-primary);
}

.context-query {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.65;
}

.context-file-list {
  margin: 0;
  padding-left: var(--space-5);
  color: var(--color-text-secondary);
  font-size: var(--font-size-12);
}

.context-definition-list {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.context-definition-list > div {
  justify-content: space-between;
  gap: var(--space-3);
}

.context-definition-list dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.context-definition-list dd {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
}

.context-citation-list {
  display: grid;
  gap: var(--space-2);
}

.context-citation-list button {
  width: 100%;
  min-height: 44px;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface-subtle);
  text-align: left;
}

.context-citation-list button > span:first-child {
  min-width: 0;
  flex: 1;
}

@media (max-width: 1439px) {
  .search-context-wrap,
  .context-panel-backdrop {
    position: fixed;
    inset: 0;
  }

  .search-context-wrap {
    z-index: 60;
  }

  .context-panel-backdrop {
    display: block;
    width: 100%;
    height: 100%;
    background: var(--color-overlay);
  }

  .search-context-panel {
    position: absolute;
    top: 0;
    right: 0;
    width: min(380px, calc(100vw - 40px));
    height: 100%;
    max-height: none;
    border: 0;
    border-radius: 0;
    box-shadow: var(--shadow-lg);
  }
}

@media (max-width: 767px) {
  .search-context-panel {
    width: 100%;
  }
}
</style>
