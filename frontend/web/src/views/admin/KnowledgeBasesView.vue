<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, reactive, ref } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  createKnowledgeBase,
  listKnowledgeBases,
  updateKnowledgeBase,
  type KnowledgeBaseRecord,
} from "../../services/knowledge";

const { message, modal } = AntApp.useApp();
const knowledgeBases = ref<readonly KnowledgeBaseRecord[]>([]);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedId = ref<string>();
const isCreating = ref(false);
const loading = ref(false);
const saving = ref(false);
const editor = reactive({
  name: "",
  description: "",
  chunkSize: 800,
  chunkOverlap: 120,
});

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

const statusLabel = (status: string): string =>
  status === "active" ? "正常" : "已归档";

const statusTone = (status: string): string =>
  status === "active" ? "success" : "warning";

const formatDate = (value: string | null): string =>
  value === null ? "-" : new Date(value).toLocaleString("zh-CN");

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    knowledgeBases.value = await listKnowledgeBases();
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
    chunkSize: 800,
    chunkOverlap: 120,
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
    chunkSize: item.chunk_size,
    chunkOverlap: item.chunk_overlap,
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
  if (
    editor.chunkSize < 200 ||
    editor.chunkSize > 4000 ||
    editor.chunkOverlap < 0 ||
    editor.chunkOverlap > 1000
  ) {
    message.warning("请输入有效的切分参数");
    return;
  }

  saving.value = true;
  try {
    const payload = {
      name: editor.name.trim(),
      description: editor.description.trim(),
      chunk_size: editor.chunkSize,
      chunk_overlap: editor.chunkOverlap,
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
      description="管理真实知识库、切分参数、文档规模和索引状态。"
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
              <th scope="col">可检索文档</th>
              <th scope="col">片段</th>
              <th scope="col">切分参数</th>
              <th scope="col">状态</th>
              <th scope="col">更新时间</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredKnowledgeBases" :key="item.id">
              <td>
                <strong>{{ item.name }}</strong>
                <small>{{ item.description || "暂无说明" }}</small>
              </td>
              <td>{{ item.document_count }}</td>
              <td>{{ item.ready_document_count }}</td>
              <td>{{ item.chunk_count }}</td>
              <td>{{ item.chunk_size }} / {{ item.chunk_overlap }}</td>
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
        <div class="parameter-grid">
          <label>
            <span>切分大小</span>
            <input
              v-model.number="editor.chunkSize"
              type="number"
              min="200"
              max="4000"
              step="50"
            />
          </label>
          <label>
            <span>重叠字符</span>
            <input
              v-model.number="editor.chunkOverlap"
              type="number"
              min="0"
              max="1000"
              step="10"
            />
          </label>
        </div>
        <p class="preview-note">
          系统优先按 Markdown 标题、段落、表格和代码块切分；切分大小和重叠字符只用于超长段落兜底拆分。
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
  </div>
</template>

<style scoped>
.parameter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

@media (max-width: 767px) {
  .parameter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
