<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { ChevronLeft, FileDown, ScrollText } from "../../components/icons";
import { localPageData } from "../../data/local-pages";

const route = useRoute();
const { message } = AntApp.useApp();

const sections = [
  { id: "overview", label: "发布目标", page: 1 },
  { id: "preflight", label: "发布前检查", page: 3 },
  { id: "rollback", label: "回滚流程", page: 8 },
  { id: "evidence", label: "验收证据", page: 12 },
] as const;
type SectionId = (typeof sections)[number]["id"];

const activeSection = ref<SectionId>("overview");

const knowledgeBaseId = computed(() => String(route.params.kb_id ?? ""));
const knowledgeBase = computed(() =>
  localPageData.knowledgeBases.find(
    (item) => item.id === knowledgeBaseId.value,
  ),
);
const document = computed(() => {
  if (knowledgeBase.value === undefined) return undefined;

  return localPageData.documents.find(
    (item) =>
      item.id === String(route.params.document_id ?? "") &&
      item.knowledgeBaseId === knowledgeBase.value?.id,
  );
});
const documentTitle = computed(
  () => document.value?.name.replace(/\.[^.]+$/u, "") ?? "",
);
const returnPath = computed(() =>
  knowledgeBase.value === undefined
    ? "/knowledge"
    : `/knowledge/${knowledgeBase.value.id}`,
);

watch(
  () => route.query.page,
  (value) => {
    const page = typeof value === "string" ? Number.parseInt(value, 10) : 1;
    activeSection.value =
      [...sections].reverse().find((section) => section.page <= page)?.id ??
      "overview";
  },
  { immediate: true },
);

const previewExport = (): void => {
  void message.info("已打开导出本地预览；鉴权任务接口接入前不会生成文件");
};
</script>

<template>
  <div class="business-page local-page">
    <PageHeader
      eyebrow="知识库 / 文档预览"
      :title="document?.name ?? '文档不存在'"
      :description="
        document
          ? `${document.category} · ${document.pages} 页 · ${document.owner}`
          : '当前固定样例中没有此文档。'
      "
    >
      <template #actions>
        <RouterLink class="secondary-button" :to="returnPath">
          <ChevronLeft :size="17" aria-hidden="true" />
          返回目录
        </RouterLink>
        <button
          v-if="document"
          class="primary-button"
          type="button"
          @click="previewExport"
        >
          <FileDown :size="17" aria-hidden="true" />
          导出文档
        </button>
      </template>
    </PageHeader>

    <InlineState
      v-if="!document"
      kind="error"
      :title="knowledgeBase ? '此知识库中未找到文档' : '未找到知识库'"
      :description="
        knowledgeBase
          ? '文档与当前知识库不匹配，请从文档目录重新进入；此状态不会请求业务接口。'
          : '父级知识库不存在，请返回知识库列表；此状态不会请求业务接口。'
      "
    />

    <div
      v-else
      class="document-layout"
      :class="{ 'single-column': document.id !== 'release-guide' }"
    >
      <ResourcePanel
        v-if="document.id === 'release-guide'"
        title="页码目录"
        description="点击章节切换本地高亮位置。"
      >
        <nav class="page-outline" aria-label="文档页码目录">
          <button
            v-for="section in sections"
            :key="section.id"
            type="button"
            :class="{ active: activeSection === section.id }"
            :aria-current="
              activeSection === section.id ? 'location' : undefined
            "
            @click="activeSection = section.id"
          >
            <span>{{ section.label }}</span>
            <span>第 {{ section.page }} 页</span>
          </button>
        </nav>
      </ResourcePanel>

      <ResourcePanel
        title="正文预览"
        description="受控 Vue 模板，不解析真实 Markdown。"
      >
        <template #actions>
          <span class="local-preview-badge">本地预览</span>
        </template>

        <article
          v-if="document.id === 'release-guide'"
          class="document-content"
        >
          <header>
            <ScrollText :size="24" aria-hidden="true" />
            <div>
              <h2>{{ documentTitle }}</h2>
              <p>版本 2.4 · 平台团队 · 本地固定内容</p>
            </div>
          </header>

          <section :class="{ highlighted: activeSection === 'overview' }">
            <h3>1. 发布目标</h3>
            <p>
              本指南用于统一发布前准备、执行窗口、验证证据和异常回滚路径，减少跨团队信息遗漏。
            </p>
          </section>

          <section :class="{ highlighted: activeSection === 'preflight' }">
            <h3>2. 发布前检查</h3>
            <p>
              发布窗口开始前必须完成质量门禁、数据库变更确认和回滚路径演练。
            </p>
            <table>
              <thead>
                <tr>
                  <th scope="col">检查项</th>
                  <th scope="col">负责人</th>
                  <th scope="col">证据</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>前端质量门禁</td>
                  <td>前端负责人</td>
                  <td>类型、Lint、测试、构建</td>
                </tr>
                <tr>
                  <td>数据变更确认</td>
                  <td>后端负责人</td>
                  <td>迁移记录与回退脚本</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section :class="{ highlighted: activeSection === 'rollback' }">
            <h3>3. 回滚流程</h3>
            <p>
              当核心健康检查持续失败时，停止后续发布动作，按既定顺序恢复上一稳定版本。
            </p>
            <pre><code>verify health
freeze rollout
restore previous release
record verification evidence</code></pre>
            <p class="citation-highlight">
              引用定位示例：第 8 页强调先停止扩散，再执行恢复与证据记录。
            </p>
          </section>

          <section :class="{ highlighted: activeSection === 'evidence' }">
            <h3>4. 验收证据</h3>
            <p>
              每次发布至少保留检查结果、变更记录、健康状态和最终责任人确认，不在页面中记录凭据。
            </p>
          </section>
        </article>
        <InlineState
          v-else
          kind="info"
          :title="`${documentTitle}正文尚未加入固定样例`"
          description="当前页面保留文档元信息与安全空状态，不会用其他文档内容冒充，也不会请求业务接口。"
        />
      </ResourcePanel>
    </div>
  </div>
</template>

<style scoped>
.local-page {
  display: grid;
  gap: var(--space-6);
}

.document-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.7fr) minmax(0, 2.3fr);
  align-items: start;
  gap: var(--space-6);
}

.document-layout.single-column {
  grid-template-columns: minmax(0, 1fr);
}

.page-outline {
  display: grid;
  gap: var(--space-1);
}

.page-outline button {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 0 var(--space-3);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: transparent;
  text-align: left;
}

.page-outline button span:last-child {
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
  white-space: nowrap;
}

.page-outline button.active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-weight: var(--font-weight-medium);
}

.document-content {
  max-width: 860px;
  margin: 0 auto;
  color: var(--color-text-secondary);
  line-height: 1.75;
}

.document-content > header {
  display: flex;
  gap: var(--space-3);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-primary);
}

.document-content h2,
.document-content h3 {
  color: var(--color-text);
}

.document-content h2 {
  margin-bottom: var(--space-1);
  font-size: var(--font-size-24);
}

.document-content header p {
  margin-bottom: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
}

.document-content section {
  padding: var(--space-5);
  border-radius: var(--radius-8);
  transition: background var(--transition-fast);
}

.document-content section.highlighted {
  background: var(--color-primary-soft);
}

.document-content table {
  width: 100%;
  border-collapse: collapse;
}

.document-content th,
.document-content td {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  text-align: left;
}

.document-content th {
  background: var(--color-table-head);
}

.document-content pre {
  padding: var(--space-4);
  overflow: auto;
  border-radius: var(--radius-8);
  color: var(--slate-100);
  background: var(--slate-950);
  font-family: var(--font-mono);
}

.citation-highlight {
  padding: var(--space-3);
  border-left: 3px solid var(--color-primary);
  background: var(--blue-50);
}

@media (max-width: 980px) {
  .document-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .document-content section {
    padding: var(--space-4) 0;
  }

  .document-content section.highlighted {
    padding: var(--space-4);
  }
}
</style>
