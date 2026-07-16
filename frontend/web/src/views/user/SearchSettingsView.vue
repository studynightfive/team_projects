<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, reactive, ref } from "vue";

import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { CheckCircle2, RotateCcw, Settings2 } from "../../components/icons";
import { aiSearchMockData } from "../../mocks/ai-search";
import type { SearchMode, SearchScope } from "../../types/ai-search";

type SearchLanguage = "zh-CN" | "en-US";
type CitationStyle = "inline" | "list" | "both";

interface SearchSettingsForm {
  defaultMode: SearchMode;
  defaultScope: SearchScope;
  defaultModelId: string;
  language: SearchLanguage;
  citationStyle: CitationStyle;
  openCitationInSidePanel: boolean;
  showPermissionStatus: boolean;
  showRelevance: boolean;
}

const defaultSettings: SearchSettingsForm = {
  defaultMode: "smart",
  defaultScope: "all",
  defaultModelId: "enterprise-general",
  language: "zh-CN",
  citationStyle: "both",
  openCitationInSidePanel: true,
  showPermissionStatus: true,
  showRelevance: false,
};

const { message } = AntApp.useApp();
const form = reactive<SearchSettingsForm>({ ...defaultSettings });
const savedSettings = ref<SearchSettingsForm>({ ...defaultSettings });
const pendingReset = ref(false);

const hasUnsavedChanges = computed(
  () => JSON.stringify(form) !== JSON.stringify(savedSettings.value),
);

const selectedMode = computed(() =>
  aiSearchMockData.modeOptions.find(
    (option) => option.value === form.defaultMode,
  ),
);
const selectedScope = computed(() =>
  aiSearchMockData.scopeOptions.find(
    (option) => option.value === form.defaultScope,
  ),
);
const selectedModel = computed(() =>
  aiSearchMockData.modelOptions.find(
    (option) => option.value === form.defaultModelId,
  ),
);

const saveSettings = (): void => {
  savedSettings.value = { ...form };
  pendingReset.value = false;
  void message.success("搜索偏好已在当前页面保存，刷新后恢复默认模拟配置");
};

const resetSettings = (): void => {
  Object.assign(form, defaultSettings);
  savedSettings.value = { ...defaultSettings };
  pendingReset.value = false;
  void message.success("已恢复默认搜索偏好，本次调整仅影响当前页面");
};
</script>

<template>
  <div class="business-page search-settings-page">
    <PageHeader
      eyebrow="个性化搜索"
      title="搜索设置"
      description="设置默认检索方式和引用呈现偏好；当前仅用于本地交互验证。"
    >
      <template #actions>
        <span class="local-preview-badge">不会写入服务器</span>
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

    <div v-if="pendingReset" class="reset-confirmation" role="alert">
      <div>
        <strong>确认恢复默认搜索偏好？</strong>
        <p>当前页面的模式、范围、模型、语言和引用设置都会被重置。</p>
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
          @click="resetSettings"
        >
          确认恢复
        </button>
      </div>
    </div>

    <form class="settings-layout" @submit.prevent="saveSettings">
      <div class="settings-main-column">
        <ResourcePanel
          title="默认搜索方式"
          description="新建搜索时会预先使用以下选择，仍可在搜索框中临时修改。"
        >
          <div class="settings-fields">
            <label class="settings-field">
              <span>默认搜索模式</span>
              <select v-model="form.defaultMode">
                <option
                  v-for="option in aiSearchMockData.modeOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
              <small>{{ selectedMode?.description }}</small>
            </label>

            <label class="settings-field">
              <span>默认搜索范围</span>
              <select v-model="form.defaultScope">
                <option
                  v-for="option in aiSearchMockData.scopeOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
              <small>{{ selectedScope?.description }}</small>
            </label>

            <label class="settings-field">
              <span>默认回答模型</span>
              <select v-model="form.defaultModelId">
                <option
                  v-for="option in aiSearchMockData.modelOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
              <small>{{ selectedModel?.description }}</small>
            </label>

            <label class="settings-field">
              <span>回答语言</span>
              <select v-model="form.language">
                <option value="zh-CN">简体中文</option>
                <option value="en-US">英文</option>
              </select>
              <small>只改变回答语言，不改变可检索的数据范围。</small>
            </label>
          </div>
        </ResourcePanel>

        <ResourcePanel
          title="引用偏好"
          description="引用用于核验答案依据，关闭附加信息不会扩大内容权限。"
        >
          <fieldset class="citation-options">
            <legend>默认引用呈现方式</legend>
            <label>
              <input v-model="form.citationStyle" type="radio" value="inline" />
              <div>
                <strong>正文内标记</strong>
                <small>在结论旁显示对应的引用编号。</small>
              </div>
            </label>
            <label>
              <input v-model="form.citationStyle" type="radio" value="list" />
              <div>
                <strong>答案后列表</strong>
                <small>正文保持简洁，在底部集中展示来源。</small>
              </div>
            </label>
            <label>
              <input v-model="form.citationStyle" type="radio" value="both" />
              <div>
                <strong>正文与列表</strong>
                <small>同时保留定位标记和完整来源信息。</small>
              </div>
            </label>
          </fieldset>

          <div class="preference-toggles">
            <label>
              <input v-model="form.openCitationInSidePanel" type="checkbox" />
              <div>
                <strong>在侧栏打开引用</strong>
                <small>减少离开答案上下文的次数。</small>
              </div>
            </label>
            <label>
              <input v-model="form.showPermissionStatus" type="checkbox" />
              <div>
                <strong>显示来源权限状态</strong>
                <small>明确标注可访问和受限来源。</small>
              </div>
            </label>
            <label>
              <input v-model="form.showRelevance" type="checkbox" />
              <div>
                <strong>显示相关度</strong>
                <small>在原始结果中展示本地模拟的匹配分值。</small>
              </div>
            </label>
          </div>
        </ResourcePanel>
      </div>

      <aside class="settings-summary">
        <ResourcePanel
          title="当前偏好摘要"
          description="用于确认本次页面内调整。"
        >
          <dl>
            <div>
              <dt>搜索模式</dt>
              <dd>{{ selectedMode?.label }}</dd>
            </div>
            <div>
              <dt>搜索范围</dt>
              <dd>{{ selectedScope?.label }}</dd>
            </div>
            <div>
              <dt>回答模型</dt>
              <dd>{{ selectedModel?.label }}</dd>
            </div>
            <div>
              <dt>回答语言</dt>
              <dd>{{ form.language === "zh-CN" ? "简体中文" : "英文" }}</dd>
            </div>
            <div>
              <dt>引用呈现</dt>
              <dd>
                {{
                  {
                    inline: "正文内标记",
                    list: "答案后列表",
                    both: "正文与列表",
                  }[form.citationStyle]
                }}
              </dd>
            </div>
          </dl>

          <div class="local-settings-notice">
            <Settings2 :size="18" aria-hidden="true" />
            <p>
              当前设置不读取账号偏好，也不会发送保存请求；刷新页面后恢复固定默认值。
            </p>
          </div>

          <button
            class="primary-button settings-save-button"
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
.search-settings-page,
.settings-main-column {
  display: grid;
  gap: var(--space-5);
}

.reset-confirmation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-8);
  background: var(--color-warning-soft);
}

.reset-confirmation p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}

.reset-confirmation > div:last-child {
  display: flex;
  gap: var(--space-2);
}

.settings-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(300px, 0.6fr);
  gap: var(--space-5);
  align-items: start;
}

.settings-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-5);
}

.settings-field {
  display: grid;
  gap: var(--space-2);
}

.settings-field > span,
.citation-options legend {
  color: var(--color-text);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-medium);
}

.settings-field select {
  width: 100%;
  min-height: 42px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-8);
  color: var(--color-text);
  background: var(--color-surface);
}

.settings-field small,
.citation-options small,
.preference-toggles small {
  color: var(--color-text-muted);
  line-height: 1.5;
}

.citation-options {
  display: grid;
  gap: var(--space-3);
  margin: 0;
  padding: 0 0 var(--space-5);
  border: 0;
  border-bottom: 1px solid var(--color-border);
}

.citation-options legend {
  margin-bottom: var(--space-3);
}

.citation-options label,
.preference-toggles label {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-subtle);
}

.citation-options input,
.preference-toggles input {
  margin-top: 3px;
}

.citation-options label > div,
.preference-toggles label > div {
  display: grid;
  gap: var(--space-1);
}

.citation-options strong,
.preference-toggles strong {
  color: var(--color-text);
  font-weight: var(--font-weight-medium);
}

.preference-toggles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-5);
}

.settings-summary {
  position: sticky;
  top: calc(var(--topbar-height) + var(--space-5));
}

.settings-summary dl {
  display: grid;
  gap: var(--space-3);
  margin: 0;
}

.settings-summary dl div {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: var(--space-3);
}

.settings-summary dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
}

.settings-summary dd {
  margin: 0;
  color: var(--color-text);
  text-align: right;
}

.local-settings-notice {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding: var(--space-3);
  border-radius: var(--radius-8);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.local-settings-notice p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-12);
  line-height: 1.6;
}

.settings-save-button {
  width: 100%;
  min-height: 42px;
  margin-top: var(--space-4);
}

.settings-save-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

@media (max-width: 1180px) {
  .settings-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .settings-summary {
    position: static;
  }
}

@media (max-width: 767px) {
  .settings-field select,
  .settings-save-button {
    min-height: 44px;
  }

  .reset-confirmation,
  .settings-fields,
  .preference-toggles {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
  }

  .reset-confirmation > div:last-child {
    width: 100%;
  }

  .reset-confirmation > div:last-child > * {
    min-height: 44px;
    flex: 1;
  }
}
</style>
