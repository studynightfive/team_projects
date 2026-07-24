<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onMounted, ref, watch } from "vue";

import { toPublicApiError } from "../api/client";
import InlineState from "../components/InlineState.vue";
import ListPagination from "../components/ListPagination.vue";
import StatCard from "../components/StatCard.vue";
import {
  BadgeCheck,
  CircleX,
  Database,
  Gauge,
  RefreshCw,
} from "../components/icons";
import {
  getDashboardMetrics,
  listDepartments,
  type DashboardDays,
  type DashboardMetrics,
  type DepartmentRecord,
} from "../services/admin";
import { useSessionStore } from "../stores/session";

const { message } = AntApp.useApp();
const sessionStore = useSessionStore();
const metrics = ref<DashboardMetrics>();
const departments = ref<readonly DepartmentRecord[]>([]);
const loading = ref(false);
const loadError = ref("");
const lastUpdated = ref("尚未刷新");
const days = ref<DashboardDays>(30);
const departmentId = ref("");
const leaderboardPage = ref(1);
const leaderboardPageSize = ref(10);
let loadSequence = 0;

const canSelectDepartment = computed(() =>
  sessionStore.hasAnyPermission(["admin.department.view"]),
);

const summaryCards = computed(() => [
  {
    label: "知识覆盖率",
    value: `${metrics.value?.knowledge_coverage.rate ?? 0}%`,
    trend: `${metrics.value?.knowledge_coverage.numerator ?? 0} / ${
      metrics.value?.knowledge_coverage.denominator ?? 0
    } 个企业知识库`,
    tone: "blue" as const,
    icon: Database,
  },
  {
    label: "活跃检索",
    value: String(metrics.value?.active_searches ?? 0),
    trend: `最近 ${metrics.value?.period.days ?? days.value} 天已完成请求`,
    tone: "violet" as const,
    icon: Gauge,
  },
  {
    label: "有效回答",
    value: String(metrics.value?.effective_answers ?? 0),
    trend: "命中引用并完成生成或缓存复用",
    tone: "green" as const,
    icon: BadgeCheck,
  },
  {
    label: "未命中",
    value: String(metrics.value?.unanswered_queries ?? 0),
    trend: "未找到可引用内容的回答",
    tone: "red" as const,
    icon: CircleX,
  },
]);

const loadOverview = async (): Promise<void> => {
  const sequence = ++loadSequence;
  loading.value = true;
  loadError.value = "";
  try {
    const dashboard = await getDashboardMetrics({
      days: days.value,
      department_id: departmentId.value || undefined,
      leaderboard_page: leaderboardPage.value,
      leaderboard_page_size: leaderboardPageSize.value,
    });
    if (sequence !== loadSequence) return;
    metrics.value = dashboard;
    lastUpdated.value = `${new Date().toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
    })} 更新`;
  } catch (error: unknown) {
    if (sequence !== loadSequence) return;
    const publicError = toPublicApiError(error);
    if (metrics.value === undefined) loadError.value = publicError.message;
    else void message.error(publicError.message);
  } finally {
    if (sequence === loadSequence) loading.value = false;
  }
};

const initialize = async (): Promise<void> => {
  if (canSelectDepartment.value) {
    try {
      departments.value = await listDepartments();
    } catch (error: unknown) {
      void message.warning(toPublicApiError(error).message);
    }
  }
  await loadOverview();
};

const changeLeaderboardPage = (
  page: number,
  pageSize: number,
): void => {
  leaderboardPage.value = pageSize === leaderboardPageSize.value ? page : 1;
  leaderboardPageSize.value = pageSize;
  void loadOverview();
};

watch([days, departmentId], () => {
  leaderboardPage.value = 1;
  void loadOverview();
});

onMounted(() => {
  void initialize();
});
</script>

<template>
  <div class="dashboard-page admin-dashboard">
    <header class="admin-page-heading">
      <div>
        <span class="system-label">管理系统</span>
        <h1>业务运营看板</h1>
        <p>
          按真实知识建设与检索结果，观察覆盖、回答质量、处理效率和部门贡献。
        </p>
      </div>
      <div class="admin-heading-actions dashboard-controls">
        <label>
          <span>统计周期</span>
          <select v-model="days" aria-label="统计周期">
            <option :value="7">最近 7 天</option>
            <option :value="30">最近 30 天</option>
            <option :value="90">最近 90 天</option>
          </select>
        </label>
        <label v-if="canSelectDepartment && departments.length > 0">
          <span>部门范围</span>
          <select v-model="departmentId" aria-label="部门范围">
            <option value="">全部部门</option>
            <option
              v-for="department in departments"
              :key="department.id"
              :value="department.id"
            >
              {{ department.name }}
            </option>
          </select>
        </label>
        <button
          class="admin-primary-button"
          type="button"
          :disabled="loading"
          @click="loadOverview"
        >
          <RefreshCw :size="17" aria-hidden="true" />
          {{ loading ? "刷新中" : "刷新看板" }}
        </button>
        <span class="last-updated">{{ lastUpdated }}</span>
      </div>
    </header>

    <InlineState
      v-if="loadError && metrics === undefined"
      kind="error"
      title="业务看板加载失败"
      :description="loadError"
    />
    <InlineState
      v-else-if="metrics === undefined"
      kind="loading"
      title="正在汇总业务指标"
      description="正在计算知识覆盖、检索质量与部门贡献。"
    />

    <template v-else>
      <section class="stat-grid admin-stat-grid" aria-label="业务指标">
        <StatCard
          v-for="item in summaryCards"
          :key="item.label"
          :label="item.label"
          :value="item.value"
          :trend="item.trend"
          :tone="item.tone"
          :icon="item.icon"
          admin
        />
      </section>

      <section class="content-card quality-card" aria-labelledby="quality-title">
        <header class="card-heading">
          <div>
            <h2 id="quality-title">效率与质量</h2>
            <p>
              {{ metrics.scope.department_name }} · 最近
              {{ metrics.period.days }} 天
            </p>
          </div>
        </header>
        <dl class="dashboard-facts">
          <div>
            <dt>文档处理成功率</dt>
            <dd>{{ metrics.document_processing.rate }}%</dd>
            <small>
              成功 {{ metrics.document_processing.numerator }} /
              {{ metrics.document_processing.denominator }}
            </small>
          </div>
          <div>
            <dt>答案缓存命中率</dt>
            <dd>{{ metrics.answer_cache.rate }}%</dd>
            <small>
              命中 {{ metrics.answer_cache.numerator }} /
              {{ metrics.answer_cache.denominator }}
            </small>
          </div>
          <div>
            <dt>平均响应时间</dt>
            <dd>{{ metrics.response_time.average_ms }} ms</dd>
            <small>{{ metrics.response_time.sample_count }} 次完成请求</small>
          </div>
        </dl>
      </section>

      <section class="content-card leaderboard-card" aria-labelledby="leaderboard-title">
        <header class="card-heading">
          <div>
            <h2 id="leaderboard-title">部门知识贡献榜</h2>
            <p>相同内容只计一次，搜索和重复处理不计分。</p>
          </div>
        </header>
        <div
          v-if="metrics.department_leaderboard.items.length > 0"
          class="leaderboard-table-scroll"
          tabindex="0"
        >
          <table class="leaderboard-table">
            <thead>
              <tr>
                <th scope="col">排名</th>
                <th scope="col">部门</th>
                <th scope="col">积分</th>
                <th scope="col">有效文档</th>
                <th scope="col">贡献人数</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in metrics.department_leaderboard.items"
                :key="item.department_id"
              >
                <td><span class="rank-mark">{{ item.rank }}</span></td>
                <td>{{ item.department_name }}</td>
                <td><strong>{{ item.points }}</strong></td>
                <td>{{ item.contribution_count }}</td>
                <td>{{ item.contributor_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <InlineState
          v-else
          kind="empty"
          title="暂无部门贡献"
          description="文档成功处理并启用索引后，将在这里形成真实积分。"
        />
        <ListPagination
          v-if="metrics.department_leaderboard.total > 0"
          :page="metrics.department_leaderboard.page"
          :page-size="metrics.department_leaderboard.page_size"
          :total="metrics.department_leaderboard.total"
          @change="changeLeaderboardPage"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.dashboard-controls label {
  display: grid;
  gap: var(--space-1);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.dashboard-controls select {
  min-width: 132px;
  height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-6);
  color: var(--color-text);
  background: var(--color-surface);
}

.card-heading > div {
  min-width: 0;
}

.card-heading p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.dashboard-facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
  padding: 0 var(--space-6) var(--space-6);
}

.dashboard-facts div {
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-muted);
}

.dashboard-facts dt,
.dashboard-facts small {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.dashboard-facts dd {
  margin: var(--space-2) 0 var(--space-1);
  color: var(--color-text);
  font-size: var(--font-size-20);
  font-weight: var(--font-weight-semibold);
}

.leaderboard-table-scroll {
  overflow-x: auto;
}

.leaderboard-table {
  width: 100%;
  border-collapse: collapse;
}

.leaderboard-table th,
.leaderboard-table td {
  min-width: 112px;
  padding: var(--space-3) var(--space-6);
  border-top: 1px solid var(--color-border);
  text-align: left;
}

.leaderboard-table th {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
}

.rank-mark {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  color: var(--color-admin);
  background: var(--color-admin-soft);
  font-weight: var(--font-weight-semibold);
}

.leaderboard-card :deep(.list-pagination) {
  padding: var(--space-4) var(--space-6);
}

@media (max-width: 1023px) {
  .admin-page-heading {
    flex-direction: column;
  }

  .dashboard-controls {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 767px) {
  .dashboard-controls label,
  .dashboard-controls select,
  .dashboard-controls .admin-primary-button {
    width: 100%;
  }

  .dashboard-facts {
    grid-template-columns: 1fr;
    padding: 0 var(--space-4) var(--space-4);
  }

  .leaderboard-table th,
  .leaderboard-table td {
    padding-right: var(--space-4);
    padding-left: var(--space-4);
  }

  .leaderboard-card :deep(.list-pagination) {
    padding: var(--space-4);
  }
}
</style>
