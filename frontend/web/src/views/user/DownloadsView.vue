<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { Download, RefreshCw, X } from "../../components/icons";
import { localPageData } from "../../data/local-pages";

const { message } = AntApp.useApp();
const query = ref("");
const status = ref("全部状态");
const visibleIds = ref<string[]>(
  localPageData.downloads.map((item) => item.id),
);
const pendingDeleteId = ref<string>();

const statuses = computed(() => [
  "全部状态",
  ...new Set(localPageData.downloads.map((item) => item.status)),
]);

const filteredDownloads = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase("zh-CN");

  return localPageData.downloads.filter((item) => {
    const isVisible = visibleIds.value.includes(item.id);
    const matchesStatus =
      status.value === "全部状态" || item.status === status.value;
    const matchesQuery =
      normalizedQuery.length === 0 ||
      `${item.name}${item.format}`
        .toLocaleLowerCase("zh-CN")
        .includes(normalizedQuery);

    return isVisible && matchesStatus && matchesQuery;
  });
});

const statusTone = (itemStatus: string): string => {
  if (itemStatus === "已完成") return "success";
  if (itemStatus === "失败" || itemStatus === "已过期") return "failed";
  return "warning";
};

const requestDownload = (name: string): void => {
  void message.info(`${name} 等待鉴权下载接口，当前不会构造文件地址`);
};

const recreateExport = (name: string): void => {
  void message.info(`${name} 的重新创建仅为本地预览，不会提交导出任务`);
};

const confirmDelete = (): void => {
  if (!pendingDeleteId.value) return;

  visibleIds.value = visibleIds.value.filter(
    (id) => id !== pendingDeleteId.value,
  );
  pendingDeleteId.value = undefined;
  void message.success("任务记录已从本地预览中移除");
};
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="用户工作区"
      title="我的下载"
      description="查看导出任务状态和过期反馈；所有下载操作都保持鉴权接口边界。"
    >
      <template #actions>
        <span class="local-preview-badge">不生成下载地址</span>
      </template>
    </PageHeader>

    <ResourcePanel
      title="导出任务"
      description="任务进度、筛选和删除仅保留到本次刷新。"
    >
      <div class="filter-bar">
        <label class="filter-field grow">
          <span>搜索导出任务</span>
          <input
            v-model="query"
            type="search"
            placeholder="搜索文件名或格式"
            autocomplete="off"
          />
        </label>
        <label>
          <span>导出任务状态</span>
          <select v-model="status">
            <option v-for="item in statuses" :key="item">{{ item }}</option>
          </select>
        </label>
      </div>

      <div v-if="pendingDeleteId" class="delete-confirmation" role="alert">
        <div>
          <strong>确认删除这条本地任务记录？</strong>
          <p>不会请求服务端，刷新后固定任务会恢复。</p>
        </div>
        <div>
          <button
            class="secondary-button compact"
            type="button"
            @click="pendingDeleteId = undefined"
          >
            取消
          </button>
          <button
            class="primary-button compact"
            type="button"
            @click="confirmDelete"
          >
            确认删除
          </button>
        </div>
      </div>

      <div
        v-if="filteredDownloads.length > 0"
        class="data-table-scroll"
        tabindex="0"
        aria-label="导出任务表格，可横向滚动"
      >
        <table class="data-table download-table">
          <thead>
            <tr>
              <th scope="col">文件</th>
              <th scope="col">格式</th>
              <th scope="col">状态</th>
              <th scope="col">进度</th>
              <th scope="col">创建时间</th>
              <th scope="col">有效期</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredDownloads" :key="item.id">
              <td class="download-name">{{ item.name }}</td>
              <td>{{ item.format }}</td>
              <td>
                <span class="status-chip" :class="statusTone(item.status)">
                  {{ item.status }}
                </span>
              </td>
              <td>
                <div class="progress-cell">
                  <progress
                    :value="item.progress"
                    max="100"
                    :aria-label="`${item.name}导出进度 ${item.progress}%`"
                  >
                    {{ item.progress }}%
                  </progress>
                  <span>{{ item.progress }}%</span>
                </div>
              </td>
              <td>{{ item.created }}</td>
              <td>{{ item.expires }}</td>
              <td>
                <div class="table-actions">
                  <button
                    v-if="item.status === '已完成'"
                    class="table-action"
                    type="button"
                    @click="requestDownload(item.name)"
                  >
                    <Download :size="15" aria-hidden="true" />
                    下载
                  </button>
                  <button
                    v-else-if="
                      item.status === '失败' || item.status === '已过期'
                    "
                    class="table-action"
                    type="button"
                    @click="recreateExport(item.name)"
                  >
                    <RefreshCw :size="15" aria-hidden="true" />
                    重新创建
                  </button>
                  <span v-else class="pending-copy">等待完成</span>
                  <button
                    class="delete-action"
                    type="button"
                    :aria-label="`删除${item.name}任务记录`"
                    @click="pendingDeleteId = item.id"
                  >
                    <X :size="15" aria-hidden="true" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <InlineState
        v-else
        kind="empty"
        title="没有匹配的导出任务"
        description="请清除关键词或切换任务状态。"
      />

      <template #footer>
        <span>共 {{ filteredDownloads.length }} 条本地任务</span>
        <span>第 1 / 1 页</span>
      </template>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.local-page {
  display: grid;
  gap: var(--space-6);
}

.download-table {
  min-width: 960px;
}

.download-name {
  max-width: 280px;
  overflow: hidden;
  font-weight: var(--font-weight-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-cell {
  display: grid;
  grid-template-columns: 100px auto;
  align-items: center;
  gap: var(--space-2);
}

.progress-cell progress {
  width: 100px;
  accent-color: var(--color-primary);
}

.table-actions,
.delete-confirmation,
.delete-confirmation > div:last-child {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.table-action,
.delete-action {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  gap: var(--space-1);
  border-radius: var(--radius-8);
  background: transparent;
}

.table-action {
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
}

.delete-action {
  width: 32px;
  justify-content: center;
  color: var(--color-danger-text);
}

.pending-copy {
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
  white-space: nowrap;
}

.delete-confirmation {
  justify-content: space-between;
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--red-100);
  border-radius: var(--radius-8);
  background: var(--color-danger-soft);
}

.delete-confirmation p {
  margin: var(--space-1) 0 0;
  color: var(--color-danger-text);
  font-size: var(--font-size-13);
}

@media (max-width: 767px) {
  .table-action,
  .delete-action {
    min-height: 44px;
  }

  .delete-action {
    width: 44px;
  }

  .delete-confirmation {
    display: grid;
  }
}
</style>
