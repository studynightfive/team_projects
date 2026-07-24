<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import InlineState from "../components/InlineState.vue";
import ListPagination from "../components/ListPagination.vue";
import AiSearchBox from "../components/search/AiSearchBox.vue";
import SearchContextPanel from "../components/search/SearchContextPanel.vue";
import {
  Award,
  BadgeCheck,
  ChevronRight,
  Database,
  FileText,
  FileUp,
  FolderHeart,
  PanelRightOpen,
  RefreshCw,
  SquareLibrary,
} from "../components/icons";
import { isRealApiMode } from "../config/runtime";
import { loadAiSearchHome } from "../services/ai-search";
import { getMyIncentives, type UserIncentives } from "../services/incentives";
import { listKnowledgeBases } from "../services/knowledge";
import { useSessionStore } from "../stores/session";
import type {
  AiSearchHomeData,
  KnowledgeBaseOption,
  QuickAction,
  SearchMode,
  SearchRequest,
  SearchSourceType,
} from "../types/ai-search";

const { message } = AntApp.useApp();
const router = useRouter();
const sessionStore = useSessionStore();
const homeData = ref<AiSearchHomeData>();
const loadError = ref("");
const query = ref("");
const mode = ref<SearchMode>("smart");
const sources = ref<SearchSourceType[]>([]);
const workspaceIds = ref<string[]>([]);
const modelId = ref("enterprise-general");
const knowledgeBaseOptions = ref<readonly KnowledgeBaseOption[]>([]);
const isContextOpen = ref(false);
const contextTrigger = ref<HTMLElement>();
const incentives = ref<UserIncentives>();
const incentivesLoading = ref(false);
const incentivesError = ref("");
const incentivePage = ref(1);
const incentivePageSize = ref(10);

let loadController: AbortController | undefined;
let incentiveController: AbortController | undefined;
let desktopContextQuery: MediaQueryList | undefined;

const quickActionIcons = {
  upload: FileUp,
  space: SquareLibrary,
  favorite: FolderHeart,
  "data-source": Database,
} as const satisfies Record<QuickAction["icon"], typeof FileUp>;

const modelLabel = computed(
  () =>
    homeData.value?.modelOptions.find(
      (option) => option.value === modelId.value,
    )?.label ?? "企业通用模型",
);
const selectedKnowledgeBases = computed(() =>
  workspaceIds.value
    .map((id) => knowledgeBaseOptions.value.find((item) => item.id === id))
    .filter((item): item is KnowledgeBaseOption => item !== undefined),
);
const canUploadKnowledge = computed(() => {
  const permissions = sessionStore.currentUser?.permissions ?? [];
  return permissions.some((permission) =>
    ["admin.document.upload", "document.upload"].includes(permission),
  );
});
const visibleQuickActions = computed(
  () =>
    homeData.value?.quickActions.filter(
      (action) => action.icon !== "upload" || canUploadKnowledge.value,
    ) ?? [],
);
const apiModeLabel = computed(() =>
  homeData.value?.meta.apiRequestsAllowed === true ? "真实接口" : "模拟数据",
);

const initializeHome = async (): Promise<void> => {
  loadController?.abort();
  loadController = new AbortController();
  loadError.value = "";

  try {
    const data = await loadAiSearchHome(loadController.signal);
    homeData.value = data;
    sources.value = ["knowledge"];
    if (
      data.modelOptions.length > 0 &&
      !data.modelOptions.some((item) => item.value === modelId.value)
    ) {
      modelId.value = data.modelOptions[0]?.value ?? "env-deepseek";
    }
    if (data.meta.apiRequestsAllowed) {
      const knowledgeBases = await listKnowledgeBases(loadController.signal);
      knowledgeBaseOptions.value = knowledgeBases.map((item) => ({
        id: item.id,
        name: item.name,
        documentCount: item.document_count,
        readyDocumentCount: item.ready_document_count,
        status: item.status,
      }));
      workspaceIds.value = workspaceIds.value.filter((id) =>
        knowledgeBaseOptions.value.some((item) => item.id === id),
      );
      if (
        workspaceIds.value.length === 0 &&
        knowledgeBaseOptions.value[0] !== undefined
      )
        workspaceIds.value = [knowledgeBaseOptions.value[0].id];
    }
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = "工作台数据暂时无法加载，请重新尝试。";
  }
};

const loadIncentives = async (): Promise<void> => {
  if (!isRealApiMode) return;
  incentiveController?.abort();
  const controller = new AbortController();
  incentiveController = controller;
  incentivesLoading.value = true;
  incentivesError.value = "";
  try {
    incentives.value = await getMyIncentives(
      {
        page: incentivePage.value,
        page_size: incentivePageSize.value,
      },
      controller.signal,
    );
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    incentivesError.value = "贡献数据暂时无法加载，请稍后重试。";
  } finally {
    if (incentiveController === controller) {
      incentivesLoading.value = false;
    }
  }
};

const changeIncentivePage = (page: number, pageSize: number): void => {
  incentivePage.value = pageSize === incentivePageSize.value ? page : 1;
  incentivePageSize.value = pageSize;
  void loadIncentives();
};

const formatContributionDate = (value: string): string =>
  new Date(value).toLocaleDateString("zh-CN");

const showNotice = (notice: string): void => {
  void message.info(notice);
};

const submitSearch = (request: SearchRequest): void => {
  if (isRealApiMode) {
    void router.push({
      path: "/search",
      state: {
        initialSearch: {
          q: request.query,
          sources: request.sources.join(","),
          workspaceIds: [...(request.workspaceIds ?? [])],
          modelId: request.modelId,
        },
      },
    });
    return;
  }

  void router.push({
    path: "/search",
    query: {
      q: request.query,
      sources: request.sources.join(","),
      model: request.modelId,
    },
  });
};

const runQuickAction = (action: QuickAction): void => {
  if (action.icon === "upload") {
    if (!canUploadKnowledge.value) {
      void message.warning("当前账号没有上传文档权限");
      return;
    }
    const kbId = workspaceIds.value[0] ?? knowledgeBaseOptions.value[0]?.id;
    if (kbId === undefined) {
      void message.warning("暂无可用知识库，请先到企业知识库创建后再上传");
      void router.push("/knowledge");
      return;
    }
    void router.push({
      path: `/knowledge/${kbId}`,
      query: { action: "upload" },
    });
    return;
  }
  void router.push(action.to);
};

const openContext = (trigger: HTMLElement): void => {
  contextTrigger.value = trigger;
  isContextOpen.value = true;
};

const syncDesktopContext = (
  event: MediaQueryListEvent | MediaQueryList,
): void => {
  isContextOpen.value = event.matches;
};

onMounted(() => {
  void initializeHome();
  void loadIncentives();
  if (typeof window.matchMedia !== "function") return;
  desktopContextQuery = window.matchMedia("(min-width: 1440px)");
  syncDesktopContext(desktopContextQuery);
  desktopContextQuery.addEventListener("change", syncDesktopContext);
});

onBeforeUnmount(() => {
  loadController?.abort();
  incentiveController?.abort();
  desktopContextQuery?.removeEventListener("change", syncDesktopContext);
});
</script>

<template>
  <div class="business-page ai-search-home">
    <div v-if="loadError" class="home-state-wrap">
      <InlineState
        kind="error"
        title="工作台加载失败"
        :description="loadError"
      />
      <button class="primary-button" type="button" @click="initializeHome">
        重新加载
      </button>
    </div>

    <div
      v-else-if="homeData === undefined"
      class="home-state-wrap"
      aria-live="polite"
    >
      <InlineState
        kind="loading"
        title="正在准备 AI 搜索工作台"
        description="正在加载搜索范围、知识空间和企业知识库概览。"
      />
    </div>

    <div
      v-else
      class="workbench-home-layout"
      :class="{ 'context-open': isContextOpen }"
    >
      <main class="workbench-home-main">
        <header class="search-hero">
          <div class="search-hero-status">
            <span>企业知识中心</span>
            <span :aria-label="`当前使用${apiModeLabel}`">{{
              apiModeLabel
            }}</span>
          </div>
          <p class="search-hero-greeting">
            {{ sessionStore.displayName }}，欢迎回到工作台
          </p>
          <h1>今天想查找什么？</h1>
          <p class="search-hero-description">
            搜索企业知识库中的文档和业务资料，获得带来源依据的智能答案。
          </p>

          <AiSearchBox
            v-model:query="query"
            v-model:sources="sources"
            v-model:workspace-ids="workspaceIds"
            v-model:model-id="modelId"
            :mode="mode"
            :model-options="homeData.modelOptions"
            :knowledge-base-options="knowledgeBaseOptions"
            :requires-workspace="isRealApiMode"
            @submit="submitSearch"
            @notice="showNotice"
          />
        </header>

        <section class="home-section" aria-labelledby="quick-action-title">
          <header class="home-section-heading">
            <div>
              <span>高频任务</span>
              <h2 id="quick-action-title">快捷开始</h2>
            </div>
            <button
              v-if="!isContextOpen"
              class="secondary-button compact"
              type="button"
              @click="openContext($event.currentTarget as HTMLElement)"
            >
              <PanelRightOpen :size="16" aria-hidden="true" />
              搜索上下文
            </button>
          </header>
          <div class="quick-action-list">
            <button
              v-for="action in visibleQuickActions"
              :key="action.id"
              type="button"
              @click="runQuickAction(action)"
            >
              <span class="quick-action-icon" aria-hidden="true">
                <component :is="quickActionIcons[action.icon]" :size="19" />
              </span>
              <span>
                <strong>{{ action.label }}</strong>
                <small>{{ action.description }}</small>
              </span>
              <ChevronRight :size="16" aria-hidden="true" />
            </button>
          </div>
        </section>

        <section
          v-if="isRealApiMode"
          class="home-section incentive-section"
          aria-labelledby="incentive-title"
        >
          <header class="home-section-heading">
            <div>
              <span>知识共建</span>
              <h2 id="incentive-title">我的贡献</h2>
            </div>
            <button
              class="secondary-button compact"
              type="button"
              :disabled="incentivesLoading"
              @click="loadIncentives"
            >
              <RefreshCw :size="15" aria-hidden="true" />
              刷新
            </button>
          </header>

          <InlineState
            v-if="incentivesLoading && incentives === undefined"
            kind="loading"
            title="正在统计贡献"
            description="正在核对已成功处理并启用索引的文档。"
          />
          <InlineState
            v-else-if="incentivesError && incentives === undefined"
            kind="error"
            title="贡献数据加载失败"
            :description="incentivesError"
          />
          <template v-else-if="incentives !== undefined">
            <div class="incentive-summary">
              <div>
                <Award :size="20" aria-hidden="true" />
                <span>
                  <small>累计积分</small>
                  <strong>{{ incentives.points }}</strong>
                </span>
              </div>
              <div>
                <FileText :size="20" aria-hidden="true" />
                <span>
                  <small>有效贡献</small>
                  <strong>{{ incentives.contribution_count }} 份</strong>
                </span>
              </div>
              <div>
                <BadgeCheck :size="20" aria-hidden="true" />
                <span>
                  <small>部门排名</small>
                  <strong>
                    {{
                      incentives.department_rank === null ||
                        incentives.department_rank === undefined
                        ? "-"
                        : `第 ${incentives.department_rank} 名`
                    }}
                  </strong>
                </span>
              </div>
            </div>

            <div class="badge-list" aria-label="贡献徽章">
              <span
                v-for="badge in incentives.badges"
                :key="badge.code"
                :class="{ earned: badge.earned }"
              >
                <BadgeCheck :size="15" aria-hidden="true" />
                {{ badge.name }}
              </span>
            </div>

            <p v-if="incentives.next_badge" class="next-badge">
              距离“{{ incentives.next_badge.name }}”还差
              {{ incentives.next_badge.remaining_points }} 分
            </p>

            <div
              v-if="incentives.contributions.items.length > 0"
              class="contribution-list"
            >
              <div
                v-for="item in incentives.contributions.items"
                :key="item.id"
              >
                <FileText :size="17" aria-hidden="true" />
                <span>
                  <strong>{{ item.title }}</strong>
                  <small>{{ formatContributionDate(item.occurred_at) }}</small>
                </span>
                <b>+{{ item.points }}</b>
              </div>
            </div>
            <p v-else class="contribution-empty">
              暂无有效贡献。文档成功处理并启用索引后将在这里计分。
            </p>

            <ListPagination
              v-if="incentives.contributions.total > 0"
              :page="incentives.contributions.page"
              :page-size="incentives.contributions.page_size"
              :total="incentives.contributions.total"
              @change="changeIncentivePage"
            />
          </template>
        </section>

        <div class="home-information-grid">
          <section
            class="home-section knowledge-space-section"
            aria-labelledby="knowledge-space-title"
          >
            <header class="home-section-heading">
              <div>
                <span>常用知识</span>
                <h2 id="knowledge-space-title">知识空间</h2>
              </div>
              <RouterLink
                class="secondary-button compact home-view-all-button"
                to="/spaces"
              >
                查看全部
                <ChevronRight :size="14" aria-hidden="true" />
              </RouterLink>
            </header>
            <div class="knowledge-space-list">
              <RouterLink
                v-for="space in homeData.knowledgeSpaces.slice(0, 3)"
                :key="space.id"
                :to="`/spaces?space=${space.id}`"
              >
                <span class="space-mark" aria-hidden="true"><SquareLibrary :size="18" /></span>
                <span>
                  <strong>{{ space.name }}</strong>
                  <small>{{ space.department }} ·
                    {{ space.documentCount }} 份文档</small>
                </span>
                <ChevronRight :size="16" aria-hidden="true" />
              </RouterLink>
            </div>
          </section>
        </div>
      </main>

      <SearchContextPanel
        class="home-search-context"
        :open="isContextOpen"
        :query="query || '尚未输入搜索问题'"
        :selected-knowledge-bases="selectedKnowledgeBases"
        :knowledge-base-options="knowledgeBaseOptions"
        :model-label="modelLabel"
        :citations="[]"
        :return-focus-to="contextTrigger"
        @close="isContextOpen = false"
      />
    </div>
  </div>
</template>

<style scoped>
.ai-search-home {
  min-width: 0;
}

.home-state-wrap {
  display: grid;
  max-width: 720px;
  gap: var(--space-4);
  margin: var(--space-16) auto;
  justify-items: start;
}

.workbench-home-layout,
.workbench-home-main {
  min-width: 0;
}

.workbench-home-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--space-8);
}

.search-hero {
  width: 100%;
  min-width: 0;
  max-width: 980px;
  margin: var(--space-4) auto var(--space-2);
  text-align: center;
}

.search-hero-status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.search-hero-status span:last-child {
  padding: 2px var(--space-2);
  border-radius: var(--radius-4);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: var(--font-weight-medium);
}

.search-hero-greeting,
.search-hero h1,
.search-hero-description {
  font-family:
    "Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", SimSun,
    "宋体", var(--font-sans);
}

.search-hero-greeting {
  margin-bottom: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-16);
}

.search-hero h1 {
  margin-bottom: var(--space-3);
  color: var(--color-text);
  font-size: var(--font-size-30);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.025em;
  line-height: 1.25;
}

.search-hero-description {
  max-width: 720px;
  margin: 0 auto var(--space-6);
  color: var(--color-text-muted);
  font-size: var(--font-size-15, 15px);
  line-height: 1.75;
}

.home-section {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.home-section-heading,
.home-section-heading > div,
.quick-action-list button,
.recent-search-list button,
.knowledge-space-list a {
  display: flex;
  align-items: center;
}

.home-section-heading {
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.home-section-heading > button,
.home-section-heading > a {
  flex: 0 0 auto;
  margin-left: auto;
}

.home-section-heading > div {
  align-items: center;
  flex-direction: row;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.home-section-heading > div > span,
.home-section-heading h2 {
  display: inline-flex;
  align-items: center;
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-20);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.01em;
  line-height: var(--line-height-title);
}

.home-section-heading h2 {
  gap: var(--space-2);
}

.home-section-heading h2::before {
  color: var(--color-text-muted);
  content: "—";
  font-size: var(--font-size-14);
  font-weight: normal;
}

.home-section-heading .home-view-all-button {
  border-color: var(--blue-300);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.quick-action-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-3);
}

.quick-action-list button {
  position: relative;
  display: grid;
  min-width: 0;
  min-height: 132px;
  align-content: start;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface-subtle);
  text-align: center;
}

.quick-action-list button > span:nth-child(2),
.recent-search-list button > span,
.knowledge-space-list a > span:nth-child(2) {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: var(--space-1);
}

.quick-action-list button > span:nth-child(2) {
  width: 100%;
  justify-items: center;
}

.quick-action-list button > svg {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
}

.quick-action-list strong,
.recent-search-list strong,
.knowledge-space-list strong {
  overflow: hidden;
  color: var(--color-text);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-action-list strong {
  overflow: visible;
  text-overflow: clip;
  white-space: normal;
}

.quick-action-list small,
.recent-search-list small,
.knowledge-space-list small {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
  line-height: 1.5;
}

.quick-action-icon,
.space-mark {
  display: grid;
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.home-information-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: var(--space-4);
}

.recent-search-list,
.knowledge-space-list {
  display: grid;
}

.recent-search-list button,
.knowledge-space-list a {
  min-width: 0;
  min-height: 56px;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-top: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  background: transparent;
  text-align: left;
  text-decoration: none;
}

.knowledge-space-list a {
  justify-content: flex-start;
}

.knowledge-space-list .space-mark {
  flex-basis: 34px;
  width: 34px;
  height: 34px;
}

.incentive-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
}

.incentive-summary > div {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-surface-muted);
}

.incentive-summary span,
.contribution-list span {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.incentive-summary small,
.contribution-list small {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.incentive-summary strong {
  color: var(--color-text);
  font-size: var(--font-size-18);
}

.badge-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.badge-list span {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  color: var(--color-text-subtle);
  background: var(--color-surface-muted);
  font-size: var(--font-size-12);
}

.badge-list span.earned {
  border-color: var(--green-300);
  color: var(--color-success-text);
  background: var(--green-50);
}

.next-badge,
.contribution-empty {
  margin: var(--space-3) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.contribution-list {
  display: grid;
  margin-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.contribution-list > div {
  display: grid;
  min-width: 0;
  grid-template-columns: 24px minmax(0, 1fr) max-content;
  align-items: center;
  gap: var(--space-3);
  min-height: 58px;
  border-bottom: 1px solid var(--color-border);
}

.contribution-list > div > svg {
  color: var(--color-primary);
}

.contribution-list strong {
  overflow: hidden;
  color: var(--color-text);
  font-size: var(--font-size-13);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contribution-list b {
  color: var(--color-success-text);
  font-size: var(--font-size-13);
}

@media (min-width: 1440px) {
  .workbench-home-layout.context-open {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 320px;
    gap: var(--space-8);
  }

  .home-search-context {
    margin-top: 189px;
  }
}

@media (max-width: 1180px) {
  .quick-action-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .home-information-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .workbench-home-main {
    gap: var(--space-5);
  }

  .search-hero {
    margin-top: 0;
    text-align: left;
  }

  .search-hero h1 {
    font-size: var(--font-size-24);
  }

  .search-hero-description {
    margin-bottom: var(--space-5);
  }

  .home-section {
    padding: var(--space-4);
  }

  .home-section-heading {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    align-items: start;
    gap: var(--space-3);
  }

  .home-section-heading > button,
  .home-section-heading > a {
    margin-left: 0;
    justify-self: end;
  }

  .quick-action-list {
    grid-template-columns: minmax(0, 1fr);
  }

  .quick-action-list button {
    min-height: 72px;
  }

  .home-section-heading .secondary-button {
    width: auto;
  }

  .incentive-summary {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
