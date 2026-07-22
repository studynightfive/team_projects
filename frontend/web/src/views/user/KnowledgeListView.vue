<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { isRealApiMode } from "../../config/runtime";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import { useListPagination } from "../../composables/useListPagination";
import { ArrowUpRight, BookOpen, Search } from "../../components/icons";
import { localPageData } from "../../data/local-pages";
import { toPublicApiError } from "../../api/client";
import {
  listKnowledgeBases,
  type KnowledgeBaseRecord,
} from "../../services/knowledge";
const query = ref("");
const type = ref("全部类型");
const realKnowledgeBases = ref<readonly KnowledgeBaseRecord[]>([]);
const loadState = ref<"idle" | "loading" | "error">("idle");
const loadError = ref("");

let loadController: AbortController | undefined;

const realItems = computed(() =>
  realKnowledgeBases.value.map((item, index) => ({
    id: item.id,
    name: item.name,
    description: item.description ?? "暂无说明",
    type: item.kind === "personal" ? "个人知识库" : item.department_name,
    tone: (["blue", "green", "violet", "amber"][index % 4] ?? "blue") as
      | "blue"
      | "green"
      | "violet"
      | "amber",
    documents: item.document_count,
    readyDocuments: item.ready_document_count,
    chunks: item.chunk_count,
    updated:
      item.updated_at === null
        ? "刚刚"
        : new Intl.DateTimeFormat("zh-CN", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          }).format(new Date(item.updated_at)),
  })),
);

const displayItems = computed(() =>
  isRealApiMode ? realItems.value : localPageData.knowledgeBases,
);

const knowledgeBaseTypes = computed(() => [
  "全部类型",
  ...new Set(displayItems.value.map((item) => item.type)),
]);

const filteredKnowledgeBases = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase("zh-CN");

  return displayItems.value.filter((item) => {
    const matchesType = type.value === "全部类型" || item.type === type.value;
    const matchesQuery =
      normalizedQuery.length === 0 ||
      `${item.name}${item.description}`
        .toLocaleLowerCase("zh-CN")
        .includes(normalizedQuery);

    return matchesType && matchesQuery;
  });
});
const {
  page: knowledgeBasesPage,
  pageSize: knowledgeBasesPageSize,
  pagedItems: pagedKnowledgeBases,
  setPage: setKnowledgeBasesPage,
} = useListPagination(filteredKnowledgeBases);

const loadRealKnowledgeBases = async (): Promise<void> => {
  if (!isRealApiMode) return;
  loadController?.abort();
  loadController = new AbortController();
  loadState.value = "loading";
  loadError.value = "";
  try {
    realKnowledgeBases.value = await listKnowledgeBases(loadController.signal);
    loadState.value = "idle";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = toPublicApiError(error).message;
    loadState.value = "error";
  }
};

onMounted(() => {
  void loadRealKnowledgeBases();
});

onBeforeUnmount(() => {
  loadController?.abort();
});
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="用户工作区"
      title="企业知识库"
      :description="
        isRealApiMode
          ? '浏览本部门企业知识库，并管理仅自己可见的个人知识库。'
          : '浏览当前本地预览中的知识空间，正式可见范围等待权限契约。'
      "
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
      :description="
        isRealApiMode
          ? '展示当前账号可访问的真实知识库。'
          : '固定展示数据仅用于确认卡片层级、筛选和响应式布局。'
      "
    >
      <template #actions>
        <span class="local-preview-badge">{{
          isRealApiMode ? "真实接口" : "本地预览"
        }}</span>
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

      <InlineState
        v-if="loadState === 'loading'"
        kind="loading"
        title="正在加载知识库"
        description="正在读取当前账号可访问的知识库。"
      />

      <InlineState
        v-else-if="loadState === 'error'"
        kind="error"
        title="知识库加载失败"
        :description="loadError"
      />

      <div v-else-if="filteredKnowledgeBases.length > 0" class="knowledge-grid">
        <article
          v-for="item in pagedKnowledgeBases"
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
            <span v-if="'readyDocuments' in item">
              {{ item.readyDocuments }} 个已就绪
            </span>
            <span v-if="'chunks' in item">{{ item.chunks }} 个分块</span>
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
      <ListPagination
        v-if="filteredKnowledgeBases.length > 0"
        :page="knowledgeBasesPage"
        :page-size="knowledgeBasesPageSize"
        :total="filteredKnowledgeBases.length"
        @change="setKnowledgeBasesPage"
      />

      <InlineState
        v-else
        kind="empty"
        title="没有匹配的知识库"
        :description="
          isRealApiMode
            ? '请调整关键词或类型；企业知识库由管理中心维护。'
            : '请调整关键词或类型；真实数据权限尚未接入。'
        "
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

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
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

  .parameter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
