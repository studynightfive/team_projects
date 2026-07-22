<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, reactive, ref } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { useListPagination } from "../../composables/useListPagination";
import {
  createKnowledgeBase,
  listKnowledgeBases,
  uploadDocuments,
  updateKnowledgeBase,
  type ChunkStrategy,
  type KnowledgeBaseRecord,
} from "../../services/knowledge";
import {
  listDepartments,
  type DepartmentRecord,
} from "../../services/admin";
import { useSessionStore } from "../../stores/session";

const { message, modal } = AntApp.useApp();
const sessionStore = useSessionStore();
const knowledgeBases = ref<readonly KnowledgeBaseRecord[]>([]);
const departments = ref<readonly DepartmentRecord[]>([]);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedId = ref<string>();
const isCreating = ref(false);
const loading = ref(false);
const saving = ref(false);
const uploadKnowledgeBase = ref<KnowledgeBaseRecord>();
const uploadInputRef = ref<HTMLInputElement>();
const uploading = ref(false);
const uploadStrategy = ref<ChunkStrategy>("recursive");
const uploadChunkSize = ref(800);
const uploadChunkOverlap = ref(120);
const editor = reactive({
  name: "",
  description: "",
  departmentId: "",
});

const canManageDepartments = computed(() =>
  sessionStore.hasAnyPermission(["admin.department.view"]),
);

const selectedKnowledgeBase = computed(() =>
  knowledgeBases.value.find((item) => item.id === selectedId.value),
);

const filteredKnowledgeBases = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return knowledgeBases.value.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [item.name, item.description ?? ""].some((value) =>
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
  page: knowledgeBasesPage,
  pageSize: knowledgeBasesPageSize,
  pagedItems: pagedKnowledgeBases,
  setPage: setKnowledgeBasesPage,
} = useListPagination(filteredKnowledgeBases);

const statusLabel = (status: string): string =>
  status === "active" ? "正常" : "已归档";

const statusTone = (status: string): string =>
  status === "active" ? "success" : "warning";

const formatDate = (value: string | null): string =>
  value === null ? "-" : new Date(value).toLocaleString("zh-CN");

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const [knowledgeBaseItems, departmentItems] = await Promise.all([
      listKnowledgeBases(),
      canManageDepartments.value ? listDepartments() : Promise.resolve([]),
    ]);
    knowledgeBases.value = knowledgeBaseItems.filter(
      (item) => item.kind !== "personal",
    );
    departments.value = departmentItems;
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

const startCreate = (): void => {
  selectedId.value = undefined;
  isCreating.value = true;
  Object.assign(editor, {
    name: "",
    description: "",
    departmentId:
      sessionStore.currentUser?.department?.id ?? departments.value[0]?.id ?? "",
  });
};

const startEdit = (id: string): void => {
  const item = knowledgeBases.value.find((kb) => kb.id === id);
  if (item === undefined) return;
  selectedId.value = id;
  isCreating.value = false;
  Object.assign(editor, {
    name: item.name,
    description: item.description ?? "",
    departmentId: item.department_id,
  });
};

const closeEditor = (): void => {
  selectedId.value = undefined;
  isCreating.value = false;
};

const saveKnowledgeBase = async (): Promise<void> => {
  if (editor.name.trim() === "") {
    message.warning("请填写知识库名称");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: editor.name.trim(),
      description: editor.description.trim(),
      department_id: editor.departmentId || undefined,
    };
    if (isCreating.value) {
      await createKnowledgeBase(payload);
      message.success("知识库已创建");
    } else if (selectedKnowledgeBase.value !== undefined) {
      await updateKnowledgeBase(selectedKnowledgeBase.value.id, payload);
      message.success("知识库配置已保存");
    }
    closeEditor();
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    saving.value = false;
  }
};

const startUpload = (item: KnowledgeBaseRecord): void => {
  uploadKnowledgeBase.value = item;
  uploadStrategy.value = "recursive";
  uploadChunkSize.value = 800;
  uploadChunkOverlap.value = 120;
};

const uploadFiles = async (files: readonly File[]): Promise<void> => {
  if (uploadKnowledgeBase.value === undefined || files.length === 0) return;
  if (uploadChunkOverlap.value >= uploadChunkSize.value) {
    message.warning("重叠字符必须小于切分大小");
    return;
  }
  uploading.value = true;
  try {
    await uploadDocuments(uploadKnowledgeBase.value.id, files, {
      chunkStrategy: uploadStrategy.value,
      chunkSize: uploadChunkSize.value,
      chunkOverlap: uploadChunkOverlap.value,
    });
    message.success(`已提交 ${files.length} 个文档处理任务`);
    uploadKnowledgeBase.value = undefined;
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    uploading.value = false;
  }
};

const handleUpload = async (event: Event): Promise<void> => {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  input.value = "";
  await uploadFiles(files);
};

const confirmArchive = (item: KnowledgeBaseRecord): void => {
  const nextStatus = item.status === "active" ? "archived" : "active";
  modal.confirm({
    title: nextStatus === "archived" ? "归档知识库" : "恢复知识库",
    content: `确认${nextStatus === "archived" ? "归档" : "恢复"} ${item.name}？`,
    okText: "确认",
    cancelText: "取消",
    onOk: async () => {
      await updateKnowledgeBase(item.id, { status: nextStatus });
      message.success("知识库状态已更新");
      await loadData();
    },
  });
};

onMounted(loadData);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="内容治理"
      title="知识库管理"
      description="管理企业知识库、文档规模和索引状态。切分方法在上传文档时选择。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
        <button class="admin-primary-button" type="button" @click="startCreate">
          新建知识库
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="知识库清单"
      :description="
        '当前显示 ' + String(filteredKnowledgeBases.length) + ' 个知识库'
      "
    >
      <div class="filter-bar" aria-label="知识库筛选">
        <label>
          <span>搜索知识库</span>
          <input v-model="query" type="search" placeholder="名称或说明" />
        </label>
        <label>
          <span>状态</span>
          <select v-model="statusFilter">
            <option>全部状态</option>
            <option>正常</option>
            <option>已归档</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="loading"
        kind="loading"
        title="正在加载知识库"
        description="请稍候。"
      />
      <InlineState
        v-else-if="filteredKnowledgeBases.length === 0"
        kind="empty"
        title="没有匹配的知识库"
        description="请调整关键词或状态。"
      />
      <div v-else class="data-table-scroll" tabindex="0">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">知识库</th>
              <th scope="col">文档</th>
              <th scope="col">所属部门</th>
              <th scope="col">可检索文档</th>
              <th scope="col">片段</th>
              <th scope="col">状态</th>
              <th scope="col">更新时间</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pagedKnowledgeBases" :key="item.id">
              <td>
                <strong>{{ item.name }}</strong>
                <small>{{ item.description || "暂无说明" }}</small>
              </td>
              <td>{{ item.document_count }}</td>
              <td>{{ item.department_name }}</td>
              <td>{{ item.ready_document_count }}</td>
              <td>{{ item.chunk_count }}</td>
              <td>
                <span class="status-chip" :class="statusTone(item.status)">
                  {{ statusLabel(item.status) }}
                </span>
              </td>
              <td>{{ formatDate(item.updated_at) }}</td>
              <td>
                <div class="table-actions">
                  <button
                    class="text-button"
                    type="button"
                    @click="startUpload(item)"
                  >
                    上传文档
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="startEdit(item.id)"
                  >
                    编辑
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmArchive(item)"
                  >
                    {{ item.status === "active" ? "归档" : "恢复" }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <ListPagination
        v-if="filteredKnowledgeBases.length > 0"
        :page="knowledgeBasesPage"
        :page-size="knowledgeBasesPageSize"
        :total="filteredKnowledgeBases.length"
        @change="setKnowledgeBasesPage"
      />
    </ResourcePanel>

    <Drawer
      :open="isCreating || selectedKnowledgeBase !== undefined"
      :title="isCreating ? '新建知识库' : '编辑知识库'"
      width="460"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form" @submit.prevent="saveKnowledgeBase">
        <label>
          <span>知识库名称</span>
          <input
            v-model="editor.name"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <label>
          <span>说明</span>
          <textarea v-model="editor.description" rows="3" />
        </label>
        <label v-if="canManageDepartments">
          <span>所属部门</span>
          <select v-model="editor.departmentId" required>
            <option value="" disabled>请选择部门</option>
            <option v-for="item in departments" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </label>
        <p v-else class="preview-note">
          所属部门：{{ sessionStore.currentUser?.department?.name ?? "待分配" }}
        </p>
        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="closeEditor">
            取消
          </button>
          <button class="admin-primary-button" type="submit" :disabled="saving">
            {{ saving ? "保存中" : "保存" }}
          </button>
        </div>
      </form>
    </Drawer>

    <Drawer
      :open="uploadKnowledgeBase !== undefined"
      title="上传并处理文档"
      width="500"
      root-class-name="variant-admin"
      @close="uploadKnowledgeBase = undefined"
    >
      <div class="drawer-form">
        <p class="preview-note">目标知识库：{{ uploadKnowledgeBase?.name }}</p>
        <label>
          <span>切分方法</span>
          <select v-model="uploadStrategy">
            <option value="fixed">固定长度</option>
            <option value="semantic">语义</option>
            <option value="recursive">递归</option>
            <option value="format">格式</option>
          </select>
        </label>
        <div class="parameter-grid">
          <label>
            <span>切分大小</span>
            <input v-model.number="uploadChunkSize" type="number" min="100" max="4000" />
          </label>
          <label>
            <span>重叠字符</span>
            <input v-model.number="uploadChunkOverlap" type="number" min="0" max="1000" />
          </label>
        </div>
        <button
          class="upload-drop-zone"
          type="button"
          :disabled="uploading"
          @click="uploadInputRef?.click()"
          @dragover.prevent
          @drop.prevent="uploadFiles(Array.from($event.dataTransfer?.files ?? []))"
        >
          <strong>{{ uploading ? "正在上传并处理" : "点击或拖拽文件到这里上传" }}</strong>
          <span>文件会先转为 Markdown、清洗，再按所选方法切分和向量化</span>
        </button>
        <input
          ref="uploadInputRef"
          class="visually-hidden"
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.md,.markdown,.txt,.csv,.xlsx,.pptx,.html,.json"
          @change="handleUpload"
        />
      </div>
    </Drawer>
  </div>
</template>

<style scoped>
.parameter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.upload-drop-zone {
  display: grid;
  min-height: 150px;
  place-items: center;
  align-content: center;
  gap: var(--space-2);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  cursor: pointer;
}

@media (max-width: 767px) {
  .parameter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
