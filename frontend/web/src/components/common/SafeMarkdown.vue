<script setup lang="ts">
import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    content: string;
    citationIds?: readonly string[];
  }>(),
  { citationIds: () => [] },
);

const emit = defineEmits<{
  citation: [citationId: string, trigger: HTMLElement];
}>();

const markdown = new MarkdownIt({
  html: false,
  linkify: false,
  typographer: true,
  breaks: false,
});

const defaultLinkOpen =
  markdown.renderer.rules.link_open ??
  ((tokens, index, options, _environment, renderer) =>
    renderer.renderToken(tokens, index, options));

markdown.renderer.rules.link_open = (
  tokens,
  index,
  options,
  environment,
  renderer,
) => {
  tokens[index]?.attrSet("target", "_blank");
  tokens[index]?.attrSet("rel", "noopener noreferrer");
  return defaultLinkOpen(tokens, index, options, environment, renderer);
};

/** 双层关闭原始 HTML 并过滤渲染结果，避免未来 Mock 被误当作可信输入。 */
const addCitationButtons = (sanitized: string): string => {
  if (props.citationIds.length === 0 || typeof document === "undefined") {
    return sanitized;
  }

  const template = document.createElement("template");
  template.innerHTML = sanitized;
  const walker = document.createTreeWalker(
    template.content,
    NodeFilter.SHOW_TEXT,
  );
  const textNodes: Text[] = [];
  let currentNode = walker.nextNode();
  while (currentNode !== null) {
    if (currentNode instanceof Text) textNodes.push(currentNode);
    currentNode = walker.nextNode();
  }

  const markerPattern = /\[(\d+)\]/gu;
  for (const textNode of textNodes) {
    const parentElement = textNode.parentElement;
    if (
      parentElement !== null &&
      parentElement.closest("code, pre, a, button") !== null
    ) {
      continue;
    }

    const matches = [...textNode.data.matchAll(markerPattern)];
    if (matches.length === 0) continue;

    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const match of matches) {
      const marker = match[0];
      const markerStart = match.index;
      const citationIndex = Number(match[1]) - 1;
      if (
        markerStart === undefined ||
        props.citationIds[citationIndex] === undefined
      ) {
        continue;
      }

      fragment.append(textNode.data.slice(cursor, markerStart));
      const button = document.createElement("button");
      button.type = "button";
      button.className = "markdown-citation";
      button.dataset.citationIndex = String(citationIndex);
      button.setAttribute("aria-label", `查看引用 ${citationIndex + 1}`);
      button.textContent = marker;
      fragment.append(button);
      cursor = markerStart + marker.length;
    }
    fragment.append(textNode.data.slice(cursor));
    textNode.replaceWith(fragment);
  }

  return template.innerHTML;
};

const sanitizedHtml = computed(() => {
  const sanitized = DOMPurify.sanitize(markdown.render(props.content), {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["style", "iframe", "object", "embed", "form"],
    FORBID_ATTR: ["style"],
  });
  return addCitationButtons(sanitized);
});

const handleClick = (event: MouseEvent): void => {
  if (!(event.target instanceof Element)) return;
  const trigger = event.target.closest<HTMLElement>(
    "button[data-citation-index]",
  );
  if (trigger === null) return;

  const citationIndex = Number(trigger.dataset.citationIndex);
  const citationId = props.citationIds[citationIndex];
  if (citationId !== undefined) emit("citation", citationId, trigger);
};
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="safe-markdown" @click="handleClick" v-html="sanitizedHtml" />
</template>

<style scoped>
.safe-markdown {
  color: var(--color-text-secondary);
  font-size: var(--font-size-15, 15px);
  line-height: 1.8;
}

.safe-markdown :deep(h2),
.safe-markdown :deep(h3) {
  margin: var(--space-8) 0 var(--space-3);
  color: var(--color-text);
  font-weight: var(--font-weight-semibold);
  line-height: 1.35;
}

.safe-markdown :deep(h2) {
  font-size: var(--font-size-20);
}

.safe-markdown :deep(h3) {
  font-size: var(--font-size-16);
}

.safe-markdown :deep(p),
.safe-markdown :deep(ul),
.safe-markdown :deep(ol),
.safe-markdown :deep(blockquote),
.safe-markdown :deep(table) {
  margin: 0 0 var(--space-4);
}

.safe-markdown :deep(ul),
.safe-markdown :deep(ol) {
  padding-left: var(--space-6);
}

.safe-markdown :deep(li + li) {
  margin-top: var(--space-2);
}

.safe-markdown :deep(strong) {
  color: var(--color-text);
  font-weight: var(--font-weight-semibold);
}

.safe-markdown :deep(a) {
  color: var(--color-primary);
  text-underline-offset: 3px;
}

.safe-markdown :deep(.markdown-citation) {
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  padding: 0 4px;
  border-radius: var(--radius-4);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: 0.85em;
  font-weight: var(--font-weight-semibold);
  vertical-align: baseline;
}

.safe-markdown :deep(blockquote) {
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid var(--color-primary);
  color: var(--color-text-secondary);
  background: var(--color-primary-soft);
}

.safe-markdown :deep(table) {
  display: block;
  width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}

.safe-markdown :deep(th),
.safe-markdown :deep(td) {
  min-width: 120px;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  text-align: left;
}

.safe-markdown :deep(th) {
  color: var(--color-text);
  background: var(--color-table-head);
  font-weight: var(--font-weight-semibold);
}

.safe-markdown :deep(code) {
  padding: 2px var(--space-1);
  border-radius: var(--radius-4);
  background: var(--color-surface-subtle);
  font-family: var(--font-mono);
  font-size: 0.9em;
}

.safe-markdown :deep(pre) {
  padding: var(--space-4);
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.safe-markdown :deep(pre code) {
  padding: 0;
  background: transparent;
}

@media (max-width: 767px) {
  .safe-markdown :deep(.markdown-citation) {
    min-width: 44px;
    min-height: 44px;
    justify-content: center;
  }
}
</style>
