<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { isRealApiMode } from "../../config/runtime";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import DocumentTaskProgress from "../../components/documents/DocumentTaskProgress.vue";
import DocumentUploadQueue from "../../components/documents/DocumentUploadQueue.vue";
import { useListPagination } from "../../composables/useListPagination";
import { ChevronLeft, Download, Eye, RotateCcw } from "../../components/icons";
import { localPageData } from "../../data/local-pages";
import { toPublicApiError } from "../../api/client";
import { useSessionStore } from "../../stores/session";
import { createExportTask } from "../../services/downloads";
import {
  batchReprocessDocuments,
  listDocuments,
  listKnowledgeBases,
  uploadDocuments,
  type ChunkStrategy,
  type DocumentBatchTaskItem,
  type DocumentRecord,
  type KnowledgeBaseRecord,
} from "../../services/knowledge";

const route = useRoute();
const router = useRouter();
const { message } = AntApp.useApp();
const sessionStore = useSessionStore();
const query = ref("");
const status = ref("全部状态");
const selectedDocumentIds = ref<string[]>([]);
const realKnowledgeBase = ref<KnowledgeBaseRecord>();
const realDocuments = ref<readonly DocumentRecord[]>([]);
const loadState = ref<"idle" | "loading" | "error">(
  isRealApiMode ? "loading" : "idle",
);
const loadError = ref("");
const uploadZoneRef = ref<HTMLElement>();
const isUploading = ref(false);
const uploadResetToken = ref(0);
const chunkStrategy = ref<ChunkStrategy>("recursive");
const chunkSize = ref(800);
const chunkOverlap = ref(120);
const isExporting = ref(false);
const isReprocessing = ref(false);
const batchTasks = ref<readonly DocumentBatchTaskItem[]>([]);

let loadController: AbortController | undefined;

const knowledgeBase = computed(() =>
  isRealApiMode
    ? realKnowledgeBase.value
    : localPageData.knowledgeBases.find(
        (item) => item.id === String(route.params.kb_id ?? ""),
      ),
);
const knowledgeBaseDocumentCount = computed(() =>
  isRealApiMode
    ? (realKnowledgeBase.value?.document_count ?? 0)
    : (localPageData.knowledgeBases.find(
        (item) => item.id === String(route.params.kb_id ?? ""),
      )?.documents ?? 0),
);
const isLoadingRealDetail = computed(
  () =>
    isRealApiMode &&
    (loadState.value === "loading" ||
      (loadState.value === "idle" && realKnowledgeBase.value === undefined)),
);
const pageTitle = computed(() => {
  if (isLoadingRealDetail.value) return "正在加载知识库";
  return knowledgeBase.value?.name ?? "知识库不存在";
});
const pageDescription = computed(() => {
  if (isLoadingRealDetail.value) return "正在读取当前账号可访问的知识库文档。";
  return (
    knowledgeBase.value?.description ??
    (isRealApiMode
      ? "请确认当前账号拥有该知识库权限。"
      : "当前固定样例中没有此知识库。")
  );
});
const canUploadKnowledge = computed(() => {
  const permissions = sessionStore.currentUser?.permissions ?? [];
  return (
    realKnowledgeBase.value?.kind === "personal" &&
    permissions.includes("personal.document.upload")
  );
});
const canReprocessKnowledge = computed(() => {
  const permissions = sessionStore.currentUser?.permissions ?? [];
  return (
    (realKnowledgeBase.value?.kind === "personal" &&
      permissions.includes("personal.document.upload")) ||
    (realKnowledgeBase.value?.kind === "enterprise" &&
      permissions.includes("admin.document.upload"))
  );
});

const displayDocuments = computed(() =>
  isRealApiMode
    ? realDocuments.value.map((item) => ({
        id: item.id,
        knowledgeBaseId: item.knowledge_base_id,
        name: item.title,
        category: item.extension.toUpperCase(),
        status:
          item.status === "ready"
            ? "已索引"
            : item.status === "manual_review"
              ? "需复核"
              : "处理中",
        pages: item.page_count ?? "-",
        owner: item.parser_name ?? "系统解析",
        updated:
          item.updated_at === null
            ? "刚刚"
            : new Intl.DateTimeFormat("zh-CN", {
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              }).format(new Date(item.updated_at)),
      }))
    : localPageData.documents,
);

const filteredDocuments = computed(() => {
  const currentKnowledgeBaseId = knowledgeBase.value?.id;
  if (currentKnowledgeBaseId === undefined) return [];

  const normalizedQuery = query.value.trim().toLocaleLowerCase("zh-CN");

  return displayDocuments.value.filter((item) => {
    const matchesKnowledgeBase =
      item.knowledgeBaseId === currentKnowledgeBaseId;
    const matchesStatus =
      status.value === "全部状态" || item.status === status.value;
    const matchesQuery =
      normalizedQuery.length === 0 ||
      `${item.name}${item.category}${item.owner}`
        .toLocaleLowerCase("zh-CN")
        .includes(normalizedQuery);

    return matchesKnowledgeBase && matchesStatus && matchesQuery;
  });
});
const {
  page: documentsPage,
  pageSize: documentsPageSize,
  pagedItems: pagedDocuments,
  setPage: setDocumentsPage,
} = useListPagination(filteredDocuments);

const allVisibleSelected = computed(
  () =>
    pagedDocuments.value.length > 0 &&
    pagedDocuments.value.every((item) =>
      selectedDocumentIds.value.includes(item.id),
    ),
);

const toggleDocument = (documentId: string): void => {
  selectedDocumentIds.value = selectedDocumentIds.value.includes(documentId)
    ? selectedDocumentIds.value.filter((id) => id !== documentId)
    : [...selectedDocumentIds.value, documentId];
};

const toggleAllVisible = (): void => {
  if (allVisibleSelected.value) {
    const visibleIds = new Set(pagedDocuments.value.map((item) => item.id));
    selectedDocumentIds.value = selectedDocumentIds.value.filter(
      (id) => !visibleIds.has(id),
    );
    return;
  }

  selectedDocumentIds.value = [
    ...new Set([
      ...selectedDocumentIds.value,
      ...pagedDocuments.value.map((item) => item.id),
    ]),
  ];
};

const exportSelected = async (): Promise<void> => {
  if (!isRealApiMode) {
    void message.info(`已选择 ${selectedDocumentIds.value.length} 个模拟文档`);
    return;
  }
  isExporting.value = true;
  try {
    await createExportTask({
      format: "markdown",
      document_ids: selectedDocumentIds.value,
    });
    void message.success("导出任务已创建，可在下载中心查看进度");
    await router.push("/downloads");
  } catch (error: unknown) {
    void message.error(toPublicApiError(error).message);
  } finally {
    isExporting.value = false;
  }
};

const reprocessSelected = async (): Promise<void> => {
  if (selectedDocumentIds.value.length === 0) return;
  isReprocessing.value = true;
  try {
    batchTasks.value = await batchReprocessDocuments(
      selectedDocumentIds.value,
    );
    message.success("文档已进入重新处理队列");
    await loadRealDetail();
  } catch (error: unknown) {
    message.error(toPublicApiError(error).message);
  } finally {
    isReprocessing.value = false;
  }
};

const loadRealDetail = async (): Promise<void> => {
  if (!isRealApiMode) return;
  const kbId = String(route.params.kb_id ?? "");
  if (kbId === "") return;

  loadController?.abort();
  loadController = new AbortController();
  loadState.value = "loading";
  loadError.value = "";
  try {
    const [knowledgeBases, documents] = await Promise.all([
      listKnowledgeBases(loadController.signal),
      listDocuments(kbId, loadController.signal),
    ]);
    realKnowledgeBase.value = knowledgeBases.find((item) => item.id === kbId);
    realDocuments.value = documents;
    selectedDocumentIds.value = [];
    loadState.value = "idle";
    await consumeUploadActionQuery();
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = toPublicApiError(error).message;
    loadState.value = "error";
  }
};

const focusUploadZone = async (): Promise<void> => {
  await nextTick();
  uploadZoneRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
  uploadZoneRef.value?.focus({ preventScroll: true });
};

const consumeUploadActionQuery = async (): Promise<void> => {
  if (String(route.query.action ?? "") !== "upload") return;
  if (!isRealApiMode || !canUploadKnowledge.value) return;
  if (knowledgeBase.value === undefined) return;
  await focusUploadZone();
  const nextQuery = { ...route.query };
  delete nextQuery.action;
  await router.replace({
    path: route.path,
    query: nextQuery,
  });
};

const uploadFiles = async (files: readonly File[]): Promise<void> => {
  if (!isRealApiMode || files.length === 0) return;
  if (chunkOverlap.value >= chunkSize.value) {
    message.warning("重叠字符必须小于切分大小");
    return;
  }

  isUploading.value = true;
  try {
    const results = await uploadDocuments(String(route.params.kb_id ?? ""), files, {
      chunkStrategy: chunkStrategy.value,
      chunkSize: chunkSize.value,
      chunkOverlap: chunkOverlap.value,
    });
    const readyCount = results.filter(
      (item) => item.document.status === "ready",
    ).length;
    message.success(`已上传 ${results.length} 个文档，${readyCount} 个已完成索引`);
    uploadResetToken.value += 1;
    await loadRealDetail();
  } catch (error: unknown) {
    message.error(toPublicApiError(error).message);
  } finally {
    isUploading.value = false;
  }
};

watch(
  () => route.params.kb_id,
  () => {
    void loadRealDetail();
  },
);

watch(
  () => route.query.action,
  () => {
    if (loadState.value === "idle") {
      void consumeUploadActionQuery();
    }
  },
);

onMounted(() => {
  void loadRealDetail();
});

onBeforeUnmount(() => {
  loadController?.abort();
});
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="企业知识库 / 文档目录"
      :title="pageTitle"
      :description="pageDescription"
    >
      <template #actions>
        <RouterLink class="secondary-button" to="/knowledge">
          <ChevronLeft :size="17" aria-hidden="true" />
          返回知识库
        </RouterLink>
        <button
          v-if="canReprocessKnowledge"
          class="secondary-button"
          type="button"
          :disabled="selectedDocumentIds.length === 0 || isReprocessing"
          @click="reprocessSelected"
        >
          <RotateCcw :size="17" aria-hidden="true" />
          {{
            isReprocessing
              ? "正在提交"
              : `重新处理（${selectedDocumentIds.length}）`
          }}
        </button>
        <button
          class="primary-button"
          type="button"
          :disabled="selectedDocumentIds.length === 0 || isExporting"
          @click="exportSelected"
        >
          <Download :size="17" aria-hidden="true" />
          {{ isExporting ? "正在创建任务" : `导出所选（${selectedDocumentIds.length}）` }}
        </button>
      </template>
    </PageHeader>

    <InlineState
      v-if="isLoadingRealDetail"
      kind="loading"
      title="正在加载文档目录"
      description="正在读取真实知识库和文档列表。"
    />

    <InlineState
      v-else-if="isRealApiMode && loadState === 'error'"
      kind="error"
      title="文档加载失败"
      :description="loadError"
    />

    <InlineState
      v-else-if="!knowledgeBase"
      kind="error"
      title="未找到知识库"
      :description="
        isRealApiMode
          ? '请确认当前账号拥有该知识库权限。'
          : '请从知识库列表重新进入；此状态不会请求业务接口。'
      "
    />

    <ResourcePanel
      v-else
      title="文档目录"
      :description="
        isRealApiMode
          ? `${realDocuments.length} 个真实文档，已就绪文档会进入 RAG 检索。`
          : `${knowledgeBaseDocumentCount} 个文档为页面层级示意，当前展示固定样例。`
      "
    >
      <template #actions>
        <span class="local-preview-badge">{{
          isRealApiMode ? "真实接口" : "本地预览"
        }}</span>
      </template>

      <div
        v-if="isRealApiMode && canUploadKnowledge"
        ref="uploadZoneRef"
        class="upload-workbench"
        tabindex="-1"
      >
        <DocumentUploadQueue
          :uploading="isUploading"
          :reset-token="uploadResetToken"
          @submit="uploadFiles"
        />
      </div>

      <div v-if="isRealApiMode && canUploadKnowledge" class="chunk-options">
        <label>
          <span>切分方法</span>
          <select v-model="chunkStrategy">
            <option value="fixed">固定长度</option>
            <option value="semantic">语义</option>
            <option value="recursive">递归</option>
            <option value="format">格式</option>
          </select>
        </label>
        <label>
          <span>切分大小</span>
          <input v-model.number="chunkSize" type="number" min="100" max="4000" />
        </label>
        <label>
          <span>重叠字符</span>
          <input v-model.number="chunkOverlap" type="number" min="0" max="1000" />
        </label>
      </div>

      <div v-if="canReprocessKnowledge" class="reprocess-guide">
        <RotateCcw :size="18" aria-hidden="true" />
        <p>
          更换 Embedding 模型或修改切分配置后，请勾选文档重新处理，完成前旧索引不会混入新模型向量。
        </p>
      </div>

      <DocumentTaskProgress
        v-if="batchTasks.length > 0"
        :items="batchTasks"
        @finished="loadRealDetail"
      />

      <div class="filter-bar">
        <label class="filter-field grow">
          <span>搜索文档</span>
          <input
            v-model="query"
            type="search"
            placeholder="搜索名称、分类或负责人"
            autocomplete="off"
          />
        </label>
        <label>
          <span>文档状态</span>
          <select v-model="status">
            <option>全部状态</option>
            <option>已索引</option>
            <option>处理中</option>
            <option>需复核</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="loadState === 'loading'"
        kind="loading"
        title="正在加载文档"
        description="正在读取知识库文档目录。"
      />

      <InlineState
        v-else-if="loadState === 'error'"
        kind="error"
        title="文档加载失败"
        :description="loadError"
      />

      <div
        v-else-if="filteredDocuments.length > 0"
        class="data-table-scroll"
        tabindex="0"
        aria-label="文档目录表格，可横向滚动"
      >
        <table class="data-table document-table mobile-sticky-actions">
          <thead>
            <tr>
              <th scope="col" class="selection-column">
                <input
                  type="checkbox"
                  :checked="allVisibleSelected"
                  aria-label="选择当前筛选中的全部文档"
                  @change="toggleAllVisible"
                />
              </th>
              <th scope="col">文档</th>
              <th scope="col">分类</th>
              <th scope="col">状态</th>
              <th scope="col">页数</th>
              <th scope="col">负责人</th>
              <th scope="col">更新时间</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pagedDocuments" :key="item.id">
              <td>
                <input
                  type="checkbox"
                  :checked="selectedDocumentIds.includes(item.id)"
                  :aria-label="`选择${item.name}`"
                  @change="toggleDocument(item.id)"
                />
              </td>
              <td class="document-name">{{ item.name }}</td>
              <td>{{ item.category }}</td>
              <td>
                <span
                  class="status-chip"
                  :class="{
                    success: item.status === '已索引',
                    warning: item.status !== '已索引',
                  }"
                >
                  {{ item.status }}
                </span>
              </td>
              <td>{{ item.pages }}</td>
              <td>{{ item.owner }}</td>
              <td>{{ item.updated }}</td>
              <td>
                <RouterLink
                  class="table-action"
                  :to="`/knowledge/${knowledgeBase.id}/documents/${item.id}`"
                >
                  <Eye :size="15" aria-hidden="true" />
                  预览
                </RouterLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <ListPagination
        v-if="filteredDocuments.length > 0"
        :page="documentsPage"
        :page-size="documentsPageSize"
        :total="filteredDocuments.length"
        @change="setDocumentsPage"
      />

      <InlineState
        v-else
        kind="empty"
        title="没有匹配的文档"
        description="请清除关键词或切换状态筛选。"
      />

      <template #footer>
        <span>
          当前展示 {{ filteredDocuments.length }}
          条{{ isRealApiMode ? "真实文档" : "固定样例" }}
        </span>
        <span>选中 {{ selectedDocumentIds.length }} 条</span>
      </template>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.local-page {
  display: grid;
  gap: var(--space-6);
}

.document-table {
  min-width: 940px;
}

.selection-column {
  width: 48px;
}

.document-name {
  max-width: 280px;
  overflow: hidden;
  font-weight: var(--font-weight-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-action {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
  white-space: nowrap;
}

.chunk-options {
  display: grid;
  grid-template-columns: minmax(180px, 1.4fr) repeat(2, minmax(120px, 1fr));
  gap: var(--space-3);
}

.reprocess-guide {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border-left: 3px solid var(--color-primary);
  color: var(--color-text-secondary);
  background: var(--color-primary-soft);
}

.reprocess-guide p {
  margin: 0;
  line-height: 1.6;
}

@media (max-width: 767px) {
  .chunk-options {
    grid-template-columns: minmax(0, 1fr);
  }

  .document-table.mobile-sticky-actions th:last-child,
  .document-table.mobile-sticky-actions td:last-child {
    min-width: 96px;
  }
}
</style>
