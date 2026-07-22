<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { useListPagination } from "../../composables/useListPagination";
import { isRealApiMode } from "../../config/runtime";
import { useSessionStore } from "../../stores/session";
import {
  createModel,
  deleteModel,
  listModelProviders,
  listModels,
  testModel,
  updateModel,
  upsertModelProvider,
  type ModelItem,
  type ModelProvider,
} from "../../services/admin";

const { message, modal } = AntApp.useApp();
const sessionStore = useSessionStore();
const models = ref<readonly ModelItem[]>([]);
const providers = ref<readonly ModelProvider[]>([]);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedModelId = ref<string>();
const isCreating = ref(false);
const credential = ref("");
const connectionResult = ref("");
const loading = ref(false);
const saving = ref(false);
const initializingProvider = ref(false);
const testingConnection = ref(false);
const deletingModelId = ref<string>();
const hasPermission = (permission: string): boolean =>
  !isRealApiMode || sessionStore.hasAnyPermission([permission]);
const canCreate = computed(() => hasPermission("admin.model.create"));
const canEdit = computed(() => hasPermission("admin.model.edit"));
const canDelete = computed(() => hasPermission("admin.model.delete"));
const canSave = computed(() =>
  isCreating.value ? canCreate.value : canEdit.value,
);
const editor = reactive({
  providerCode: "",
  modelName: "deepseek-chat",
  kind: "chat",
  enabled: true,
  temperature: 0.2,
  maxTokens: 4096,
  dimensions: 1536,
  distance: "cosine",
  topN: 10,
});

const providerPresets = [
  { code: "deepseek", display_name: "DeepSeek", base_url: "https://api.deepseek.com" },
  { code: "dashscope", display_name: "阿里云 DashScope", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1" },
  { code: "moonshot", display_name: "Kimi / Moonshot", base_url: "https://api.moonshot.cn/v1" },
  { code: "zhipu", display_name: "智谱 BigModel", base_url: "https://open.bigmodel.cn/api/paas/v4" },
  { code: "minimax", display_name: "MiniMax", base_url: "https://api.minimax.io/v1" },
  { code: "volcengine", display_name: "火山引擎豆包", base_url: "https://ark.cn-beijing.volces.com/api/v3" },
  { code: "qianfan", display_name: "百度千帆", base_url: "https://qianfan.baidubce.com/v2" },
] as const;

const selectedModel = computed(() =>
  models.value.find((model) => model.id === selectedModelId.value),
);

const filteredModels = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return models.value.filter((model) => {
    const providerName = providerLabel(model.provider_code);
    const matchesQuery =
      keyword.length === 0 ||
      [model.model_name, model.provider_code, providerName, model.kind].some(
        (value) => value.toLowerCase().includes(keyword),
      );
    const status = model.enabled ? "已启用" : "已停用";
    return (
      matchesQuery &&
      (statusFilter.value === "全部状态" || status === statusFilter.value)
    );
  });
});
const {
  page: modelsPage,
  pageSize: modelsPageSize,
  pagedItems: pagedModels,
  setPage: setModelsPage,
} = useListPagination(filteredModels);

const providerLabel = (code: string): string =>
  providers.value.find((provider) => provider.code === code)?.display_name ??
  code;

const kindLabel = (kind: string): string =>
  ({ chat: "问答生成", embedding: "向量化", rerank: "结果重排" })[kind] ?? kind;
const chatModels = computed(() =>
  models.value.filter((model) => model.kind === "chat"),
);
const embeddingModels = computed(() =>
  models.value.filter((model) => model.kind === "embedding"),
);
const enabledChatModels = computed(() =>
  chatModels.value.filter((model) => model.enabled),
);
const enabledEmbeddingModels = computed(() =>
  embeddingModels.value.filter((model) => model.enabled),
);
const defaultChatModel = computed(
  () => enabledChatModels.value[0],
);
const defaultEmbeddingModel = computed(
  () =>
    enabledEmbeddingModels.value.find((model) => model.provider_code === "dashscope") ??
    enabledEmbeddingModels.value[0],
);

const clearSensitiveState = (): void => {
  credential.value = "";
  connectionResult.value = "";
};

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const [providerItems, modelItems] = await Promise.all([
      listModelProviders(),
      listModels(),
    ]);
    providers.value = [...providerItems];
    models.value = [...modelItems];
    editor.providerCode =
      providerItems.find((provider) => provider.enabled)?.code ?? "";
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

const ensureCommonProviders = async (): Promise<void> => {
  if (initializingProvider.value) return;
  const missing = providerPresets.filter(
    (preset) => !providers.value.some((provider) => provider.code === preset.code),
  );
  if (missing.length === 0) {
    message.info("常用模型供应商已经初始化");
    return;
  }
  initializingProvider.value = true;
  try {
    await Promise.all(
      missing.map((preset) =>
        upsertModelProvider({ ...preset, enabled: true }),
      ),
    );
    message.success(`已初始化 ${missing.length} 个常用供应商`);
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    initializingProvider.value = false;
  }
};

const startChatCreate = (): void => {
  if (!startCreate()) return;
  Object.assign(editor, {
    providerCode: providers.value.find((item) => item.enabled)?.code ?? "",
    modelName: "",
    kind: "chat",
    temperature: 0.2,
    maxTokens: 1200,
    enabled: true,
  });
};

const startEmbeddingCreate = (): void => {
  if (!startCreate()) return;
  Object.assign(editor, {
    providerCode: providers.value.some(
      (item) => item.code === "dashscope" && item.enabled,
    )
      ? "dashscope"
      : providers.value.find((provider) => provider.enabled)?.code ?? "",
    modelName: "text-embedding-v2",
    kind: "embedding",
    dimensions: 1536,
    distance: "cosine",
    enabled: true,
  });
};

const startCreate = (): boolean => {
  if (providers.value.length === 0) {
    message.warning("暂无可用供应商，请刷新页面或先初始化供应商");
    return false;
  }
  if (!providers.value.some((provider) => provider.enabled)) {
    message.warning("模型供应商均已停用，请先启用供应商");
    return false;
  }
  selectedModelId.value = undefined;
  isCreating.value = true;
  clearSensitiveState();
  Object.assign(editor, {
    providerCode:
      providers.value.find((provider) => provider.enabled)?.code ?? "",
    modelName: "deepseek-chat",
    kind: "chat",
    enabled: true,
    temperature: 0.2,
    maxTokens: 4096,
  });
  return true;
};

const startEdit = (id: string): void => {
  const model = models.value.find((item) => item.id === id);
  if (model === undefined) return;

  selectedModelId.value = id;
  isCreating.value = false;
  clearSensitiveState();
  Object.assign(editor, {
    providerCode: model.provider_code,
    modelName: model.model_name,
    kind: model.kind,
    enabled: model.enabled,
    temperature:
      typeof model.parameters.temperature === "number"
        ? model.parameters.temperature
        : 0.2,
    maxTokens:
      typeof model.parameters.max_tokens === "number"
        ? model.parameters.max_tokens
        : 4096,
    dimensions: model.dimensions ?? 1536,
    distance: model.distance ?? "cosine",
    topN: model.top_n ?? 10,
  });
};

const closeEditor = (): void => {
  selectedModelId.value = undefined;
  isCreating.value = false;
  clearSensitiveState();
};

const testConnection = async (): Promise<void> => {
  if (selectedModel.value === undefined) {
    connectionResult.value = "请先保存配置；保存不会检查模型是否开通。";
    return;
  }
  if (testingConnection.value) return;
  testingConnection.value = true;
  try {
    const result = await testModel(selectedModel.value.id);
    if (!result.ok) {
      connectionResult.value = result.error_message ?? "模型连通性测试失败。";
      message.error(connectionResult.value);
      return;
    }
    connectionResult.value = `供应商认证与连通性测试成功，耗时 ${result.latency_ms}ms。`;
    message.success("供应商认证与连通性测试成功");
  } catch (err) {
    connectionResult.value = toPublicApiError(err).message;
    message.error(connectionResult.value);
  } finally {
    testingConnection.value = false;
  }
};

const saveModel = async (): Promise<void> => {
  if (saving.value) return;
  if (providers.value.length === 0) {
    message.warning("暂无可用供应商，请刷新页面后重试");
    return;
  }
  if (editor.providerCode === "" || editor.modelName.trim() === "") {
    message.warning("请选择供应商并填写模型标识");
    return;
  }

  saving.value = true;
  try {
    const parameters =
      editor.kind === "chat"
        ? {
            ...(selectedModel.value?.parameters ?? {}),
            temperature: editor.temperature,
            max_tokens: editor.maxTokens,
          }
        : { ...(selectedModel.value?.parameters ?? {}) };
    const payload = {
      model_name: editor.modelName.trim(),
      parameters,
      enabled: editor.enabled,
      api_key: credential.value === "" ? undefined : credential.value,
      dimensions: editor.kind === "embedding" ? editor.dimensions : undefined,
      distance: editor.kind === "embedding" ? editor.distance : undefined,
      top_n: editor.kind === "rerank" ? editor.topN : undefined,
    };
    if (isCreating.value) {
      await createModel({
        provider_code: editor.providerCode,
        model_name: payload.model_name,
        kind: editor.kind,
        parameters: payload.parameters,
        enabled: payload.enabled,
        api_key: payload.api_key,
        dimensions: payload.dimensions,
        distance: payload.distance,
        top_n: payload.top_n,
      });
      message.success("模型已创建");
    } else if (selectedModel.value !== undefined) {
      await updateModel(selectedModel.value.id, payload);
      message.success("模型配置已保存");
    }
    closeEditor();
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    saving.value = false;
  }
};

const confirmDelete = (model: ModelItem): void => {
  if (deletingModelId.value !== undefined) return;
  modal.confirm({
    title: "删除模型配置",
    content: `确认删除 ${model.model_name}？不会展示或返回任何密钥。`,
    okText: "确认删除",
    cancelText: "取消",
    onOk: async () => {
      deletingModelId.value = model.id;
      try {
        await deleteModel(model.id);
        message.success("模型配置已删除");
        await loadData();
      } catch (err) {
        message.error(toPublicApiError(err).message);
      } finally {
        deletingModelId.value = undefined;
      }
    },
  });
};

onMounted(loadData);
onBeforeUnmount(clearSensitiveState);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="AI 配置"
      title="模型管理"
      description="维护真实模型配置；密钥只允许写入，不在页面回显。"
    >
      <template #actions>
        <button
          v-if="canCreate"
          class="secondary-button"
          type="button"
          :disabled="initializingProvider"
          @click="ensureCommonProviders"
        >
          {{ initializingProvider ? "初始化中" : "初始化常用供应商" }}
        </button>
        <button
          v-if="canCreate"
          class="secondary-button"
          type="button"
          :disabled="loading || providers.length === 0"
          @click="startChatCreate"
        >
          新增聊天模型
        </button>
        <button class="secondary-button" type="button" :disabled="loading" @click="loadData">
          {{ loading ? "刷新中" : "刷新" }}
        </button>
        <button
          v-if="canCreate"
          class="admin-primary-button"
          type="button"
          :disabled="loading || providers.length === 0"
          @click="startCreate"
        >
          新增模型
        </button>
      </template>
    </PageHeader>

    <section class="model-overview-grid" aria-label="RAG 模型配置概览">
      <article class="model-overview-card">
        <span>RAG 回答模型</span>
        <h2>{{ defaultChatModel?.model_name ?? "未配置" }}</h2>
        <p>
          {{
            defaultChatModel === undefined
              ? "请新增任一启用的聊天模型；未选择时后端才使用环境变量兜底。"
              : `${providerLabel(defaultChatModel.provider_code)} · ${
                defaultChatModel.api_key_set ? "密钥已配置" : "密钥未配置"
              }`
          }}
        </p>
      </article>
      <article class="model-overview-card">
        <span>向量检索模型</span>
        <h2>{{ defaultEmbeddingModel?.model_name ?? "未配置" }}</h2>
        <p>
          {{
            defaultEmbeddingModel === undefined
              ? "请新增 1536 维 embedding 模型；否则向量检索会退回关键词。"
              : `${providerLabel(defaultEmbeddingModel.provider_code)} · ${
                defaultEmbeddingModel.dimensions ?? "-"
              } 维`
          }}
        </p>
      </article>
      <article class="model-overview-card">
        <span>模型总览</span>
        <h2>{{ models.length }} 个配置</h2>
        <p>
          {{ enabledChatModels.length }} 个启用聊天模型，{{
            enabledEmbeddingModels.length
          }}
          个启用向量模型。
        </p>
      </article>
    </section>

    <ResourcePanel
      title="模型配置"
      description="RAG 检索回答会使用启用的聊天模型；向量检索会使用启用的 embedding 模型。密钥值永不展示。"
    >
      <template #actions>
        <button
          v-if="canCreate"
          class="secondary-button compact"
          type="button"
          :disabled="loading || providers.length === 0"
          @click="startEmbeddingCreate"
        >
          新增向量模型
        </button>
      </template>
      <div class="filter-bar" aria-label="模型筛选">
        <label>
          <span>搜索模型</span>
          <input
            v-model="query"
            type="search"
            placeholder="供应商、模型或用途"
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
        v-if="loading"
        kind="loading"
        title="正在加载模型"
        description="请稍候。"
      />
      <InlineState
        v-else-if="providers.length === 0"
        kind="empty"
        title="没有可用的模型供应商"
        description="请刷新页面；拥有创建权限的管理员也可以先初始化 DeepSeek 供应商。"
      />
      <InlineState
        v-else-if="filteredModels.length === 0"
        kind="empty"
        title="没有模型配置"
        description="供应商已就绪，可以新增聊天或向量模型配置。"
      />
      <div v-else class="data-table-scroll" tabindex="0">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">供应商 / 模型</th>
              <th scope="col">用途</th>
              <th scope="col">状态</th>
              <th scope="col">凭据</th>
              <th scope="col">参数</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in pagedModels" :key="model.id">
              <td>
                <strong>{{ providerLabel(model.provider_code) }}</strong>
                <small>{{ model.model_name }}</small>
              </td>
              <td>{{ kindLabel(model.kind) }}</td>
              <td>
                <span
                  class="status-chip"
                  :class="model.enabled ? 'success' : 'neutral'"
                >
                  {{ model.enabled ? "已启用" : "已停用" }}
                </span>
              </td>
              <td>{{ model.api_key_set ? "已配置" : "未配置" }}</td>
              <td>
                <span v-if="model.kind === 'embedding'">
                  {{ model.dimensions ?? "-" }} 维 · {{ model.distance ?? "-" }}
                </span>
                <span v-else-if="model.kind === 'rerank'">
                  top_n={{ model.top_n ?? "-" }}
                </span>
                <span v-else>{{ JSON.stringify(model.parameters) }}</span>
              </td>
              <td>
                <div class="table-actions">
                  <button
                    v-if="canEdit"
                    class="text-button"
                    type="button"
                    @click="startEdit(model.id)"
                  >
                    配置
                  </button>
                  <button
                    v-if="canDelete"
                    class="text-button"
                    type="button"
                    :disabled="deletingModelId !== undefined"
                    @click="confirmDelete(model)"
                  >
                    {{ deletingModelId === model.id ? "删除中" : "删除" }}
                  </button>
                  <span v-if="!canEdit && !canDelete">仅查看</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <ListPagination
        v-if="filteredModels.length > 0"
        :page="modelsPage"
        :page-size="modelsPageSize"
        :total="filteredModels.length"
        @change="setModelsPage"
      />
    </ResourcePanel>

    <Drawer
      :open="isCreating || selectedModel !== undefined"
      :title="isCreating ? '新增模型' : '模型配置'"
      width="460"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form" @submit.prevent="saveModel">
        <label>
          <span>供应商</span>
          <select v-model="editor.providerCode" :disabled="!isCreating">
            <option
              v-for="provider in providers"
              :key="provider.code"
              :value="provider.code"
              :disabled="!provider.enabled"
            >
              {{ provider.display_name }}
            </option>
          </select>
        </label>
        <label>
          <span>模型标识</span>
          <input
            id="model-name-input"
            v-model="editor.modelName"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <label>
          <span>用途</span>
          <select v-model="editor.kind" :disabled="!isCreating">
            <option value="chat">问答生成</option>
            <option value="embedding">向量化</option>
            <option value="rerank">结果重排</option>
          </select>
        </label>
        <div class="parameter-grid">
          <label v-if="editor.kind === 'chat'">
            <span>温度</span>
            <input
              v-model.number="editor.temperature"
              type="number"
              min="0"
              max="2"
              step="0.1"
            />
          </label>
          <label v-if="editor.kind === 'chat'">
            <span>最大输出</span>
            <input
              v-model.number="editor.maxTokens"
              type="number"
              min="1"
              max="32768"
              step="1"
            />
          </label>
          <label v-if="editor.kind === 'embedding'">
            <span>向量维度</span>
            <input
              v-model.number="editor.dimensions"
              type="number"
              min="1"
              max="4096"
              step="1"
            />
          </label>
          <label v-if="editor.kind === 'embedding'">
            <span>距离算法</span>
            <select v-model="editor.distance">
              <option value="cosine">cosine</option>
              <option value="l2">l2</option>
              <option value="inner_product">inner_product</option>
            </select>
          </label>
          <label v-if="editor.kind === 'rerank'">
            <span>Top N</span>
            <input
              v-model.number="editor.topN"
              type="number"
              min="1"
              max="1000"
              step="1"
            />
          </label>
        </div>
        <label>
          <span>状态</span>
          <select v-model="editor.enabled">
            <option :value="true">已启用</option>
            <option :value="false">已停用</option>
          </select>
        </label>
        <label>
          <span>密钥（仅写入）</span>
          <input
            v-model="credential"
            type="password"
            autocomplete="new-password"
            placeholder="留空则不修改已有密钥"
          />
        </label>
        <button
          v-if="canEdit"
          class="secondary-button"
          type="button"
          :disabled="testingConnection"
          @click="testConnection"
        >
          {{ testingConnection ? "测试中" : "测试供应商认证与连通性" }}
        </button>
        <p v-if="connectionResult" class="preview-note" role="status">
          {{ connectionResult }}
        </p>
        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="closeEditor">
            取消并清空密钥
          </button>
          <button
            v-if="canSave"
            class="admin-primary-button"
            type="submit"
            :disabled="saving || providers.length === 0"
          >
            {{ saving ? "保存中" : "保存配置" }}
          </button>
        </div>
      </form>
    </Drawer>
  </div>
</template>

<style scoped>
.model-overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.model-overview-card {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.model-overview-card span {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.model-overview-card h2 {
  margin: 0;
  font-size: var(--font-size-22);
}

.model-overview-card p {
  margin: 0;
  color: var(--color-text-secondary);
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

@media (max-width: 767px) {
  .model-overview-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .parameter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
