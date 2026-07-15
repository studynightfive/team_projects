<script setup lang="ts">
import { Drawer } from "ant-design-vue";
import { computed, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { localPageData } from "../../data/local-pages";

const query = ref("");
const resultFilter = ref("全部结果");
const timeFilter = ref("全部时间");
const selectedId = ref<string>();
const selectedLog = computed(() =>
  localPageData.auditLogs.find((item) => item.id === selectedId.value),
);
const filteredLogs = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return localPageData.auditLogs.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [item.operator, item.action, item.resource].some((value) =>
        value.toLowerCase().includes(keyword),
      );
    const matchesResult =
      resultFilter.value === "全部结果" || item.result === resultFilter.value;
    const matchesTime =
      timeFilter.value === "全部时间" ||
      (timeFilter.value === "今天"
        ? item.time.startsWith("2026-07-16")
        : item.time >= "2026-07-09");
    return matchesQuery && matchesResult && matchesTime;
  });
});

const resultTone = (result: string): string =>
  result === "成功" ? "success" : "danger";

const maskIp = (ip: string): string => {
  const segments = ip.split(".");
  return segments.length === 4
    ? segments.slice(0, 3).join(".") + ".xxx"
    : "已掩码";
};

const maskRequestId = (requestId: string): string =>
  `demo-req-**${requestId.slice(-2)}`;
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="安全审计"
      title="审计日志"
      description="只读查看固定演示日志；请求标识和 IP 均使用确定性掩码。"
    >
      <template #actions>
        <span class="local-preview-badge">只读本地数据</span>
      </template>
    </PageHeader>

    <ResourcePanel
      title="操作记录"
      :description="'当前显示 ' + String(filteredLogs.length) + ' 条记录'"
    >
      <div class="filter-bar" aria-label="审计日志筛选">
        <label>
          <span>搜索记录</span>
          <input
            v-model="query"
            type="search"
            placeholder="操作人、操作类型或资源"
          />
        </label>
        <label>
          <span>时间范围</span>
          <select v-model="timeFilter">
            <option>全部时间</option>
            <option>今天</option>
            <option>过去 7 天</option>
          </select>
        </label>
        <label>
          <span>结果</span>
          <select v-model="resultFilter">
            <option>全部结果</option>
            <option>成功</option>
            <option>失败</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="filteredLogs.length === 0"
        kind="empty"
        title="没有匹配的审计记录"
        description="请调整关键词、时间范围或结果。"
      />
      <div
        v-else
        class="data-table-scroll"
        tabindex="0"
        aria-label="审计日志表格，可横向滚动"
      >
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">时间</th>
              <th scope="col">操作人</th>
              <th scope="col">操作类型</th>
              <th scope="col">资源</th>
              <th scope="col">Request ID</th>
              <th scope="col">IP</th>
              <th scope="col">结果</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredLogs" :key="item.id">
              <td class="numeric">{{ item.time }}</td>
              <td>{{ item.operator }}</td>
              <td>{{ item.action }}</td>
              <td>{{ item.resource }}</td>
              <td class="numeric">{{ maskRequestId(item.requestId) }}</td>
              <td class="numeric">{{ maskIp(item.ip) }}</td>
              <td>
                <span class="status-chip" :class="resultTone(item.result)">
                  {{ item.result }}
                </span>
              </td>
              <td>
                <button
                  class="text-button"
                  type="button"
                  @click="selectedId = item.id"
                >
                  查看详情
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <div class="panel-pagination">
          <span>第 1 / 1 页</span>
          <button class="pagination-button" type="button" disabled>
            上一页
          </button>
          <button class="pagination-button" type="button" disabled>
            下一页
          </button>
        </div>
      </template>
    </ResourcePanel>

    <Drawer
      :open="selectedLog !== undefined"
      title="审计详情（只读）"
      width="460"
      root-class-name="variant-admin"
      @close="selectedId = undefined"
    >
      <dl v-if="selectedLog" class="detail-list">
        <div>
          <dt>时间</dt>
          <dd>{{ selectedLog.time }}</dd>
        </div>
        <div>
          <dt>操作人</dt>
          <dd>{{ selectedLog.operator }}</dd>
        </div>
        <div>
          <dt>操作类型</dt>
          <dd>{{ selectedLog.action }}</dd>
        </div>
        <div>
          <dt>资源</dt>
          <dd>{{ selectedLog.resource }}</dd>
        </div>
        <div>
          <dt>Request ID</dt>
          <dd>{{ maskRequestId(selectedLog.requestId) }}</dd>
        </div>
        <div>
          <dt>IP</dt>
          <dd>{{ maskIp(selectedLog.ip) }}</dd>
        </div>
        <div>
          <dt>结果</dt>
          <dd>{{ selectedLog.result }}</dd>
        </div>
        <div>
          <dt>安全详情</dt>
          <dd>{{ selectedLog.detail }}</dd>
        </div>
      </dl>
      <p class="preview-note">不展示请求体、凭据、内部堆栈或未掩码网络标识。</p>
    </Drawer>
  </div>
</template>
