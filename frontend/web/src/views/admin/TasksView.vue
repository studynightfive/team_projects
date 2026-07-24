<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, ref } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { useListPagination } from "../../composables/useListPagination";
import { listAdminTasks, type AdminTask } from "../../services/admin";

const { message } = AntApp.useApp();
const tasks = ref<readonly AdminTask[]>([]);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedId = ref<string>();
const loading = ref(false);
const selectedTask = computed(() =>
  tasks.value.find((item) => item.task_id === selectedId.value),
);
const filteredTasks = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return tasks.value.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [item.document_title, item.stage, item.knowledge_base_name].some((value) =>
        value.toLowerCase().includes(keyword),
      );
    return (
      matchesQuery &&
      (statusFilter.value === "全部状态" ||
        statusLabel(item.status) === statusFilter.value)
    );
  });
});
const {
  page: tasksPage,
  pageSize: tasksPageSize,
  pagedItems: pagedTasks,
  setPage: setTasksPage,
} = useListPagination(filteredTasks);

const statusLabel = (status: string): string =>
  ({
    queued: "排队中",
    running: "处理中",
    succeeded: "成功",
    failed: "失败",
    cancelled: "已取消",
    manual_review: "需人工处理",
  })[status] ?? status;

const statusTone = (status: string): string =>
  ({
    queued: "info",
    running: "info",
    succeeded: "success",
    failed: "danger",
    cancelled: "neutral",
    manual_review: "warning",
  })[status] ?? "neutral";

const formatDate = (value: string | null): string =>
  value === null ? "-" : new Date(value).toLocaleString("zh-CN");

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const page = await listAdminTasks();
    tasks.value = page.items;
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
      eyebrow="文档与任务"
      title="任务中心"
      description="查看真实文档处理任务的阶段、进度、失败原因和请求标识。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="任务列表"
      :description="'当前显示 ' + String(filteredTasks.length) + ' 项任务'"
    >
      <div class="filter-bar" aria-label="任务筛选">
        <label>
          <span>搜索任务</span>
          <input
            v-model="query"
            type="search"
            placeholder="文档、知识库或处理阶段"
          />
        </label>
        <label>
          <span>任务状态</span>
          <select v-model="statusFilter">
            <option>全部状态</option>
            <option>排队中</option>
            <option>处理中</option>
            <option>成功</option>
            <option>失败</option>
            <option>需人工处理</option>
            <option>已取消</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="loading"
        kind="loading"
        title="正在加载任务"
        description="请稍候。"
      />
      <InlineState
        v-else-if="filteredTasks.length === 0"
        kind="empty"
        title="没有匹配的任务"
        description="上传文档后会生成处理任务。"
      />
      <div v-else class="data-table-scroll" tabindex="0">
        <table class="data-table mobile-sticky-actions">
          <thead>
            <tr>
              <th scope="col">文档</th>
              <th scope="col">知识库</th>
              <th scope="col">处理阶段</th>
              <th scope="col">状态</th>
              <th scope="col">进度</th>
              <th scope="col">说明</th>
              <th scope="col">创建时间</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pagedTasks" :key="item.task_id">
              <td>
                <strong>{{ item.document_title }}</strong>
                <small>{{ item.task_type }}</small>
              </td>
              <td>{{ item.knowledge_base_name }}</td>
              <td>{{ item.stage }}</td>
              <td>
                <span class="status-chip" :class="statusTone(item.status)">
                  {{ statusLabel(item.status) }}
                </span>
              </td>
              <td>
                <div class="progress-cell">
                  <progress
                    :value="item.progress"
                    max="100"
                    :aria-label="`${item.document_title}处理进度 ${item.progress}%`"
                  />
                  <span>{{ Math.round(item.progress) }}%</span>
                </div>
              </td>
              <td>{{ item.error_message ?? "-" }}</td>
              <td>{{ formatDate(item.created_at) }}</td>
              <td>
                <button
                  class="text-button"
                  type="button"
                  @click="selectedId = item.task_id"
                >
                  详情
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <ListPagination
        v-if="filteredTasks.length > 0"
        :page="tasksPage"
        :page-size="tasksPageSize"
        :total="filteredTasks.length"
        @change="setTasksPage"
      />
    </ResourcePanel>

    <Drawer
      :open="selectedTask !== undefined"
      title="任务详情"
      width="420"
      root-class-name="variant-admin"
      @close="selectedId = undefined"
    >
      <dl v-if="selectedTask" class="detail-list">
        <div>
          <dt>任务 ID</dt>
          <dd>{{ selectedTask.task_id }}</dd>
        </div>
        <div>
          <dt>文档</dt>
          <dd>{{ selectedTask.document_title }}</dd>
        </div>
        <div>
          <dt>处理阶段</dt>
          <dd>{{ selectedTask.stage }}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>{{ statusLabel(selectedTask.status) }}</dd>
        </div>
        <div>
          <dt>进度</dt>
          <dd>{{ Math.round(selectedTask.progress) }}%</dd>
        </div>
        <div>
          <dt>重试次数</dt>
          <dd>{{ selectedTask.retry_count }}</dd>
        </div>
        <div>
          <dt>Request ID</dt>
          <dd>{{ selectedTask.request_id }}</dd>
        </div>
        <div v-if="selectedTask.error_message">
          <dt>错误信息</dt>
          <dd>{{ selectedTask.error_message }}</dd>
        </div>
      </dl>
    </Drawer>
  </div>
</template>

<style scoped>
.progress-cell {
  display: flex;
  min-width: 130px;
  align-items: center;
  gap: var(--space-2);
}

.progress-cell progress {
  width: 86px;
  accent-color: var(--color-admin);
}

.progress-cell span {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}
</style>
