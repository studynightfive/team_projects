<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
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
const editor = reactive({
  providerCode: "deepseek",
  modelName: "deepseek-v4-pro",
  kind: "chat",
  enabled: true,
  temperature: 0.2,
  maxTokens: 4096,
  dimensions: 1024,
  distance: "cosine",
  topN: 10,
});

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
  () =>
    enabledChatModels.value.find((model) => model.provider_code === "deepseek") ??
    enabledChatModels.value[0],
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
    providers.value = providerItems;
    models.value = modelItems;
    editor.providerCode = providerItems[0]?.code ?? "deepseek";
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

const ensureDeepSeekProvider = async (): Promise<void> => {
  try {
    await upsertModelProvider({
      code: "deepseek",
      display_name: "DeepSeek",
      base_url: "https://api.deepseek.com",
      enabled: true,
    });
    message.success("DeepSeek 供应商已初始化");
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  }
};

const startDeepSeekCreate = (): void => {
  startCreate();
  Object.assign(editor, {
    providerCode: "deepseek",
    modelName: "deepseek-v4-pro",
    kind: "chat",
    temperature: 0.2,
    maxTokens: 1200,
    enabled: true,
  });
};

const startEmbeddingCreate = (): void => {
  startCreate();
  Object.assign(editor, {
    providerCode: providers.value.some((item) => item.code === "dashscope")
      ? "dashscope"
      : providers.value[0]?.code ?? "deepseek",
    modelName: "qwen3.7-text-embedding",
    kind: "embedding",
    dimensions: 1024,
    distance: "cosine",
    enabled: true,
  });
};

const startCreate = (): void => {
  selectedModelId.value = undefined;
  isCreating.value = true;
  clearSensitiveState();
  Object.assign(editor, {
    providerCode: providers.value[0]?.code ?? "deepseek",
    modelName: "deepseek-v4-pro",
    kind: "chat",
    enabled: true,
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
    dimensions: model.dimensions ?? 1024,
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
    connectionResult.value = "请先保存模型后再测试连通性。";
    return;
  }
  try {
    await testModel(selectedModel.value.id);
    connectionResult.value = "连通性测试成功。";
    message.success("连通性测试成功");
  } catch (err) {
    connectionResult.value = toPublicApiError(err).message;
  }
};

const saveModel = async (): Promise<void> => {
  if (editor.providerCode === "" || editor.modelName.trim() === "") {
    message.warning("请选择供应商并填写模型标识");
    return;
  }

  saving.value = true;
  try {
    const payload = {
      model_name: editor.modelName.trim(),
      parameters: {
        temperature: editor.temperature,
        max_tokens: editor.maxTokens,
      },
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
  modal.confirm({
    title: "删除模型配置",
    content: `确认删除 ${model.model_name}？不会展示或返回任何密钥。`,
    okText: "确认删除",
    cancelText: "取消",
    onOk: async () => {
      await deleteModel(model.id);
      message.success("模型配置已删除");
      await loadData();
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
          class="secondary-button"
          type="button"
          @click="ensureDeepSeekProvider"
        >
          初始化 DeepSeek
        </button>
        <button class="secondary-button" type="button" @click="startDeepSeekCreate">
          新增 DeepSeek 模型
        </button>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
        <button class="admin-primary-button" type="button" @click="startCreate">
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
              ? "请新增 DeepSeek 聊天模型；未配置时后端会尝试使用环境变量兜底。"
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
              ? "请新增 Qwen embedding 模型；否则向量检索会退回兜底向量。"
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
        <button class="secondary-button compact" type="button" @click="startEmbeddingCreate">
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
        v-else-if="filteredModels.length === 0"
        kind="empty"
        title="没有模型配置"
        description="先初始化 DeepSeek 供应商，再新增模型配置。"
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
            <tr v-for="model in filteredModels" :key="model.id">
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
                    class="text-button"
                    type="button"
                    @click="startEdit(model.id)"
                  >
                    配置
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmDelete(model)"
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
            >
              {{ provider.display_name }}
            </option>
          </select>
        </label>
        <label>
          <span>模型标识</span>
          <input
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
        <button class="secondary-button" type="button" @click="testConnection">
          测试连通性
        </button>
        <p v-if="connectionResult" class="preview-note" role="status">
          {{ connectionResult }}
        </p>
        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="closeEditor">
            取消并清空密钥
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
