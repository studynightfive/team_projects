<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, reactive, ref } from "vue";

import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  CheckCircle2,
  Monitor,
  Moon,
  RotateCcw,
  Settings2,
  ShieldCheck,
  Sun,
} from "../../components/icons";
import {
  defaultAccountPreferences,
  type AccountPreferences,
  type ContentDensity,
  type DefaultWorkspace,
  type LinkOpenMode,
  type NotificationDigest,
} from "../../data/account-support";
import { type ThemeMode, useThemeStore } from "../../stores/theme";

const themeStore = useThemeStore();
const { mode: themeMode, resolvedTheme } = storeToRefs(themeStore);

const form = reactive<AccountPreferences>({ ...defaultAccountPreferences });
const savedPreferences = ref<AccountPreferences>({
  ...defaultAccountPreferences,
});
const pendingReset = ref(false);
const statusMessage = ref("当前显示固定默认偏好");

const workspaceLabels = {
  "ai-search": "AI 搜索",
  knowledge: "企业知识库",
  assistant: "AI 助手",
} satisfies Record<DefaultWorkspace, string>;
const densityLabels = {
  comfortable: "舒适",
  compact: "紧凑",
} satisfies Record<ContentDensity, string>;
const linkModeLabels = {
  "same-tab": "当前标签页",
  "new-tab": "新标签页",
} satisfies Record<LinkOpenMode, string>;
const digestLabels = {
  realtime: "实时",
  daily: "每日摘要",
  weekly: "每周摘要",
} satisfies Record<NotificationDigest, string>;
const themeLabels = {
  system: "跟随系统",
  light: "浅色",
  dark: "深色",
} satisfies Record<ThemeMode, string>;
const themeOptions = [
  {
    value: "system",
    label: "跟随系统",
    description: "自动匹配设备当前的浅色或深色外观。",
    icon: Monitor,
  },
  {
    value: "light",
    label: "浅色模式",
    description: "使用明亮背景，适合日间与高亮环境。",
    icon: Sun,
  },
  {
    value: "dark",
    label: "深色模式",
    description: "降低大面积背景亮度，适合夜间使用。",
    icon: Moon,
  },
] as const;

const hasUnsavedChanges = computed(
  () => JSON.stringify(form) !== JSON.stringify(savedPreferences.value),
);
const themeSummary = computed(() =>
  themeMode.value === "system"
    ? `${themeLabels.system}（当前${themeLabels[resolvedTheme.value]}）`
    : themeLabels[themeMode.value],
);

const savePreferences = (): void => {
  savedPreferences.value = { ...form };
  pendingReset.value = false;
  statusMessage.value = "偏好已在当前页面保存，刷新后恢复固定默认值";
};

const resetPreferences = (): void => {
  themeStore.resetThemeMode();
  Object.assign(form, defaultAccountPreferences);
  savedPreferences.value = { ...defaultAccountPreferences };
  pendingReset.value = false;
  statusMessage.value = "已恢复默认偏好，本次调整未写入服务器";
};
</script>

<template>
  <div class="business-page preferences-page">
    <PageHeader
      eyebrow="账号与支持"
      title="偏好设置"
      description="调整全局界面主题，以及工作台、内容呈现和通知偏好。"
    >
      <template #actions>
        <span class="local-preview-badge">主题仅保存在当前浏览器</span>
        <button
          class="secondary-button"
          type="button"
          @click="pendingReset = true"
        >
          <RotateCcw :size="16" aria-hidden="true" />
          恢复默认
        </button>
      </template>
    </PageHeader>

    <div v-if="pendingReset" class="preferences-reset" role="alert">
      <div>
        <strong>确认恢复默认偏好？</strong>
        <p>界面主题将跟随系统，其他偏好恢复为固定样例。</p>
      </div>
      <div>
        <button
          class="secondary-button compact"
          type="button"
          @click="pendingReset = false"
        >
          取消
        </button>
        <button
          class="primary-button compact"
          type="button"
          @click="resetPreferences"
        >
          确认恢复
        </button>
      </div>
    </div>

    <form class="preferences-layout" @submit.prevent="savePreferences">
      <div class="preferences-main-column">
        <ResourcePanel
          title="外观与背景"
          description="主题选择会立即应用到用户工作区、管理中心、登录页和错误页。"
        >
          <fieldset class="theme-options">
            <legend class="visually-hidden">界面主题</legend>
            <label
              v-for="option in themeOptions"
              :key="option.value"
              class="theme-option"
              :class="{ selected: themeMode === option.value }"
            >
              <input
                :checked="themeMode === option.value"
                :value="option.value"
                name="theme-mode"
                type="radio"
                @change="themeStore.setThemeMode(option.value)"
              />
              <span class="theme-option-icon">
                <component :is="option.icon" :size="20" aria-hidden="true" />
              </span>
              <span class="theme-option-copy">
                <strong>{{ option.label }}</strong>
                <small>{{ option.description }}</small>
              </span>
            </label>
          </fieldset>
          <p class="theme-storage-note">
            这里只保存主题模式，不保存账号、通知内容或其他业务偏好。
          </p>
        </ResourcePanel>

        <ResourcePanel
          title="工作台体验"
          description="这些选项只展示未来账号偏好的界面与数据结构，不改变当前路由行为。"
        >
          <div class="preference-fields">
            <label>
              <span>默认工作入口</span>
              <select v-model="form.defaultWorkspace">
                <option value="ai-search">AI 搜索</option>
                <option value="knowledge">企业知识库</option>
                <option value="assistant">AI 助手</option>
              </select>
              <small>正式接入后用于登录后的默认落点。</small>
            </label>
            <label>
              <span>内容密度</span>
              <select v-model="form.contentDensity">
                <option value="comfortable">舒适</option>
                <option value="compact">紧凑</option>
              </select>
              <small>当前不会修改现有页面间距。</small>
            </label>
            <label>
              <span>内容链接打开方式</span>
              <select v-model="form.linkOpenMode">
                <option value="same-tab">当前标签页</option>
                <option value="new-tab">新标签页</option>
              </select>
              <small>只针对未来文档与引用链接，不影响导航菜单。</small>
            </label>
            <label>
              <span>通知摘要频率</span>
              <select v-model="form.notificationDigest">
                <option value="realtime">实时</option>
                <option value="daily">每日摘要</option>
                <option value="weekly">每周摘要</option>
              </select>
              <small>当前不会发送邮件或浏览器推送。</small>
            </label>
          </div>
        </ResourcePanel>

        <ResourcePanel
          title="通知偏好"
          description="安全提醒保持启用；其他类型可预览开关状态。"
        >
          <fieldset class="preference-options">
            <legend class="visually-hidden">通知类型</legend>
            <label>
              <input v-model="form.taskNotifications" type="checkbox" />
              <span>
                <strong>任务进度与失败提醒</strong>
                <small>导出、文档处理和研究任务状态变化。</small>
              </span>
            </label>
            <label>
              <input v-model="form.knowledgeNotifications" type="checkbox" />
              <span>
                <strong>知识更新提醒</strong>
                <small>已关注知识库和空间新增或更新内容。</small>
              </span>
            </label>
            <label class="locked-option">
              <input
                :checked="form.securityNotifications"
                type="checkbox"
                disabled
              />
              <span>
                <strong>账号与安全提醒</strong>
                <small>关键安全提醒不可关闭，避免遗漏权限和会话风险。</small>
              </span>
              <ShieldCheck :size="18" aria-hidden="true" />
            </label>
          </fieldset>
        </ResourcePanel>
      </div>

      <aside class="preferences-summary">
        <ResourcePanel
          title="当前偏好摘要"
          description="用于确认本次页面内调整。"
        >
          <dl>
            <div>
              <dt>界面主题</dt>
              <dd>{{ themeSummary }}</dd>
            </div>
            <div>
              <dt>默认入口</dt>
              <dd>{{ workspaceLabels[form.defaultWorkspace] }}</dd>
            </div>
            <div>
              <dt>内容密度</dt>
              <dd>{{ densityLabels[form.contentDensity] }}</dd>
            </div>
            <div>
              <dt>打开方式</dt>
              <dd>{{ linkModeLabels[form.linkOpenMode] }}</dd>
            </div>
            <div>
              <dt>通知摘要</dt>
              <dd>{{ digestLabels[form.notificationDigest] }}</dd>
            </div>
            <div>
              <dt>任务提醒</dt>
              <dd>{{ form.taskNotifications ? "开启" : "关闭" }}</dd>
            </div>
            <div>
              <dt>知识提醒</dt>
              <dd>{{ form.knowledgeNotifications ? "开启" : "关闭" }}</dd>
            </div>
          </dl>

          <div class="preferences-local-note">
            <Settings2 :size="18" aria-hidden="true" />
            <p>
              主题会保存在当前浏览器；其他业务偏好不读取账号数据，刷新后恢复固定默认值。
            </p>
          </div>

          <p class="preference-status" aria-live="polite">
            {{ hasUnsavedChanges ? "有未保存的页面内调整" : statusMessage }}
          </p>
          <button
            class="primary-button preference-save-button"
            type="submit"
            :disabled="!hasUnsavedChanges"
          >
            <CheckCircle2 :size="16" aria-hidden="true" />
            {{ hasUnsavedChanges ? "保存本地偏好" : "偏好已保存" }}
          </button>
        </ResourcePanel>
      </aside>
    </form>
  </div>
</template>

<style scoped>
.preferences-page,
.preferences-main-column {
  gap: var(--space-5);
}

.preferences-reset,
.preferences-reset > div,
.preference-options label,
.preferences-local-note {
  display: flex;
  align-items: center;
}

.preferences-reset {
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-8);
  background: var(--color-warning-soft);
}

.preferences-reset strong {
  color: var(--color-warning-text);
}

.preferences-reset p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}

.preferences-reset > div {
  gap: var(--space-2);
}

.preferences-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
  gap: var(--space-5);
  align-items: start;
}

.preferences-main-column {
  display: grid;
}

.theme-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  border: 0;
}

.theme-option {
  display: grid;
  min-width: 0;
  min-height: 112px;
  grid-template-columns: auto auto minmax(0, 1fr);
  align-items: start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-12);
  background: var(--color-surface);
  cursor: pointer;
  transition:
    border-color var(--transition-fast),
    background var(--transition-fast),
    box-shadow var(--transition-fast);
}

.theme-option:hover {
  border-color: var(--color-border-strong);
}

.theme-option.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.theme-option input {
  width: 18px;
  height: 18px;
  margin: 3px 0 0;
  accent-color: var(--color-primary);
}

.theme-option-icon {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.theme-option.selected .theme-option-icon {
  color: var(--white);
  background: var(--color-primary);
}

.theme-option-copy {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.theme-option-copy strong {
  color: var(--color-text);
  font-size: var(--font-size-14);
}

.theme-option-copy small,
.theme-storage-note {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
  line-height: 1.55;
}

.theme-storage-note {
  margin: var(--space-3) 0 0;
}

.preference-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-5);
}

.preference-fields label {
  display: grid;
  min-width: 0;
  gap: var(--space-2);
}

.preference-fields label > span {
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-medium);
}

.preference-fields select {
  width: 100%;
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text);
  background: var(--color-surface);
}

.preference-fields small,
.preference-options small {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
  line-height: 1.55;
}

.preference-options {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  border: 0;
}

.preference-options label {
  min-height: 68px;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
}

.preference-options input {
  width: 18px;
  height: 18px;
  flex: none;
}

.preference-options label > span {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: var(--space-1);
}

.preference-options strong {
  color: var(--color-text);
  font-size: var(--font-size-14);
}

.locked-option {
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
}

.preferences-summary {
  position: sticky;
  top: calc(var(--topbar-height) + var(--space-5));
}

.preferences-summary dl {
  display: grid;
  gap: var(--space-3);
  margin: 0;
}

.preferences-summary dl div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
}

.preferences-summary dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
}

.preferences-summary dd {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-medium);
  text-align: right;
}

.preferences-local-note {
  align-items: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding: var(--space-3);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.preferences-local-note svg {
  flex: none;
}

.preferences-local-note p,
.preference-status {
  margin: 0;
  font-size: var(--font-size-12);
  line-height: 1.6;
}

.preference-status {
  min-height: 20px;
  margin-top: var(--space-4);
  color: var(--color-text-muted);
}

.preference-save-button {
  width: 100%;
  margin-top: var(--space-3);
}

.preference-save-button:disabled {
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
  cursor: not-allowed;
}

@media (max-width: 1000px) {
  .preferences-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .preferences-summary {
    position: static;
  }
}

@media (max-width: 767px) {
  .preferences-reset,
  .preferences-reset > div {
    align-items: stretch;
    flex-direction: column;
  }

  .preference-fields {
    grid-template-columns: minmax(0, 1fr);
  }

  .theme-options {
    grid-template-columns: minmax(0, 1fr);
  }

  .theme-option {
    min-height: 96px;
  }

  .preference-fields select {
    min-height: 44px;
  }
}
</style>
