<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, reactive, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { localPageData } from "../../data/local-pages";

interface KnowledgeBaseItem {
  id: string;
  name: string;
  owner: string;
  documents: number;
  members: number;
  status: string;
  retrieval: string;
  authorizationGroups: string[];
}

const parseRetrieval = (
  retrieval: string,
): { mode: string; topK: number; threshold: number } => {
  const match = /^(.*?) \/ TopK (\d+) \/ (\d+(?:\.\d+)?)$/u.exec(retrieval);
  if (match === null) return { mode: "混合", topK: 8, threshold: 0.62 };

  return {
    mode: match[1] ?? "混合",
    topK: Number(match[2]),
    threshold: Number(match[3]),
  };
};

const { message, modal } = AntApp.useApp();
const knowledgeBases = ref<KnowledgeBaseItem[]>(
  localPageData.adminKnowledgeBases.map((item) => ({
    ...item,
    authorizationGroups: ["普通用户"],
  })),
);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedId = ref<string>();
const isCreating = ref(false);
const authorizationGroups = ref<string[]>([]);
const editor = reactive({
  name: "",
  owner: "",
  mode: "混合",
  topK: 8,
  threshold: 0.62,
});

const selectedKnowledgeBase = computed(() =>
  knowledgeBases.value.find((item) => item.id === selectedId.value),
);

const filteredKnowledgeBases = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return knowledgeBases.value.filter((item) => {
    const matchesQuery =
      keyword.length === 0 ||
      [item.name, item.owner, item.retrieval].some((value) =>
        value.toLowerCase().includes(keyword),
      );
    const matchesStatus =
      statusFilter.value === "全部状态" || item.status === statusFilter.value;
    return matchesQuery && matchesStatus;
  });
});

const statusTone = (status: string): string =>
  status === "正常" ? "success" : "warning";

const startCreate = (): void => {
  selectedId.value = undefined;
  isCreating.value = true;
  authorizationGroups.value = [];
  Object.assign(editor, {
    name: "",
    owner: "",
    mode: "混合",
    topK: 8,
    threshold: 0.62,
  });
};

const startEdit = (id: string): void => {
  const item = knowledgeBases.value.find(
    (knowledgeBase) => knowledgeBase.id === id,
  );
  if (item === undefined) return;

  selectedId.value = id;
  isCreating.value = false;
  authorizationGroups.value = [...item.authorizationGroups];
  const retrieval = parseRetrieval(item.retrieval);
  Object.assign(editor, {
    name: item.name,
    owner: item.owner,
    mode: retrieval.mode,
    topK: retrieval.topK,
    threshold: retrieval.threshold,
  });
};

const closeEditor = (): void => {
  selectedId.value = undefined;
  isCreating.value = false;
  authorizationGroups.value = [];
};

const savePreview = (): void => {
  if (editor.name.trim().length === 0 || editor.owner.trim().length === 0) {
    void message.warning("请填写知识库名称和归属团队");
    return;
  }

  if (
    !Number.isInteger(editor.topK) ||
    editor.topK < 1 ||
    editor.topK > 50 ||
    !Number.isFinite(editor.threshold) ||
    editor.threshold < 0 ||
    editor.threshold > 1
  ) {
    void message.warning("请输入有效的 TopK 和阈值");
    return;
  }

  const retrieval =
    editor.mode +
    " / TopK " +
    String(editor.topK) +
    " / " +
    editor.threshold.toFixed(2);

  if (isCreating.value) {
    knowledgeBases.value.push({
      id: "kb-local-preview-" + String(knowledgeBases.value.length + 1),
      name: editor.name.trim(),
      owner: editor.owner.trim(),
      documents: 0,
      members: 0,
      status: "正常",
      retrieval,
      authorizationGroups: [...authorizationGroups.value],
    });
  } else {
    const item = selectedKnowledgeBase.value;
    if (item !== undefined) {
      Object.assign(item, {
        name: editor.name.trim(),
        owner: editor.owner.trim(),
        retrieval,
        authorizationGroups: [...authorizationGroups.value],
      });
    }
  }

  void message.success("知识库配置与授权已更新为本地预览状态");
  closeEditor();
};

const archivePreview = (id: string): void => {
  const item = knowledgeBases.value.find(
    (knowledgeBase) => knowledgeBase.id === id,
  );
  if (item === undefined) return;

  item.status = item.status === "归档中" ? "正常" : "归档中";
  void message.success("归档状态已在当前页面切换");
};

const confirmDelete = (id: string): void => {
  const item = knowledgeBases.value.find(
    (knowledgeBase) => knowledgeBase.id === id,
  );
  if (item === undefined) return;

  modal.confirm({
    title: "删除知识库预览",
    content: "仅从当前页面预览中移除；不会删除文档、成员、索引或任何后端数据。",
    okText: "确认本地预览",
    cancelText: "取消",
    onOk: () => {
      knowledgeBases.value = knowledgeBases.value.filter(
        (knowledgeBase) => knowledgeBase.id !== id,
      );
      void message.success(item.name + " 已从本地预览中移除");
    },
  });
};
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="内容治理"
      title="知识库管理"
      description="集中预览知识库规模、检索参数、归档状态和授权范围。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
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
          <input
            v-model="query"
            type="search"
            placeholder="名称、归属团队或检索参数"
          />
        </label>
        <label>
          <span>状态</span>
          <select v-model="statusFilter">
            <option>全部状态</option>
            <option>正常</option>
            <option>归档中</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="filteredKnowledgeBases.length === 0"
        kind="empty"
        title="没有匹配的知识库"
        description="请调整关键词或状态。"
      />
      <div
        v-else
        class="data-table-scroll"
        tabindex="0"
        aria-label="知识库表格，可横向滚动"
      >
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">知识库</th>
              <th scope="col">归属团队</th>
              <th scope="col">文档</th>
              <th scope="col">成员</th>
              <th scope="col">检索参数</th>
              <th scope="col">状态</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredKnowledgeBases" :key="item.id">
              <td>
                <strong>{{ item.name }}</strong>
              </td>
              <td>{{ item.owner }}</td>
              <td>{{ item.documents }}</td>
              <td>{{ item.members }}</td>
              <td>{{ item.retrieval }}</td>
              <td>
                <span class="status-chip" :class="statusTone(item.status)">
                  {{ item.status }}
                </span>
              </td>
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
                    @click="archivePreview(item.id)"
                  >
                    {{ item.status === "归档中" ? "恢复" : "归档" }}
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmDelete(item.id)"
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
      :open="isCreating || selectedKnowledgeBase !== undefined"
      :title="isCreating ? '新建知识库（本地预览）' : '知识库配置（本地预览）'"
      width="460"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form" @submit.prevent="savePreview">
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
          <span>归属团队</span>
          <input
            v-model="editor.owner"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <label>
          <span>检索模式</span>
          <select v-model="editor.mode">
            <option>混合</option>
            <option>向量</option>
            <option>关键词</option>
          </select>
        </label>
        <div class="retrieval-parameter-grid">
          <label>
            <span>TopK</span>
            <input
              v-model.number="editor.topK"
              type="number"
              min="1"
              max="50"
              step="1"
              required
            />
          </label>
          <label>
            <span>阈值</span>
            <input
              v-model.number="editor.threshold"
              type="number"
              min="0"
              max="1"
              step="0.01"
              required
            />
          </label>
        </div>
        <fieldset class="checkbox-list">
          <legend>授权范围预览</legend>
          <label>
            <input
              v-model="authorizationGroups"
              type="checkbox"
              value="平台管理员"
            />
            <span>平台管理员</span>
          </label>
          <label>
            <input
              v-model="authorizationGroups"
              type="checkbox"
              value="知识库编辑者"
            />
            <span>知识库编辑者</span>
          </label>
          <label>
            <input
              v-model="authorizationGroups"
              type="checkbox"
              value="普通用户"
            />
            <span>普通用户</span>
          </label>
        </fieldset>
        <p class="preview-note">
          参数范围和授权字段等待 OpenAPI 确认，本页不写入真实配置。
        </p>
        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="closeEditor">
            取消
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
.retrieval-parameter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

@media (max-width: 767px) {
  .retrieval-parameter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
