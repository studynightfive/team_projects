<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import SearchStatusBadge from "../../components/search/SearchStatusBadge.vue";
import { Database, RefreshCw, Search } from "../../components/icons";
import { aiSearchMockData } from "../../mocks/ai-search";
import type {
  DataSourceConnectionStatus,
  DataSourceType,
} from "../../types/ai-search";

const { message } = AntApp.useApp();
const keyword = ref("");
const statusFilter = ref<"all" | DataSourceConnectionStatus>("all");
const sourceTypeLabels = {
  "knowledge-base": "知识库",
  "cloud-drive": "云盘",
  "project-management": "项目管理",
  "code-repository": "代码仓库",
  "customer-management": "客户管理",
  ticketing: "工单系统",
  collaboration: "协作平台",
  internet: "互联网",
} satisfies Record<DataSourceType, string>;

const filteredSources = computed(() => {
  const normalizedKeyword = keyword.value.trim().toLocaleLowerCase("zh-CN");
  return aiSearchMockData.dataSources.filter(
    (source) =>
      (statusFilter.value === "all" ||
        source.connectionStatus === statusFilter.value) &&
      (normalizedKeyword.length === 0 ||
        `${source.name}${source.description}`
          .toLocaleLowerCase("zh-CN")
          .includes(normalizedKeyword)),
  );
});

const showSourceAction = (sourceName: string, actionLabel: string): void => {
  void message.info(
    `${sourceName}：${actionLabel}仅展示本地模拟说明，不会建立真实连接`,
  );
};
</script>

<template>
  <div class="business-page data-sources-page">
    <PageHeader
      eyebrow="企业信息接入"
      title="数据源"
      description="查看内容规模、同步进度和权限状态；本页不执行真实连接或同步。"
    >
      <template #actions>
        <span class="local-preview-badge">8 个模拟数据源</span>
        <button
          class="secondary-button"
          type="button"
          @click="message.info('当前不会发起真实同步请求')"
        >
          <RefreshCw :size="16" aria-hidden="true" />
          刷新状态
        </button>
      </template>
    </PageHeader>

    <div class="source-filter-bar">
      <label>
        <span class="visually-hidden">搜索数据源</span>
        <Search :size="17" aria-hidden="true" />
        <input
          v-model="keyword"
          type="search"
          placeholder="搜索数据源名称或说明"
        />
      </label>
      <select v-model="statusFilter" aria-label="按连接状态筛选数据源">
        <option value="all">全部连接状态</option>
        <option value="connected">已连接</option>
        <option value="syncing">正在同步</option>
        <option value="failed">同步失败</option>
        <option value="disconnected">未连接</option>
        <option value="permission-error">权限异常</option>
      </select>
    </div>

    <div v-if="filteredSources.length > 0" class="data-source-grid">
      <article v-for="source in filteredSources" :key="source.id">
        <header>
          <span class="data-source-icon" aria-hidden="true"><Database :size="20" /></span>
          <SearchStatusBadge :status="source.connectionStatus" />
        </header>
        <div>
          <span class="data-source-type">{{ sourceTypeLabels[source.type] }}</span>
          <h2>{{ source.name }}</h2>
          <p>{{ source.description }}</p>
        </div>
        <dl>
          <div>
            <dt>已同步内容</dt>
            <dd>{{ source.contentCount.toLocaleString("zh-CN") }} 条</dd>
          </div>
          <div>
            <dt>最近同步</dt>
            <dd>
              {{
                source.lastSyncedAt === "尚未同步"
                  ? source.lastSyncedAt
                  : new Date(source.lastSyncedAt).toLocaleString("zh-CN")
              }}
            </dd>
          </div>
          <div>
            <dt>权限状态</dt>
            <dd><SearchStatusBadge :status="source.permissionStatus" /></dd>
          </div>
        </dl>
        <div class="sync-progress">
          <span>同步进度</span>
          <strong>{{ source.syncProgress }}%</strong>
          <div
            role="progressbar"
            :aria-valuenow="source.syncProgress"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <span :style="{ width: `${source.syncProgress}%` }" />
          </div>
        </div>
        <footer>
          <span>模拟数据</span>
          <button
            type="button"
            @click="showSourceAction(source.name, source.actionLabel)"
          >
            {{ source.actionLabel }}
          </button>
        </footer>
      </article>
    </div>

    <InlineState
      v-else
      kind="empty"
      title="没有符合条件的数据源"
      description="请清空关键词或选择全部连接状态。"
    />
  </div>
</template>

<style scoped>
.data-sources-page {
  gap: var(--space-5);
}

.source-filter-bar,
.source-filter-bar label,
.data-source-grid article > header,
.data-source-grid footer,
.sync-progress > div {
  display: flex;
  align-items: center;
}

.source-filter-bar {
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.source-filter-bar label {
  min-height: 40px;
  flex: 1;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
}

.source-filter-bar input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
}

.source-filter-bar input:focus-visible {
  box-shadow: none;
}

.source-filter-bar select {
  min-width: 200px;
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.data-source-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}

.data-source-grid article {
  display: grid;
  min-width: 0;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.data-source-grid article > header,
.data-source-grid footer {
  justify-content: space-between;
  gap: var(--space-3);
}

.data-source-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.data-source-grid h2 {
  margin: var(--space-1) 0 var(--space-2);
  color: var(--color-text);
  font-size: var(--font-size-18);
}

.data-source-type {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
}

.data-source-grid p {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.65;
}

.data-source-grid dl {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.data-source-grid dl div {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  gap: var(--space-2);
  align-items: center;
}

.data-source-grid dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.data-source-grid dd {
  margin: 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--font-size-12);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sync-progress {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.sync-progress > div {
  grid-column: 1 / -1;
  height: 6px;
  overflow: hidden;
  border-radius: var(--radius-pill);
  background: var(--color-surface-subtle);
}

.sync-progress > div span {
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
}

.data-source-grid footer {
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.data-source-grid footer span {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.data-source-grid footer button {
  min-height: 34px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: var(--font-size-12);
}

@media (max-width: 1180px) {
  .data-source-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .source-filter-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .source-filter-bar label,
  .source-filter-bar select {
    width: 100%;
    min-height: 44px;
  }

  .data-source-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
