<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, ref } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { listAuditLogs, type AuditLogItem } from "../../services/admin";

const { message } = AntApp.useApp();
const logs = ref<readonly AuditLogItem[]>([]);
const query = ref("");
const resultFilter = ref("全部结果");
const selectedId = ref<string>();
const loading = ref(false);
const selectedLog = computed(() =>
  logs.value.find((item) => item.id === selectedId.value),
);
const filteredLogs = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return logs.value.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [
        item.username ?? "",
        item.action,
        item.resource_type ?? "",
        item.resource_id ?? "",
      ].some((value) => value.toLowerCase().includes(keyword));
    const result = resultLabel(item.result);
    return (
      matchesQuery &&
      (resultFilter.value === "全部结果" || result === resultFilter.value)
    );
  });
});

const resultLabel = (result: string): string =>
  ({ success: "成功", failure: "失败", denied: "拒绝" })[result] ?? result;

const resultTone = (result: string): string =>
  result === "success" ? "success" : "danger";

const formatDate = (value: string | null): string =>
  value === null ? "-" : new Date(value).toLocaleString("zh-CN");

const maskIp = (ip: string | null): string => {
  if (ip === null || ip === "") return "未记录";
  const segments = ip.split(".");
  return segments.length === 4
    ? segments.slice(0, 3).join(".") + ".xxx"
    : "已掩码";
};

const maskRequestId = (requestId: string | null): string =>
  requestId === null || requestId === ""
    ? "未记录"
    : `${requestId.slice(0, 6)}****${requestId.slice(-4)}`;

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const page = await listAuditLogs();
    logs.value = page.items;
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

onMounted(loadData);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="安全审计"
      title="审计日志"
      description="只读查看真实操作记录；请求标识和 IP 在前端掩码展示。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
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
          <span>结果</span>
          <select v-model="resultFilter">
            <option>全部结果</option>
            <option>成功</option>
            <option>失败</option>
            <option>拒绝</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="loading"
        kind="loading"
        title="正在加载审计日志"
        description="请稍候。"
      />
      <InlineState
        v-else-if="filteredLogs.length === 0"
        kind="empty"
        title="没有匹配的审计记录"
        description="真实操作产生后会在这里显示。"
      />
      <div v-else class="data-table-scroll" tabindex="0">
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
              <td class="numeric">{{ formatDate(item.created_at) }}</td>
              <td>{{ item.username ?? "系统" }}</td>
              <td>{{ item.action }}</td>
              <td>{{ item.resource_type ?? "-" }} / {{ item.resource_id ?? "-" }}</td>
              <td class="numeric">{{ maskRequestId(item.request_id) }}</td>
              <td class="numeric">{{ maskIp(item.ip_address) }}</td>
              <td>
                <span class="status-chip" :class="resultTone(item.result)">
                  {{ resultLabel(item.result) }}
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
    </ResourcePanel>

    <Drawer
      :open="selectedLog !== undefined"
      title="审计详情"
      width="460"
      root-class-name="variant-admin"
      @close="selectedId = undefined"
    >
      <dl v-if="selectedLog" class="detail-list">
        <div>
          <dt>时间</dt>
          <dd>{{ formatDate(selectedLog.created_at) }}</dd>
        </div>
        <div>
          <dt>操作人</dt>
          <dd>{{ selectedLog.username ?? "系统" }}</dd>
        </div>
        <div>
          <dt>操作类型</dt>
          <dd>{{ selectedLog.action }}</dd>
        </div>
        <div>
          <dt>资源</dt>
          <dd>
            {{ selectedLog.resource_type ?? "-" }} /
            {{ selectedLog.resource_id ?? "-" }}
          </dd>
        </div>
        <div>
          <dt>Request ID</dt>
          <dd>{{ maskRequestId(selectedLog.request_id) }}</dd>
        </div>
        <div>
          <dt>IP</dt>
          <dd>{{ maskIp(selectedLog.ip_address) }}</dd>
        </div>
        <div>
          <dt>结果</dt>
          <dd>{{ resultLabel(selectedLog.result) }}</dd>
        </div>
        <div>
          <dt>安全详情</dt>
          <dd>{{ selectedLog.detail ?? "未记录详情" }}</dd>
        </div>
      </dl>
      <p class="preview-note">不展示请求体、凭据、内部堆栈或未掩码网络标识。</p>
    </Drawer>
  </div>
</template>
