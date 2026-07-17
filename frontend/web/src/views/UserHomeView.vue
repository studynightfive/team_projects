<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import InlineState from "../components/InlineState.vue";
import AiSearchBox from "../components/search/AiSearchBox.vue";
import SearchContextPanel from "../components/search/SearchContextPanel.vue";
import SearchStatusBadge from "../components/search/SearchStatusBadge.vue";
import {
  ChevronRight,
  Database,
  FileUp,
  FlaskConical,
  FolderHeart,
  PanelRightOpen,
  ScanSearch,
  SquareLibrary,
} from "../components/icons";
import { foundationData } from "../data/foundation";
import { loadAiSearchHome } from "../services/ai-search";
import type {
  AiSearchHomeData,
  QuickAction,
  SearchMode,
  SearchRequest,
  SearchSourceType,
} from "../types/ai-search";

interface SearchBoxHandle {
  focus: () => void;
  openFilePicker: () => void;
}

const { message } = AntApp.useApp();
const router = useRouter();
const searchBoxRef = ref<SearchBoxHandle>();
const homeData = ref<AiSearchHomeData>();
const loadError = ref("");
const query = ref("");
const mode = ref<SearchMode>("smart");
const sources = ref<SearchSourceType[]>([]);
const modelId = ref("enterprise-general");
const isContextOpen = ref(false);
const attachmentNames = ref<string[]>([]);
const contextTrigger = ref<HTMLElement>();

let loadController: AbortController | undefined;
let desktopContextQuery: MediaQueryList | undefined;

const quickActionIcons = {
  upload: FileUp,
  research: FlaskConical,
  space: SquareLibrary,
  favorite: FolderHeart,
  "data-source": Database,
} as const satisfies Record<QuickAction["icon"], typeof FileUp>;

const connectedSourceCount = computed(
  () =>
    homeData.value?.dataSources.filter(
      (source) => source.connectionStatus === "connected",
    ).length ?? 0,
);
const modelLabel = computed(
  () =>
    homeData.value?.modelOptions.find(
      (option) => option.value === modelId.value,
    )?.label ?? "企业通用模型",
);

const formatDate = (value: string): string =>
  new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));

const initializeHome = async (): Promise<void> => {
  loadController?.abort();
  loadController = new AbortController();
  loadError.value = "";

  try {
    const data = await loadAiSearchHome(loadController.signal);
    homeData.value = data;
    sources.value = [
      ...(data.scopeOptions.find((option) => option.value === "all")?.sources ??
        []),
    ];
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = "工作台数据暂时无法加载，请重新尝试。";
  }
};

const showNotice = (notice: string): void => {
  void message.info(notice);
};

const submitSearch = (request: SearchRequest): void => {
  void router.push({
    path: "/search",
    query: {
      q: request.query,
      mode: request.mode,
      sources: request.sources.join(","),
      model: request.modelId,
    },
    state: { attachmentNames: [...(request.attachmentIds ?? [])] },
  });
};

const fillSuggestion = async (suggestion: string): Promise<void> => {
  query.value = suggestion;
  await nextTick();
  searchBoxRef.value?.focus();
};

const openRecentSearch = (historyId: string): void => {
  const item = homeData.value?.recentSearches.find(
    (history) => history.id === historyId,
  );
  if (item === undefined) return;

  void router.push({
    path: "/search",
    query: {
      q: item.query,
      mode: item.mode,
      sources: item.sources.join(","),
      model: modelId.value,
    },
  });
};

const runQuickAction = (action: QuickAction): void => {
  if (action.icon === "upload") {
    searchBoxRef.value?.openFilePicker();
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
  if (typeof window.matchMedia !== "function") return;
  desktopContextQuery = window.matchMedia("(min-width: 1440px)");
  syncDesktopContext(desktopContextQuery);
  desktopContextQuery.addEventListener("change", syncDesktopContext);
});

onBeforeUnmount(() => {
  loadController?.abort();
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
        description="正在加载搜索范围、知识空间和数据源概览。"
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
            <span aria-label="当前使用模拟数据">模拟数据</span>
          </div>
          <p class="search-hero-greeting">
            {{ foundationData.userView.profile.name }}，欢迎回到工作台
          </p>
          <h1>今天想查找什么？</h1>
          <p class="search-hero-description">
            搜索企业知识、项目资料、制度文档与业务信息，获得带来源依据的智能答案。
          </p>

          <AiSearchBox
            ref="searchBoxRef"
            v-model:query="query"
            v-model:mode="mode"
            v-model:sources="sources"
            v-model:model-id="modelId"
            :mode-options="homeData.modeOptions"
            :scope-options="homeData.scopeOptions"
            :model-options="homeData.modelOptions"
            @attachments-change="attachmentNames = $event"
            @submit="submitSearch"
            @notice="showNotice"
          />

          <div class="search-suggestion-list" aria-label="快捷提问">
            <span>常用问题</span>
            <button
              v-for="suggestion in homeData.suggestions"
              :key="suggestion"
              type="button"
              @click="fillSuggestion(suggestion)"
            >
              <ScanSearch :size="15" aria-hidden="true" />
              {{ suggestion }}
            </button>
          </div>
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
              v-for="action in homeData.quickActions"
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

        <div class="home-information-grid">
          <section
            class="home-section recent-search-section"
            aria-labelledby="recent-search-title"
          >
            <header class="home-section-heading">
              <div>
                <span>继续工作</span>
                <h2 id="recent-search-title">最近搜索</h2>
              </div>
              <RouterLink
                class="secondary-button compact home-view-all-button"
                to="/history"
              >
                查看全部
                <ChevronRight :size="14" aria-hidden="true" />
              </RouterLink>
            </header>
            <div class="recent-search-list">
              <button
                v-for="history in homeData.recentSearches"
                :key="history.id"
                type="button"
                @click="openRecentSearch(history.id)"
              >
                <span>
                  <strong>{{ history.query }}</strong>
                  <small>{{ formatDate(history.createdAt) }} ·
                    {{ history.resultCount }} 条结果</small>
                </span>
                <ChevronRight :size="16" aria-hidden="true" />
              </button>
            </div>
          </section>

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

        <section
          class="home-section data-source-overview"
          aria-labelledby="data-source-overview-title"
        >
          <header class="home-section-heading">
            <div>
              <span>信息可用性</span>
              <h2 id="data-source-overview-title">数据源状态</h2>
            </div>
            <RouterLink
              class="secondary-button compact home-view-all-button"
              to="/data-sources"
            >
              {{ connectedSourceCount }} 个已连接，查看全部
              <ChevronRight :size="14" aria-hidden="true" />
            </RouterLink>
          </header>
          <div class="data-source-summary-list">
            <article
              v-for="source in homeData.dataSources.slice(0, 4)"
              :key="source.id"
            >
              <span class="source-mark" aria-hidden="true"><Database :size="17" /></span>
              <span>
                <strong>{{ source.name }}</strong>
                <small>{{
                  source.contentCount.toLocaleString("zh-CN")
                }}
                  条已同步内容</small>
              </span>
              <SearchStatusBadge :status="source.connectionStatus" />
            </article>
          </div>
          <p class="mock-data-notice">{{ homeData.meta.notice }}</p>
        </section>
      </main>

      <SearchContextPanel
        class="home-search-context"
        :open="isContextOpen"
        :query="query || '尚未输入搜索问题'"
        :selected-sources="sources"
        :source-options="homeData.scopeOptions"
        :model-label="modelLabel"
        :citations="[]"
        :data-sources="homeData.dataSources"
        :attachment-names="attachmentNames"
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

.search-suggestion-list {
  display: flex;
  max-width: 100%;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-4);
  text-align: left;
}

.search-suggestion-list > span {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.search-suggestion-list button {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  font-size: var(--font-size-12);
}

.search-suggestion-list button svg {
  flex: 0 0 15px;
  color: var(--color-primary);
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
.knowledge-space-list a,
.data-source-summary-list article {
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
.knowledge-space-list a > span:nth-child(2),
.data-source-summary-list article > span:nth-child(2) {
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
.knowledge-space-list strong,
.data-source-summary-list strong {
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
.knowledge-space-list small,
.data-source-summary-list small {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
  line-height: 1.5;
}

.quick-action-icon,
.space-mark,
.source-mark {
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

.data-source-summary-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
}

.data-source-summary-list article {
  display: grid;
  min-width: 0;
  min-height: 132px;
  align-content: start;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
  text-align: center;
}

.data-source-summary-list article > span:nth-child(2) {
  width: 100%;
  justify-items: center;
}

.data-source-summary-list strong {
  overflow: visible;
  text-overflow: clip;
  white-space: normal;
}

.mock-data-notice {
  margin: var(--space-4) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
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

  .data-source-summary-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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

  .search-suggestion-list {
    justify-content: flex-start;
    flex-wrap: nowrap;
    margin-right: calc(var(--content-gutter) * -1);
    padding-right: var(--content-gutter);
    overflow-x: auto;
  }

  .search-suggestion-list > span {
    display: none;
  }

  .search-suggestion-list button {
    flex: 0 0 240px;
    min-height: 44px;
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

  .quick-action-list,
  .data-source-summary-list {
    grid-template-columns: minmax(0, 1fr);
  }

  .quick-action-list button {
    min-height: 72px;
  }

  .home-section-heading .secondary-button {
    width: auto;
  }
}
</style>
