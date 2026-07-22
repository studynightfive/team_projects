<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { useListPagination } from "../../composables/useListPagination";
import { listAdminDocuments, type AdminDocument } from "../../services/admin";
import { deleteDocument, reprocessDocument } from "../../services/knowledge";

const { message, modal } = AntApp.useApp();
const documents = ref<readonly AdminDocument[]>([]);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedId = ref<string>();
const loading = ref(false);
const selectedDocument = computed(() =>
  documents.value.find((item) => item.id === selectedId.value),
);
const filteredDocuments = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return documents.value.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [item.title, item.original_filename, item.knowledge_base_name].some(
        (value) => value.toLowerCase().includes(keyword),
      );
    return (
      matchesQuery &&
      (statusFilter.value === "全部状态" ||
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
    const page = await listAdminDocuments();
    documents.value = page.items;
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

const retryDocument = async (id: string): Promise<void> => {
  try {
    await reprocessDocument(id);
    message.success("文档已重新进入处理流程");
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  }
};

const confirmDelete = (item: AdminDocument): void => {
  modal.confirm({
    title: "删除文档",
    content: `确认删除 ${item.title}？此操作会删除文件、索引和处理记录。`,
    okText: "确认删除",
    cancelText: "取消",
    onOk: async () => {
      await deleteDocument(item.id);
      message.success("文档已删除");
      await loadData();
    },
  });
};

onMounted(loadData);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="内容治理"
      title="文档管理"
      description="查看所有真实文档的知识库归属、处理状态和索引结果。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="文档清单"
      :description="'当前显示 ' + String(filteredDocuments.length) + ' 个文档'"
    >
      <div class="filter-bar" aria-label="文档筛选">
        <label>
          <span>搜索文档</span>
          <input v-model="query" type="search" placeholder="文档名称或知识库" />
        </label>
        <label>
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

      <InlineState
        v-if="loading"
        kind="loading"
        title="正在加载文档"
        description="请稍候。"
      />
      <InlineState
        v-else-if="filteredDocuments.length === 0"
        kind="empty"
        title="没有匹配的文档"
        description="上传文档后会在这里显示。"
      />
      <div v-else class="data-table-scroll" tabindex="0">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">文档</th>
              <th scope="col">知识库</th>
              <th scope="col">大小</th>
              <th scope="col">状态</th>
              <th scope="col">更新时间</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pagedDocuments" :key="item.id">
              <td>
                <strong>{{ item.title }}</strong>
                <small>{{ item.original_filename }}</small>
              </td>
              <td>{{ item.knowledge_base_name }}</td>
              <td>{{ formatBytes(item.size_bytes) }}</td>
              <td>
                <span class="status-chip" :class="statusTone(item.status)">
                  {{ statusLabel(item.status) }}
                </span>
              </td>
              <td>{{ formatDate(item.updated_at) }}</td>
              <td>
                <div class="table-actions">
                  <RouterLink
                    class="text-button"
                    :to="`/knowledge/${item.knowledge_base_id}/documents/${item.id}`"
                  >
                    查看
                  </RouterLink>
                  <button
                    class="text-button"
                    type="button"
                    @click="selectedId = item.id"
                  >
                    详情
                  </button>
                  <button
                    v-if="['failed', 'manual_review', 'ready'].includes(item.status)"
                    class="text-button"
                    type="button"
                    @click="retryDocument(item.id)"
                  >
                    重试
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmDelete(item)"
                  >
                    删除
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
      :open="selectedDocument !== undefined"
      title="文档详情"
      width="420"
      root-class-name="variant-admin"
      @close="selectedId = undefined"
    >
      <dl v-if="selectedDocument" class="detail-list">
        <div>
          <dt>文档名称</dt>
          <dd>{{ selectedDocument.title }}</dd>
        </div>
        <div>
          <dt>原始文件名</dt>
          <dd>{{ selectedDocument.original_filename }}</dd>
        </div>
        <div>
          <dt>所属知识库</dt>
          <dd>{{ selectedDocument.knowledge_base_name }}</dd>
        </div>
        <div>
          <dt>文件大小</dt>
          <dd>{{ formatBytes(selectedDocument.size_bytes) }}</dd>
        </div>
        <div>
          <dt>处理状态</dt>
          <dd>{{ statusLabel(selectedDocument.status) }}</dd>
        </div>
        <div v-if="selectedDocument.error_message">
          <dt>错误信息</dt>
          <dd>{{ selectedDocument.error_message }}</dd>
        </div>
        <div>
          <dt>更新时间</dt>
          <dd>{{ formatDate(selectedDocument.updated_at) }}</dd>
        </div>
      </dl>
    </Drawer>
  </div>
</template>
