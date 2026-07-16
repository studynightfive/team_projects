<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

import type { CitationSource, SearchResultItem } from "../../types/ai-search";
import {
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Copy,
  ExternalLink,
  FileText,
  X,
} from "../icons";
import SearchStatusBadge from "./SearchStatusBadge.vue";

const props = defineProps<{
  open: boolean;
  document?: CitationSource | SearchResultItem;
  returnFocusTo?: HTMLElement;
}>();

const emit = defineEmits<{
  "update:open": [value: boolean];
  favorite: [documentId: string];
  notice: [message: string];
}>();

const panelRef = ref<HTMLElement>();
const closeButtonRef = ref<HTMLButtonElement>();
const activeHitIndex = ref(0);

const hitCount = computed(() => props.document?.documentContent.length ?? 0);

const close = (): void => emit("update:open", false);

const moveHit = async (direction: -1 | 1): Promise<void> => {
  if (hitCount.value === 0) return;
  activeHitIndex.value =
    (activeHitIndex.value + direction + hitCount.value) % hitCount.value;
  await nextTick();
  panelRef.value
    ?.querySelector<HTMLElement>(".document-preview-content .active-hit")
    ?.scrollIntoView?.({ block: "center" });
};

const copyLink = async (): Promise<void> => {
  const path = `${window.location.origin}/search?document=${encodeURIComponent(props.document?.id ?? "")}`;
  try {
    await navigator.clipboard.writeText(path);
    emit("notice", "文档链接已复制");
  } catch {
    emit("notice", "浏览器未允许复制，请使用地址栏复制");
  }
};

const openOriginal = (): void => {
  emit("notice", "当前为本地预览，原文地址将在文档接口接入后开放");
};

const getFocusableElements = (): HTMLElement[] => {
  if (panelRef.value === undefined) return [];
  return Array.from(
    panelRef.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
    ),
  );
};

const handleKeydown = (event: KeyboardEvent): void => {
  if (event.key === "Escape") {
    event.preventDefault();
    close();
    return;
  }
  if (event.key !== "Tab") return;

  const focusable = getFocusableElements();
  const first = focusable.at(0);
  const last = focusable.at(-1);
  if (first === undefined || last === undefined) {
    event.preventDefault();
  } else if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
};

watch(
  () => props.open,
  async (open) => {
    document.body.classList.toggle("preview-drawer-open", open);
    if (open) {
      activeHitIndex.value = 0;
      await nextTick();
      closeButtonRef.value?.focus();
    } else {
      props.returnFocusTo?.focus();
    }
  },
  { flush: "post" },
);

onBeforeUnmount(() => document.body.classList.remove("preview-drawer-open"));
</script>

<template>
  <div
    v-if="open && document"
    class="document-preview-drawer"
    @keydown="handleKeydown"
  >
    <button
      class="document-preview-backdrop"
      type="button"
      aria-label="关闭文档预览"
      @click="close"
    />
    <aside
      ref="panelRef"
      class="document-preview-panel"
      role="dialog"
      aria-modal="true"
      :aria-label="`预览文档 ${document.title}`"
    >
      <header class="document-preview-header">
        <div>
          <span>文档预览</span>
          <h2>{{ document.title }}</h2>
        </div>
        <button
          ref="closeButtonRef"
          class="icon-button"
          type="button"
          aria-label="关闭文档预览"
          @click="close"
        >
          <X :size="20" aria-hidden="true" />
        </button>
      </header>

      <div class="document-preview-meta">
        <span><FileText :size="15" aria-hidden="true" />{{
          document.fileType
        }}</span>
        <span>{{ document.spaceName }}</span>
        <span>负责人：{{ document.owner }}</span>
        <span>更新于 {{ document.updatedAt }}</span>
        <SearchStatusBadge :status="document.verifiedStatus" />
        <SearchStatusBadge :status="document.permissionStatus" />
      </div>

      <div class="document-hit-toolbar" aria-label="命中内容导航">
        <span>命中位置 {{ hitCount === 0 ? 0 : activeHitIndex + 1 }} /
          {{ hitCount }}</span>
        <div>
          <button
            type="button"
            aria-label="上一个命中位置"
            :disabled="hitCount === 0"
            @click="moveHit(-1)"
          >
            <ChevronLeft :size="17" aria-hidden="true" />
            上一个
          </button>
          <button
            type="button"
            aria-label="下一个命中位置"
            :disabled="hitCount === 0"
            @click="moveHit(1)"
          >
            下一个
            <ChevronRight :size="17" aria-hidden="true" />
          </button>
        </div>
      </div>

      <article class="document-preview-content">
        <p
          v-for="(paragraph, index) in document.documentContent"
          :key="`${document.id}-${index}`"
          :class="{ 'active-hit': index === activeHitIndex }"
        >
          {{ paragraph }}
        </p>
      </article>

      <footer class="document-preview-actions">
        <button class="secondary-button" type="button" @click="copyLink">
          <Copy :size="16" aria-hidden="true" />
          复制链接
        </button>
        <button
          class="secondary-button"
          type="button"
          @click="emit('favorite', document.id)"
        >
          <Bookmark :size="16" aria-hidden="true" />
          收藏文档
        </button>
        <button class="primary-button" type="button" @click="openOriginal">
          <ExternalLink :size="16" aria-hidden="true" />
          在新页面打开
        </button>
      </footer>
    </aside>
  </div>
</template>

<style scoped>
.document-preview-drawer,
.document-preview-backdrop {
  position: fixed;
  inset: 0;
}

.document-preview-drawer {
  z-index: 80;
}

.document-preview-backdrop {
  width: 100%;
  height: 100%;
  padding: 0;
  background: var(--color-overlay);
}

.document-preview-panel {
  position: absolute;
  top: 0;
  right: 0;
  display: grid;
  width: min(640px, calc(100vw - 80px));
  height: 100%;
  grid-template-rows: auto auto auto minmax(0, 1fr) auto;
  overflow: hidden;
  background: var(--color-surface);
  box-shadow: var(--shadow-lg);
}

.document-preview-header,
.document-preview-meta,
.document-hit-toolbar,
.document-preview-actions {
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.document-preview-header,
.document-hit-toolbar,
.document-preview-actions,
.document-preview-meta,
.document-hit-toolbar > div,
.document-preview-meta > span {
  display: flex;
  align-items: center;
}

.document-preview-header,
.document-hit-toolbar {
  justify-content: space-between;
  gap: var(--space-4);
}

.document-preview-header span {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.document-preview-header h2 {
  margin: var(--space-1) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-18);
}

.document-preview-meta {
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.document-preview-meta > span {
  gap: var(--space-1);
}

.document-hit-toolbar {
  padding-top: var(--space-3);
  padding-bottom: var(--space-3);
  color: var(--color-text-secondary);
  background: var(--color-surface-subtle);
  font-size: var(--font-size-13);
}

.document-hit-toolbar > div,
.document-preview-actions {
  gap: var(--space-2);
}

.document-hit-toolbar button {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-2);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: transparent;
}

.document-preview-content {
  padding: var(--space-6);
  overflow-y: auto;
  color: var(--color-text-secondary);
  font-size: var(--font-size-15, 15px);
  line-height: 1.85;
}

.document-preview-content p {
  margin-bottom: var(--space-5);
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid transparent;
}

.document-preview-content p.active-hit {
  border-left-color: var(--color-warning);
  background: var(--amber-50);
}

.document-preview-actions {
  justify-content: flex-end;
  border-top: 1px solid var(--color-border);
  border-bottom: 0;
}

@media (max-width: 767px) {
  .document-preview-panel {
    width: 100%;
  }

  .document-preview-header,
  .document-preview-meta,
  .document-hit-toolbar,
  .document-preview-content,
  .document-preview-actions {
    padding-right: var(--space-4);
    padding-left: var(--space-4);
  }

  .document-preview-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .document-preview-actions .primary-button {
    grid-column: 1 / -1;
  }
}
</style>
