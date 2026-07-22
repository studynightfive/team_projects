<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { useListPagination } from "../../composables/useListPagination";
import { Download, RefreshCw, X } from "../../components/icons";
import { toPublicApiError } from "../../api/client";
import { isRealApiMode } from "../../config/runtime";
import { localPageData } from "../../data/local-pages";
import {
  createExportTask,
  deleteExportTask,
  downloadExportBlob,
  listAllExportTasks,
  type ExportFormat,
  type ExportStatus,
  type ExportTaskRecord,
} from "../../services/downloads";
import {
  prepareFileSave,
  type PreparedFileSave,
} from "../../services/file-save";

const { message, modal } = AntApp.useApp();
const query = ref("");
const status = ref("全部状态");
const visibleIds = ref<string[]>(
  localPageData.downloads.map((item) => item.id),
);
const realDownloads = ref<readonly ExportTaskRecord[]>([]);
const realTotal = ref(0);
const loadState = ref<"idle" | "loading" | "error">("idle");
const loadError = ref("");
const busyTaskId = ref<string>();

let loadController: AbortController | undefined;

interface DownloadRow {
  readonly id: string;
  readonly name: string;
  readonly format: string;
  readonly status: string;
  readonly progress: number;
  readonly created: string;
  readonly expires: string;
  readonly downloadUrl?: string | null;
  readonly documentIds?: readonly string[];
  readonly rawFormat?: ExportFormat;
  readonly errorMessage?: string | null;
  readonly sourceType?: "document" | "answer";
}

const statusLabels = {
  pending: "等待中",
  running: "处理中",
  done: "已完成",
  failed: "失败",
  expired: "已过期",
  cancelled: "已取消",
} as const satisfies Record<ExportStatus, string>;

const formatLabels = {
  pdf: "PDF",
  docx: "DOCX",
  markdown: "Markdown",
  csv: "CSV",
  txt: "TXT",
} as const satisfies Record<ExportFormat, string>;

const formatDateTime = (value: string | null): string => {
  if (value === null || value === "") return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
};

const toRealDownloadRow = (item: ExportTaskRecord): DownloadRow => ({
  id: item.id,
  name:
    item.filename ??
    (item.source_type === "answer"
      ? `RAG 问答结果 ${item.id.slice(0, 8)}`
      : `文档导出 ${item.id.slice(0, 8)}（${item.document_ids.length} 个文档）`),
  format: formatLabels[item.format],
  status: statusLabels[item.status],
  progress: item.progress,
  created: formatDateTime(item.created_at),
  expires: formatDateTime(item.expires_at),
  downloadUrl: item.download_url,
  documentIds: item.document_ids,
  rawFormat: item.format,
  errorMessage: item.error_message,
  sourceType: item.source_type,
});

const downloadRows = computed<readonly DownloadRow[]>(() =>
  isRealApiMode
    ? realDownloads.value.map(toRealDownloadRow)
    : localPageData.downloads,
);

const statuses = computed(() => [
  "全部状态",
  ...new Set(downloadRows.value.map((item) => item.status)),
]);

const filteredDownloads = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase("zh-CN");

  return downloadRows.value.filter((item) => {
    const isVisible = isRealApiMode || visibleIds.value.includes(item.id);
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
const {
  page: downloadsPage,
  pageSize: downloadsPageSize,
  pagedItems: pagedDownloads,
  setPage: setDownloadsPage,
} = useListPagination(filteredDownloads);

const statusTone = (itemStatus: string): string => {
  if (itemStatus === "已完成") return "success";
  if (itemStatus === "失败" || itemStatus === "已过期") return "failed";
  return "warning";
};

const loadRealDownloads = async (): Promise<void> => {
  if (!isRealApiMode) return;

  loadController?.abort();
  loadController = new AbortController();
  loadState.value = "loading";
  loadError.value = "";

  try {
    const page = await listAllExportTasks(loadController.signal);
    realDownloads.value = page.items;
    realTotal.value = page.total;
    loadState.value = "idle";
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    loadError.value = toPublicApiError(error).message;
    loadState.value = "error";
  }
};

const downloadFormatOptions = {
  pdf: { mediaType: "application/pdf", extension: ".pdf", label: "PDF 文档" },
  docx: {
    mediaType:
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    extension: ".docx",
    label: "Word 文档",
  },
  markdown: {
    mediaType: "text/markdown",
    extension: ".md",
    label: "Markdown 文档",
  },
  csv: { mediaType: "text/csv", extension: ".csv", label: "CSV 文件" },
  txt: { mediaType: "text/plain", extension: ".txt", label: "文本文件" },
} as const satisfies Record<
  ExportFormat,
  {
    readonly mediaType: string;
    readonly extension: string;
    readonly label: string;
  }
>;

const requestDownload = async (item: DownloadRow): Promise<void> => {
  if (!isRealApiMode) {
    void message.info(`${item.name} 等待鉴权下载接口，当前不会构造文件地址`);
    return;
  }

  if (item.downloadUrl === null || item.downloadUrl === undefined) {
    void message.warning("当前任务尚未生成可下载文件。");
    return;
  }

  const isZip = item.name.toLocaleLowerCase("zh-CN").endsWith(".zip");
  const format =
    item.rawFormat === undefined
      ? downloadFormatOptions.pdf
      : downloadFormatOptions[item.rawFormat];
  let destination: PreparedFileSave | undefined;
  try {
    destination = await prepareFileSave({
      suggestedName: item.name,
      description: isZip ? "ZIP 压缩包" : format.label,
      mediaType: isZip ? "application/zip" : format.mediaType,
      extensions: [isZip ? ".zip" : format.extension],
    });
  } catch (error: unknown) {
    void message.error(toPublicApiError(error).message);
    return;
  }
  if (destination === undefined) return;

  busyTaskId.value = item.id;
  try {
    const result = await downloadExportBlob(item.downloadUrl);
    await destination.save(result.blob, result.filename);
    void message.success("文件已通过鉴权接口保存。");
  } catch (error: unknown) {
    void message.error(toPublicApiError(error).message);
  } finally {
    busyTaskId.value = undefined;
  }
};

const recreateExport = async (item: DownloadRow): Promise<void> => {
  if (!isRealApiMode) {
    void message.info(`${item.name} 的重新创建仅为本地预览，不会提交导出任务`);
    return;
  }

  if (
    item.rawFormat === undefined ||
    item.documentIds === undefined ||
    item.documentIds.length === 0
  ) {
    void message.warning("当前任务缺少原始文档信息，无法重新创建。");
    return;
  }

  busyTaskId.value = item.id;
  try {
    await createExportTask({
      format: item.rawFormat,
      document_ids: item.documentIds,
    });
    void message.success("已重新创建导出任务。");
    await loadRealDownloads();
  } catch (error: unknown) {
    void message.error(toPublicApiError(error).message);
  } finally {
    busyTaskId.value = undefined;
  }
};

const requestDelete = (downloadId: string): void => {
  modal.confirm({
    title: isRealApiMode
      ? "确认删除这条导出任务？"
      : "确认删除这条本地任务记录？",
    content: isRealApiMode
      ? "会删除服务端导出任务记录和已生成文件。"
      : "不会请求服务端，刷新后固定任务会恢复。",
    okText: "确认删除",
    okType: "danger",
    cancelText: "取消",
    centered: true,
    autoFocusButton: "cancel",
    onOk: async () => {
      if (isRealApiMode) {
        busyTaskId.value = downloadId;
        try {
          await deleteExportTask(downloadId);
          realDownloads.value = realDownloads.value.filter(
            (item) => item.id !== downloadId,
          );
          realTotal.value = Math.max(0, realTotal.value - 1);
          void message.success("导出任务已删除");
        } catch (error: unknown) {
          void message.error(toPublicApiError(error).message);
        } finally {
          busyTaskId.value = undefined;
        }
        return;
      }

      visibleIds.value = visibleIds.value.filter((id) => id !== downloadId);
      void message.success("任务记录已从本地预览中移除");
    },
  });
};

onMounted(() => {
  void loadRealDownloads();
});

onBeforeUnmount(() => {
  loadController?.abort();
});
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="用户工作区"
      title="我的下载"
      :description="
        isRealApiMode
          ? '查看真实导出任务状态，并通过鉴权接口下载或删除文件。'
          : '查看导出任务状态和过期反馈；所有下载操作都保持鉴权接口边界。'
      "
    >
      <template #actions>
        <span class="local-preview-badge">{{
          isRealApiMode ? "真实接口" : "不生成下载地址"
        }}</span>
      </template>
    </PageHeader>

    <ResourcePanel
      title="导出任务"
      :description="
        isRealApiMode
          ? '列表、下载、删除和重新创建均请求后端导出接口。'
          : '任务进度、筛选和删除仅保留到本次刷新。'
      "
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

      <InlineState
        v-if="loadState === 'loading'"
        kind="loading"
        title="正在加载导出任务"
        description="正在从后端读取我的下载列表。"
      />

      <InlineState
        v-else-if="loadState === 'error'"
        kind="error"
        title="导出任务加载失败"
        :description="loadError"
      />

      <div
        v-else-if="filteredDownloads.length > 0"
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
            <tr v-for="item in pagedDownloads" :key="item.id">
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
                    :disabled="busyTaskId === item.id"
                    @click="requestDownload(item)"
                  >
                    <Download :size="15" aria-hidden="true" />
                    下载
                  </button>
                  <button
                    v-else-if="
                      (item.status === '失败' || item.status === '已过期') &&
                        item.sourceType !== 'answer'
                    "
                    class="table-action"
                    type="button"
                    :disabled="busyTaskId === item.id"
                    @click="recreateExport(item)"
                  >
                    <RefreshCw :size="15" aria-hidden="true" />
                    重新创建
                  </button>
                  <span
                    v-else-if="
                      item.status === '失败' || item.status === '已过期'
                    "
                    class="pending-copy"
                  >
                    请重新导出
                  </span>
                  <span v-else class="pending-copy">等待完成</span>
                  <button
                    class="delete-action"
                    type="button"
                    :aria-label="`删除${item.name}任务记录`"
                    :disabled="busyTaskId === item.id"
                    @click="requestDelete(item.id)"
                  >
                    <X :size="15" aria-hidden="true" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <ListPagination
        v-if="filteredDownloads.length > 0"
        :page="downloadsPage"
        :page-size="downloadsPageSize"
        :total="filteredDownloads.length"
        @change="setDownloadsPage"
      />

      <InlineState
        v-else
        kind="empty"
        title="没有匹配的导出任务"
        description="请清除关键词或切换任务状态。"
      />

      <template #footer>
        <span>
          共 {{ filteredDownloads.length }} 条{{
            isRealApiMode ? "真实任务" : "本地任务"
          }}
        </span>
        <span v-if="isRealApiMode">服务端总数 {{ realTotal }} 条</span>
        <span>已加载全部记录</span>
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

.table-actions {
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

@media (max-width: 767px) {
  .table-action,
  .delete-action {
    min-height: 44px;
  }

  .delete-action {
    width: 44px;
  }
}
</style>
