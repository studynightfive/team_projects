<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { ArrowUpRight, RefreshCw, Search } from "../../components/icons";
import { localPageData } from "../../data/local-pages";

type SearchMode = "关键词" | "向量" | "混合";

const { message } = AntApp.useApp();
const route = useRoute();
const mode = ref<SearchMode>("混合");
const query = ref("");
const submittedQuery = ref("");
const knowledgeBaseId = ref("全部知识库");
const tag = ref("全部标签");
const topK = ref(8);
const threshold = ref(62);

const tags = computed(() => [
  "全部标签",
  ...new Set(localPageData.searchResults.flatMap((item) => item.tags)),
]);

const filteredResults = computed(() => {
  const normalizedQuery = submittedQuery.value
    .trim()
    .toLocaleLowerCase("zh-CN");

  return localPageData.searchResults
    .filter((item) => {
      const matchesKnowledgeBase =
        knowledgeBaseId.value === "全部知识库" ||
        item.knowledgeBaseId === knowledgeBaseId.value;
      const matchesTag =
        tag.value === "全部标签" || item.tags.includes(tag.value);
      const matchesQuery =
        normalizedQuery.length === 0 ||
        `${item.title}${item.snippet}${item.tags.join("")}`
          .toLocaleLowerCase("zh-CN")
          .includes(normalizedQuery);
      const score = Number.parseInt(item.score, 10);

      return (
        matchesKnowledgeBase &&
        matchesTag &&
        matchesQuery &&
        score >= threshold.value
      );
    })
    .slice(0, topK.value);
});

watch(
  () => route.query.q,
  (value) => {
    const nextQuery = typeof value === "string" ? value.trim() : "";
    query.value = nextQuery || "发布";
    submittedQuery.value = query.value;
  },
  { immediate: true },
);

const submitSearch = (): void => {
  const nextQuery = query.value.trim();
  if (nextQuery.length === 0) {
    void message.warning("请输入检索内容");
    return;
  }

  submittedQuery.value = nextQuery;
  void message.info(`${mode.value}检索已在固定数据中完成，不会发送业务请求`);
};

const resetSearch = (): void => {
  mode.value = "混合";
  query.value = "发布";
  submittedQuery.value = "发布";
  knowledgeBaseId.value = "全部知识库";
  tag.value = "全部标签";
  topK.value = 8;
  threshold.value = 62;
};
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="用户工作区"
      title="知识检索"
      description="比较关键词、向量和混合检索的页面流程；结果来自固定本地数据。"
    >
      <template #actions>
        <span class="local-preview-badge">业务 API 请求为 0</span>
      </template>
    </PageHeader>

    <ResourcePanel
      title="检索条件"
      description="参数只保留在当前页面，刷新后恢复默认。"
    >
      <form class="search-form" @submit.prevent="submitSearch">
        <fieldset class="mode-switcher">
          <legend>检索方式</legend>
          <button
            v-for="item in ['关键词', '向量', '混合'] as const"
            :key="item"
            type="button"
            :class="{ active: mode === item }"
            :aria-pressed="mode === item"
            @click="mode = item"
          >
            {{ item }}
          </button>
        </fieldset>

        <label class="query-field">
          <span>检索内容</span>
          <span class="query-input">
            <Search :size="18" aria-hidden="true" />
            <input
              v-model="query"
              type="search"
              placeholder="输入关键词或问题"
              autocomplete="off"
            />
          </span>
        </label>

        <div class="parameter-grid">
          <label>
            <span>知识库</span>
            <select v-model="knowledgeBaseId">
              <option>全部知识库</option>
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
            <span>元数据标签</span>
            <select v-model="tag">
              <option v-for="item in tags" :key="item">{{ item }}</option>
            </select>
          </label>
          <label>
            <span>TopK：{{ topK }}</span>
            <input v-model.number="topK" type="range" min="3" max="20" />
          </label>
          <label>
            <span>相关度阈值：{{ threshold }}%</span>
            <input v-model.number="threshold" type="range" min="40" max="90" />
          </label>
        </div>

        <div class="form-actions">
          <button class="primary-button" type="submit">
            <Search :size="17" aria-hidden="true" />
            开始本地检索
          </button>
          <button class="secondary-button" type="button" @click="resetSearch">
            <RefreshCw :size="17" aria-hidden="true" />
            重置参数
          </button>
        </div>
      </form>
    </ResourcePanel>

    <ResourcePanel
      title="检索结果"
      :description="`“${submittedQuery}” · ${mode}模式 · ${filteredResults.length} 条固定结果`"
    >
      <div v-if="filteredResults.length > 0" class="search-results">
        <article v-for="item in filteredResults" :key="item.id">
          <div class="result-heading">
            <div>
              <span>{{ item.score }} 相关</span>
              <h3>{{ item.title }}</h3>
            </div>
            <span>第 {{ item.page }} 页</span>
          </div>
          <p>{{ item.snippet }}</p>
          <div class="result-footer">
            <div class="tag-list" aria-label="结果标签">
              <span v-for="itemTag in item.tags" :key="itemTag">
                {{ itemTag }}
              </span>
            </div>
            <RouterLink
              :to="`/knowledge/${item.knowledgeBaseId}/documents/${item.documentId}?page=${item.page}`"
            >
              查看原文
              <ArrowUpRight :size="16" aria-hidden="true" />
            </RouterLink>
          </div>
        </article>
      </div>

      <InlineState
        v-else
        kind="empty"
        title="未找到匹配内容"
        description="请尝试更短的关键词、其他标签或全部知识库。"
      />
    </ResourcePanel>
  </div>
</template>

<style scoped>
.local-page,
.search-form,
.search-results {
  display: grid;
  gap: var(--space-6);
}

.mode-switcher {
  display: flex;
  width: fit-content;
  gap: var(--space-1);
  margin: 0;
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
}

.mode-switcher legend {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.mode-switcher button {
  min-height: 36px;
  padding: 0 var(--space-4);
  border-radius: 6px;
  color: var(--color-text-muted);
  background: transparent;
}

.mode-switcher button.active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: var(--font-weight-medium);
}

.query-field,
.parameter-grid label {
  display: grid;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.query-input {
  display: flex;
  min-height: 44px;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.query-input:focus-within {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-focus);
}

.query-input input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}

.parameter-grid span {
  font-size: var(--font-size-13);
}

.parameter-grid select {
  width: 100%;
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.form-actions,
.result-footer,
.result-heading {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.search-results article {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
}

.result-heading,
.result-footer {
  justify-content: space-between;
}

.result-heading h3 {
  margin: var(--space-1) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-18);
}

.result-heading span,
.search-results p {
  color: var(--color-text-muted);
}

.search-results p {
  margin-bottom: 0;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tag-list span {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-4);
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  font-size: var(--font-size-12);
}

.result-footer a {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .parameter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .search-form input,
  .search-form select,
  .search-form button {
    min-height: 44px;
  }

  .mode-switcher,
  .form-actions,
  .result-heading,
  .result-footer {
    width: 100%;
    align-items: stretch;
  }

  .mode-switcher button {
    flex: 1;
    min-height: 44px;
    padding: 0 var(--space-2);
  }

  .parameter-grid,
  .form-actions,
  .result-heading,
  .result-footer {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
