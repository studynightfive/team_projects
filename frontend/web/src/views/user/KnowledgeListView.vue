<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import InlineState from "../../components/InlineState.vue";
import { ArrowUpRight, BookOpen, Search } from "../../components/icons";
import { localPageData } from "../../data/local-pages";

const query = ref("");
const type = ref("全部类型");

const knowledgeBaseTypes = computed(() => [
  "全部类型",
  ...new Set(localPageData.knowledgeBases.map((item) => item.type)),
]);

const filteredKnowledgeBases = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase("zh-CN");

  return localPageData.knowledgeBases.filter((item) => {
    const matchesType = type.value === "全部类型" || item.type === type.value;
    const matchesQuery =
      normalizedQuery.length === 0 ||
      `${item.name}${item.description}`
        .toLocaleLowerCase("zh-CN")
        .includes(normalizedQuery);

    return matchesType && matchesQuery;
  });
});
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="用户工作区"
      title="企业知识库"
      description="浏览当前本地预览中的知识空间，正式可见范围等待权限契约。"
    >
      <template #actions>
        <RouterLink class="primary-button" to="/search">
          <Search :size="17" aria-hidden="true" />
          开始检索
        </RouterLink>
      </template>
    </PageHeader>

    <ResourcePanel
      title="可浏览知识库"
      description="固定展示数据仅用于确认卡片层级、筛选和响应式布局。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
      </template>

      <div class="filter-bar">
        <label class="filter-field grow">
          <span>搜索知识库</span>
          <input
            v-model="query"
            type="search"
            placeholder="搜索名称或说明"
            autocomplete="off"
          />
        </label>
        <label>
          <span>知识库类型</span>
          <select v-model="type">
            <option v-for="item in knowledgeBaseTypes" :key="item">
              {{ item }}
            </option>
          </select>
        </label>
        <span class="result-count">
          {{ filteredKnowledgeBases.length }} 个结果
        </span>
      </div>

      <div v-if="filteredKnowledgeBases.length > 0" class="knowledge-grid">
        <article
          v-for="item in filteredKnowledgeBases"
          :key="item.id"
          class="knowledge-card"
          :class="`tone-${item.tone}`"
        >
          <span class="knowledge-icon" aria-hidden="true">
            <BookOpen :size="22" :stroke-width="1.8" />
          </span>
          <div class="knowledge-card-copy">
            <span class="type-label">{{ item.type }}</span>
            <h3>{{ item.name }}</h3>
            <p>{{ item.description }}</p>
          </div>
          <div class="knowledge-card-meta">
            <span>{{ item.documents }} 个文档</span>
            <span>更新于 {{ item.updated }}</span>
          </div>
          <RouterLink
            class="card-link"
            :to="`/knowledge/${item.id}`"
            :aria-label="`进入${item.name}`"
          >
            查看文档
            <ArrowUpRight :size="16" aria-hidden="true" />
          </RouterLink>
        </article>
      </div>

      <InlineState
        v-else
        kind="empty"
        title="没有匹配的知识库"
        description="请调整关键词或类型；真实数据权限尚未接入。"
      />
    </ResourcePanel>
  </div>
</template>

<style scoped>
.local-page {
  display: grid;
  gap: var(--space-6);
}

.result-count {
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
  white-space: nowrap;
}

.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.knowledge-card {
  display: grid;
  min-width: 0;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.knowledge-icon {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.tone-green .knowledge-icon {
  color: var(--color-success-text);
  background: var(--color-success-soft);
}

.tone-violet .knowledge-icon {
  color: var(--color-admin);
  background: var(--color-admin-soft);
}

.tone-amber .knowledge-icon {
  color: var(--color-warning-text);
  background: var(--color-warning-soft);
}

.knowledge-card-copy {
  min-width: 0;
}

.type-label {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.knowledge-card h3 {
  margin: var(--space-1) 0 var(--space-2);
  font-size: var(--font-size-18);
}

.knowledge-card p {
  margin-bottom: 0;
  color: var(--color-text-muted);
}

.knowledge-card-meta,
.card-link {
  grid-column: 2;
  display: flex;
  align-items: center;
}

.knowledge-card-meta {
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
}

.card-link {
  width: fit-content;
  gap: var(--space-1);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
}

@media (max-width: 900px) {
  .knowledge-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .result-count {
    width: 100%;
    margin-left: 0;
  }

  .knowledge-card {
    padding: var(--space-4);
  }
}
</style>
