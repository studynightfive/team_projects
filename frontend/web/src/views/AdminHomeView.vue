<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { ref } from "vue";

import StatCard from "../components/StatCard.vue";
import {
  ChevronLeft,
  ChevronRight,
  FileDown,
  RefreshCw,
} from "../components/icons";
import {
  adminMetricIcons,
  foundationData,
  serviceIcons,
  serviceStatusTone,
} from "../data/foundation";

const { message } = AntApp.useApp();
const timeRange = ref("最近 24 小时");
const lastUpdated = ref("刚刚更新");

const refreshOverview = (): void => {
  lastUpdated.value = `${new Date().toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  })} 更新`;
  void message.success("概览数据已按当前演示数据刷新");
};

const showUpcomingNotice = (feature: string): void => {
  void message.info(`${feature}将在对应管理里程碑开放`);
};

const priorityClass = (priority: "高" | "中" | "低"): string =>
  ({ 高: "high", 中: "medium", 低: "low" })[priority];
</script>

<template>
  <div class="dashboard-page admin-dashboard">
    <header class="admin-page-heading">
      <div>
        <span class="system-label">管理系统</span>
        <h1>平台运行总览</h1>
        <p>用于验证管理层级与信息密度，不代表真实监控数据。</p>
      </div>
      <div class="admin-heading-actions">
        <label class="time-range-select">
          <span class="visually-hidden">统计时间范围</span>
          <select v-model="timeRange">
            <option>最近 24 小时</option>
            <option>最近 7 天</option>
            <option>最近 30 天</option>
          </select>
        </label>
        <button
          class="admin-primary-button"
          type="button"
          @click="refreshOverview"
        >
          <RefreshCw :size="17" aria-hidden="true" />
          刷新概览
        </button>
        <button
          class="secondary-button"
          type="button"
          @click="showUpcomingNotice('导出报告')"
        >
          <FileDown :size="17" aria-hidden="true" />
          导出报告
        </button>
        <span class="last-updated">{{ lastUpdated }}</span>
      </div>
    </header>

    <section class="stat-grid admin-stat-grid" aria-label="管理指标">
      <StatCard
        v-for="item in foundationData.adminView.summary"
        :key="item.label"
        :label="item.label"
        :value="item.value"
        :trend="item.trend"
        :tone="item.tone"
        :icon="adminMetricIcons[item.icon]"
        :series="item.series"
        admin
      />
    </section>

    <div class="admin-operations-grid">
      <section
        class="content-card service-card"
        aria-labelledby="service-title"
      >
        <header class="card-heading">
          <h2 id="service-title">服务健康状态</h2>
          <button
            class="text-button"
            type="button"
            @click="showUpcomingNotice('详细监控')"
          >
            查看详细监控
          </button>
        </header>
        <div class="service-list">
          <div
            v-for="service in foundationData.adminView.serviceHealth"
            :key="service.name"
            class="service-row"
          >
            <span class="service-icon" aria-hidden="true">
              <component
                :is="serviceIcons[service.icon]"
                :size="20"
                :stroke-width="1.8"
              />
            </span>
            <strong>{{ service.name }}</strong>
            <span
              class="status-badge"
              :class="serviceStatusTone[service.status]"
            >
              {{ service.status }}
            </span>
            <span class="service-metric">
              {{ service.metricLabel }}
              <strong>{{ service.metricValue }}</strong>
            </span>
          </div>
        </div>
      </section>

      <section
        class="content-card governance-card"
        aria-labelledby="governance-title"
      >
        <header class="card-heading">
          <div class="heading-with-count">
            <h2 id="governance-title">待治理事项</h2>
            <span class="count-badge" aria-label="7 项待治理">7</span>
          </div>
        </header>
        <div class="governance-list">
          <article
            v-for="item in foundationData.adminView.governanceQueue"
            :key="item.name"
            class="governance-row"
          >
            <div class="governance-main">
              <div>
                <strong>{{ item.name }}</strong>
                <span
                  class="priority-badge"
                  :class="priorityClass(item.priority)"
                >
                  {{ item.priority }}优先级
                </span>
              </div>
              <p>
                <span>{{ item.scope }}</span>
                <span>{{ item.submitter }}</span>
                <time>{{ item.time }}</time>
              </p>
            </div>
            <div class="governance-actions">
              <button
                class="secondary-button compact"
                type="button"
                @click="showUpcomingNotice(`查看${item.name}`)"
              >
                查看
              </button>
              <button
                class="admin-primary-button compact"
                type="button"
                @click="showUpcomingNotice(`处理${item.name}`)"
              >
                处理
              </button>
            </div>
          </article>
        </div>
      </section>
    </div>

    <section class="content-card audit-card" aria-labelledby="audit-title">
      <header class="card-heading audit-heading">
        <h2 id="audit-title">审计日志</h2>
        <button
          class="text-button"
          type="button"
          @click="showUpcomingNotice('完整审计日志')"
        >
          查看全部
        </button>
      </header>
      <div
        class="audit-table-scroll"
        tabindex="0"
        aria-label="审计日志表格，可横向滚动"
      >
        <table class="audit-table">
          <thead>
            <tr>
              <th scope="col">时间</th>
              <th scope="col">操作人</th>
              <th scope="col">操作类型</th>
              <th scope="col">操作对象</th>
              <th scope="col">IP 地址</th>
              <th scope="col">结果</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in foundationData.adminView.auditLogs"
              :key="item.time"
            >
              <td>{{ item.time }}</td>
              <td>{{ item.operator }}</td>
              <td>{{ item.action }}</td>
              <td :title="item.target">{{ item.target }}</td>
              <td class="numeric">{{ item.ip }}</td>
              <td>
                <span
                  class="result-badge"
                  :class="item.result === '成功' ? 'success' : 'failed'"
                >
                  {{ item.result }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer class="audit-pagination">
        <span>共 {{ foundationData.adminView.pagination.total }} 条</span>
        <span>
          {{ foundationData.adminView.pagination.page }} /
          {{ foundationData.adminView.pagination.totalPages }} 页
        </span>
        <button class="pagination-button" type="button" disabled>
          <ChevronLeft :size="15" aria-hidden="true" />
          上一页
        </button>
        <button
          class="pagination-button"
          type="button"
          @click="showUpcomingNotice('审计日志下一页')"
        >
          下一页
          <ChevronRight :size="15" aria-hidden="true" />
        </button>
      </footer>
    </section>
  </div>
</template>
