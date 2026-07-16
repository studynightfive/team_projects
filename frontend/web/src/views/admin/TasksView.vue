<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { localPageData } from "../../data/local-pages";

type TaskItem = (typeof localPageData.tasks)[number];

const { message } = AntApp.useApp();
const tasks = ref<TaskItem[]>(localPageData.tasks.map((item) => ({ ...item })));
const query = ref("");
const statusFilter = ref("全部状态");
const selectedId = ref<string>();
const selectedTask = computed(() =>
  tasks.value.find((item) => item.id === selectedId.value),
);
const filteredTasks = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return tasks.value.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [item.name, item.stage, item.detail].some((value) =>
        value.toLowerCase().includes(keyword),
      );
    return (
      matchesQuery &&
      (statusFilter.value === "全部状态" || item.status === statusFilter.value)
    );
  });
});

const statusTone = (status: string): string =>
  ({
    处理中: "info",
    失败: "danger",
    需人工处理: "warning",
    成功: "success",
  })[status] ?? "neutral";

const updateTaskPreview = (id: string, action: "重试" | "复核"): void => {
  const item = tasks.value.find((task) => task.id === id);
  if (item === undefined) return;
  item.status = "处理中";
  item.detail =
    action === "重试"
      ? "本地预览：已重新进入处理队列"
      : "本地预览：已提交人工复核";
  void message.success(action + "状态已在当前页面更新");
};
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="文档与任务"
      title="任务中心"
      description="查看处理阶段、进度、失败原因和人工复核入口。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
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
            placeholder="文档、处理阶段或说明"
          />
        </label>
        <label>
          <span>任务状态</span>
          <select v-model="statusFilter">
            <option>全部状态</option>
            <option>处理中</option>
            <option>失败</option>
            <option>需人工处理</option>
            <option>成功</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="filteredTasks.length === 0"
        kind="empty"
        title="没有匹配的任务"
        description="请调整关键词或任务状态。"
      />
      <div
        v-else
        class="data-table-scroll"
        tabindex="0"
        aria-label="任务表格，可横向滚动"
      >
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">文档</th>
              <th scope="col">处理阶段</th>
              <th scope="col">状态</th>
              <th scope="col">进度</th>
              <th scope="col">说明</th>
              <th scope="col">创建时间</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredTasks" :key="item.id">
              <td>
                <strong>{{ item.name }}</strong>
              </td>
              <td>{{ item.stage }}</td>
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
                    :aria-label="`${item.name}处理进度 ${item.progress}%`"
                  />
                  <span>{{ item.progress }}%</span>
                </div>
              </td>
              <td>{{ item.detail }}</td>
              <td>{{ item.created }}</td>
              <td>
                <div class="table-actions">
                  <button
                    class="text-button"
                    type="button"
                    @click="selectedId = item.id"
                  >
                    详情
                  </button>
                  <button
                    v-if="item.status === '失败'"
                    class="text-button"
                    type="button"
                    @click="updateTaskPreview(item.id, '重试')"
                  >
                    重试
                  </button>
                  <button
                    v-if="item.status === '需人工处理'"
                    class="text-button"
                    type="button"
                    @click="updateTaskPreview(item.id, '复核')"
                  >
                    人工复核
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </ResourcePanel>

    <Drawer
      :open="selectedTask !== undefined"
      title="任务详情（本地预览）"
      width="420"
      root-class-name="variant-admin"
      @close="selectedId = undefined"
    >
      <dl v-if="selectedTask" class="detail-list">
        <div>
          <dt>文档</dt>
          <dd>{{ selectedTask.name }}</dd>
        </div>
        <div>
          <dt>处理阶段</dt>
          <dd>{{ selectedTask.stage }}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>{{ selectedTask.status }}</dd>
        </div>
        <div>
          <dt>进度</dt>
          <dd>{{ selectedTask.progress }}%</dd>
        </div>
        <div>
          <dt>说明</dt>
          <dd>{{ selectedTask.detail }}</dd>
        </div>
        <div>
          <dt>创建时间</dt>
          <dd>{{ selectedTask.created }}</dd>
        </div>
      </dl>
      <p class="preview-note">
        当前进度不会自动变化；未实现轮询、重试或人工复核接口。
      </p>
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
