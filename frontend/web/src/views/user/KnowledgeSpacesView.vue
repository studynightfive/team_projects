<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import {
  BookOpen,
  ChevronRight,
  Search,
  SquareLibrary,
} from "../../components/icons";
import { useListPagination } from "../../composables/useListPagination";
import { isRealApiMode } from "../../config/runtime";
import { aiSearchMockData } from "../../mocks/ai-search";
import {
  listKnowledgeBases,
  type KnowledgeBaseRecord,
} from "../../services/knowledge";

interface DisplaySpace {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly department: string;
  readonly scope: string;
  readonly documentCount: number;
  readonly readyDocumentCount: number;
  readonly chunkCount: number;
}

const route = useRoute();
const router = useRouter();
const keyword = ref("");
const department = ref("all");
const realKnowledgeBases = ref<readonly KnowledgeBaseRecord[]>([]);
const loadState = ref<"idle" | "loading" | "success" | "error">("idle");
const loadError = ref("");
let loadController: AbortController | undefined;

const realSpaces = computed<readonly DisplaySpace[]>(() =>
  realKnowledgeBases.value.map((kb) => ({
    id: kb.id,
    name: kb.name,
    description:
      kb.description ??
      (kb.kind === "personal"
        ? "仅本人可访问的个人文档空间。"
        : "当前部门共享的企业知识空间。"),
    department: kb.department_name,
    scope: kb.kind === "personal" ? "个人空间" : "部门共享",
    documentCount: kb.document_count,
    readyDocumentCount: kb.ready_document_count,
    chunkCount: kb.chunk_count,
  })),
);

const mockSpaces = computed<readonly DisplaySpace[]>(() =>
  aiSearchMockData.knowledgeSpaces.map((space) => ({
    id: space.id,
    name: space.name,
    description: space.description,
    department: space.department,
    scope: space.permissionType,
    documentCount: space.documentCount,
    readyDocumentCount: space.documentCount,
    chunkCount: 0,
  })),
);

const spaces = computed<readonly DisplaySpace[]>(() =>
  isRealApiMode ? realSpaces.value : mockSpaces.value,
);
const departments = computed(() => [
  ...new Set(spaces.value.map((space) => space.department)),
]);
const filteredSpaces = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase("zh-CN");
  return spaces.value.filter(
    (space) =>
      (department.value === "all" || space.department === department.value) &&
      (normalizedKeyword.length === 0 ||
        `${space.name}${space.description}${space.department}`
          .toLocaleLowerCase("zh-CN")
          .includes(normalizedKeyword)),
  );
});
const selectedSpaceId = computed(() => {
  const value = Array.isArray(route.query.space)
    ? route.query.space[0]
    : route.query.space;
  return typeof value === "string" ? value : "";
});
const {
  page: spacesPage,
  pageSize: spacesPageSize,
  pagedItems: pagedSpaces,
  setPage: setSpacesPage,
} = useListPagination(filteredSpaces);

const askSpace = (space: DisplaySpace): void => {
  const question = `请总结${space.name}的核心内容`;
  if (isRealApiMode) {
    void router.push({
      path: "/search",
      state: {
        initialSearch: {
          q: question,
          mode: "smart",
          sources: "knowledge",
          workspaceIds: [space.id],
        },
      },
    });
    return;
  }
  void router.push({
    path: "/search",
    query: {
      q: question,
      mode: "smart",
      sources: "knowledge",
      model: "enterprise-general",
    },
  });
};

const loadRealSpaces = async (): Promise<void> => {
  if (!isRealApiMode) return;
  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loadState.value = "loading";
  loadError.value = "";
  try {
    realKnowledgeBases.value = await listKnowledgeBases(controller.signal);
    loadState.value = "success";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = toPublicApiError(error).message;
    loadState.value = "error";
  }
};

onMounted(() => void loadRealSpaces());
onBeforeUnmount(() => loadController?.abort());
</script>

<template>
  <div class="business-page knowledge-spaces-page">
    <PageHeader
      eyebrow="知识空间"
      title="我的空间"
      description="集中查看当前账号可访问的个人和部门知识库。"
    >
      <template #actions>
        <span class="local-preview-badge">
          {{ spaces.length }} 个可访问空间
        </span>
      </template>
    </PageHeader>

    <div class="space-filter-bar">
      <label>
        <span class="visually-hidden">搜索知识空间</span>
        <Search :size="17" aria-hidden="true" />
        <input
          v-model="keyword"
          type="search"
          placeholder="搜索空间名称、简介或所属部门"
        />
      </label>
      <select v-model="department" aria-label="按部门筛选知识空间">
        <option value="all">全部部门</option>
        <option v-for="item in departments" :key="item" :value="item">
          {{ item }}
        </option>
      </select>
    </div>

    <InlineState
      v-if="isRealApiMode && loadState === 'loading'"
      kind="loading"
      title="正在加载空间"
      description="系统正在读取当前账号可访问的知识库。"
    />
    <InlineState
      v-else-if="isRealApiMode && loadState === 'error'"
      kind="error"
      title="空间加载失败"
      :description="loadError"
    />

    <section
      v-else-if="filteredSpaces.length > 0"
      class="knowledge-space-grid"
      aria-label="可访问知识空间"
    >
      <article
        v-for="space in pagedSpaces"
        :key="space.id"
        :class="{ selected: selectedSpaceId === space.id }"
      >
        <header>
          <div class="space-card-icon" aria-hidden="true">
            <SquareLibrary :size="20" />
          </div>
          <span>{{ space.scope }}</span>
        </header>
        <div class="space-card-copy">
          <h2>{{ space.name }}</h2>
          <p>{{ space.description }}</p>
        </div>
        <dl>
          <div>
            <dt>所属部门</dt>
            <dd>{{ space.department }}</dd>
          </div>
          <div>
            <dt>文档规模</dt>
            <dd>
              {{ space.readyDocumentCount }} / {{ space.documentCount }} 已就绪
            </dd>
          </div>
          <div>
            <dt>可检索分块</dt>
            <dd>{{ space.chunkCount.toLocaleString("zh-CN") }}</dd>
          </div>
        </dl>
        <footer>
          <RouterLink class="secondary-button" :to="`/knowledge/${space.id}`">
            <BookOpen :size="16" aria-hidden="true" />
            查看文档
          </RouterLink>
          <button class="primary-button" type="button" @click="askSpace(space)">
            <Search :size="16" aria-hidden="true" />
            向空间提问
            <ChevronRight :size="15" aria-hidden="true" />
          </button>
        </footer>
      </article>
    </section>

    <ListPagination
      v-if="filteredSpaces.length > 0"
      :page="spacesPage"
      :page-size="spacesPageSize"
      :total="filteredSpaces.length"
      @change="setSpacesPage"
    />

    <InlineState
      v-if="
        loadState !== 'loading' &&
          loadState !== 'error' &&
          filteredSpaces.length === 0
      "
      kind="empty"
      title="没有匹配的知识空间"
      description="请清空关键词或切换到全部部门。"
    />
  </div>
</template>

<style scoped>
.knowledge-spaces-page {
  gap: var(--space-5);
}

.space-filter-bar,
.space-filter-bar label,
.knowledge-space-grid article > header,
.knowledge-space-grid article > footer {
  display: flex;
  align-items: center;
}

.space-filter-bar {
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
}

.space-filter-bar label {
  min-height: 42px;
  flex: 1;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
}

.space-filter-bar input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
}

.space-filter-bar select {
  min-width: 210px;
  min-height: 42px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.knowledge-space-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.knowledge-space-grid article {
  display: grid;
  min-height: 320px;
  grid-template-rows: auto 1fr auto auto;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.knowledge-space-grid article.selected {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-focus);
}

.knowledge-space-grid article > header {
  justify-content: space-between;
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.space-card-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.space-card-copy h2 {
  margin: 0;
  font-size: var(--font-size-18);
}

.space-card-copy p {
  display: -webkit-box;
  margin: var(--space-2) 0 0;
  overflow: hidden;
  color: var(--color-text-muted);
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.knowledge-space-grid dl {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.knowledge-space-grid dl div {
  display: grid;
  grid-template-columns: minmax(80px, 0.45fr) minmax(0, 1fr);
  gap: var(--space-2);
}

.knowledge-space-grid dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.knowledge-space-grid dd {
  margin: 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.knowledge-space-grid article > footer {
  gap: var(--space-2);
}

.knowledge-space-grid article > footer > * {
  min-width: 0;
  flex: 1;
}

@media (max-width: 1280px) {
  .knowledge-space-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .space-filter-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .space-filter-bar label,
  .space-filter-bar select {
    width: 100%;
    min-height: 44px;
  }

  .knowledge-space-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .knowledge-space-grid article {
    min-height: 0;
    padding: var(--space-4);
  }

  .knowledge-space-grid article > footer {
    align-items: stretch;
    flex-direction: column;
  }

  .knowledge-space-grid article > footer > * {
    width: 100%;
  }
}
</style>
