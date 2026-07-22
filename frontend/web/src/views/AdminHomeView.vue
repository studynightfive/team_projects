<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { toPublicApiError } from "../api/client";
import StatCard from "../components/StatCard.vue";
import { Database, FileText, RefreshCw, UsersRound } from "../components/icons";
import {
  getDashboardMetrics,
  listAuditLogs,
  type AuditLogItem,
  type DashboardMetrics,
} from "../services/admin";

const { message } = AntApp.useApp();
const metrics = ref<DashboardMetrics>();
const auditLogs = ref<readonly AuditLogItem[]>([]);
const loading = ref(false);
const lastUpdated = ref("尚未刷新");

const summaryCards = computed(() => [
  {
    label: "用户总数",
    value: String(metrics.value?.total_users ?? 0),
    trend: `活跃 ${metrics.value?.active_users ?? 0} / 停用 ${
      metrics.value?.disabled_users ?? 0
    }`,
    tone: "blue" as const,
    icon: UsersRound,
    series: [2, 4, 6, 8, 10, metrics.value?.total_users ?? 0],
  },
  {
    label: "知识库",
    value: String(metrics.value?.total_knowledge_bases ?? 0),
    trend: "来自真实知识库表",
    tone: "green" as const,
    icon: Database,
    series: [1, 1, 2, 3, 5, metrics.value?.total_knowledge_bases ?? 0],
  },
  {
    label: "文档",
    value: String(metrics.value?.total_documents ?? 0),
    trend: "上传处理后的文档数",
    tone: "amber" as const,
    icon: FileText,
    series: [1, 3, 4, 6, 8, metrics.value?.total_documents ?? 0],
  },
  {
    label: "会话",
    value: String(metrics.value?.total_conversations ?? 0),
    trend: `用户消息 ${metrics.value?.total_chats_today ?? 0}`,
    tone: "violet" as const,
    icon: RefreshCw,
    series: [0, 1, 1, 2, 3, metrics.value?.total_conversations ?? 0],
  },
]);

const resultLabel = (result: string): string =>
  ({ success: "成功", failure: "失败", denied: "拒绝" })[result] ?? result;

const formatDate = (value: string | null): string =>
  value === null ? "-" : new Date(value).toLocaleString("zh-CN");

const loadOverview = async (): Promise<void> => {
  loading.value = true;
  try {
    const [dashboard, auditPage] = await Promise.all([
      getDashboardMetrics(),
      listAuditLogs(),
    ]);
    metrics.value = dashboard;
    auditLogs.value = auditPage.items.slice(0, 6);
    lastUpdated.value = `${new Date().toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
    })} 更新`;
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

onMounted(loadOverview);
</script>

<template>
  <div class="dashboard-page admin-dashboard">
    <header class="admin-page-heading">
      <div>
        <span class="system-label">管理系统</span>
        <h1>平台运行总览</h1>
        <p>展示真实后端聚合指标、业务数据规模和最新审计记录。</p>
      </div>
      <div class="admin-heading-actions">
        <button
          class="admin-primary-button"
          type="button"
          :disabled="loading"
          @click="loadOverview"
        >
          <RefreshCw :size="17" aria-hidden="true" />
          {{ loading ? "刷新中" : "刷新概览" }}
        </button>
        <span class="last-updated">{{ lastUpdated }}</span>
      </div>
    </header>

    <section class="stat-grid admin-stat-grid" aria-label="管理指标">
      <StatCard
        v-for="item in summaryCards"
        :key="item.label"
        :label="item.label"
        :value="item.value"
        :trend="item.trend"
        :tone="item.tone"
        :icon="item.icon"
        :series="item.series"
        admin
      />
    </section>

    <div class="admin-operations-grid single-column">
      <section class="content-card service-card" aria-labelledby="service-title">
        <header class="card-heading">
          <h2 id="service-title">核心数据</h2>
          <RouterLink class="text-button" to="/admin/documents">
            查看文档
          </RouterLink>
        </header>
        <dl class="dashboard-facts">
          <div>
            <dt>角色</dt>
            <dd>{{ metrics?.total_roles ?? 0 }}</dd>
          </div>
          <div>
            <dt>平均响应</dt>
            <dd>{{ metrics?.avg_response_time_ms ?? 0 }} ms</dd>
          </div>
          <div>
            <dt>成功率</dt>
            <dd>{{ metrics?.success_rate ?? 0 }}%</dd>
          </div>
        </dl>
      </section>
    </div>

    <section class="content-card audit-card" aria-labelledby="audit-title">
      <header class="card-heading audit-heading">
        <h2 id="audit-title">最新审计日志</h2>
        <RouterLink class="text-button" to="/admin/audit-logs">
          查看全部
        </RouterLink>
      </header>
      <div class="audit-table-scroll" tabindex="0">
        <table class="audit-table">
          <thead>
            <tr>
              <th scope="col">时间</th>
              <th scope="col">操作人</th>
              <th scope="col">操作类型</th>
              <th scope="col">操作对象</th>
              <th scope="col">结果</th>
            </tr>
          </thead>
          <tbody>
            <template v-if="auditLogs.length === 0">
              <tr>
                <td colspan="5">暂无审计记录</td>
              </tr>
            </template>
            <template v-else>
              <tr v-for="item in auditLogs" :key="item.id">
                <td>{{ formatDate(item.created_at) }}</td>
                <td>{{ item.username ?? "系统" }}</td>
                <td>{{ item.action }}</td>
                <td>
                  {{ item.resource_type ?? "-" }} /
                  {{ item.resource_id ?? "-" }}
                </td>
                <td>
                  <span
                    class="result-badge"
                    :class="item.result === 'success' ? 'success' : 'failed'"
                  >
                    {{ resultLabel(item.result) }}
                  </span>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard-facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.dashboard-facts div {
  padding: var(--space-4);
  border-radius: var(--radius-8);
  background: var(--color-surface-muted);
}

.dashboard-facts dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.dashboard-facts dd {
  margin: var(--space-2) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-20);
  font-weight: var(--font-weight-semibold);
}
</style>
