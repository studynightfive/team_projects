<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { nextTick, ref } from "vue";

import {
  BookOpen,
  Building2,
  Database,
  Eye,
  EyeOff,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
} from "../components/icons";
import PlatformLogo from "../components/PlatformLogo.vue";

const { message } = AntApp.useApp();
const account = ref("");
const password = ref("");
const rememberMe = ref(false);
const showPassword = ref(false);
const accountError = ref("");
const passwordError = ref("");
const accountInputRef = ref<HTMLInputElement>();
const passwordInputRef = ref<HTMLInputElement>();

const productValues = [
  {
    title: "AI 智能问答",
    description: "让经验主动找人，快速获得可追溯的企业答案。",
    icon: Sparkles,
  },
  {
    title: "统一知识中枢",
    description: "一个入口汇聚制度、文档、项目资料与团队经验。",
    icon: Database,
  },
  {
    title: "企业级安全",
    description: "权限、审计与数据边界贯穿每一次知识访问。",
    icon: ShieldCheck,
  },
] as const;

const showUpcomingNotice = (feature: string): void => {
  void message.info(`${feature}将在认证里程碑开放`);
};

const submit = async (): Promise<void> => {
  accountError.value =
    account.value.trim() === "" ? "请输入企业邮箱或工号" : "";
  passwordError.value = password.value === "" ? "请输入密码" : "";

  if (accountError.value !== "" || passwordError.value !== "") {
    await nextTick();
    if (accountError.value !== "") accountInputRef.value?.focus();
    else passwordInputRef.value?.focus();
    return;
  }

  void message.info("当前仅验证界面交互，认证接口将在 M02 里程碑接入");
};
</script>

<template>
  <main class="login-page-v2">
    <section class="login-brand-panel" aria-labelledby="login-brand-title">
      <PlatformLogo inverse />

      <div class="login-brand-content">
        <p class="login-brand-kicker">企业知识基础设施</p>
        <h1 id="login-brand-title">
          <span>让组织的知识，</span><br />
          <span>活在每一次决策里</span>
        </h1>
        <div class="login-value-list">
          <article v-for="item in productValues" :key="item.title">
            <span class="login-value-icon" aria-hidden="true">
              <component :is="item.icon" :size="22" :stroke-width="1.7" />
            </span>
            <div>
              <h2>{{ item.title }}</h2>
              <p>{{ item.description }}</p>
            </div>
          </article>
        </div>
      </div>

      <footer class="login-brand-footer">
        <span>2026 © 企业名称</span>
        <span>ICP备案号占位</span>
        <span>界面模板 v2.0.0</span>
      </footer>
    </section>

    <section class="login-form-panel" aria-labelledby="login-title">
      <div class="login-form-container">
        <header class="login-form-heading">
          <span class="mobile-login-mark" aria-hidden="true">
            <BookOpen :size="20" />
          </span>
          <h2 id="login-title">欢迎回到工作台</h2>
          <p>请使用企业账号登录</p>
        </header>

        <form novalidate @submit.prevent="submit">
          <div class="form-field">
            <label for="account">账号</label>
            <input
              id="account"
              ref="accountInputRef"
              v-model="account"
              type="text"
              name="account"
              autocomplete="username"
              placeholder="请输入企业邮箱或工号"
              :aria-invalid="accountError !== ''"
              :aria-describedby="
                accountError === '' ? undefined : 'account-error'
              "
              @input="accountError = ''"
            />
            <p
              v-if="accountError !== ''"
              id="account-error"
              class="field-error"
            >
              {{ accountError }}
            </p>
          </div>

          <div class="form-field password-field">
            <div class="field-label-row">
              <label for="password">密码</label>
              <button
                class="text-button"
                type="button"
                @click="showUpcomingNotice('找回密码')"
              >
                忘记密码？
              </button>
            </div>
            <div class="password-input-wrap">
              <input
                id="password"
                ref="passwordInputRef"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                name="password"
                autocomplete="current-password"
                placeholder="请输入密码"
                :aria-invalid="passwordError !== ''"
                :aria-describedby="
                  passwordError === '' ? undefined : 'password-error'
                "
                @input="passwordError = ''"
              />
              <button
                class="password-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                <component
                  :is="showPassword ? EyeOff : Eye"
                  :size="17"
                  aria-hidden="true"
                />
              </button>
            </div>
            <p
              v-if="passwordError !== ''"
              id="password-error"
              class="field-error"
            >
              {{ passwordError }}
            </p>
          </div>

          <div class="login-assist-row">
            <label class="checkbox-label">
              <input v-model="rememberMe" type="checkbox" />
              <span>记住我</span>
            </label>
            <button
              class="text-button"
              type="button"
              @click="showUpcomingNotice('企业 SSO 登录')"
            >
              企业 SSO 登录
            </button>
          </div>

          <button class="primary-button login-submit-button" type="submit">
            进入工作区
          </button>
        </form>

        <div class="alternative-login" aria-label="其他登录方式">
          <div class="alternative-divider">
            <span>其他登录方式</span>
          </div>
          <div class="alternative-buttons">
            <button
              type="button"
              aria-label="企业微信登录"
              title="企业微信登录"
              @click="showUpcomingNotice('企业微信登录')"
            >
              <MessageSquareText :size="18" aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="钉钉登录"
              title="钉钉登录"
              @click="showUpcomingNotice('钉钉登录')"
            >
              <Building2 :size="18" aria-hidden="true" />
            </button>
            <button
              type="button"
              aria-label="飞书登录"
              title="飞书登录"
              @click="showUpcomingNotice('飞书登录')"
            >
              <Sparkles :size="18" aria-hidden="true" />
            </button>
          </div>
        </div>

        <p class="login-legal">
          登录即代表您同意
          <button type="button" @click="showUpcomingNotice('用户协议')">
            《用户协议》
          </button>
          和
          <button type="button" @click="showUpcomingNotice('隐私政策')">
            《隐私政策》
          </button>
        </p>
      </div>
    </section>
  </main>
</template>
