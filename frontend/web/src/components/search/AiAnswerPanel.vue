<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { AiAnswer, CitationSource } from "../../types/ai-search";
import SafeMarkdown from "../common/SafeMarkdown.vue";
import {
  Bookmark,
  CheckCircle2,
  MessageSquareText,
  ThumbsDown,
  ThumbsUp,
  TriangleAlert,
} from "../icons";
import SearchStatusBadge from "./SearchStatusBadge.vue";

const props = defineProps<{
  answer: AiAnswer;
  favorite?: boolean;
}>();

const emit = defineEmits<{
  preview: [citation: CitationSource, trigger: HTMLElement];
  related: [question: string];
  feedback: [value: string];
  "toggle-favorite": [];
}>();

const selectedFeedback = ref("");

const citationNumberById = computed(
  () =>
    new Map(
      props.answer.citations.map((citation, index) => [citation.id, index + 1]),
    ),
);

const submitFeedback = (value: string): void => {
  selectedFeedback.value = value;
  emit("feedback", value);
};

const previewMarkdownCitation = (
  citationId: string,
  trigger: HTMLElement,
): void => {
  const citation = props.answer.citations.find((item) => item.id === citationId);
  if (citation !== undefined) emit("preview", citation, trigger);
};

watch(
  () => props.answer,
  () => {
    selectedFeedback.value = "";
  },
);
</script>

<template>
  <article class="ai-answer-panel" aria-labelledby="ai-answer-title">
    <header class="ai-answer-heading">
      <div>
        <span class="answer-kicker">企业知识智能摘要</span>
        <h2 id="ai-answer-title">{{ answer.title }}</h2>
      </div>
      <div class="answer-heading-actions">
        <SearchStatusBadge :status="answer.status" />
        <button
          class="answer-favorite-button"
          type="button"
          :aria-pressed="favorite"
          @click="emit('toggle-favorite')"
        >
          <Bookmark :size="16" aria-hidden="true" />
          {{ favorite ? "已收藏" : "收藏答案" }}
        </button>
      </div>
    </header>

    <p class="answer-summary">{{ answer.summary }}</p>

    <SafeMarkdown
      :content="answer.markdown"
      :citation-ids="answer.citations.map((citation) => citation.id)"
      @citation="previewMarkdownCitation"
    />

    <section
      class="answer-citation-index"
      aria-labelledby="answer-citation-title"
    >
      <h3 id="answer-citation-title">结论依据</h3>
      <div class="answer-citation-links">
        <button
          v-for="citation in answer.citations"
          :key="citation.id"
          type="button"
          :title="`查看来源：${citation.title}`"
          @click="
            emit('preview', citation, $event.currentTarget as HTMLElement)
          "
        >
          <span>[{{ citationNumberById.get(citation.id) }}]</span>
          {{ citation.title }}
        </button>
      </div>
    </section>

    <aside class="answer-disclaimer">
      <TriangleAlert :size="18" aria-hidden="true" />
      <p>{{ answer.disclaimer }}</p>
    </aside>

    <section class="answer-feedback" aria-labelledby="answer-feedback-title">
      <div>
        <h3 id="answer-feedback-title">这个答案对你有帮助吗？</h3>
        <p aria-live="polite">
          {{
            selectedFeedback
              ? `已记录：${selectedFeedback}`
              : "反馈仅保留在当前本地页面。"
          }}
        </p>
      </div>
      <div class="feedback-actions">
        <button
          type="button"
          :class="{ active: selectedFeedback === '有帮助' }"
          :aria-pressed="selectedFeedback === '有帮助'"
          @click="submitFeedback('有帮助')"
        >
          <ThumbsUp :size="16" aria-hidden="true" />
          有帮助
        </button>
        <button
          type="button"
          :class="{ active: selectedFeedback === '没有帮助' }"
          :aria-pressed="selectedFeedback === '没有帮助'"
          @click="submitFeedback('没有帮助')"
        >
          <ThumbsDown :size="16" aria-hidden="true" />
          没有帮助
        </button>
        <button type="button" @click="submitFeedback('答案不准确')">
          答案不准确
        </button>
        <button type="button" @click="submitFeedback('来源不可靠')">
          来源不可靠
        </button>
        <button type="button" @click="submitFeedback('内容已经过期')">
          内容已经过期
        </button>
      </div>
    </section>

    <section
      class="related-question-list"
      aria-labelledby="related-question-title"
    >
      <header>
        <MessageSquareText :size="18" aria-hidden="true" />
        <h3 id="related-question-title">继续了解</h3>
      </header>
      <button
        v-for="question in answer.relatedQuestions"
        :key="question"
        type="button"
        @click="emit('related', question)"
      >
        <CheckCircle2 :size="16" aria-hidden="true" />
        <span>{{ question }}</span>
      </button>
    </section>
  </article>
</template>

<style scoped>
.ai-answer-panel {
  min-width: 0;
  padding: var(--space-6) clamp(var(--space-4), 3vw, var(--space-8));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.ai-answer-heading,
.answer-heading-actions,
.answer-favorite-button,
.answer-disclaimer,
.answer-feedback,
.feedback-actions,
.related-question-list header,
.related-question-list button {
  display: flex;
  align-items: center;
}

.ai-answer-heading,
.answer-feedback {
  justify-content: space-between;
  gap: var(--space-4);
}

.answer-kicker {
  color: var(--color-primary);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 0.04em;
}

.ai-answer-heading h2 {
  margin: var(--space-2) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-24);
  line-height: 1.35;
}

.answer-heading-actions,
.feedback-actions {
  flex-wrap: wrap;
  gap: var(--space-2);
}

.answer-favorite-button,
.feedback-actions button {
  min-height: 34px;
  gap: var(--space-1);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  font-size: var(--font-size-13);
}

.answer-favorite-button[aria-pressed="true"],
.feedback-actions button.active {
  border-color: var(--blue-300);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.answer-summary {
  margin: var(--space-5) 0 var(--space-6);
  padding: var(--space-4);
  border-left: 3px solid var(--color-primary);
  color: var(--color-text-secondary);
  background: var(--color-primary-soft);
  font-size: var(--font-size-15, 15px);
  line-height: 1.75;
}

.answer-citation-index,
.answer-feedback,
.related-question-list {
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-border);
}

.answer-citation-index h3,
.answer-feedback h3,
.related-question-list h3 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-16);
}

.answer-citation-links {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.answer-citation-links button {
  display: flex;
  min-width: 0;
  min-height: 40px;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: var(--color-surface-subtle);
  text-align: left;
}

.answer-citation-links button span {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.answer-disclaimer {
  gap: var(--space-3);
  margin-top: var(--space-6);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
}

.answer-disclaimer svg {
  flex: 0 0 18px;
  color: var(--color-warning);
}

.answer-disclaimer p,
.answer-feedback p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.related-question-list {
  display: grid;
  gap: var(--space-2);
}

.related-question-list header {
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  color: var(--color-primary);
}

.related-question-list button {
  width: 100%;
  min-height: 44px;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-8);
  color: var(--color-text-secondary);
  background: transparent;
  text-align: left;
}

.related-question-list button svg {
  flex: 0 0 16px;
  color: var(--color-primary);
}

.related-question-list button span {
  flex: 1;
}

@media (max-width: 767px) {
  .ai-answer-panel {
    padding: var(--space-5) var(--space-4);
  }

  .ai-answer-heading,
  .answer-feedback {
    align-items: flex-start;
    flex-direction: column;
  }

  .answer-citation-links {
    grid-template-columns: minmax(0, 1fr);
  }

  .feedback-actions button,
  .answer-favorite-button,
  .answer-citation-links button {
    min-height: 44px;
  }
}
</style>
