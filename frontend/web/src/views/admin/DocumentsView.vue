<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { localPageData } from "../../data/local-pages";

type DocumentItem = (typeof localPageData.adminDocuments)[number];

const { message, modal } = AntApp.useApp();
const documents = ref<DocumentItem[]>(
  localPageData.adminDocuments.map((item) => ({ ...item })),
);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedId = ref<string>();
const selectedDocument = computed(() =>
  documents.value.find((item) => item.id === selectedId.value),
);
const filteredDocuments = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return documents.value.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [item.name, item.knowledgeBase].some((value) =>
        value.toLowerCase().includes(keyword),
      );
    return (
      matchesQuery &&
      (statusFilter.value === "全部状态" || item.status === statusFilter.value)
    );
  });
});

const statusTone = (status: string): string =>
  ({
    已索引: "success",
    处理中: "info",
    失败: "danger",
    需复核: "warning",
  })[status] ?? "neutral";

const previewUpload = (): void => {
  void message.info("上传区域仅作视觉预览，未读取任何本地文件");
};

const retryPreview = (id: string): void => {
  const item = documents.value.find((document) => document.id === id);
  if (item === undefined) return;
  item.status = "处理中";
  void message.success("文档已切换为本地重试预览状态");
};

const confirmDelete = (id: string): void => {
  const item = documents.value.find((document) => document.id === id);
  if (item === undefined) return;
  modal.confirm({
    title: "删除文档预览",
    content: "仅从当前页面移除，不会删除文件、索引或存储对象。",
    okText: "确认本地预览",
    cancelText: "取消",
    onOk: () => {
      documents.value = documents.value.filter(
        (document) => document.id !== id,
      );
      void message.success(item.name + " 已从本地预览中移除");
    },
  });
};
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="内容治理"
      title="文档管理"
      description="预览上传入口、独立文件状态、筛选、详情、删除和重试流程。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
        <button
          class="admin-primary-button"
          type="button"
          @click="previewUpload"
        >
          选择文件
        </button>
      </template>
    </PageHeader>

    <section
      class="upload-preview"
      aria-label="文档上传预览区域"
      @dragover.prevent
      @drop.prevent="previewUpload"
    >
      <strong>拖拽文档到这里</strong>
      <span>本地版本不会读取文件内容，也不会开始上传。</span>
      <button class="secondary-button" type="button" @click="previewUpload">
        查看上传说明
      </button>
    </section>

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
            <option>已索引</option>
            <option>处理中</option>
            <option>失败</option>
            <option>需复核</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="filteredDocuments.length === 0"
        kind="empty"
        title="没有匹配的文档"
        description="请调整关键词或处理状态。"
      />
      <div
        v-else
        class="data-table-scroll"
        tabindex="0"
        aria-label="文档表格，可横向滚动"
      >
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
            <tr v-for="item in filteredDocuments" :key="item.id">
              <td>
                <strong>{{ item.name }}</strong>
              </td>
              <td>{{ item.knowledgeBase }}</td>
              <td>{{ item.size }}</td>
              <td>
                <span class="status-chip" :class="statusTone(item.status)">
                  {{ item.status }}
                </span>
              </td>
              <td>{{ item.updated }}</td>
              <td>
                <div class="table-actions">
                  <button
                    class="text-button"
                    type="button"
                    @click="selectedId = item.id"
                  >
                    预览
                  </button>
                  <button
                    v-if="item.status === '失败'"
                    class="text-button"
                    type="button"
                    @click="retryPreview(item.id)"
                  >
                    重试
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmDelete(item.id)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </ResourcePanel>

    <Drawer
      :open="selectedDocument !== undefined"
      title="文档详情（本地预览）"
      width="420"
      root-class-name="variant-admin"
      @close="selectedId = undefined"
    >
      <dl v-if="selectedDocument" class="detail-list">
        <div>
          <dt>文档名称</dt>
          <dd>{{ selectedDocument.name }}</dd>
        </div>
        <div>
          <dt>所属知识库</dt>
          <dd>{{ selectedDocument.knowledgeBase }}</dd>
        </div>
        <div>
          <dt>文件大小</dt>
          <dd>{{ selectedDocument.size }}</dd>
        </div>
        <div>
          <dt>处理状态</dt>
          <dd>{{ selectedDocument.status }}</dd>
        </div>
        <div>
          <dt>更新时间</dt>
          <dd>{{ selectedDocument.updated }}</dd>
        </div>
      </dl>
      <p class="preview-note">
        无文档接口前不读取文件正文，也不提供真实预览或下载地址。
      </p>
    </Drawer>
  </div>
</template>

<style scoped>
.upload-preview {
  display: grid;
  min-height: 150px;
  align-content: center;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-6);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-12);
  color: var(--color-text-muted);
  background: var(--color-surface);
  text-align: center;
}

.upload-preview strong {
  color: var(--color-text);
  font-size: var(--font-size-16);
}
</style>
