<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, nextTick, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  BookOpenText,
  Bot,
  ChevronRight,
  Clock3,
  MessageSquareText,
  RefreshCw,
  Send,
  Sparkles,
  X,
} from "../../components/icons";
import { localPageData } from "../../data/local-pages";

type PreviewStatus = "idle" | "generating" | "stopped" | "complete";

const route = useRoute();
const { message } = AntApp.useApp();
const prompt = ref("");
const promptInput = ref<HTMLTextAreaElement | null>(null);
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
  return conversation.value?.title ?? "AI 助手";
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
const canSubmit = computed(
  () => prompt.value.trim().length > 0 && previewStatus.value !== "generating",
);

const suggestedPrompts = [
  {
    title: "检查发布准备",
    description: "梳理质量、数据、运维与回滚项",
    prompt: "发布上线前需要检查哪些内容？",
  },
  {
    title: "整理故障复盘",
    description: "归纳影响、根因、改进项和负责人",
    prompt: "帮我整理一次故障复盘应该包含哪些内容？",
  },
  {
    title: "总结项目风险",
    description: "识别进度、依赖与交付风险",
    prompt: "请帮我总结项目当前的主要风险。",
  },
] as const;

const answerSegments = [
  "发布前先确认本次变更范围、责任人和可观察的退出条件。",
  "然后完成类型检查、Lint、测试、生产构建，以及关键桌面和移动视口验证。",
  "涉及数据或服务变更时，还需要确认迁移、健康检查和回滚路径均可执行。",
] as const;

const applySuggestedPrompt = async (value: string): Promise<void> => {
  prompt.value = value;
  await nextTick();
  promptInput.value?.focus();
};

const startPreview = (): void => {
  if (previewStatus.value === "generating") return;

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
      eyebrow="用户工作区 / AI 助手"
      :title="pageTitle"
      description="从企业知识中整理答案并标注引用来源；当前页面使用固定本地样例展示完整问答流程。"
    >
      <template #actions>
        <RouterLink class="secondary-button" to="/conversations">
          <Clock3 :size="17" aria-hidden="true" />
          查看历史会话
        </RouterLink>
      </template>
    </PageHeader>

    <ResourcePanel
      class="chat-panel"
      title="对话窗口"
      description="回答将按段展示，并附带可定位的知识来源。"
    >
      <template #actions>
        <span class="local-preview-badge chat-preview-badge">
          <Sparkles :size="13" aria-hidden="true" />
          本地预览
        </span>
      </template>

      <div v-if="isMissingConversation" class="missing-conversation-state">
        <InlineState
          kind="error"
          title="未找到这条会话"
          description="请从历史会话重新进入；当前页面不会请求或猜测其他会话内容。"
        />
      </div>

      <div v-else class="chat-workspace">
        <div
          class="message-thread"
          :class="{
            'is-empty':
              conversation === undefined && activeQuestion.length === 0,
          }"
          aria-live="polite"
        >
          <template v-if="conversation">
            <article class="message user-message">
              <span class="message-avatar" aria-hidden="true">李</span>
              <div class="message-content">
                <strong class="message-author">你</strong>
                <p>发布前需要检查哪些内容？</p>
              </div>
            </article>
            <article class="message assistant-message">
              <span class="message-avatar" aria-hidden="true">
                <Bot :size="18" />
              </span>
              <div class="message-content">
                <strong class="message-author">知识助手</strong>
                <p>
                  发布前建议按质量、数据、运维和沟通四个维度确认，并提前演练可执行的回滚路径。
                </p>
                <RouterLink
                  class="citation-card"
                  to="/knowledge/product-handbook/documents/release-guide?page=8"
                >
                  <span class="citation-icon" aria-hidden="true">
                    <BookOpenText :size="18" />
                  </span>
                  <span class="citation-copy">
                    <small>引用来源</small>
                    <strong>统一发布流程与回滚指南</strong>
                    <span class="citation-meta">第 8 页 · 96% 相关</span>
                  </span>
                  <ChevronRight
                    class="citation-arrow"
                    :size="17"
                    aria-hidden="true"
                  />
                </RouterLink>
              </div>
            </article>
          </template>

          <section
            v-else-if="activeQuestion.length === 0"
            class="chat-welcome"
            aria-labelledby="chat-welcome-title"
          >
            <span class="chat-welcome-icon" aria-hidden="true">
              <Sparkles :size="25" />
            </span>
            <div class="chat-welcome-copy">
              <span>企业知识助手</span>
              <h2 id="chat-welcome-title">今天想了解什么？</h2>
              <p>描述你的目标，助手会整理关键信息并标注可追溯的知识来源。</p>
            </div>
            <div class="suggested-prompts" aria-label="快捷问题">
              <button
                v-for="suggestion in suggestedPrompts"
                :key="suggestion.title"
                class="suggested-prompt"
                type="button"
                @click="applySuggestedPrompt(suggestion.prompt)"
              >
                <span class="suggested-prompt-icon" aria-hidden="true">
                  <MessageSquareText :size="17" />
                </span>
                <span class="suggested-prompt-copy">
                  <strong>{{ suggestion.title }}</strong>
                  <small>{{ suggestion.description }}</small>
                </span>
                <ChevronRight
                  class="suggested-prompt-arrow"
                  :size="16"
                  aria-hidden="true"
                />
              </button>
            </div>
          </section>

          <template v-if="activeQuestion.length > 0">
            <article class="message user-message">
              <span class="message-avatar" aria-hidden="true">李</span>
              <div class="message-content">
                <strong class="message-author">你</strong>
                <p>{{ activeQuestion }}</p>
              </div>
            </article>
            <article class="message assistant-message">
              <span class="message-avatar" aria-hidden="true">
                <Bot :size="18" />
              </span>
              <div class="message-content">
                <strong class="message-author">知识助手</strong>
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
                  <span class="preview-status-dot" aria-hidden="true" />
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
                    <ChevronRight :size="15" aria-hidden="true" />
                  </button>
                  <button
                    v-if="previewStatus === 'generating'"
                    class="secondary-button compact stop-button"
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
          <div class="composer-heading">
            <div>
              <label for="chat-prompt">继续提问</label>
              <span>问题越具体，回答越容易形成可执行结论。</span>
            </div>
            <span class="keyboard-hint" aria-hidden="true">
              <kbd>Enter</kbd> 发送 · <kbd>Shift + Enter</kbd> 换行
            </span>
          </div>
          <div class="composer-field">
            <textarea
              id="chat-prompt"
              ref="promptInput"
              v-model="prompt"
              rows="3"
              aria-describedby="chat-preview-hint"
              placeholder="输入你想了解的问题，例如：发布上线前需要检查哪些内容？"
              @keydown.enter.exact.prevent="startPreview"
            />
            <div class="composer-toolbar">
              <span id="chat-preview-hint" class="composer-note">
                <Sparkles :size="14" aria-hidden="true" />
                当前为本地预览，不会发送内容。
              </span>
              <button
                class="primary-button composer-submit"
                type="submit"
                :disabled="!canSubmit"
              >
                <Send :size="17" aria-hidden="true" />
                发送问题
              </button>
            </div>
          </div>
        </form>
      </div>
    </ResourcePanel>
  </div>
</template>

<style scoped>
.local-page {
  display: grid;
  gap: var(--space-6);
}

.chat-page {
  max-width: 1120px;
  margin: 0 auto;
}

.chat-panel {
  box-shadow: var(--shadow-lg);
}

.chat-panel :deep(.resource-panel-body) {
  padding: 0;
}

.chat-preview-badge {
  gap: var(--space-1);
  margin-bottom: 0;
}

.missing-conversation-state {
  padding: var(--space-6);
}

.chat-workspace {
  min-width: 0;
}

.message-thread {
  display: grid;
  min-height: 280px;
  gap: var(--space-6);
  padding: var(--space-8);
}

.message-thread.is-empty {
  min-height: 0;
  padding: 0;
}

.chat-welcome {
  display: grid;
  justify-items: center;
  gap: var(--space-4);
  padding: var(--space-10) var(--space-8) var(--space-8);
  text-align: center;
}

.chat-welcome-icon {
  display: grid;
  width: 56px;
  height: 56px;
  place-items: center;
  border: 1px solid var(--blue-100);
  border-radius: var(--radius-16);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: var(--shadow-sm);
}

.chat-welcome-copy {
  max-width: 620px;
}

.chat-welcome-copy > span {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}

.chat-welcome h2 {
  margin: var(--space-1) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-24);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.02em;
}

.chat-welcome p {
  margin: var(--space-2) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-14);
  line-height: var(--line-height-description);
}

.suggested-prompts {
  display: grid;
  width: 100%;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-2);
  text-align: left;
}

.suggested-prompt {
  display: grid;
  min-width: 0;
  min-height: 88px;
  grid-template-columns: 36px minmax(0, 1fr) 16px;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  color: var(--color-text);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  text-align: left;
  transition:
    border-color var(--transition-fast),
    background var(--transition-fast),
    box-shadow var(--transition-fast);
}

.suggested-prompt-icon {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.suggested-prompt-copy {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.suggested-prompt-copy strong {
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-semibold);
}

.suggested-prompt-copy small {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
  line-height: var(--line-height-body);
}

.suggested-prompt-arrow {
  color: var(--color-text-subtle);
}

.message {
  display: grid;
  width: min(88%, 840px);
  grid-template-columns: 36px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-3);
}

.user-message {
  width: min(76%, 720px);
  grid-template-columns: minmax(0, 1fr) 36px;
  justify-self: end;
}

.user-message .message-avatar {
  grid-column: 2;
  grid-row: 1;
}

.user-message .message-content {
  grid-column: 1;
  grid-row: 1;
}

.message-avatar {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: var(--radius-12);
  color: var(--white);
  background: var(--color-primary);
  box-shadow: var(--shadow-sm);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-semibold);
}

.assistant-message .message-avatar {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.message-content {
  min-width: 0;
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-16);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.user-message .message-content {
  border-color: var(--blue-100);
  background: var(--color-primary-soft);
}

.message-author {
  display: block;
  color: var(--color-text);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-semibold);
}

.message p {
  margin: var(--space-2) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-14);
  line-height: var(--line-height-description);
  white-space: pre-wrap;
}

.assistant-message p + p {
  margin-top: var(--space-3);
}

.citation-card {
  display: grid;
  max-width: 560px;
  grid-template-columns: 40px minmax(0, 1fr) 18px;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--blue-100);
  border-radius: var(--radius-12);
  color: var(--color-primary);
  background: var(--blue-50);
  text-decoration: none;
  transition:
    border-color var(--transition-fast),
    background var(--transition-fast),
    box-shadow var(--transition-fast);
}

.citation-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-surface);
}

.citation-copy {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.citation-copy small {
  color: var(--color-primary);
  font-size: var(--font-size-12);
}

.citation-copy strong {
  color: var(--color-text);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-semibold);
}

.citation-meta {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.citation-arrow {
  color: var(--color-text-subtle);
}

.preview-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: var(--space-3);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
}

.preview-status-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-pill);
  background: currentcolor;
}

.preview-status.generating {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.preview-status.stopped {
  color: var(--color-warning-text);
  background: var(--color-warning-soft);
}

.preview-status.complete {
  color: var(--color-success-text);
  background: var(--color-success-soft);
}

.message-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.message-actions .primary-button {
  min-height: 32px;
  padding: 0 var(--space-3);
  font-size: var(--font-size-13);
}

.stop-button {
  border-color: var(--red-100);
  color: var(--color-danger-text);
  background: var(--red-50);
}

.composer {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6) var(--space-6);
  border-top: 1px solid var(--color-border);
  background: var(--color-canvas);
}

.composer-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
}

.composer-heading > div {
  display: grid;
  gap: 2px;
}

.composer label {
  color: var(--color-text);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-semibold);
}

.composer-heading > div > span,
.keyboard-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.keyboard-hint {
  white-space: nowrap;
}

.keyboard-hint kbd {
  padding: 2px var(--space-1);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-4);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  font: inherit;
}

.composer-field {
  overflow: hidden;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-12);
  background: var(--color-surface);
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.composer-field:focus-within {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-focus);
}

.composer textarea {
  display: block;
  width: 100%;
  min-height: 88px;
  resize: none;
  padding: var(--space-4);
  border: 0;
  outline: 0;
  color: var(--color-text);
  background: var(--color-surface);
  font: inherit;
  line-height: var(--line-height-body);
}

.composer textarea::placeholder {
  color: var(--color-text-subtle);
}

.composer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3);
  border-top: 1px solid var(--color-surface-subtle);
}

.composer-note {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-subtle);
  font-size: var(--font-size-12);
}

.composer-submit {
  min-height: 40px;
}

@media (hover: hover) {
  .suggested-prompt:hover {
    border-color: var(--blue-300);
    background: var(--color-primary-soft);
    box-shadow: var(--shadow-md);
  }

  .citation-card:hover {
    border-color: var(--blue-300);
    background: var(--color-surface);
    box-shadow: var(--shadow-sm);
  }

  .stop-button:hover {
    border-color: var(--red-100);
    background: var(--color-danger-soft);
  }
}

@media (max-width: 900px) {
  .suggested-prompts {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .chat-panel :deep(.resource-panel-header) {
    padding-right: var(--space-4);
    padding-left: var(--space-4);
  }

  .message-thread {
    min-height: 240px;
    gap: var(--space-5);
    padding: var(--space-5) var(--space-4);
  }

  .chat-welcome {
    gap: var(--space-3);
    padding: var(--space-8) var(--space-4) var(--space-5);
  }

  .chat-welcome h2 {
    font-size: var(--font-size-20);
  }

  .suggested-prompt {
    min-height: 84px;
  }

  .message,
  .assistant-message {
    width: 100%;
    grid-template-columns: 32px minmax(0, 1fr);
  }

  .user-message {
    width: 100%;
    grid-template-columns: minmax(0, 1fr) 32px;
  }

  .message-avatar {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-8);
  }

  .user-message .message-avatar {
    grid-column: 2;
  }

  .user-message .message-content {
    grid-column: 1;
  }

  .message-content {
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-12);
  }

  .citation-card {
    grid-template-columns: 36px minmax(0, 1fr) 16px;
  }

  .citation-icon {
    width: 36px;
    height: 36px;
  }

  .composer {
    padding: var(--space-4);
  }

  .composer-heading {
    align-items: flex-start;
  }

  .keyboard-hint {
    display: none;
  }

  .composer-toolbar {
    display: grid;
  }

  .composer-note {
    line-height: var(--line-height-body);
  }

  .composer-submit {
    width: 100%;
    min-height: 44px;
  }
}
</style>
