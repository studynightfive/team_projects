<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { toPublicApiError } from "../../api/client";
import SafeMarkdown from "../../components/common/SafeMarkdown.vue";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { isRealApiMode } from "../../config/runtime";
import {
  ChevronLeft,
  Download,
  Eye,
  FileDown,
  FileText,
  LayoutList,
  ScanSearch,
  ScrollText,
} from "../../components/icons";
import { localPageData } from "../../data/local-pages";
import {
  getDocument,
  getDocumentChunks,
  getDocumentMarkdown,
  getDocumentOriginal,
  type DocumentChunkRecord,
  type DocumentDetailRecord,
} from "../../services/knowledge";
import { createExportTask } from "../../services/downloads";
import { prepareFileSave } from "../../services/file-save";

const route = useRoute();
const { message } = AntApp.useApp();

const sections = [
  { id: "overview", label: "发布目标", page: 1 },
  { id: "preflight", label: "发布前检查", page: 3 },
  { id: "rollback", label: "回滚流程", page: 8 },
  { id: "evidence", label: "验收证据", page: 12 },
] as const;
type SectionId = (typeof sections)[number]["id"];

const activeSection = ref<SectionId>("overview");
type PreviewMode = "original" | "markdown" | "chunks";
type ContentState = "idle" | "loading" | "error" | "unavailable";

const activePreview = ref<PreviewMode>("original");
const realDocument = ref<DocumentDetailRecord>();
const markdownContent = ref("");
const originalBlob = ref<Blob>();
const originalUrl = ref("");
const originalText = ref("");
const originalLoaded = ref(false);
const chunks = ref<readonly DocumentChunkRecord[]>([]);
const chunksPage = ref(1);
const chunksPageSize = ref(20);
const chunksTotal = ref(0);
const loadState = ref<"idle" | "loading" | "error">(
  isRealApiMode ? "loading" : "idle",
);
const originalState = ref<ContentState>("idle");
const markdownState = ref<ContentState>("idle");
const chunksState = ref<ContentState>("idle");
const loadError = ref("");
const originalError = ref("");
const markdownError = ref("");
const chunksError = ref("");

let loadController: AbortController | undefined;
let contentController: AbortController | undefined;

const knowledgeBaseId = computed(() => String(route.params.kb_id ?? ""));
const knowledgeBase = computed(() =>
  localPageData.knowledgeBases.find(
    (item) => item.id === knowledgeBaseId.value,
  ),
);
const documentId = computed(() => String(route.params.document_id ?? ""));
const localDocument = computed(() => {
  if (knowledgeBase.value === undefined) return undefined;

  return localPageData.documents.find(
    (item) =>
      item.id === documentId.value &&
      item.knowledgeBaseId === knowledgeBase.value?.id,
  );
});
const displayDocument = computed(() =>
  isRealApiMode ? realDocument.value : localDocument.value,
);
const isLoadingRealDocument = computed(
  () =>
    isRealApiMode &&
    (loadState.value === "loading" ||
      (loadState.value === "idle" && realDocument.value === undefined)),
);
const documentTitle = computed(
  () =>
    (isRealApiMode
      ? realDocument.value?.title
      : localDocument.value?.name.replace(/\.[^.]+$/u, "")) ?? "",
);
const returnPath = computed(() =>
  knowledgeBaseId.value === "" ? "/knowledge" : `/knowledge/${knowledgeBaseId.value}`,
);
const realDocumentDescription = computed(() => {
  const item = realDocument.value;
  if (item === undefined) return "正在读取真实文档详情。";
  return [
    item.extension.toUpperCase(),
    item.page_count === null ? undefined : `${item.page_count} 页`,
    item.status === "ready" ? "已索引" : "处理中",
    item.parser_name ?? undefined,
  ]
    .filter((value): value is string => value !== undefined)
    .join(" · ");
});
const pageTitle = computed(() => {
  if (isLoadingRealDocument.value) return "正在加载文档";
  if (displayDocument.value === undefined) return "文档不存在";
  return isRealApiMode
    ? (realDocument.value?.title ?? "文档预览")
    : (localDocument.value?.name ?? "文档预览");
});
const pageDescription = computed(() => {
  if (isLoadingRealDocument.value) return "正在读取真实文档详情。";
  if (displayDocument.value === undefined) {
    return isRealApiMode
      ? "正在确认真实文档是否存在。"
      : "当前固定样例中没有此文档。";
  }
  if (isRealApiMode) return realDocumentDescription.value;
  return `${localDocument.value?.category} · ${localDocument.value?.pages} 页 · ${localDocument.value?.owner}`;
});

const originalKind = computed<"pdf" | "image" | "text" | "download">(() => {
  const item = realDocument.value;
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

const ocrStatusLabel = computed(() => {
  const status = realDocument.value?.ocr.status;
  return (
    {
      disabled: "未启用 OCR",
      pending: "OCR 待处理",
      not_required: "无需 OCR",
      completed: "OCR 已完成",
      low_confidence: "OCR 需复核",
      unavailable: "OCR 不可用",
    }[status ?? "pending"] ?? "OCR 状态未知"
  );
});

const ocrConfidenceLabel = computed(() => {
  const confidence = realDocument.value?.ocr.average_confidence;
  return confidence === null || confidence === undefined
    ? "未记录置信度"
    : `平均置信度 ${Math.round(confidence * 100)}%`;
});

const revokeOriginalUrl = (): void => {
  if (originalUrl.value !== "") {
    URL.revokeObjectURL(originalUrl.value);
    originalUrl.value = "";
  }
};

const loadOriginal = async (): Promise<void> => {
  const item = realDocument.value;
  if (item === undefined || originalLoaded.value) return;
  if (originalKind.value === "download") {
    originalLoaded.value = true;
    originalState.value = "unavailable";
    return;
  }
  contentController?.abort();
  contentController = new AbortController();
  originalState.value = "loading";
  originalError.value = "";
  try {
    const blob = await getDocumentOriginal(item.id, contentController.signal);
    originalBlob.value = blob;
    if (originalKind.value === "text") {
      originalText.value = await blob.text();
    } else {
      revokeOriginalUrl();
      originalUrl.value = URL.createObjectURL(blob);
    }
    originalLoaded.value = true;
    originalState.value = "idle";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    originalError.value = toPublicApiError(error).message;
    originalState.value = "error";
  }
};

const loadMarkdown = async (): Promise<void> => {
  const item = realDocument.value;
  if (item === undefined || markdownContent.value !== "") return;
  if (item.status !== "ready") {
    markdownState.value = "unavailable";
    return;
  }
  contentController?.abort();
  contentController = new AbortController();
  markdownState.value = "loading";
  markdownError.value = "";
  try {
    const markdown = await getDocumentMarkdown(
      item.id,
      contentController.signal,
    );
    markdownContent.value = markdown.content;
    markdownState.value = "idle";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    markdownError.value = toPublicApiError(error).message;
    markdownState.value = "error";
  }
};

const loadChunks = async (): Promise<void> => {
  const item = realDocument.value;
  if (item === undefined) return;
  if (item.status !== "ready") {
    chunksState.value = "unavailable";
    return;
  }
  contentController?.abort();
  contentController = new AbortController();
  chunksState.value = "loading";
  chunksError.value = "";
  try {
    const page = await getDocumentChunks(
      item.id,
      chunksPage.value,
      chunksPageSize.value,
      contentController.signal,
    );
    chunks.value = page.items;
    chunksTotal.value = page.total;
    chunksState.value = "idle";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    chunksError.value = toPublicApiError(error).message;
    chunksState.value = "error";
  }
};

const selectPreview = (mode: PreviewMode): void => {
  activePreview.value = mode;
  if (mode === "original") void loadOriginal();
  if (mode === "markdown") void loadMarkdown();
  if (mode === "chunks") void loadChunks();
};

const changeChunksPage = (page: number, pageSize: number): void => {
  chunksPage.value = pageSize === chunksPageSize.value ? page : 1;
  chunksPageSize.value = pageSize;
  void loadChunks();
};

const loadRealDocument = async (): Promise<void> => {
  if (!isRealApiMode) return;

  loadController?.abort();
  contentController?.abort();
  loadController = new AbortController();
  loadState.value = "loading";
  activePreview.value = "original";
  originalState.value = "idle";
  markdownState.value = "idle";
  chunksState.value = "idle";
  loadError.value = "";
  originalError.value = "";
  markdownError.value = "";
  chunksError.value = "";
  revokeOriginalUrl();
  originalBlob.value = undefined;
  originalText.value = "";
  originalLoaded.value = false;
  markdownContent.value = "";
  chunks.value = [];
  chunksPage.value = 1;
  chunksTotal.value = 0;
  realDocument.value = undefined;

  try {
    const document = await getDocument(documentId.value, loadController.signal);
    if (document.knowledge_base_id !== knowledgeBaseId.value) {
      loadError.value = "文档不属于当前知识库，请从知识库目录重新打开。";
      loadState.value = "error";
      return;
    }
    realDocument.value = document;
    loadState.value = "idle";
    await loadOriginal();
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    if (loadState.value === "loading") {
      loadError.value = toPublicApiError(error).message;
      loadState.value = "error";
      return;
    }
    originalError.value = toPublicApiError(error).message;
    originalState.value = "error";
  }
};

watch(
  () => route.query.page,
  (value) => {
    const page = typeof value === "string" ? Number.parseInt(value, 10) : 1;
    activeSection.value =
      [...sections].reverse().find((section) => section.page <= page)?.id ??
      "overview";
  },
  { immediate: true },
);

const previewExport = async (): Promise<void> => {
  if (isRealApiMode) {
    const id = documentId.value;
    if (id.length === 0) {
      void message.warning("当前文档缺少标识，无法创建导出任务");
      return;
    }
    try {
      await createExportTask({
        format: "markdown",
        document_ids: [id],
      });
      void message.success("已创建导出任务，可在「我的下载」中查看并下载");
    } catch (error: unknown) {
      void message.error(toPublicApiError(error).message);
    }
    return;
  }
  void message.info("已打开导出本地预览；鉴权任务接口接入前不会生成文件");
};

const downloadOriginal = async (): Promise<void> => {
  const item = realDocument.value;
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
  () => route.params.document_id,
  () => {
    void loadRealDocument();
  },
);

onMounted(() => {
  void loadRealDocument();
});

onBeforeUnmount(() => {
  loadController?.abort();
  contentController?.abort();
  revokeOriginalUrl();
});
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="企业知识库 / 文档预览"
      :title="pageTitle"
      :description="pageDescription"
    >
      <template #actions>
        <RouterLink class="secondary-button" :to="returnPath">
          <ChevronLeft :size="17" aria-hidden="true" />
          返回目录
        </RouterLink>
        <button
          v-if="isRealApiMode && realDocument"
          class="secondary-button"
          type="button"
          @click="downloadOriginal"
        >
          <Download :size="17" aria-hidden="true" />
          下载原件
        </button>
        <button
          v-if="displayDocument"
          class="primary-button"
          type="button"
          @click="previewExport"
        >
          <FileDown :size="17" aria-hidden="true" />
          导出 Markdown
        </button>
      </template>
    </PageHeader>

    <InlineState
      v-if="isLoadingRealDocument"
      kind="loading"
      title="正在加载文档预览"
      description="正在读取真实文档详情和处理后的 Markdown 内容。"
    />

    <InlineState
      v-else-if="isRealApiMode && loadState === 'error'"
      kind="error"
      title="文档加载失败"
      :description="loadError"
    />

    <InlineState
      v-else-if="!displayDocument"
      kind="error"
      :title="
        isRealApiMode
          ? '未找到真实文档'
          : knowledgeBase
            ? '此知识库中未找到文档'
            : '未找到知识库'
      "
      :description="
        isRealApiMode
          ? '请确认该文档仍存在，并且当前账号拥有访问该知识库的权限。'
          : knowledgeBase
            ? '文档与当前知识库不匹配，请从文档目录重新进入；此状态不会请求业务接口。'
            : '父级知识库不存在，请返回知识库列表；此状态不会请求业务接口。'
      "
    />

    <div
      v-else
      class="document-layout"
      :class="{
        'single-column':
          isRealApiMode || localDocument?.id !== 'release-guide',
      }"
    >
      <ResourcePanel
        v-if="!isRealApiMode && localDocument?.id === 'release-guide'"
        title="页码目录"
        description="点击章节切换本地高亮位置。"
      >
        <nav class="page-outline" aria-label="文档页码目录">
          <button
            v-for="section in sections"
            :key="section.id"
            type="button"
            :class="{ active: activeSection === section.id }"
            :aria-current="
              activeSection === section.id ? 'location' : undefined
            "
            @click="activeSection = section.id"
          >
            <span>{{ section.label }}</span>
            <span>第 {{ section.page }} 页</span>
          </button>
        </nav>
      </ResourcePanel>

      <div v-if="isRealApiMode && realDocument" class="real-preview-shell">
        <section
          class="ocr-summary"
          :class="{ warning: realDocument.ocr.review_required }"
          aria-label="OCR 识别状态"
        >
          <ScanSearch :size="20" aria-hidden="true" />
          <div>
            <strong>{{ ocrStatusLabel }}</strong>
            <p>{{ realDocument.ocr.message }}</p>
          </div>
          <dl>
            <div>
              <dt>识别语言</dt>
              <dd>{{ realDocument.ocr.language }}</dd>
            </div>
            <div>
              <dt>识别质量</dt>
              <dd>{{ ocrConfidenceLabel }}</dd>
            </div>
          </dl>
        </section>

        <div class="preview-tabs" role="tablist" aria-label="文档预览方式">
          <button
            type="button"
            role="tab"
            :aria-selected="activePreview === 'original'"
            :class="{ active: activePreview === 'original' }"
            @click="selectPreview('original')"
          >
            <Eye :size="17" aria-hidden="true" />
            原文
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="activePreview === 'markdown'"
            :class="{ active: activePreview === 'markdown' }"
            @click="selectPreview('markdown')"
          >
            <FileText :size="17" aria-hidden="true" />
            Markdown
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="activePreview === 'chunks'"
            :class="{ active: activePreview === 'chunks' }"
            @click="selectPreview('chunks')"
          >
            <LayoutList :size="17" aria-hidden="true" />
            分块
          </button>
        </div>

        <ResourcePanel
          :title="
            activePreview === 'original'
              ? '原文预览'
              : activePreview === 'markdown'
                ? 'Markdown 预览'
                : '检索分块'
          "
          :description="
            activePreview === 'original'
              ? '默认展示上传原件；不支持浏览器预览的格式可下载核对。'
              : activePreview === 'markdown'
                ? '展示后台清洗后的标准中间格式，前端会再次进行安全过滤。'
                : '展示当前活动索引代次中的真实检索分块。'
          "
        >
          <template #actions>
            <span class="local-preview-badge">真实接口</span>
          </template>

          <template v-if="activePreview === 'original'">
            <InlineState
              v-if="originalState === 'loading'"
              kind="loading"
              title="正在读取原文"
              description="正在通过鉴权接口加载上传原件。"
            />
            <InlineState
              v-else-if="originalState === 'error'"
              kind="error"
              title="原文加载失败"
              :description="originalError"
            />
            <div
              v-else-if="originalState === 'unavailable'"
              class="original-download-state"
            >
              <InlineState
                kind="info"
                title="此格式由本机应用打开"
                description="浏览器无法可靠还原 Office 原版式，请下载原件后使用对应应用查看。"
              />
              <button
                class="primary-button"
                type="button"
                @click="downloadOriginal"
              >
                <Download :size="17" aria-hidden="true" />
                下载原件
              </button>
            </div>
            <object
              v-else-if="originalKind === 'pdf' && originalUrl"
              class="pdf-preview"
              :data="originalUrl"
              type="application/pdf"
              :aria-label="`${documentTitle} 原文 PDF`"
            >
              <p>当前浏览器无法内联显示 PDF，请下载原件查看。</p>
            </object>
            <img
              v-else-if="originalKind === 'image' && originalUrl"
              class="image-preview"
              :src="originalUrl"
              :alt="`${documentTitle} 原图`"
            />
            <pre
              v-else-if="originalKind === 'text'"
              class="text-original-preview"
            ><code>{{ originalText }}</code></pre>
          </template>

          <template v-else-if="activePreview === 'markdown'">
            <InlineState
              v-if="markdownState === 'loading'"
              kind="loading"
              title="正在读取 Markdown"
              description="正在读取文档处理后的标准化内容。"
            />
            <InlineState
              v-else-if="markdownState === 'unavailable'"
              kind="info"
              title="Markdown 尚未生成"
              description="文档处理完成后会生成 Markdown，并进入切分和索引流程。"
            />
            <InlineState
              v-else-if="markdownState === 'error'"
              kind="error"
              title="Markdown 加载失败"
              :description="markdownError"
            />
            <article v-else class="document-content real-document-content">
              <header>
                <ScrollText :size="24" aria-hidden="true" />
                <div>
                  <h2>{{ documentTitle }}</h2>
                  <p>{{ realDocumentDescription }}</p>
                </div>
              </header>
              <SafeMarkdown :content="markdownContent" />
            </article>
          </template>

          <template v-else>
            <InlineState
              v-if="chunksState === 'loading'"
              kind="loading"
              title="正在读取分块"
              description="正在加载当前页的真实检索分块。"
            />
            <InlineState
              v-else-if="chunksState === 'unavailable'"
              kind="info"
              title="分块尚未生成"
              description="文档完成切分和索引后，可在这里核对分块结果。"
            />
            <InlineState
              v-else-if="chunksState === 'error'"
              kind="error"
              title="分块加载失败"
              :description="chunksError"
            />
            <InlineState
              v-else-if="chunks.length === 0"
              kind="empty"
              title="当前没有活动分块"
              description="请确认文档已处理完成并启用索引。"
            />
            <div v-else class="chunk-list">
              <article v-for="chunk in chunks" :key="chunk.id">
                <header>
                  <div>
                    <span>分块 {{ chunk.chunk_no }}</span>
                    <strong>{{ chunk.heading || "无标题分块" }}</strong>
                  </div>
                  <span
                    class="status-chip"
                    :class="
                      chunk.embedding_status === 'vector'
                        ? 'success'
                        : chunk.embedding_status === 'fallback'
                          ? 'warning'
                          : 'danger'
                    "
                  >
                    {{
                      chunk.embedding_status === "vector"
                        ? "向量就绪"
                        : chunk.embedding_status === "fallback"
                          ? "回退索引"
                          : "缺少向量"
                    }}
                  </span>
                </header>
                <dl>
                  <div>
                    <dt>页码</dt>
                    <dd>{{ chunk.page_no ?? "-" }}</dd>
                  </div>
                  <div>
                    <dt>字符范围</dt>
                    <dd>{{ chunk.char_start }}-{{ chunk.char_end }}</dd>
                  </div>
                  <div>
                    <dt>Token 估算</dt>
                    <dd>{{ chunk.token_estimate }}</dd>
                  </div>
                  <div>
                    <dt>索引代次</dt>
                    <dd>{{ chunk.index_generation }}</dd>
                  </div>
                </dl>
                <p>{{ chunk.content }}</p>
              </article>
              <ListPagination
                :page="chunksPage"
                :page-size="chunksPageSize"
                :total="chunksTotal"
                @change="changeChunksPage"
              />
            </div>
          </template>
        </ResourcePanel>
      </div>

      <ResourcePanel
        v-if="!isRealApiMode"
        title="正文预览"
        :description="
          isRealApiMode
            ? '展示后端文档处理生成的 Markdown，前端会再次进行安全过滤。'
            : '受控 Vue 模板，不解析真实 Markdown。'
        "
      >
        <template #actions>
          <span class="local-preview-badge">{{
            isRealApiMode ? "真实接口" : "本地预览"
          }}</span>
        </template>

        <InlineState
          v-if="isRealApiMode && markdownState === 'loading'"
          kind="loading"
          title="正在生成正文预览"
          description="正在读取文档处理后的 Markdown 内容。"
        />

        <InlineState
          v-else-if="isRealApiMode && markdownState === 'unavailable'"
          kind="info"
          title="文档仍在处理中"
          description="文档处理完成后会生成 Markdown 预览，并进入 RAG 检索。请稍后刷新目录或重新打开预览。"
        />

        <InlineState
          v-else-if="isRealApiMode && markdownState === 'error'"
          kind="error"
          title="正文预览加载失败"
          :description="markdownError"
        />

        <article
          v-else-if="isRealApiMode"
          class="document-content real-document-content"
        >
          <header>
            <ScrollText :size="24" aria-hidden="true" />
            <div>
              <h2>{{ documentTitle }}</h2>
              <p>{{ realDocumentDescription }}</p>
            </div>
          </header>
          <SafeMarkdown :content="markdownContent" />
        </article>

        <article
          v-else-if="localDocument?.id === 'release-guide'"
          class="document-content"
        >
          <header>
            <ScrollText :size="24" aria-hidden="true" />
            <div>
              <h2>{{ documentTitle }}</h2>
              <p>版本 2.4 · 平台团队 · 本地固定内容</p>
            </div>
          </header>

          <section :class="{ highlighted: activeSection === 'overview' }">
            <h3>1. 发布目标</h3>
            <p>
              本指南用于统一发布前准备、执行窗口、验证证据和异常回滚路径，减少跨团队信息遗漏。
            </p>
          </section>

          <section :class="{ highlighted: activeSection === 'preflight' }">
            <h3>2. 发布前检查</h3>
            <p>
              发布窗口开始前必须完成质量门禁、数据库变更确认和回滚路径演练。
            </p>
            <table>
              <thead>
                <tr>
                  <th scope="col">检查项</th>
                  <th scope="col">负责人</th>
                  <th scope="col">证据</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>前端质量门禁</td>
                  <td>前端负责人</td>
                  <td>类型、Lint、测试、构建</td>
                </tr>
                <tr>
                  <td>数据变更确认</td>
                  <td>后端负责人</td>
                  <td>迁移记录与回退脚本</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section :class="{ highlighted: activeSection === 'rollback' }">
            <h3>3. 回滚流程</h3>
            <p>
              当核心健康检查持续失败时，停止后续发布动作，按既定顺序恢复上一稳定版本。
            </p>
            <pre><code>verify health
freeze rollout
restore previous release
record verification evidence</code></pre>
            <p class="citation-highlight">
              引用定位示例：第 8 页强调先停止扩散，再执行恢复与证据记录。
            </p>
          </section>

          <section :class="{ highlighted: activeSection === 'evidence' }">
            <h3>4. 验收证据</h3>
            <p>
              每次发布至少保留检查结果、变更记录、健康状态和最终责任人确认，不在页面中记录凭据。
            </p>
          </section>
        </article>
        <InlineState
          v-else
          kind="info"
          :title="`${documentTitle}正文尚未加入固定样例`"
          description="当前页面保留文档元信息与安全空状态，不会用其他文档内容冒充，也不会请求业务接口。"
        />
      </ResourcePanel>
    </div>
  </div>
</template>

<style scoped>
.local-page {
  display: grid;
  gap: var(--space-6);
}

.document-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.7fr) minmax(0, 2.3fr);
  align-items: start;
  gap: var(--space-6);
}

.document-layout.single-column {
  grid-template-columns: minmax(0, 1fr);
}

.real-preview-shell {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}

.ocr-summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-success);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.ocr-summary.warning {
  border-left-color: var(--color-warning);
  background: var(--color-warning-soft);
}

.ocr-summary > svg {
  color: var(--color-primary);
}

.ocr-summary strong {
  color: var(--color-text);
}

.ocr-summary p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
}

.ocr-summary dl,
.chunk-list article dl {
  display: flex;
  gap: var(--space-4);
  margin: 0;
}

.ocr-summary dl div,
.chunk-list article dl div {
  display: grid;
  gap: 2px;
}

.ocr-summary dt,
.chunk-list article dt {
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
}

.ocr-summary dd,
.chunk-list article dd {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}

.preview-tabs {
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  padding: 3px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.preview-tabs button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border-radius: 6px;
  color: var(--color-text-secondary);
  background: transparent;
}

.preview-tabs button.active {
  color: var(--color-primary);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  font-weight: var(--font-weight-medium);
}

.original-download-state {
  display: grid;
  justify-items: start;
  gap: var(--space-4);
}

.pdf-preview {
  width: 100%;
  min-height: 720px;
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.image-preview {
  display: block;
  max-width: 100%;
  max-height: 75vh;
  margin: 0 auto;
  object-fit: contain;
}

.text-original-preview {
  max-height: 70vh;
  margin: 0;
  padding: var(--space-5);
  overflow: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface-subtle);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.chunk-list {
  display: grid;
  gap: var(--space-3);
}

.chunk-list article {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.chunk-list article > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.chunk-list article > header div {
  display: grid;
  gap: var(--space-1);
}

.chunk-list article > header div span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.chunk-list article > header strong {
  color: var(--color-text);
}

.chunk-list article > p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.page-outline {
  display: grid;
  gap: var(--space-1);
}

.page-outline button {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 0 var(--space-3);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: transparent;
  text-align: left;
}

.page-outline button span:last-child {
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
  white-space: nowrap;
}

.page-outline button.active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: var(--font-weight-medium);
}

.document-content {
  max-width: 860px;
  margin: 0 auto;
  color: var(--color-text-secondary);
  line-height: 1.75;
}

.document-content > header {
  display: flex;
  gap: var(--space-3);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-primary);
}

.document-content h2,
.document-content h3 {
  color: var(--color-text);
}

.document-content h2 {
  margin-bottom: var(--space-1);
  font-size: var(--font-size-24);
}

.document-content header p {
  margin-bottom: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
}

.document-content section {
  padding: var(--space-5);
  border-radius: var(--radius-8);
  transition: background var(--transition-fast);
}

.document-content section.highlighted {
  background: var(--color-primary-soft);
}

.document-content table {
  width: 100%;
  border-collapse: collapse;
}

.document-content th,
.document-content td {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  text-align: left;
}

.document-content th {
  background: var(--color-table-head);
}

.document-content pre {
  padding: var(--space-4);
  overflow: auto;
  border-radius: var(--radius-8);
  color: var(--slate-100);
  background: var(--slate-950);
  font-family: var(--font-mono);
}

.citation-highlight {
  padding: var(--space-3);
  border-left: 3px solid var(--color-primary);
  background: var(--blue-50);
}

@media (max-width: 980px) {
  .document-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .ocr-summary {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .ocr-summary dl {
    grid-column: 1 / -1;
    flex-wrap: wrap;
    padding-left: calc(20px + var(--space-3));
  }

  .preview-tabs {
    display: grid;
    width: 100%;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .preview-tabs button {
    min-width: 0;
    min-height: 44px;
    justify-content: center;
    padding: 0 var(--space-2);
  }

  .pdf-preview {
    min-height: 65vh;
  }

  .chunk-list article > header {
    align-items: stretch;
    flex-direction: column;
  }

  .chunk-list article dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chunk-list article dd {
    overflow-wrap: anywhere;
  }

  .document-content section {
    padding: var(--space-4) 0;
  }

  .document-content table {
    display: block;
    max-width: 100%;
    overflow-x: auto;
    white-space: nowrap;
  }

  .document-content section.highlighted {
    padding: var(--space-4);
  }
}
</style>
