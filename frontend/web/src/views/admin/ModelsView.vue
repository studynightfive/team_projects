<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onBeforeUnmount, reactive, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { localPageData } from "../../data/local-pages";

type ModelItem = (typeof localPageData.models)[number];

const { message, modal } = AntApp.useApp();
const models = ref<ModelItem[]>(
  localPageData.models.map((model) => ({ ...model })),
);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedModelId = ref<string>();
const isCreating = ref(false);
const credential = ref("");
const connectionResult = ref("");
const editor = reactive({
  name: "",
  provider: "",
  model: "",
  purpose: "问答生成",
  status: "已停用",
  temperature: 0.2,
  maxTokens: 4096,
});

const selectedModel = computed(() =>
  models.value.find((model) => model.id === selectedModelId.value),
);

const filteredModels = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return models.value.filter((model) => {
    const matchesQuery =
      keyword.length === 0 ||
      [model.name, model.provider, model.model, model.purpose].some((value) =>
        value.toLowerCase().includes(keyword),
      );
    const matchesStatus =
      statusFilter.value === "全部状态" || model.status === statusFilter.value;
    return matchesQuery && matchesStatus;
  });
});

const statusTone = (status: string): string =>
  status === "已启用" ? "success" : "neutral";

const clearSensitiveState = (): void => {
  credential.value = "";
  connectionResult.value = "";
};

const startCreate = (): void => {
  selectedModelId.value = undefined;
  isCreating.value = true;
  clearSensitiveState();
  Object.assign(editor, {
    name: "",
    provider: "",
    model: "",
    purpose: "问答生成",
    status: "已停用",
    temperature: 0.2,
    maxTokens: 4096,
  });
};

const startEdit = (id: string): void => {
  const model = models.value.find((item) => item.id === id);
  if (model === undefined) return;

  selectedModelId.value = id;
  isCreating.value = false;
  clearSensitiveState();
  Object.assign(editor, {
    name: model.name,
    provider: model.provider,
    model: model.model,
    purpose: model.purpose,
    status: model.status,
    temperature: 0.2,
    maxTokens: 4096,
  });
};

const closeEditor = (): void => {
  selectedModelId.value = undefined;
  isCreating.value = false;
  clearSensitiveState();
};

const testConnectionPreview = (): void => {
  connectionResult.value =
    "仅完成界面反馈预览；未读取密钥，也未发送连通性请求。";
  void message.info("连通性测试未访问网络");
};

const savePreview = (): void => {
  if (
    editor.name.trim().length === 0 ||
    editor.provider.trim().length === 0 ||
    editor.model.trim().length === 0
  ) {
    void message.warning("请填写名称、供应商和模型标识");
    return;
  }

  if (isCreating.value) {
    models.value.push({
      id: "model-local-preview-" + String(models.value.length + 1),
      name: editor.name.trim(),
      provider: editor.provider.trim(),
      model: editor.model.trim(),
      purpose: editor.purpose,
      status: editor.status,
      credential: "未配置",
      latency: "未测试",
    });
  } else {
    const model = selectedModel.value;
    if (model !== undefined) {
      Object.assign(model, {
        name: editor.name.trim(),
        provider: editor.provider.trim(),
        model: editor.model.trim(),
        purpose: editor.purpose,
        status: editor.status,
      });
    }
  }

  clearSensitiveState();
  void message.success("模型配置已更新为本地预览状态，密钥输入已清空");
  closeEditor();
};

const confirmDelete = (id: string): void => {
  const model = models.value.find((item) => item.id === id);
  if (model === undefined) return;

  modal.confirm({
    title: "删除模型配置预览",
    content: "仅从当前页面预览中移除，不会影响任何服务或凭据。",
    okText: "确认本地预览",
    cancelText: "取消",
    onOk: () => {
      models.value = models.value.filter((item) => item.id !== id);
      void message.success(model.name + " 已从本地预览中移除");
    },
  });
};

onBeforeUnmount(clearSensitiveState);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="AI 配置"
      title="模型管理"
      description="预览供应商、模型用途、参数、状态与安全的密钥占位流程。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
        <button class="admin-primary-button" type="button" @click="startCreate">
          新增模型
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="模型配置"
      description="密钥值永不展示；输入框默认空白并在关闭或保存时立即清空。"
    >
      <div class="filter-bar" aria-label="模型筛选">
        <label>
          <span>搜索模型</span>
          <input
            v-model="query"
            type="search"
            placeholder="名称、供应商、模型或用途"
          />
        </label>
        <label>
          <span>启用状态</span>
          <select v-model="statusFilter">
            <option>全部状态</option>
            <option>已启用</option>
            <option>已停用</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="filteredModels.length === 0"
        kind="empty"
        title="没有匹配的模型"
        description="请调整搜索关键词或状态。"
      />
      <div
        v-else
        class="data-table-scroll"
        tabindex="0"
        aria-label="模型配置表格，可横向滚动"
      >
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">配置名称</th>
              <th scope="col">供应商 / 模型</th>
              <th scope="col">用途</th>
              <th scope="col">状态</th>
              <th scope="col">凭据</th>
              <th scope="col">最近延迟</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in filteredModels" :key="model.id">
              <td>
                <strong>{{ model.name }}</strong>
              </td>
              <td>
                {{ model.provider }}
                <small>{{ model.model }}</small>
              </td>
              <td>{{ model.purpose }}</td>
              <td>
                <span class="status-chip" :class="statusTone(model.status)">
                  {{ model.status }}
                </span>
              </td>
              <td>{{ model.credential }}</td>
              <td>{{ model.latency }}</td>
              <td>
                <div class="table-actions">
                  <button
                    class="text-button"
                    type="button"
                    @click="startEdit(model.id)"
                  >
                    配置
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmDelete(model.id)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </ResourcePanel>

    <Drawer
      :open="isCreating || selectedModel !== undefined"
      :title="isCreating ? '新增模型（本地预览）' : '模型配置（本地预览）'"
      width="460"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form" @submit.prevent="savePreview">
        <label>
          <span>配置名称</span>
          <input
            v-model="editor.name"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <label>
          <span>供应商</span>
          <input
            v-model="editor.provider"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <label>
          <span>模型标识</span>
          <input
            v-model="editor.model"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <label>
          <span>用途</span>
          <select v-model="editor.purpose">
            <option>问答生成</option>
            <option>向量化</option>
            <option>结果重排</option>
          </select>
        </label>
        <div class="parameter-grid">
          <label>
            <span>温度</span>
            <input
              v-model.number="editor.temperature"
              type="number"
              min="0"
              max="2"
              step="0.1"
            />
          </label>
          <label>
            <span>最大输出</span>
            <input
              v-model.number="editor.maxTokens"
              type="number"
              min="1"
              max="32768"
              step="1"
            />
          </label>
        </div>
        <label>
          <span>状态</span>
          <select v-model="editor.status">
            <option>已启用</option>
            <option>已停用</option>
          </select>
        </label>
        <label>
          <span>密钥（仅本次界面输入）</span>
          <input
            v-model="credential"
            type="password"
            autocomplete="new-password"
            placeholder="默认留空，不读取已有密钥"
          />
        </label>
        <button
          class="secondary-button"
          type="button"
          @click="testConnectionPreview"
        >
          测试连通性（本地预览）
        </button>
        <p v-if="connectionResult" class="preview-note" role="status">
          {{ connectionResult }}
        </p>
        <p class="preview-note">
          参数名称仅用于布局预览；无 OpenAPI 时不代表真实模型配置字段。
        </p>
        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="closeEditor">
            取消并清空密钥
          </button>
          <button class="admin-primary-button" type="submit">
            保存本地预览
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
