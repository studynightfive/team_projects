<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  Bot,
  BookOpen,
  ChevronRight,
  Search,
  ShieldCheck,
} from "../../components/icons";
import {
  helpCategories,
  helpTopics,
  type HelpCategory,
} from "../../data/account-support";

const keyword = ref("");
const category = ref<"all" | HelpCategory>("all");

const filteredTopics = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase("zh-CN");

  return helpTopics.filter(
    (topic) =>
      (category.value === "all" || topic.category === category.value) &&
      (normalizedKeyword.length === 0 ||
        `${topic.question}${topic.answer}${topic.category}`
          .toLocaleLowerCase("zh-CN")
          .includes(normalizedKeyword)),
  );
});
</script>

<template>
  <div class="business-page help-center-page">
    <PageHeader
      eyebrow="账号与支持"
      title="帮助中心"
      description="查找常见问题、了解当前能力边界，并快速进入已有核心功能。"
    >
      <template #actions>
        <span class="local-preview-badge">本地帮助内容</span>
      </template>
    </PageHeader>

    <section class="help-entry-grid" aria-label="常用帮助入口">
      <RouterLink to="/" class="help-entry-card">
        <span aria-hidden="true"><Search :size="22" /></span>
        <div>
          <strong>开始 AI 搜索</strong>
          <p>用具体问题查找企业知识和可核验来源。</p>
        </div>
        <ChevronRight :size="18" aria-hidden="true" />
      </RouterLink>
      <RouterLink to="/knowledge" class="help-entry-card">
        <span aria-hidden="true"><BookOpen :size="22" /></span>
        <div>
          <strong>浏览企业知识库</strong>
          <p>按知识库和文档目录查看已有内容。</p>
        </div>
        <ChevronRight :size="18" aria-hidden="true" />
      </RouterLink>
      <RouterLink to="/preferences" class="help-entry-card">
        <span aria-hidden="true"><ShieldCheck :size="22" /></span>
        <div>
          <strong>账号与偏好</strong>
          <p>了解安全边界并预览个人使用偏好。</p>
        </div>
        <ChevronRight :size="18" aria-hidden="true" />
      </RouterLink>
    </section>

    <ResourcePanel
      title="常见问题"
      description="展开问题查看说明；当前不会提交工单或连接外部客服。"
    >
      <div class="help-filter-bar">
        <label class="help-search-field">
          <span class="visually-hidden">搜索帮助内容</span>
          <Search :size="18" aria-hidden="true" />
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索问题、功能或安全说明"
            autocomplete="off"
          />
        </label>
        <label class="help-category-field">
          <span>问题分类</span>
          <select v-model="category">
            <option value="all">全部分类</option>
            <option v-for="item in helpCategories" :key="item">
              {{ item }}
            </option>
          </select>
        </label>
      </div>

      <div v-if="filteredTopics.length > 0" class="faq-list">
        <details v-for="topic in filteredTopics" :key="topic.id">
          <summary>
            <span>
              <small>{{ topic.category }}</small>
              <strong>{{ topic.question }}</strong>
            </span>
            <ChevronRight :size="18" aria-hidden="true" />
          </summary>
          <p>{{ topic.answer }}</p>
        </details>
      </div>

      <InlineState
        v-else
        kind="empty"
        title="没有找到相关帮助"
        description="请尝试更短的关键词，或切换到全部分类。"
      />

      <template #footer>
        <span>共 {{ filteredTopics.length }} 个问题</span>
        <span class="help-security-note">
          <Bot :size="15" aria-hidden="true" />
          高风险操作请以项目规范和后端权限结果为准
        </span>
      </template>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.help-center-page {
  gap: var(--space-5);
}

.help-entry-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.help-entry-card {
  display: grid;
  min-width: 0;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  text-decoration: none;
}

.help-entry-card > span {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.help-entry-card strong {
  display: block;
  color: var(--color-text);
  font-size: var(--font-size-15);
}

.help-entry-card p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
  line-height: 1.55;
}

.help-filter-bar,
.help-search-field,
.help-security-note {
  display: flex;
  align-items: center;
}

.help-filter-bar {
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.help-search-field {
  min-height: 40px;
  flex: 1 1 360px;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
}

.help-search-field input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
}

.help-search-field input:focus-visible {
  box-shadow: none;
}

.help-category-field {
  display: grid;
  min-width: 190px;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.help-category-field select {
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text);
  background: var(--color-surface);
}

.faq-list {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
}

.faq-list details {
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.faq-list details:first-child {
  border-top: 0;
}

.faq-list summary {
  display: flex;
  min-height: 72px;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  cursor: pointer;
  list-style: none;
}

.faq-list summary::-webkit-details-marker {
  display: none;
}

.faq-list summary span {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.faq-list summary small {
  color: var(--color-primary);
  font-size: var(--font-size-12);
}

.faq-list summary strong {
  color: var(--color-text);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-medium);
}

.faq-list summary svg {
  flex: none;
  transition: transform var(--transition-fast);
}

.faq-list details[open] summary svg {
  transform: rotate(90deg);
}

.faq-list details > p {
  margin: 0;
  padding: 0 var(--space-4) var(--space-5);
  color: var(--color-text-secondary);
  line-height: 1.75;
}

.help-security-note {
  gap: var(--space-1);
}

@media (max-width: 900px) {
  .help-entry-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .help-filter-bar {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }

  .help-search-field,
  .help-category-field {
    width: 100%;
    min-height: 44px;
  }

  .help-category-field select {
    min-height: 44px;
  }

  .help-entry-card {
    padding: var(--space-4);
  }

  .faq-list summary {
    min-height: 76px;
  }
}
</style>
