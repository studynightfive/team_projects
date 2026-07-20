<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, reactive, ref, watch } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  createRetrievalDataset,
  getRetrievalRun,
  isRetrievalTestResult,
  listRetrievalDatasets,
  listRetrievalRuns,
  runRetrievalTest,
  searchRetrievalCandidates,
  updateRetrievalDataset,
  type RetrievalDataset,
  type RetrievalDatasetQuery,
  type RetrievalPerQueryResult,
  type RetrievalRun,
  type RetrievalSearchHit,
  type RetrievalTestMode,
  type RetrievalTestResult,
} from "../../services/admin";
import {
  listKnowledgeBases,
  type KnowledgeBaseRecord,
} from "../../services/knowledge";

interface QueryDraft {
  readonly id: string;
  query: string;
  notes: string;
  relevantChunkIds: string[];
  candidates: readonly RetrievalSearchHit[];
  loading: boolean;
}

interface DatasetEditor {
  id: string | null;
  name: string;
  description: string;
  kbId: string;
  queries: QueryDraft[];
}

const { message } = AntApp.useApp();
const datasets = ref<readonly RetrievalDataset[]>([]);
const runs = ref<readonly RetrievalRun[]>([]);
const knowledgeBases = ref<readonly KnowledgeBaseRecord[]>([]);
const selectedDatasetId = ref("");
const selectedKbId = ref("");
const topK = ref(8);
const threshold = ref(0);
const mode = ref<RetrievalTestMode>("hybrid");
const rerank = ref(false);
const loading = ref(false);
const running = ref(false);
const saving = ref(false);
const loadingResultId = ref("");
const selectedResult = ref<RetrievalTestResult | null>(null);
const editorOpen = ref(false);
const editor = reactive<DatasetEditor>({
  id: null,
  name: "",
  description: "",
  kbId: "",
  queries: [],
});

const modeOptions: readonly {
  readonly value: RetrievalTestMode;
  readonly label: string;
  readonly description: string;
}[] = [
  {
    value: "keyword",
    label: "关键词",
    description: "适合今晚稳定演示，会用 PostgreSQL 文本检索。",
  },
  {
    value: "hybrid",
    label: "混合",
    description: "关键词与向量融合，适合验证 Qwen embedding 效果。",
  },
  {
    value: "vector",
    label: "向量",
    description: "只使用 embedding 相似度，需要文档已有真实向量。",
  },
];

const demoQuestions: readonly string[] = [
  "HIS 医院信息系统需要支持哪些关键能力？",
  "EMR 电子病历系统有哪些重点要求？",
  "LIS 检验业务的关键流程是什么？",
  "PACS/RIS 影像系统的建设重点是什么？",
  "医保结算模块有哪些主要风险？",
  "患者主索引需要解决哪些问题？",
  "临床数据中心包含哪些数据主题？",
  "系统集成为什么要区分同步接口和异步消息？",
  "医疗数据安全和权限控制应该怎么做？",
  "医疗信息化项目实施分为哪些阶段？",
];

const selectedDataset = computed(() =>
  datasets.value.find((dataset) => dataset.id === selectedDatasetId.value),
);

const filteredDatasets = computed(() =>
  selectedKbId.value === ""
    ? datasets.value
    : datasets.value.filter((dataset) => dataset.kb_id === selectedKbId.value),
);

const selectedDatasetQueries = computed(
  () => selectedDataset.value?.queries ?? [],
);

const selectedKb = computed(() =>
  knowledgeBases.value.find((item) => item.id === selectedKbId.value),
);

const editorTitle = computed(() =>
  editor.id === null ? "新建测试集" : "编辑测试集",
);

const statusTone = (status: string): string =>
  ({ done: "success", running: "info", pending: "info", failed: "danger" })[
    status
  ] ?? "neutral";

const statusLabel = (status: string): string =>
  ({ done: "完成", running: "运行中", pending: "等待中", failed: "失败" })[
    status
  ] ?? status;

const formatDate = (value: string | null): string =>
  value === null ? "-" : new Date(value).toLocaleString("zh-CN");

const formatPercent = (value: number): string =>
  `${Math.round(value * 1000) / 10}%`;

const formatScore = (value: number): string =>
  String(Math.round(value * 1000) / 1000);

const getKnowledgeBaseName = (id: string): string =>
  knowledgeBases.value.find((item) => item.id === id)?.name ?? "未知知识库";

const shortId = (id: string): string => id.slice(0, 8);

const makeDraft = (
  query: Partial<RetrievalDatasetQuery> = {},
): QueryDraft => ({
  id: crypto.randomUUID(),
  query: query.query ?? "",
  notes: query.notes ?? "",
  relevantChunkIds: [...(query.relevant_chunk_ids ?? [])],
  candidates: [],
  loading: false,
});

const resetEditor = (kbId = selectedKbId.value): void => {
  editor.id = null;
  editor.name = "";
  editor.description = "";
  editor.kbId = kbId;
  editor.queries = [makeDraft()];
};

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const [datasetPage, runPage, kbItems] = await Promise.all([
      listRetrievalDatasets(),
      listRetrievalRuns(),
      listKnowledgeBases(),
    ]);
    datasets.value = datasetPage.items;
    runs.value = runPage.items;
    knowledgeBases.value = kbItems;
    if (
      selectedDatasetId.value === "" ||
      !datasetPage.items.some((item) => item.id === selectedDatasetId.value)
    ) {
      selectedDatasetId.value = datasetPage.items[0]?.id ?? "";
    }
    if (
      selectedKbId.value === "" ||
      !kbItems.some((item) => item.id === selectedKbId.value)
    ) {
      selectedKbId.value =
        datasetPage.items[0]?.kb_id ?? kbItems[0]?.id ?? "";
    }
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

watch(selectedKbId, () => {
  selectedDatasetId.value = filteredDatasets.value[0]?.id ?? "";
});

const startCreate = (): void => {
  resetEditor(selectedKbId.value || knowledgeBases.value[0]?.id || "");
  editorOpen.value = true;
};

const startEdit = (dataset: RetrievalDataset): void => {
  editor.id = dataset.id;
  editor.name = dataset.name;
  editor.description = dataset.description;
  editor.kbId = dataset.kb_id;
  editor.queries = dataset.queries.map((query) => makeDraft(query));
  editorOpen.value = true;
};

const closeEditor = (): void => {
  editorOpen.value = false;
};

const addQuestion = (): void => {
  editor.queries.push(makeDraft());
};

const fillDemoQuestions = (): void => {
  editor.queries = demoQuestions.map((query) => makeDraft({ query }));
};

const removeQuestion = (id: string): void => {
  editor.queries = editor.queries.filter((query) => query.id !== id);
};

const isChunkSelected = (draft: QueryDraft, chunkId: string): boolean =>
  draft.relevantChunkIds.includes(chunkId);

const toggleChunk = (draft: QueryDraft, chunkId: string): void => {
  draft.relevantChunkIds = isChunkSelected(draft, chunkId)
    ? draft.relevantChunkIds.filter((id) => id !== chunkId)
    : [...draft.relevantChunkIds, chunkId];
};

const loadCandidates = async (draft: QueryDraft): Promise<void> => {
  if (editor.kbId === "") {
    message.warning("请先选择知识库");
    return;
  }
  if (draft.query.trim() === "") {
    message.warning("请先填写测试问题");
    return;
  }
  draft.loading = true;
  try {
    draft.candidates = await searchRetrievalCandidates({
      query: draft.query.trim(),
      mode: mode.value,
      kb_id: editor.kbId,
      top_k: 8,
      threshold: 0,
      rerank: false,
    });
    if (draft.candidates.length === 0) {
      message.warning("该问题暂未检索到候选片段");
    }
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    draft.loading = false;
  }
};

const normalizeEditorQueries = (): RetrievalDatasetQuery[] =>
  editor.queries
    .map((draft) => ({
      query: draft.query.trim(),
      relevant_chunk_ids: [...new Set(draft.relevantChunkIds)],
      notes: draft.notes.trim() === "" ? null : draft.notes.trim(),
    }))
    .filter((query) => query.query !== "");

const saveDataset = async (): Promise<void> => {
  const queries = normalizeEditorQueries();
  if (editor.name.trim() === "") {
    message.warning("请填写测试集名称");
    return;
  }
  if (editor.kbId === "") {
    message.warning("请先选择知识库");
    return;
  }
  if (queries.length === 0) {
    message.warning("至少需要一个测试问题");
    return;
  }
  if (queries.some((query) => query.relevant_chunk_ids.length === 0)) {
    message.warning("每个测试问题至少需要选择一个相关 chunk");
    return;
  }

  saving.value = true;
  try {
    const payload = {
      name: editor.name.trim(),
      description: editor.description.trim(),
      queries,
    };
    const saved =
      editor.id === null
        ? await createRetrievalDataset({ ...payload, kb_id: editor.kbId })
        : await updateRetrievalDataset(editor.id, payload);
    selectedDatasetId.value = saved.id;
    selectedKbId.value = saved.kb_id;
    message.success(editor.id === null ? "测试集已创建" : "测试集已保存");
    closeEditor();
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    saving.value = false;
  }
};

const runTest = async (): Promise<void> => {
  if (selectedDataset.value === undefined) {
    message.warning("请先选择测试集");
    return;
  }
  running.value = true;
  try {
    selectedResult.value = await runRetrievalTest({
      dataset_id: selectedDataset.value.id,
      mode: mode.value,
      top_k: topK.value,
      threshold: threshold.value,
      rerank: rerank.value,
    });
    message.success("命中率测试已完成");
    const runPage = await listRetrievalRuns();
    runs.value = runPage.items;
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    running.value = false;
  }
};

const viewRun = async (run: RetrievalRun): Promise<void> => {
  loadingResultId.value = run.id;
  try {
    const detail = await getRetrievalRun(run.id);
    if (!isRetrievalTestResult(detail)) {
      selectedResult.value = null;
      message.info(
        detail.status === "failed"
          ? (detail.error_message ?? "该评测运行失败。")
          : `该评测仍为 ${detail.status} 状态，当前进度 ${detail.progress}%。`,
      );
      return;
    }
    selectedResult.value = detail;
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loadingResultId.value = "";
  }
};

const resultRows = computed<readonly RetrievalPerQueryResult[]>(
  () => selectedResult.value?.per_query ?? [],
);

onMounted(loadData);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="检索质量"
      title="命中率测试"
      description="维护真实测试集，标注相关 chunk，并调用后端检索评估接口生成指标。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
        <button class="admin-primary-button" type="button" @click="startCreate">
          新建测试集
        </button>
      </template>
    </PageHeader>

    <div class="retrieval-test-layout">
      <ResourcePanel
        title="测试参数"
        :description="
          selectedKb === undefined
            ? '请选择知识库和测试集。'
            : '当前知识库：' +
              selectedKb.name +
              '，' +
              String(selectedDatasetQueries.length) +
              ' 个问题'
        "
      >
        <InlineState
          v-if="loading"
          kind="loading"
          title="正在加载测试数据"
          description="请稍候。"
        />
        <form v-else class="retrieval-form" @submit.prevent="runTest">
          <label>
            <span>知识库</span>
            <select v-model="selectedKbId">
              <option
                v-for="item in knowledgeBases"
                :key="item.id"
                :value="item.id"
              >
                {{ item.name }}
              </option>
            </select>
          </label>
          <label>
            <span>测试集</span>
            <select v-model="selectedDatasetId">
              <option
                v-for="dataset in filteredDatasets"
                :key="dataset.id"
                :value="dataset.id"
              >
                {{ dataset.name }}（{{ dataset.queries.length }} 题）
              </option>
            </select>
          </label>
          <div class="mode-options" aria-label="检索模式">
            <label
              v-for="item in modeOptions"
              :key="item.value"
              class="mode-option"
              :class="{ active: mode === item.value }"
            >
              <input v-model="mode" type="radio" :value="item.value" />
              <strong>{{ item.label }}</strong>
              <span>{{ item.description }}</span>
            </label>
          </div>
          <div class="parameter-grid">
            <label>
              <span>TopK</span>
              <input
                v-model.number="topK"
                type="number"
                min="1"
                max="50"
                step="1"
              />
            </label>
            <label>
              <span>阈值 {{ threshold.toFixed(2) }}</span>
              <input
                v-model.number="threshold"
                type="range"
                min="0"
                max="1"
                step="0.01"
              />
            </label>
          </div>
          <label class="checkbox-line">
            <input v-model="rerank" type="checkbox" />
            <span>启用重排</span>
          </label>
          <div class="form-actions">
            <button
              class="admin-primary-button"
              type="submit"
              :disabled="running || selectedDataset === undefined"
            >
              {{ running ? "运行中" : "运行测试" }}
            </button>
            <button
              v-if="selectedDataset"
              class="secondary-button"
              type="button"
              @click="startEdit(selectedDataset)"
            >
              编辑测试集
            </button>
          </div>
        </form>
      </ResourcePanel>

      <div class="retrieval-main">
        <ResourcePanel
          title="测试集清单"
          :description="'当前共有 ' + String(datasets.length) + ' 个真实测试集'"
        >
          <InlineState
            v-if="datasets.length === 0"
            kind="empty"
            title="暂无测试集"
            description="点击新建测试集，标注问题和相关 chunk 后即可运行。"
          />
          <div v-else class="dataset-list">
            <article
              v-for="dataset in filteredDatasets"
              :key="dataset.id"
              class="dataset-card"
              :class="{ active: dataset.id === selectedDatasetId }"
            >
              <button type="button" @click="selectedDatasetId = dataset.id">
                <strong>{{ dataset.name }}</strong>
                <span>{{ dataset.description || "暂无说明" }}</span>
              </button>
              <dl>
                <div>
                  <dt>问题</dt>
                  <dd>{{ dataset.queries.length }}</dd>
                </div>
                <div>
                  <dt>知识库</dt>
                  <dd>{{ getKnowledgeBaseName(dataset.kb_id) }}</dd>
                </div>
              </dl>
              <button
                class="text-button"
                type="button"
                @click="startEdit(dataset)"
              >
                编辑
              </button>
            </article>
          </div>
        </ResourcePanel>

        <ResourcePanel
          title="运行结果"
          :description="
            selectedResult === null
              ? '运行测试后展示指标和逐题命中详情。'
              : '结果 ID：' + shortId(selectedResult.id)
          "
        >
          <InlineState
            v-if="selectedResult === null"
            kind="empty"
            title="暂无结果详情"
            description="选择测试集并运行后，系统会展示命中率、MRR、Recall 和逐题明细。"
          />
          <template v-else>
            <div class="metric-grid">
              <div>
                <span>Hit Rate</span>
                <strong>{{ formatPercent(selectedResult.metrics.hit_rate) }}</strong>
              </div>
              <div>
                <span>MRR</span>
                <strong>{{ formatScore(selectedResult.metrics.mrr) }}</strong>
              </div>
              <div>
                <span>Recall@K</span>
                <strong>{{ formatPercent(selectedResult.metrics.recall_at_k) }}</strong>
              </div>
              <div>
                <span>Precision@K</span>
                <strong>{{ formatPercent(selectedResult.metrics.precision_at_k) }}</strong>
              </div>
              <div>
                <span>NDCG@K</span>
                <strong>{{ formatScore(selectedResult.metrics.ndcg_at_k) }}</strong>
              </div>
              <div>
                <span>MAP@K</span>
                <strong>{{ formatScore(selectedResult.metrics.map_at_k) }}</strong>
              </div>
            </div>
            <div class="data-table-scroll" tabindex="0">
              <table class="data-table compact-table">
                <thead>
                  <tr>
                    <th scope="col">问题</th>
                    <th scope="col">命中</th>
                    <th scope="col">Recall</th>
                    <th scope="col">耗时</th>
                    <th scope="col">命中片段</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in resultRows" :key="item.query">
                    <td>{{ item.query }}</td>
                    <td>
                      <span
                        class="status-chip"
                        :class="item.hit ? 'success' : 'danger'"
                      >
                        {{ item.hit ? "命中" : "未命中" }}
                      </span>
                    </td>
                    <td>{{ formatPercent(item.recall) }}</td>
                    <td>{{ item.latency_ms }}ms</td>
                    <td class="chunk-cell">
                      {{ item.retrieved_chunk_ids.map(shortId).join("、") || "-" }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </ResourcePanel>

        <ResourcePanel
          title="真实测试记录"
          :description="'当前共有 ' + String(runs.length) + ' 条运行记录'"
        >
          <InlineState
            v-if="runs.length === 0"
            kind="empty"
            title="暂无测试记录"
            description="创建测试集并运行后会在这里显示结果。"
          />
          <div v-else class="data-table-scroll" tabindex="0">
            <table class="data-table">
              <thead>
                <tr>
                  <th scope="col">运行 ID</th>
                  <th scope="col">测试集</th>
                  <th scope="col">状态</th>
                  <th scope="col">进度</th>
                  <th scope="col">问题数</th>
                  <th scope="col">开始时间</th>
                  <th scope="col">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="run in runs" :key="run.id">
                  <td class="numeric">{{ shortId(run.id) }}</td>
                  <td>{{ shortId(run.dataset_id) }}</td>
                  <td>
                    <span class="status-chip" :class="statusTone(run.status)">
                      {{ statusLabel(run.status) }}
                    </span>
                  </td>
                  <td>{{ run.progress }}%</td>
                  <td>{{ run.total }}</td>
                  <td>{{ formatDate(run.started_at) }}</td>
                  <td>
                    <button
                      class="text-button"
                      type="button"
                      :disabled="loadingResultId === run.id"
                      @click="viewRun(run)"
                    >
                      {{ loadingResultId === run.id ? "读取中" : "查看结果" }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </ResourcePanel>
      </div>
    </div>

    <Drawer
      :open="editorOpen"
      :title="editorTitle"
      width="760"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form retrieval-dataset-editor" @submit.prevent="saveDataset">
        <div class="editor-grid">
          <label>
            <span>测试集名称</span>
            <input
              v-model="editor.name"
              type="text"
              autocomplete="off"
              required
              placeholder="医疗信息化演示测试集"
            />
          </label>
          <label>
            <span>知识库</span>
            <select v-model="editor.kbId" :disabled="editor.id !== null">
              <option
                v-for="item in knowledgeBases"
                :key="item.id"
                :value="item.id"
              >
                {{ item.name }}
              </option>
            </select>
          </label>
        </div>
        <label>
          <span>说明</span>
          <textarea
            v-model="editor.description"
            rows="2"
            placeholder="用于今晚演示医疗信息化知识库检索质量。"
          />
        </label>

        <div class="question-toolbar">
          <strong>测试问题</strong>
          <div>
            <button
              class="secondary-button compact"
              type="button"
              @click="fillDemoQuestions"
            >
              填充医疗问题
            </button>
            <button
              class="admin-primary-button compact"
              type="button"
              @click="addQuestion"
            >
              添加问题
            </button>
          </div>
        </div>

        <section
          v-for="(draft, index) in editor.queries"
          :key="draft.id"
          class="question-card"
        >
          <div class="question-card-header">
            <strong>问题 {{ index + 1 }}</strong>
            <button
              class="text-button"
              type="button"
              :disabled="editor.queries.length === 1"
              @click="removeQuestion(draft.id)"
            >
              删除
            </button>
          </div>
          <label>
            <span>问题文本</span>
            <input
              v-model="draft.query"
              type="text"
              autocomplete="off"
              placeholder="例如：HIS 医院信息系统需要支持哪些关键能力？"
            />
          </label>
          <label>
            <span>备注</span>
            <input
              v-model="draft.notes"
              type="text"
              autocomplete="off"
              placeholder="可填写期望命中的章节或判断口径"
            />
          </label>
          <div class="candidate-toolbar">
            <span>
              已选 {{ draft.relevantChunkIds.length }} 个相关 chunk
            </span>
            <button
              class="secondary-button compact"
              type="button"
              :disabled="draft.loading"
              @click="loadCandidates(draft)"
            >
              {{ draft.loading ? "检索中" : "检索候选" }}
            </button>
          </div>
          <div v-if="draft.candidates.length > 0" class="candidate-list">
            <label
              v-for="candidate in draft.candidates"
              :key="candidate.chunk_id"
              class="candidate-item"
            >
              <input
                type="checkbox"
                :checked="isChunkSelected(draft, candidate.chunk_id)"
                @change="toggleChunk(draft, candidate.chunk_id)"
              />
              <span>
                <strong>
                  {{ shortId(candidate.chunk_id) }} ·
                  {{ candidate.doc_title || "未知文档" }}
                </strong>
                <small>
                  分数 {{ formatScore(candidate.score) }} ·
                  {{ candidate.text.slice(0, 180) }}
                </small>
              </span>
            </label>
          </div>
          <label>
            <span>相关 chunk ID</span>
            <textarea
              :value="draft.relevantChunkIds.join('\n')"
              rows="3"
              placeholder="也可以直接粘贴 chunk_id，每行一个。"
              @input="
                draft.relevantChunkIds = ($event.target as HTMLTextAreaElement).value
                  .split(/\s+/u)
                  .map((id) => id.trim())
                  .filter((id) => id.length > 0)
              "
            />
          </label>
        </section>

        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="closeEditor">
            取消
          </button>
          <button class="admin-primary-button" type="submit" :disabled="saving">
            {{ saving ? "保存中" : "保存测试集" }}
          </button>
        </div>
      </form>
    </Drawer>
  </div>
</template>

<style scoped>
.retrieval-test-layout {
  display: grid;
  grid-template-columns: minmax(280px, 380px) minmax(0, 1fr);
  align-items: start;
  gap: var(--space-6);
}

.retrieval-main,
.retrieval-form,
.retrieval-dataset-editor {
  display: grid;
  gap: var(--space-4);
}

.retrieval-form label,
.retrieval-dataset-editor label {
  display: grid;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}

.retrieval-form input,
.retrieval-form select,
.retrieval-dataset-editor input,
.retrieval-dataset-editor select,
.retrieval-dataset-editor textarea {
  width: 100%;
}

.mode-options {
  display: grid;
  gap: var(--space-2);
}

.mode-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-1) var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.mode-option.active {
  border-color: var(--color-admin);
  background: var(--color-admin-soft);
}

.mode-option input {
  grid-row: span 2;
  width: auto;
  margin-top: 2px;
}

.mode-option span {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.parameter-grid,
.editor-grid,
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.checkbox-line {
  display: flex !important;
  grid-template-columns: none !important;
  align-items: center;
}

.checkbox-line input {
  width: auto;
}

.form-actions,
.question-toolbar,
.candidate-toolbar,
.question-card-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.dataset-list {
  display: grid;
  gap: var(--space-3);
}

.dataset-card,
.question-card,
.candidate-item,
.metric-grid > div {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.dataset-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
}

.dataset-card.active {
  border-color: var(--color-admin);
  box-shadow: 0 0 0 1px var(--color-admin-soft);
}

.dataset-card > button:first-child {
  display: grid;
  gap: var(--space-1);
  padding: 0;
  border: 0;
  color: inherit;
  text-align: left;
  background: transparent;
  cursor: pointer;
}

.dataset-card span,
.candidate-item small {
  color: var(--color-text-muted);
}

.dataset-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.dataset-card dt,
.metric-grid span {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.dataset-card dd {
  margin: 0;
  font-weight: var(--font-weight-semibold);
}

.metric-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-grid > div {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-4);
}

.metric-grid strong {
  font-size: var(--font-size-24);
}

.question-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
}

.candidate-list {
  display: grid;
  gap: var(--space-2);
  max-height: 260px;
  overflow: auto;
}

.candidate-item {
  grid-template-columns: auto minmax(0, 1fr) !important;
  align-items: start;
  padding: var(--space-3);
}

.candidate-item input {
  width: auto;
  margin-top: 3px;
}

.candidate-item span {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.chunk-cell {
  max-width: 360px;
  word-break: break-word;
}

.compact-table td {
  vertical-align: top;
}

@media (max-width: 1180px) {
  .retrieval-test-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .parameter-grid,
  .editor-grid,
  .metric-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
