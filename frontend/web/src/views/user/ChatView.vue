<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  ArrowUpRight,
  MessageSquareText,
  RefreshCw,
  X,
} from "../../components/icons";
import { localPageData } from "../../data/local-pages";

type PreviewStatus = "idle" | "generating" | "stopped" | "complete";

const route = useRoute();
const { message } = AntApp.useApp();
const prompt = ref("");
const activeQuestion = ref("");
const previewStatus = ref<PreviewStatus>("idle");
const visibleSegmentCount = ref(0);

const requestedConversationId = computed(() =>
  String(route.params.conversation_id ?? ""),
);
const conversation = computed(() =>
  localPageData.conversations.find(
    (item) => item.id === requestedConversationId.value,
  ),
);
const isMissingConversation = computed(
  () =>
    requestedConversationId.value.length > 0 &&
    conversation.value === undefined,
);

const pageTitle = computed(() => {
  if (isMissingConversation.value) return "会话不存在";
  return conversation.value?.title ?? "新建智能问答";
});
const previewStatusText = computed(
  () =>
    ({
      idle: "等待开始",
      generating: "正在逐段展示",
      stopped: "已停止本地预览",
      complete: "本地回答展示完成",
    })[previewStatus.value],
);

const answerSegments = [
  "发布前先确认本次变更范围、责任人和可观察的退出条件。",
  "然后完成类型检查、Lint、测试、生产构建，以及关键桌面和移动视口验证。",
  "涉及数据或服务变更时，还需要确认迁移、健康检查和回滚路径均可执行。",
] as const;

const startPreview = (): void => {
  const nextQuestion = prompt.value.trim();
  if (nextQuestion.length === 0) {
    void message.warning("请输入问题");
    return;
  }

  activeQuestion.value = nextQuestion;
  prompt.value = "";
  previewStatus.value = "generating";
  visibleSegmentCount.value = 1;
};

const showNextSegment = (): void => {
  if (visibleSegmentCount.value >= answerSegments.length) {
    previewStatus.value = "complete";
    return;
  }

  visibleSegmentCount.value += 1;
  if (visibleSegmentCount.value >= answerSegments.length) {
    previewStatus.value = "complete";
  }
};

const stopPreview = (): void => {
  previewStatus.value = "stopped";
};

const retryPreview = (): void => {
  previewStatus.value = "generating";
  visibleSegmentCount.value = 1;
};
</script>

<template>
  <div class="business-page local-page chat-page">
    <PageHeader
      eyebrow="用户工作区 / 智能问答"
      :title="pageTitle"
      description="逐段回答和停止操作只改变当前页面状态，不实现 Fetch 或 SSE。"
    >
      <template #actions>
        <RouterLink class="secondary-button" to="/conversations">
          查看历史会话
        </RouterLink>
      </template>
    </PageHeader>

    <ResourcePanel title="会话内容" description="引用内容来自固定本地样例。">
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
      </template>

      <InlineState
        v-if="isMissingConversation"
        kind="error"
        title="未找到这条会话"
        description="请从历史会话重新进入；当前页面不会请求或猜测其他会话内容。"
      />

      <template v-else>
        <div class="message-thread" aria-live="polite">
          <template v-if="conversation">
            <article class="message user-message">
              <span class="message-avatar" aria-hidden="true">李</span>
              <div>
                <strong>你</strong>
                <p>发布前需要检查哪些内容？</p>
              </div>
            </article>
            <article class="message assistant-message">
              <span class="message-avatar" aria-hidden="true">
                <MessageSquareText :size="18" />
              </span>
              <div>
                <strong>知识助手</strong>
                <p>
                  发布前建议按质量、数据、运维和沟通四个维度确认，并提前演练可执行的回滚路径。
                </p>
                <RouterLink
                  class="citation-card"
                  to="/knowledge/product-handbook/documents/release-guide?page=8"
                >
                  <span>
                    <strong>统一发布流程与回滚指南</strong>
                    <small>第 8 页 · 96% 相关</small>
                  </span>
                  <ArrowUpRight :size="16" aria-hidden="true" />
                </RouterLink>
              </div>
            </article>
          </template>

          <InlineState
            v-else-if="activeQuestion.length === 0"
            kind="info"
            title="开始一次新会话"
            description="输入问题后手动推进逐段回答，页面不会启动后台计时器。"
          />

          <template v-if="activeQuestion.length > 0">
            <article class="message user-message">
              <span class="message-avatar" aria-hidden="true">李</span>
              <div>
                <strong>你</strong>
                <p>{{ activeQuestion }}</p>
              </div>
            </article>
            <article class="message assistant-message">
              <span class="message-avatar" aria-hidden="true">
                <MessageSquareText :size="18" />
              </span>
              <div>
                <strong>知识助手</strong>
                <p
                  v-for="segment in answerSegments.slice(
                    0,
                    visibleSegmentCount,
                  )"
                  :key="segment"
                >
                  {{ segment }}
                </p>
                <span class="preview-status" :class="previewStatus">
                  {{ previewStatusText }}
                </span>
                <div class="message-actions">
                  <button
                    v-if="previewStatus === 'generating'"
                    class="secondary-button compact"
                    type="button"
                    @click="showNextSegment"
                  >
                    继续展示
                  </button>
                  <button
                    v-if="previewStatus === 'generating'"
                    class="secondary-button compact"
                    type="button"
                    @click="stopPreview"
                  >
                    <X :size="15" aria-hidden="true" />
                    停止生成
                  </button>
                  <button
                    v-else
                    class="secondary-button compact"
                    type="button"
                    @click="retryPreview"
                  >
                    <RefreshCw :size="15" aria-hidden="true" />
                    重新生成
                  </button>
                </div>
              </div>
            </article>
          </template>
        </div>

        <form class="composer" @submit.prevent="startPreview">
          <label for="chat-prompt">继续提问</label>
          <textarea
            id="chat-prompt"
            v-model="prompt"
            rows="3"
            placeholder="输入你想了解的问题"
          />
          <div>
            <span>回答仅用于页面预览，不会发送内容。</span>
            <button
              class="primary-button"
              type="submit"
              :disabled="previewStatus === 'generating'"
            >
              <MessageSquareText :size="17" aria-hidden="true" />
              开始本地预览
            </button>
          </div>
        </form>
      </template>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.local-page,
.message-thread {
  display: grid;
  gap: var(--space-6);
}

.chat-page {
  max-width: 1080px;
  margin: 0 auto;
}

.message {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: var(--space-3);
}

.message-avatar {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--white);
  background: var(--color-primary);
}

.assistant-message .message-avatar {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.message > div {
  min-width: 0;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.user-message > div {
  background: var(--color-surface-subtle);
}

.message strong {
  color: var(--color-text);
  font-size: var(--font-size-13);
}

.message p {
  margin: var(--space-2) 0 0;
  color: var(--color-text-secondary);
}

.citation-card {
  display: flex;
  max-width: 520px;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--blue-100);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--blue-50);
  text-decoration: none;
}

.citation-card span {
  display: grid;
  min-width: 0;
}

.citation-card small {
  margin-top: var(--space-1);
  color: var(--color-text-muted);
}

.preview-status {
  display: inline-flex;
  margin-top: var(--space-3);
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.preview-status.generating {
  color: var(--color-primary);
}

.preview-status.stopped {
  color: var(--color-warning-text);
}

.message-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.composer {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-6);
  padding-top: var(--space-5);
  border-top: 1px solid var(--color-border);
}

.composer label {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.composer textarea {
  width: 100%;
  min-height: 96px;
  resize: vertical;
  padding: var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text);
  background: var(--color-surface);
  font: inherit;
}

.composer textarea:focus-visible {
  outline: 0;
  border-color: var(--color-primary);
  box-shadow: var(--shadow-focus);
}

.composer > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.composer > div > span {
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
}

@media (max-width: 767px) {
  .composer > div {
    display: grid;
  }

  .composer .primary-button {
    width: 100%;
    min-height: 44px;
  }
}
</style>
