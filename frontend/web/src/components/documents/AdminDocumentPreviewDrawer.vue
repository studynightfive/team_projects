<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onBeforeUnmount, ref, watch } from "vue";

import { toPublicApiError } from "../../api/client";
import type { AdminDocument } from "../../services/admin";
import { prepareFileSave } from "../../services/file-save";
import {
  getDocument,
  getDocumentChunks,
  getDocumentMarkdown,
  getDocumentOriginal,
  type DocumentChunkRecord,
  type DocumentDetailRecord,
} from "../../services/knowledge";
import SafeMarkdown from "../common/SafeMarkdown.vue";
import InlineState from "../InlineState.vue";
import ListPagination from "../ListPagination.vue";
import { Download, FileText, LayoutList, ScrollText } from "../icons";

type PreviewMode = "original" | "markdown" | "chunks";
type LoadState = "idle" | "loading" | "error" | "unavailable";

const props = defineProps<{
  open: boolean;
  document?: AdminDocument;
}>();

const emit = defineEmits<{
  "update:open": [value: boolean];
}>();

const { message } = AntApp.useApp();
const activeMode = ref<PreviewMode>("original");
const documentDetail = ref<DocumentDetailRecord>();
const detailState = ref<LoadState>("idle");
const contentState = ref<LoadState>("idle");
const errorMessage = ref("");
const originalBlob = ref<Blob>();
const originalUrl = ref("");
const originalText = ref("");
const markdownContent = ref("");
const chunks = ref<readonly DocumentChunkRecord[]>([]);
const chunksPage = ref(1);
const chunksPageSize = ref(20);
const chunksTotal = ref(0);
let detailController: AbortController | undefined;
let contentController: AbortController | undefined;

const originalKind = computed<"pdf" | "image" | "text" | "download">(() => {
  const item = documentDetail.value;
  if (item === undefined) return "download";
  if (item.mime_type === "application/pdf" || item.extension === ".pdf") {
    return "pdf";
  }
  if (item.mime_type.startsWith("image/")) return "image";
  if (
    item.mime_type.startsWith("text/") ||
    [".json", ".csv", ".xml", ".md", ".markdown"].includes(item.extension)
  ) {
    return "text";
  }
  return "download";
});

const revokeOriginalUrl = (): void => {
  if (originalUrl.value === "") return;
  URL.revokeObjectURL(originalUrl.value);
  originalUrl.value = "";
};

const resetContent = (): void => {
  contentController?.abort();
  activeMode.value = "original";
  contentState.value = "idle";
  errorMessage.value = "";
  originalBlob.value = undefined;
  originalText.value = "";
  markdownContent.value = "";
  chunks.value = [];
  chunksPage.value = 1;
  chunksTotal.value = 0;
  revokeOriginalUrl();
};

const loadOriginal = async (): Promise<void> => {
  const item = documentDetail.value;
  if (item === undefined) return;
  if (originalKind.value === "download") {
    contentState.value = "unavailable";
    return;
  }
  contentController?.abort();
  const controller = new AbortController();
  contentController = controller;
  contentState.value = "loading";
  errorMessage.value = "";
  try {
    const blob = await getDocumentOriginal(item.id, controller.signal);
    if (contentController !== controller) return;
    originalBlob.value = blob;
    if (originalKind.value === "text") {
      originalText.value = await blob.text();
    } else {
      revokeOriginalUrl();
      originalUrl.value = URL.createObjectURL(blob);
    }
    contentState.value = "idle";
  } catch (error: unknown) {
    if (contentController !== controller) return;
    if (error instanceof DOMException && error.name === "AbortError") return;
    errorMessage.value = toPublicApiError(error).message;
    contentState.value = "error";
  }
};

const loadMarkdown = async (): Promise<void> => {
  const item = documentDetail.value;
  if (item === undefined) return;
  if (item.status !== "ready") {
    contentState.value = "unavailable";
    return;
  }
  contentController?.abort();
  const controller = new AbortController();
  contentController = controller;
  contentState.value = "loading";
  errorMessage.value = "";
  try {
    const result = await getDocumentMarkdown(item.id, controller.signal);
    if (contentController !== controller) return;
    markdownContent.value = result.content;
    contentState.value = "idle";
  } catch (error: unknown) {
    if (contentController !== controller) return;
    if (error instanceof DOMException && error.name === "AbortError") return;
    errorMessage.value = toPublicApiError(error).message;
    contentState.value = "error";
  }
};

const loadChunks = async (): Promise<void> => {
  const item = documentDetail.value;
  if (item === undefined) return;
  if (item.status !== "ready") {
    contentState.value = "unavailable";
    return;
  }
  contentController?.abort();
  const controller = new AbortController();
  contentController = controller;
  contentState.value = "loading";
  errorMessage.value = "";
  try {
    const result = await getDocumentChunks(
      item.id,
      chunksPage.value,
      chunksPageSize.value,
      controller.signal,
    );
    if (contentController !== controller) return;
    chunks.value = result.items;
    chunksTotal.value = result.total;
    contentState.value = "idle";
  } catch (error: unknown) {
    if (contentController !== controller) return;
    if (error instanceof DOMException && error.name === "AbortError") return;
    errorMessage.value = toPublicApiError(error).message;
    contentState.value = "error";
  }
};

const selectMode = (mode: PreviewMode): void => {
  activeMode.value = mode;
  contentState.value = "idle";
  if (mode === "original") void loadOriginal();
  if (mode === "markdown") void loadMarkdown();
  if (mode === "chunks") void loadChunks();
};

const changeChunksPage = (page: number, pageSize: number): void => {
  chunksPage.value = pageSize === chunksPageSize.value ? page : 1;
  chunksPageSize.value = pageSize;
  void loadChunks();
};

const loadDocument = async (): Promise<void> => {
  const item = props.document;
  if (!props.open || item === undefined) return;
  detailController?.abort();
  const controller = new AbortController();
  detailController = controller;
  resetContent();
  documentDetail.value = undefined;
  detailState.value = "loading";
  try {
    const result = await getDocument(item.id, controller.signal);
    if (detailController !== controller) return;
    documentDetail.value = result;
    detailState.value = "idle";
    await loadOriginal();
  } catch (error: unknown) {
    if (detailController !== controller) return;
    if (error instanceof DOMException && error.name === "AbortError") return;
    errorMessage.value = toPublicApiError(error).message;
    detailState.value = "error";
  }
};

const downloadOriginal = async (): Promise<void> => {
  const item = documentDetail.value;
  if (item === undefined) return;
  try {
    const destination = await prepareFileSave({
      suggestedName: item.original_filename,
      description: "原始文档",
      mediaType: item.mime_type,
      extensions: [item.extension],
    });
    if (destination === undefined) return;
    const blob =
      originalBlob.value ?? (await getDocumentOriginal(item.id, undefined));
    await destination.save(blob, item.original_filename);
    void message.success("原件已下载");
  } catch (error: unknown) {
    void message.error(toPublicApiError(error).message);
  }
};

watch(
  [() => props.open, () => props.document?.id],
  ([open]) => {
    if (open) {
      void loadDocument();
      return;
    }
    detailController?.abort();
    resetContent();
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  detailController?.abort();
  resetContent();
});
</script>

<template>
  <Drawer
    :open="open"
    :title="document ? `查看文档：${document.title}` : '查看文档'"
    width="820"
    root-class-name="variant-admin admin-document-preview"
    @close="emit('update:open', false)"
  >
    <InlineState
      v-if="detailState === 'loading'"
      kind="loading"
      title="正在加载文档"
      description="正在通过鉴权接口读取文档详情。"
    />
    <InlineState
      v-else-if="detailState === 'error'"
      kind="error"
      title="文档加载失败"
      :description="errorMessage"
    />

    <div v-else-if="documentDetail" class="admin-preview-body">
      <dl class="admin-preview-meta">
        <div>
          <dt>所属知识库</dt>
          <dd>{{ document?.knowledge_base_name }}</dd>
        </div>
        <div>
          <dt>原始文件</dt>
          <dd>{{ documentDetail.original_filename }}</dd>
        </div>
        <div>
          <dt>处理状态</dt>
          <dd>{{ documentDetail.status === "ready" ? "已索引" : "处理中" }}</dd>
        </div>
      </dl>

      <div class="admin-preview-tabs" role="tablist" aria-label="文档预览方式">
        <button
          type="button"
          role="tab"
          :aria-selected="activeMode === 'original'"
          @click="selectMode('original')"
        >
          <FileText :size="16" aria-hidden="true" />
          原文
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="activeMode === 'markdown'"
          @click="selectMode('markdown')"
        >
          <ScrollText :size="16" aria-hidden="true" />
          Markdown
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="activeMode === 'chunks'"
          @click="selectMode('chunks')"
        >
          <LayoutList :size="16" aria-hidden="true" />
          分块
        </button>
      </div>

      <InlineState
        v-if="contentState === 'loading'"
        kind="loading"
        title="正在读取内容"
        description="请稍候。"
      />
      <InlineState
        v-else-if="contentState === 'error'"
        kind="error"
        title="内容加载失败"
        :description="errorMessage"
      />

      <div
        v-else-if="activeMode === 'original'"
        class="admin-preview-content"
      >
        <object
          v-if="originalKind === 'pdf' && originalUrl"
          :data="originalUrl"
          type="application/pdf"
          aria-label="PDF 原文预览"
        />
        <img
          v-else-if="originalKind === 'image' && originalUrl"
          :src="originalUrl"
          :alt="documentDetail.title"
        />
        <pre v-else-if="originalKind === 'text'">{{ originalText }}</pre>
        <div v-else class="admin-preview-download">
          <p>当前文件格式无法在浏览器中稳定预览，请下载原件查看。</p>
          <button class="secondary-button" type="button" @click="downloadOriginal">
            <Download :size="16" aria-hidden="true" />
            下载原件
          </button>
        </div>
      </div>

      <div
        v-else-if="activeMode === 'markdown'"
        class="admin-preview-content markdown-content"
      >
        <InlineState
          v-if="contentState === 'unavailable'"
          kind="empty"
          title="Markdown 尚未生成"
          description="请等待文档处理完成或重新处理文档。"
        />
        <SafeMarkdown v-else :content="markdownContent" />
      </div>

      <div v-else class="admin-preview-content chunk-content">
        <InlineState
          v-if="contentState === 'unavailable'"
          kind="empty"
          title="分块尚未生成"
          description="请等待文档处理完成或重新处理文档。"
        />
        <template v-else>
          <article v-for="chunk in chunks" :key="chunk.id">
            <header>
              <strong>分块 {{ chunk.chunk_no }}</strong>
              <span>{{ chunk.heading ?? "无标题" }}</span>
            </header>
            <p>{{ chunk.content }}</p>
          </article>
          <ListPagination
            v-if="chunksTotal > 0"
            :page="chunksPage"
            :page-size="chunksPageSize"
            :total="chunksTotal"
            @change="changeChunksPage"
          />
        </template>
      </div>
    </div>
  </Drawer>
</template>

<style scoped>
.admin-preview-body,
.admin-preview-content,
.chunk-content {
  display: grid;
  gap: var(--space-4);
}

.admin-preview-meta {
  display: grid;
  margin: 0;
  border: 1px solid var(--color-border);
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.admin-preview-meta > div {
  min-width: 0;
  padding: var(--space-3);
}

.admin-preview-meta dt,
.admin-preview-meta dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.admin-preview-meta dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.admin-preview-meta dd {
  margin-top: var(--space-1);
  color: var(--color-text);
  font-size: var(--font-size-13);
}

.admin-preview-tabs {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--color-border);
}

.admin-preview-tabs button {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  color: var(--color-text-muted);
  background: transparent;
}

.admin-preview-tabs button[aria-selected="true"] {
  border-bottom: 2px solid var(--color-primary);
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.admin-preview-content {
  min-height: 420px;
}

.admin-preview-content object {
  width: 100%;
  height: min(66vh, 720px);
  border: 1px solid var(--color-border);
}

.admin-preview-content img {
  max-width: 100%;
  max-height: 66vh;
  margin: 0 auto;
  object-fit: contain;
}

.admin-preview-content pre {
  max-height: 66vh;
  margin: 0;
  padding: var(--space-4);
  overflow: auto;
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.admin-preview-download {
  display: grid;
  place-items: center;
  gap: var(--space-3);
  min-height: 320px;
  color: var(--color-text-muted);
  text-align: center;
}

.chunk-content article {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

.chunk-content article header {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  color: var(--color-text-muted);
}

.chunk-content article p {
  margin: var(--space-3) 0 0;
  line-height: 1.7;
  overflow-wrap: anywhere;
}

@media (max-width: 767px) {
  .admin-preview-meta {
    grid-template-columns: 1fr;
  }

  .admin-preview-tabs,
  .admin-preview-tabs button {
    width: 100%;
  }

  .admin-preview-tabs button {
    justify-content: center;
  }

  .admin-preview-content {
    min-height: 320px;
  }
}
</style>
