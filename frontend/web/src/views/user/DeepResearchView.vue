<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import SearchStatusBadge from "../../components/search/SearchStatusBadge.vue";
import { Download, FileText, FlaskConical } from "../../components/icons";
import { aiSearchMockData } from "../../mocks/ai-search";
import type {
  Research,
  ResearchStatus,
  SearchSourceType,
} from "../../types/ai-search";

const { message } = AntApp.useApp();
const research: Research = aiSearchMockData.research;
const researchSourceIds = new Set<string>(research.sourceIds);
const researchSources = computed(() =>
  aiSearchMockData.dataSources.filter((source) =>
    researchSourceIds.has(source.id),
  ),
);
const sourceLabels = {
  knowledge: "企业知识库",
  project: "项目文档",
  policy: "规章制度",
  meeting: "会议记录",
  business: "业务数据",
  personal: "个人文件",
  internet: "互联网信息",
} satisfies Record<SearchSourceType, string>;
const researchStatusLabels = {
  waiting: "等待执行",
  running: "正在研究",
  completed: "研究完成",
  failed: "研究失败",
} satisfies Record<ResearchStatus, string>;

const exportReport = (): void => {
  void message.info("研究仍在执行，本地报告将在全部步骤完成后开放导出");
};
</script>

<template>
  <div class="business-page deep-research-page">
    <PageHeader
      eyebrow="复杂问题分析"
      title="深度研究"
      description="把复杂问题拆成可核验步骤，并明确区分已完成来源与待补充信息。"
    >
      <template #actions>
        <span class="local-preview-badge">模拟研究任务</span>
        <button class="secondary-button" type="button" @click="exportReport">
          <Download :size="16" aria-hidden="true" />
          导出报告
        </button>
      </template>
    </PageHeader>

    <section
      class="research-question-card"
      aria-labelledby="research-question-title"
    >
      <span class="research-icon" aria-hidden="true"><FlaskConical :size="21" /></span>
      <div>
        <span>研究问题</span>
        <h2 id="research-question-title">{{ research.question }}</h2>
        <p>{{ research.summary }}</p>
      </div>
      <SearchStatusBadge
        :status="research.status"
        :label="researchStatusLabels[research.status]"
      />
    </section>

    <div class="research-layout">
      <ResourcePanel
        title="研究计划"
        :description="`当前执行第 ${research.currentStep} 步，共 ${research.steps.length} 步`"
      >
        <ol class="research-timeline">
          <li
            v-for="(step, index) in research.steps"
            :key="step.id"
            :class="`status-${step.status}`"
          >
            <span class="research-step-index">{{ index + 1 }}</span>
            <div>
              <strong>{{ step.title }}</strong>
              <p>{{ step.description }}</p>
            </div>
            <SearchStatusBadge
              :status="step.status"
              :label="researchStatusLabels[step.status]"
            />
          </li>
        </ol>
      </ResourcePanel>

      <aside class="research-side-column">
        <ResourcePanel
          title="引用来源"
          description="仅展示本地模拟的来源边界。"
        >
          <div class="research-source-list">
            <article v-for="source in researchSources" :key="source.id">
              <span aria-hidden="true"><FileText :size="17" /></span>
              <div>
                <strong>{{ source.name }}</strong>
                <small>{{
                  source.contentCount.toLocaleString("zh-CN")
                }}
                  条内容</small>
              </div>
              <SearchStatusBadge :status="source.connectionStatus" />
            </article>
          </div>
        </ResourcePanel>

        <ResourcePanel
          title="中间结论"
          description="最终报告生成前仍需交叉验证。"
        >
          <div class="research-interim">
            <p>
              重点项目的内部进展资料已经汇总，当前发现一个资源依赖风险和一个外部验收等待项。
            </p>
            <p>
              外部公开信息源尚未连接，因此最终报告会保留明确的证据边界，不把缺失信息推断为事实。
            </p>
          </div>
        </ResourcePanel>
      </aside>
    </div>

    <div class="research-summary-grid">
      <ResourcePanel
        title="研究范围"
        description="当前任务只在以下已授权内容类型中检索。"
      >
        <div class="research-scope-list">
          <span v-for="scope in research.scopes" :key="scope">
            {{ sourceLabels[scope] }}
          </span>
        </div>
      </ResourcePanel>

      <ResourcePanel
        title="最终报告"
        description="只有全部研究步骤完成后才生成可导出的正式报告。"
      >
        <article v-if="research.status === 'completed'" class="research-report">
          <h3>{{ research.question }}</h3>
          <p>{{ research.summary }}</p>
        </article>
        <InlineState
          v-else
          kind="loading"
          title="最终报告仍在生成"
          :description="`已完成 ${research.currentStep - 1} 步，共 ${research.steps.length} 步；当前中间结论不作为正式报告。`"
        />
      </ResourcePanel>
    </div>
  </div>
</template>

<style scoped>
.deep-research-page,
.research-side-column,
.research-summary-grid {
  display: grid;
  gap: var(--space-5);
}

.research-summary-grid {
  grid-template-columns: minmax(280px, 0.7fr) minmax(0, 1.3fr);
}

.research-scope-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.research-scope-list span {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-pill);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
}

.research-report h3 {
  margin: 0 0 var(--space-3);
  color: var(--color-text);
  font-size: var(--font-size-16);
}

.research-report p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.75;
}

.research-question-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.research-icon,
.research-source-list article > span {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.research-question-card > div > span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.research-question-card h2 {
  margin: var(--space-1) 0 var(--space-2);
  color: var(--color-text);
  font-size: var(--font-size-20);
}

.research-question-card p,
.research-timeline p,
.research-interim p {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.7;
}

.research-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.55fr);
  gap: var(--space-5);
  align-items: start;
}

.research-timeline {
  display: grid;
  margin: 0;
  padding: 0;
  list-style: none;
}

.research-timeline li {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--space-3);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--color-border);
}

.research-step-index {
  position: relative;
  z-index: 1;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-pill);
  color: var(--color-text-muted);
  background: var(--color-surface);
  font-size: var(--font-size-12);
}

.status-completed .research-step-index {
  border-color: var(--color-success);
  color: var(--white);
  background: var(--color-success);
}

.status-running .research-step-index {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.research-timeline strong {
  color: var(--color-text);
  font-weight: var(--font-weight-medium);
}

.research-timeline p {
  margin-top: var(--space-1);
  font-size: var(--font-size-13);
}

.research-source-list {
  display: grid;
  gap: var(--space-3);
}

.research-source-list article {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.research-source-list article > span {
  width: 34px;
  height: 34px;
}

.research-source-list article > div {
  display: grid;
  min-width: 0;
}

.research-source-list strong {
  overflow: hidden;
  color: var(--color-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.research-source-list small {
  color: var(--color-text-muted);
}

.research-interim {
  display: grid;
  gap: var(--space-4);
}

@media (max-width: 1180px) {
  .research-layout,
  .research-summary-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .research-question-card,
  .research-timeline li,
  .research-source-list article {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .research-question-card > :last-child,
  .research-timeline li > :last-child,
  .research-source-list article > :last-child {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
