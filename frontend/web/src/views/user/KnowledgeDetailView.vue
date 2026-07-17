<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { ChevronLeft, Download, Eye } from "../../components/icons";
import { localPageData } from "../../data/local-pages";

const route = useRoute();
const { message } = AntApp.useApp();
const query = ref("");
const status = ref("全部状态");
const selectedDocumentIds = ref<string[]>([]);

const knowledgeBase = computed(() =>
  localPageData.knowledgeBases.find(
    (item) => item.id === String(route.params.kb_id ?? ""),
  ),
);

const filteredDocuments = computed(() => {
  const currentKnowledgeBaseId = knowledgeBase.value?.id;
  if (currentKnowledgeBaseId === undefined) return [];

  const normalizedQuery = query.value.trim().toLocaleLowerCase("zh-CN");

  return localPageData.documents.filter((item) => {
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

const allVisibleSelected = computed(
  () =>
    filteredDocuments.value.length > 0 &&
    filteredDocuments.value.every((item) =>
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
    const visibleIds = new Set(filteredDocuments.value.map((item) => item.id));
    selectedDocumentIds.value = selectedDocumentIds.value.filter(
      (id) => !visibleIds.has(id),
    );
    return;
  }

  selectedDocumentIds.value = [
    ...new Set([
      ...selectedDocumentIds.value,
      ...filteredDocuments.value.map((item) => item.id),
    ]),
  ];
};

const previewExport = (): void => {
  void message.info(
    `已选择 ${selectedDocumentIds.value.length} 个文档；导出仅展示本地配置，不会创建任务`,
  );
};
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="企业知识库 / 文档目录"
      :title="knowledgeBase?.name ?? '知识库不存在'"
      :description="
        knowledgeBase?.description ?? '当前固定样例中没有此知识库。'
      "
    >
      <template #actions>
        <RouterLink class="secondary-button" to="/knowledge">
          <ChevronLeft :size="17" aria-hidden="true" />
          返回知识库
        </RouterLink>
        <button
          class="primary-button"
          type="button"
          :disabled="selectedDocumentIds.length === 0"
          @click="previewExport"
        >
          <Download :size="17" aria-hidden="true" />
          导出所选（{{ selectedDocumentIds.length }}）
        </button>
      </template>
    </PageHeader>

    <InlineState
      v-if="!knowledgeBase"
      kind="error"
      title="未找到知识库"
      description="请从知识库列表重新进入；此状态不会请求业务接口。"
    />

    <ResourcePanel
      v-else
      title="文档目录"
      :description="`${knowledgeBase.documents} 个文档为页面层级示意，当前展示固定样例。`"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
      </template>

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

      <div
        v-if="filteredDocuments.length > 0"
        class="data-table-scroll"
        tabindex="0"
        aria-label="文档目录表格，可横向滚动"
      >
        <table class="data-table document-table">
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
            <tr v-for="item in filteredDocuments" :key="item.id">
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

      <InlineState
        v-else
        kind="empty"
        title="没有匹配的文档"
        description="请清除关键词或切换状态筛选。"
      />

      <template #footer>
        <span>当前展示 {{ filteredDocuments.length }} 条固定样例</span>
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
</style>
