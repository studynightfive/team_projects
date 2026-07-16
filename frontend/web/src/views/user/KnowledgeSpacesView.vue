<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import {
  ArrowUpRight,
  BookOpen,
  Search,
  SquareLibrary,
  UsersRound,
} from "../../components/icons";
import { aiSearchMockData } from "../../mocks/ai-search";

type SpaceTab = "overview" | "documents" | "members" | "questions" | "settings";

const spaceTabOptions = [
  { value: "overview", label: "空间概览" },
  { value: "documents", label: "文档列表" },
  { value: "members", label: "成员列表" },
  { value: "questions", label: "热门问题" },
  { value: "settings", label: "空间设置" },
] as const satisfies readonly { value: SpaceTab; label: string }[];

const route = useRoute();
const router = useRouter();
const keyword = ref("");
const department = ref("all");
const selectedSpaceId = ref<string>("");
const activeTab = ref<SpaceTab>("overview");

const routeSpaceId = computed(() => {
  const queryValue = route.query.space;
  const candidate = Array.isArray(queryValue) ? queryValue[0] : queryValue;

  return typeof candidate === "string" &&
    aiSearchMockData.knowledgeSpaces.some((space) => space.id === candidate)
    ? candidate
    : undefined;
});

const departments = computed(() => [
  ...new Set(aiSearchMockData.knowledgeSpaces.map((space) => space.department)),
]);
const filteredSpaces = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase("zh-CN");
  return aiSearchMockData.knowledgeSpaces.filter(
    (space) =>
      (department.value === "all" || space.department === department.value) &&
      (normalizedKeyword.length === 0 ||
        `${space.name}${space.description}${space.owner}`
          .toLocaleLowerCase("zh-CN")
          .includes(normalizedKeyword)),
  );
});
const selectedSpace = computed(() =>
  filteredSpaces.value.find((space) => space.id === selectedSpaceId.value),
);

watch(
  routeSpaceId,
  (spaceId) => {
    if (spaceId === undefined) {
      selectedSpaceId.value = filteredSpaces.value[0]?.id ?? "";
      activeTab.value = "overview";
      return;
    }

    keyword.value = "";
    department.value = "all";
    selectedSpaceId.value = spaceId;
    activeTab.value = "overview";
  },
  { immediate: true },
);

watch(
  filteredSpaces,
  (spaces) => {
    if (spaces.some((space) => space.id === selectedSpaceId.value)) return;

    selectedSpaceId.value = spaces[0]?.id ?? "";
    activeTab.value = "overview";
  },
  { immediate: true },
);

const openSpace = (spaceId: string): void => {
  selectedSpaceId.value = spaceId;
  activeTab.value = "overview";
};

const askSpace = (question?: string): void => {
  if (selectedSpace.value === undefined) return;
  void router.push({
    path: "/search",
    query: {
      q: question ?? `请总结${selectedSpace.value.name}的核心内容`,
      mode: "smart",
      sources: "knowledge",
      model: "enterprise-general",
    },
  });
};

const selectSpaceTab = (tab: SpaceTab, focus = false): void => {
  activeTab.value = tab;
  if (focus) document.getElementById(`space-tab-${tab}`)?.focus();
};

const handleSpaceTabKeydown = (
  event: KeyboardEvent,
  currentTab: SpaceTab,
): void => {
  const currentIndex = spaceTabOptions.findIndex(
    (option) => option.value === currentTab,
  );
  let nextIndex: number | undefined;
  if (event.key === "ArrowRight") {
    nextIndex = (currentIndex + 1) % spaceTabOptions.length;
  } else if (event.key === "ArrowLeft") {
    nextIndex =
      (currentIndex - 1 + spaceTabOptions.length) % spaceTabOptions.length;
  } else if (event.key === "Home") {
    nextIndex = 0;
  } else if (event.key === "End") {
    nextIndex = spaceTabOptions.length - 1;
  }
  if (nextIndex === undefined) return;

  event.preventDefault();
  const nextTab = spaceTabOptions[nextIndex]?.value;
  if (nextTab !== undefined) selectSpaceTab(nextTab, true);
};
</script>

<template>
  <div class="business-page knowledge-spaces-page">
    <PageHeader
      eyebrow="企业知识空间"
      title="我的空间"
      description="按部门和主题访问有权限的知识，并从空间上下文直接发起 AI 搜索。"
    >
      <template #actions>
        <span class="local-preview-badge">6 个模拟空间</span>
      </template>
    </PageHeader>

    <div class="space-filter-bar">
      <label>
        <span class="visually-hidden">搜索知识空间</span>
        <Search :size="17" aria-hidden="true" />
        <input
          v-model="keyword"
          type="search"
          placeholder="搜索空间名称、简介或负责人"
        />
      </label>
      <select v-model="department" aria-label="按部门筛选知识空间">
        <option value="all">全部部门</option>
        <option v-for="item in departments" :key="item" :value="item">
          {{ item }}
        </option>
      </select>
    </div>

    <div v-if="filteredSpaces.length > 0" class="knowledge-space-grid">
      <article
        v-for="space in filteredSpaces"
        :key="space.id"
        :class="{ selected: selectedSpaceId === space.id }"
      >
        <header>
          <div class="space-card-icon" aria-hidden="true">
            <SquareLibrary :size="20" />
          </div>
          <span>{{ space.permissionType }}</span>
        </header>
        <h2>{{ space.name }}</h2>
        <p>{{ space.description }}</p>
        <dl>
          <div>
            <dt>所属部门</dt>
            <dd>{{ space.department }}</dd>
          </div>
          <div>
            <dt>负责人</dt>
            <dd>{{ space.owner }}</dd>
          </div>
          <div>
            <dt>成员</dt>
            <dd>{{ space.memberCount.toLocaleString("zh-CN") }} 人</dd>
          </div>
          <div>
            <dt>文档</dt>
            <dd>{{ space.documentCount.toLocaleString("zh-CN") }} 份</dd>
          </div>
        </dl>
        <button type="button" @click="openSpace(space.id)">
          查看空间概览
          <ArrowUpRight :size="16" aria-hidden="true" />
        </button>
      </article>
    </div>

    <InlineState
      v-else
      kind="empty"
      title="没有匹配的知识空间"
      description="请清空关键词或切换到全部部门。"
    />

    <section
      v-if="selectedSpace"
      class="space-detail-panel"
      aria-labelledby="space-detail-title"
    >
      <header class="space-detail-heading">
        <div>
          <span>空间详情</span>
          <h2 id="space-detail-title">{{ selectedSpace.name }}</h2>
        </div>
        <button class="primary-button" type="button" @click="askSpace()">
          <Search :size="16" aria-hidden="true" />
          向此空间提问
        </button>
      </header>

      <div class="space-detail-tabs" role="tablist" aria-label="空间详情栏目">
        <button
          v-for="option in spaceTabOptions"
          :id="`space-tab-${option.value}`"
          :key="option.value"
          type="button"
          role="tab"
          :aria-selected="activeTab === option.value"
          aria-controls="space-detail-content"
          :tabindex="activeTab === option.value ? 0 : -1"
          @click="selectSpaceTab(option.value)"
          @keydown="handleSpaceTabKeydown($event, option.value)"
        >
          {{ option.label }}
        </button>
      </div>

      <div
        id="space-detail-content"
        class="space-detail-content"
        role="tabpanel"
        :aria-labelledby="`space-tab-${activeTab}`"
      >
        <template v-if="activeTab === 'overview'">
          <div class="space-overview-metric">
            <div>
              <BookOpen :size="18" aria-hidden="true" />
              {{ selectedSpace.documentCount }} 份文档
            </div>
            <div>
              <UsersRound :size="18" aria-hidden="true" />
              {{ selectedSpace.memberCount }} 名成员
            </div>
          </div>
          <p>{{ selectedSpace.description }}</p>
        </template>
        <template v-else-if="activeTab === 'documents'">
          <p>
            文档清单等待知识库 OpenAPI；当前空间共有
            {{ selectedSpace.documentCount }} 份模拟文档。
          </p>
        </template>
        <template v-else-if="activeTab === 'members'">
          <p>
            成员权限等待认证与知识库契约；当前仅展示负责人
            {{ selectedSpace.owner }}。
          </p>
        </template>
        <template v-else-if="activeTab === 'questions'">
          <button
            v-for="question in selectedSpace.recentQuestions"
            :key="question"
            class="space-question-button"
            type="button"
            @click="askSpace(question)"
          >
            {{ question }}
            <ArrowUpRight :size="16" aria-hidden="true" />
          </button>
        </template>
        <template v-else>
          <p>
            空间设置只对具备管理权限的用户开放；本地页面不会修改权限或服务端数据。
          </p>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.knowledge-spaces-page {
  gap: var(--space-5);
}

.space-filter-bar,
.space-filter-bar label,
.knowledge-space-grid article > header,
.knowledge-space-grid article > button,
.space-detail-heading,
.space-detail-tabs,
.space-overview-metric,
.space-question-button {
  display: flex;
  align-items: center;
}

.space-filter-bar {
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.space-filter-bar label {
  min-height: 40px;
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

.space-filter-bar input:focus-visible {
  box-shadow: none;
}

.space-filter-bar select {
  min-width: 200px;
  min-height: 40px;
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
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.knowledge-space-grid article.selected {
  border-color: var(--blue-300);
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

.knowledge-space-grid h2 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-18);
}

.knowledge-space-grid p,
.space-detail-content p {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.7;
}

.knowledge-space-grid dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  margin: 0;
}

.knowledge-space-grid dl div {
  padding: var(--space-2);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.knowledge-space-grid dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.knowledge-space-grid dd {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}

.knowledge-space-grid article > button {
  min-height: 40px;
  justify-content: space-between;
  padding: 0 var(--space-3);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.space-detail-panel {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.space-detail-heading {
  justify-content: space-between;
  gap: var(--space-4);
}

.space-detail-heading span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.space-detail-heading h2 {
  margin: var(--space-1) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-20);
}

.space-detail-tabs {
  gap: var(--space-1);
  margin-top: var(--space-5);
  padding-bottom: var(--space-3);
  overflow-x: auto;
  border-bottom: 1px solid var(--color-border);
}

.space-detail-tabs button {
  min-height: 36px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: transparent;
  white-space: nowrap;
}

.space-detail-tabs button[aria-selected="true"] {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.space-detail-content {
  padding-top: var(--space-5);
}

.space-overview-metric {
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.space-overview-metric > div {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
}

.space-question-button {
  width: 100%;
  min-height: 44px;
  justify-content: space-between;
  padding: 0 var(--space-3);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

@media (max-width: 1100px) {
  .knowledge-space-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .space-filter-bar,
  .space-detail-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .space-filter-bar select,
  .space-filter-bar label {
    width: 100%;
    min-height: 44px;
  }

  .knowledge-space-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
