<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import DocumentTaskProgress from "../../components/documents/DocumentTaskProgress.vue";
import {
  Eye,
  RefreshCw,
  RotateCcw,
  Trash2,
} from "../../components/icons";
import { useListPagination } from "../../composables/useListPagination";
import { listAdminDocuments, type AdminDocument } from "../../services/admin";
import {
  batchDeleteDocuments,
  batchReprocessDocuments,
  listRecycleBin,
  restoreDocuments,
  type DocumentBatchTaskItem,
  type RecycleBinRecord,
} from "../../services/knowledge";

type DocumentViewMode = "active" | "recycle";
type DisplayDocument = AdminDocument | RecycleBinRecord;

const { message, modal } = AntApp.useApp();
const documents = ref<readonly AdminDocument[]>([]);
const recycledDocuments = ref<readonly RecycleBinRecord[]>([]);
const viewMode = ref<DocumentViewMode>("active");
const query = ref("");
const statusFilter = ref("全部状态");
const selectedDocumentIds = ref<string[]>([]);
const detailDocument = ref<DisplayDocument>();
const loading = ref(false);
const submitting = ref(false);
const batchTasks = ref<readonly DocumentBatchTaskItem[]>([]);

const sourceDocuments = computed<readonly DisplayDocument[]>(() =>
  viewMode.value === "active" ? documents.value : recycledDocuments.value,
);
const filteredDocuments = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return sourceDocuments.value.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [item.title, item.original_filename, item.knowledge_base_name].some(
        (value) => value.toLowerCase().includes(keyword),
      );
    return (
      matchesQuery &&
      (viewMode.value === "recycle" ||
        statusFilter.value === "全部状态" ||
        statusLabel(item.status) === statusFilter.value)
    );
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

const statusLabel = (status: string): string =>
  ({
    uploaded: "已上传",
    detecting: "检测中",
    converting: "转换中",
    ocr: "OCR",
    normalizing: "标准化",
    chunking: "切分中",
    indexing: "索引中",
    ready: "已索引",
    failed: "失败",
    manual_review: "需复核",
    cancelled: "已取消",
  })[status] ?? status;

const statusTone = (status: string): string =>
  ({
    ready: "success",
    uploaded: "info",
    detecting: "info",
    converting: "info",
    ocr: "info",
    normalizing: "info",
    chunking: "info",
    indexing: "info",
    failed: "danger",
    manual_review: "warning",
    cancelled: "neutral",
  })[status] ?? "neutral";

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const formatDate = (value: string | null): string =>
  value === null ? "-" : new Date(value).toLocaleString("zh-CN");

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const activePage = await listAdminDocuments();
    documents.value = activePage.items;
    try {
      recycledDocuments.value = await listRecycleBin();
    } catch (error: unknown) {
      recycledDocuments.value = [];
      message.warning(`回收站加载失败：${toPublicApiError(error).message}`);
    }
    selectedDocumentIds.value = selectedDocumentIds.value.filter((id) =>
      (
        viewMode.value === "active"
          ? activePage.items
          : recycledDocuments.value
      ).some((item) => item.id === id),
    );
  } catch (error: unknown) {
    message.error(toPublicApiError(error).message);
  } finally {
    loading.value = false;
  }
};

const toggleDocument = (documentId: string): void => {
  selectedDocumentIds.value = selectedDocumentIds.value.includes(documentId)
    ? selectedDocumentIds.value.filter((id) => id !== documentId)
    : [...selectedDocumentIds.value, documentId];
};

const toggleAllVisible = (): void => {
  const visibleIds = new Set(pagedDocuments.value.map((item) => item.id));
  if (allVisibleSelected.value) {
    selectedDocumentIds.value = selectedDocumentIds.value.filter(
      (id) => !visibleIds.has(id),
    );
    return;
  }
  selectedDocumentIds.value = [
    ...new Set([...selectedDocumentIds.value, ...visibleIds]),
  ];
};

const reprocessSelected = async (ids = selectedDocumentIds.value): Promise<void> => {
  if (ids.length === 0) return;
  submitting.value = true;
  try {
    batchTasks.value = await batchReprocessDocuments(ids);
    message.success(`${ids.length} 个文档已进入重新处理队列`);
    selectedDocumentIds.value = [];
    await loadData();
  } catch (error: unknown) {
    message.error(toPublicApiError(error).message);
  } finally {
    submitting.value = false;
  }
};

const confirmDelete = (ids = selectedDocumentIds.value): void => {
  if (ids.length === 0) return;
  modal.confirm({
    title: `删除 ${ids.length} 个文档`,
    content:
      "文档将立即退出 RAG 检索并进入回收站，30 天内可以恢复。",
    okText: "移入回收站",
    okType: "danger",
    cancelText: "取消",
    onOk: async () => {
      submitting.value = true;
      try {
        const count = await batchDeleteDocuments(ids);
        message.success(`${count} 个文档已移入回收站`);
        selectedDocumentIds.value = [];
        await loadData();
      } finally {
        submitting.value = false;
      }
    },
  });
};

const restoreSelected = async (ids = selectedDocumentIds.value): Promise<void> => {
  if (ids.length === 0) return;
  submitting.value = true;
  try {
    batchTasks.value = await restoreDocuments(ids);
    message.success(`${ids.length} 个文档已恢复并开始重新处理`);
    selectedDocumentIds.value = [];
    await loadData();
  } catch (error: unknown) {
    message.error(toPublicApiError(error).message);
  } finally {
    submitting.value = false;
  }
};

watch(viewMode, () => {
  selectedDocumentIds.value = [];
  query.value = "";
  statusFilter.value = "全部状态";
});

onMounted(loadData);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="内容治理"
      title="文档管理"
      description="批量管理文档处理、索引重建和可恢复删除。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          <RefreshCw :size="17" aria-hidden="true" />
          刷新
        </button>
      </template>
    </PageHeader>

    <div class="reprocess-guide">
      <RotateCcw :size="19" aria-hidden="true" />
      <div>
        <strong>什么时候需要重新处理？</strong>
        <p>
          切换 Embedding 模型、调整切分配置或修复解析结果后，勾选文档重新处理，系统会重新生成 Markdown、分块和向量索引。
        </p>
      </div>
    </div>

    <DocumentTaskProgress
      v-if="batchTasks.length > 0"
      :items="batchTasks"
      @finished="loadData"
    />

    <ResourcePanel
      :title="viewMode === 'active' ? '文档清单' : '文档回收站'"
      :description="
        viewMode === 'active'
          ? `当前显示 ${filteredDocuments.length} 个有效文档`
          : `${filteredDocuments.length} 个文档可在到期前恢复`
      "
    >
      <template #actions>
        <div class="view-tabs" role="tablist" aria-label="文档视图">
          <button
            type="button"
            role="tab"
            :aria-selected="viewMode === 'active'"
            @click="viewMode = 'active'"
          >
            有效文档
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="viewMode === 'recycle'"
            @click="viewMode = 'recycle'"
          >
            回收站
            <span>{{ recycledDocuments.length }}</span>
          </button>
        </div>
      </template>

      <div class="filter-bar" aria-label="文档筛选">
        <label>
          <span>搜索文档</span>
          <input v-model="query" type="search" placeholder="文档名称或知识库" />
        </label>
        <label v-if="viewMode === 'active'">
          <span>处理状态</span>
          <select v-model="statusFilter">
            <option>全部状态</option>
            <option>已上传</option>
            <option>检测中</option>
            <option>转换中</option>
            <option>OCR</option>
            <option>标准化</option>
            <option>切分中</option>
            <option>索引中</option>
            <option>已索引</option>
            <option>失败</option>
            <option>需复核</option>
          </select>
        </label>
      </div>

      <div v-if="selectedDocumentIds.length > 0" class="batch-action-bar">
        <strong>已选择 {{ selectedDocumentIds.length }} 个文档</strong>
        <div>
          <button
            v-if="viewMode === 'active'"
            class="secondary-button"
            type="button"
            :disabled="submitting"
            @click="reprocessSelected()"
          >
            <RotateCcw :size="16" aria-hidden="true" />
            重新处理
          </button>
          <button
            v-if="viewMode === 'active'"
            class="danger-button"
            type="button"
            :disabled="submitting"
            @click="confirmDelete()"
          >
            <Trash2 :size="16" aria-hidden="true" />
            批量删除
          </button>
          <button
            v-else
            class="admin-primary-button"
            type="button"
            :disabled="submitting"
            @click="restoreSelected()"
          >
            <RotateCcw :size="16" aria-hidden="true" />
            批量恢复
          </button>
        </div>
      </div>

      <InlineState
        v-if="loading"
        kind="loading"
        title="正在加载文档"
        description="请稍候。"
      />
      <InlineState
        v-else-if="filteredDocuments.length === 0"
        kind="empty"
        :title="viewMode === 'active' ? '没有匹配的文档' : '回收站为空'"
        :description="
          viewMode === 'active'
            ? '上传文档后会在这里显示。'
            : '删除的文档会在保留期内显示于此。'
        "
      />
      <div v-else class="data-table-scroll" tabindex="0">
        <table class="data-table mobile-sticky-actions">
          <thead>
            <tr>
              <th scope="col" class="selection-column">
                <input
                  type="checkbox"
                  :checked="allVisibleSelected"
                  aria-label="选择当前页全部文档"
                  @change="toggleAllVisible"
                />
              </th>
              <th scope="col">文档</th>
              <th scope="col">知识库</th>
              <th scope="col">大小</th>
              <th scope="col">{{ viewMode === "active" ? "状态" : "清理时间" }}</th>
              <th scope="col">{{ viewMode === "active" ? "更新时间" : "删除时间" }}</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pagedDocuments" :key="item.id">
              <td>
                <input
                  type="checkbox"
                  :checked="selectedDocumentIds.includes(item.id)"
                  :aria-label="`选择 ${item.title}`"
                  @change="toggleDocument(item.id)"
                />
              </td>
              <td>
                <strong>{{ item.title }}</strong>
                <small>{{ item.original_filename }}</small>
              </td>
              <td>{{ item.knowledge_base_name }}</td>
              <td>{{ formatBytes(item.size_bytes) }}</td>
              <td>
                <span
                  v-if="viewMode === 'active'"
                  class="status-chip"
                  :class="statusTone(item.status)"
                >
                  {{ statusLabel(item.status) }}
                </span>
                <span v-else>{{ formatDate(item.purge_after) }}</span>
              </td>
              <td>
                {{
                  formatDate(
                    viewMode === "active" ? item.updated_at : item.deleted_at,
                  )
                }}
              </td>
              <td>
                <div class="table-actions">
                  <RouterLink
                    v-if="viewMode === 'active'"
                    class="text-button"
                    :to="`/knowledge/${item.knowledge_base_id}/documents/${item.id}`"
                  >
                    <Eye :size="15" aria-hidden="true" />
                    查看
                  </RouterLink>
                  <button
                    class="text-button"
                    type="button"
                    @click="detailDocument = item"
                  >
                    详情
                  </button>
                  <button
                    v-if="
                      viewMode === 'active' &&
                        ['failed', 'manual_review', 'ready'].includes(item.status)
                    "
                    class="text-button"
                    type="button"
                    @click="reprocessSelected([item.id])"
                  >
                    重新处理
                  </button>
                  <button
                    v-if="viewMode === 'active'"
                    class="text-button danger-text"
                    type="button"
                    @click="confirmDelete([item.id])"
                  >
                    删除
                  </button>
                  <button
                    v-else
                    class="text-button"
                    type="button"
                    @click="restoreSelected([item.id])"
                  >
                    恢复
                  </button>
                </div>
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
    </ResourcePanel>

    <Drawer
      :open="detailDocument !== undefined"
      title="文档详情"
      width="420"
      root-class-name="variant-admin"
      @close="detailDocument = undefined"
    >
      <dl v-if="detailDocument" class="detail-list">
        <div>
          <dt>文档名称</dt>
          <dd>{{ detailDocument.title }}</dd>
        </div>
        <div>
          <dt>原始文件名</dt>
          <dd>{{ detailDocument.original_filename }}</dd>
        </div>
        <div>
          <dt>所属知识库</dt>
          <dd>{{ detailDocument.knowledge_base_name }}</dd>
        </div>
        <div>
          <dt>切分配置</dt>
          <dd>
            {{ detailDocument.chunk_strategy }} /
            {{ detailDocument.chunk_size }} /
            {{ detailDocument.chunk_overlap }}
          </dd>
        </div>
        <div>
          <dt>处理状态</dt>
          <dd>{{ statusLabel(detailDocument.status) }}</dd>
        </div>
        <div v-if="detailDocument.error_message">
          <dt>错误信息</dt>
          <dd>{{ detailDocument.error_message }}</dd>
        </div>
        <div v-if="detailDocument.deleted_at">
          <dt>回收站保留至</dt>
          <dd>{{ formatDate(detailDocument.purge_after) }}</dd>
        </div>
      </dl>
    </Drawer>
  </div>
</template>

<style scoped>
.selection-column {
  width: 48px;
}

.reprocess-guide {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  border-left: 3px solid var(--color-primary);
  background: var(--color-primary-soft);
}

.reprocess-guide p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.view-tabs,
.batch-action-bar,
.batch-action-bar > div {
  display: flex;
  align-items: center;
}

.view-tabs {
  gap: var(--space-1);
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
}

.view-tabs button {
  min-height: 34px;
  padding: 0 var(--space-3);
  border-radius: calc(var(--radius-8) - 2px);
  color: var(--color-text-muted);
  background: transparent;
}

.view-tabs button[aria-selected="true"] {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.view-tabs span {
  margin-left: var(--space-1);
}

.batch-action-bar {
  min-height: 52px;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.batch-action-bar > div {
  gap: var(--space-2);
}

.danger-text {
  color: var(--color-danger);
}

@media (max-width: 767px) {
  .batch-action-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .batch-action-bar > div {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
