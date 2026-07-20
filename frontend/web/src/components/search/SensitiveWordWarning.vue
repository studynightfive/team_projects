<script setup lang="ts">
import { AlertTriangle, ShieldAlert, X } from "../icons";

defineProps<{
  open: boolean;
  reason: string;
  regexMatches: readonly string[];
  bertConfidence: number;
  bertLabel: string;
  verdict: string;
}>();

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="sensitive-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="敏感内容警告"
      @click.self="emit('close')"
      @keydown.escape="emit('close')"
    >
      <div class="sensitive-dialog">
        <header class="sensitive-dialog-header">
          <div class="sensitive-dialog-icon">
            <ShieldAlert :size="28" aria-hidden="true" />
          </div>
          <div class="sensitive-dialog-title-group">
            <h2>内容安全提醒</h2>
            <p>您输入的问题可能包含敏感内容，已被系统拦截</p>
          </div>
          <button
            class="sensitive-dialog-close"
            type="button"
            aria-label="关闭警告"
            @click="emit('close')"
          >
            <X :size="20" aria-hidden="true" />
          </button>
        </header>

        <div class="sensitive-dialog-body">
          <div class="sensitive-info-card">
            <div class="sensitive-info-row">
              <span class="sensitive-info-label">拦截层级</span>
              <span class="sensitive-info-value">
                <span
                  class="sensitive-badge"
                  :class="{
                    'badge-regex': verdict === 'regex',
                    'badge-bert': verdict === 'bert',
                  }"
                >
                  {{ verdict === "regex" ? "Layer 1 · 正则匹配" : "Layer 2 · BERT 语义识别" }}
                </span>
              </span>
            </div>

            <div class="sensitive-info-row">
              <span class="sensitive-info-label">拦截原因</span>
              <span class="sensitive-info-value sensitive-reason">{{ reason }}</span>
            </div>

            <div v-if="regexMatches.length > 0" class="sensitive-info-row">
              <span class="sensitive-info-label">匹配规则</span>
              <ul class="sensitive-matches">
                <li v-for="match in regexMatches" :key="match">
                  <AlertTriangle :size="14" aria-hidden="true" />
                  {{ match }}
                </li>
              </ul>
            </div>

            <div
              v-if="verdict === 'bert' && bertConfidence > 0"
              class="sensitive-info-row"
            >
              <span class="sensitive-info-label">置信度</span>
              <span class="sensitive-info-value">
                {{ (bertConfidence * 100).toFixed(1) }}%
                <span v-if="bertLabel" class="sensitive-bert-label">
                  — {{ bertLabel }}
                </span>
              </span>
            </div>
          </div>

          <p class="sensitive-hint">
            请修改问题内容后重新提交。如果您认为这是误判，请联系系统管理员。
          </p>
        </div>

        <footer class="sensitive-dialog-footer">
          <button
            class="primary-button"
            type="button"
            autofocus
            @click="emit('close')"
          >
            我知道了，修改问题
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.sensitive-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
}

.sensitive-dialog {
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  display: grid;
  gap: 0;
  border-radius: var(--radius-12);
  background: var(--color-surface);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  animation: sensitive-dialog-in 200ms ease-out;
}

@keyframes sensitive-dialog-in {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.sensitive-dialog-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-5) var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.sensitive-dialog-icon {
  display: grid;
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: var(--radius-12);
  color: var(--color-warning-text, #b45309);
  background: var(--amber-50);
}

.sensitive-dialog-title-group {
  flex: 1;
  min-width: 0;
}

.sensitive-dialog-title-group h2 {
  margin: 0;
  font-size: var(--font-size-18);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.sensitive-dialog-title-group p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-14);
  color: var(--color-text-muted);
}

.sensitive-dialog-close {
  display: grid;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-text-muted);
  background: transparent;
  margin-left: var(--space-2);
}

.sensitive-dialog-body {
  padding: var(--space-4) var(--space-5);
  overflow-y: auto;
}

.sensitive-info-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.sensitive-info-row {
  display: grid;
  gap: var(--space-1);
}

.sensitive-info-label {
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.sensitive-info-value {
  font-size: var(--font-size-14);
  color: var(--color-text);
}

.sensitive-badge {
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  padding: 0 var(--space-2);
  border-radius: var(--radius-4);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
}

.badge-regex {
  color: var(--color-warning-text, #b45309);
  background: var(--amber-50);
}

.badge-bert {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.sensitive-reason {
  line-height: 1.5;
}

.sensitive-matches {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: var(--space-1);
}

.sensitive-matches li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-4);
  background: var(--amber-50);
  font-size: var(--font-size-13);
  color: var(--color-warning-text, #b45309);
}

.sensitive-bert-label {
  display: block;
  font-size: var(--font-size-12);
  color: var(--color-text-muted);
  margin-top: var(--space-1);
}

.sensitive-hint {
  margin: var(--space-4) 0 0;
  font-size: var(--font-size-13);
  color: var(--color-text-muted);
  line-height: 1.6;
}

.sensitive-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--color-border);
}

.sensitive-dialog-footer .primary-button {
  min-height: 40px;
  padding: 0 var(--space-5);
  border-radius: var(--radius-8);
  color: var(--white);
  background: var(--color-primary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-14);
}

@media (max-width: 767px) {
  .sensitive-dialog {
    max-width: 100%;
    border-radius: var(--radius-16) var(--radius-16) 0 0;
    align-self: end;
    animation: sensitive-dialog-mobile-in 300ms ease-out;
  }

  @keyframes sensitive-dialog-mobile-in {
    from {
      transform: translateY(100%);
    }
    to {
      transform: translateY(0);
    }
  }

  .sensitive-dialog-footer .primary-button {
    width: 100%;
  }
}
</style>
