<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, ref, watch } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { localPageData } from "../../data/local-pages";

const { message } = AntApp.useApp();
const allDocumentsValue = "all";
const query = ref("发布前需要完成哪些检查？");
const mode = ref("混合");
const knowledgeBaseId = ref(localPageData.sampleRoutes.knowledgeBaseId);
const documentScope = ref(allDocumentsValue);
const topK = ref(8);
const threshold = ref(0.62);
const hasRun = ref(false);
const requestId = "demo-retrieval-preview";

const availableDocuments = computed(() =>
  localPageData.documents.filter(
    (document) => document.knowledgeBaseId === knowledgeBaseId.value,
  ),
);
const filteredResults = computed(() =>
  localPageData.retrievalResults
    .filter(
      (result) =>
        result.knowledgeBaseId === knowledgeBaseId.value &&
        (documentScope.value === allDocumentsValue ||
          result.documentId === documentScope.value) &&
        Number.parseFloat(result.score) >= threshold.value,
    )
    .slice(0, topK.value),
);

const getKnowledgeBaseName = (id: string): string =>
  localPageData.knowledgeBases.find((item) => item.id === id)?.name ??
  "未知知识库";

watch(knowledgeBaseId, () => {
  documentScope.value = allDocumentsValue;
});

const runPreview = (): void => {
  if (query.value.trim().length === 0) {
    void message.warning("请输入测试问题");
    return;
  }
  hasRun.value = true;
  void message.success("已生成固定本地结果，未发送检索请求");
};
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="检索质量"
      title="命中率测试"
      description="保留检索模式、范围、TopK 和阈值，使用固定结果验证页面结构。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
      </template>
    </PageHeader>

    <div class="retrieval-test-layout">
      <ResourcePanel
        title="测试参数"
        description="参数名称与范围等待 OpenAPI 确认。"
      >
        <form class="retrieval-form" @submit.prevent="runPreview">
          <label>
            <span>测试问题</span>
            <textarea v-model="query" rows="4" />
          </label>
          <label>
            <span>检索模式</span>
            <select v-model="mode">
              <option>混合</option>
              <option>向量</option>
              <option>关键词</option>
            </select>
          </label>
          <label>
            <span>知识库</span>
            <select v-model="knowledgeBaseId">
              <option
                v-for="item in localPageData.knowledgeBases"
                :key="item.id"
                :value="item.id"
              >
                {{ item.name }}
              </option>
            </select>
          </label>
          <label>
            <span>文档范围</span>
            <select v-model="documentScope">
              <option :value="allDocumentsValue">全部文档</option>
              <option
                v-for="document in availableDocuments"
                :key="document.id"
                :value="document.id"
              >
                {{ document.name }}
              </option>
            </select>
          </label>
          <div class="parameter-grid">
            <label>
              <span>TopK</span>
              <input
                v-model.number="topK"
                type="number"
                min="1"
                max="50"
                step="1"
              />
            </label>
            <label>
              <span>阈值 {{ threshold.toFixed(2) }}</span>
              <input
                v-model.number="threshold"
                type="range"
                min="0"
                max="1"
                step="0.01"
              />
            </label>
          </div>
          <button class="admin-primary-button" type="submit">
            运行本地测试
          </button>
        </form>
      </ResourcePanel>

      <ResourcePanel
        title="固定测试结果"
        :description="
          hasRun
            ? mode +
              '模式 · TopK ' +
              String(topK) +
              ' · 阈值 ' +
              threshold.toFixed(2) +
              ' · ' +
              requestId
            : '运行后显示确定性结果'
        "
      >
        <InlineState
          v-if="!hasRun"
          kind="empty"
          title="尚未运行测试"
          description="设置参数并运行本地测试，不会访问检索服务。"
        />
        <ol v-else-if="filteredResults.length > 0" class="retrieval-results">
          <li v-for="(result, index) in filteredResults" :key="result.id">
            <div class="result-rank">{{ index + 1 }}</div>
            <div>
              <header>
                <strong>{{ result.title }}</strong>
                <span class="status-chip info">{{ result.score }}</span>
              </header>
              <p>{{ result.snippet }}</p>
              <small>
                第 {{ result.page }} 页 ·
                {{ getKnowledgeBaseName(result.knowledgeBaseId) }}
              </small>
            </div>
          </li>
        </ol>
        <InlineState
          v-else
          kind="empty"
          title="没有命中当前参数的固定结果"
          description="请降低阈值、扩大文档范围或切换到包含固定样例的知识库。"
        />
      </ResourcePanel>
    </div>
  </div>
</template>

<style scoped>
.retrieval-test-layout {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  align-items: start;
  gap: var(--space-6);
}

.retrieval-form {
  display: grid;
  gap: var(--space-4);
}

.retrieval-form label {
  display: grid;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}

.retrieval-form input,
.retrieval-form select,
.retrieval-form textarea {
  width: 100%;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.retrieval-results {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.retrieval-results li {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
}

.retrieval-results header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
}

.retrieval-results p {
  margin: var(--space-2) 0;
  color: var(--color-text-secondary);
}

.retrieval-results small {
  color: var(--color-text-muted);
}

.result-rank {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-admin);
  background: var(--color-admin-soft);
  font-weight: var(--font-weight-semibold);
}

@media (max-width: 1180px) {
  .retrieval-test-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .parameter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
