<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed, nextTick, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  Award,
  BookOpen,
  Bot,
  Building2,
  Database,
  Eye,
  EyeOff,
  Lock,
  MessageSquareText,
  Network,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from "../components/icons";
import PlatformLogo from "../components/PlatformLogo.vue";
import { toPublicApiError } from "../api/client";
import { useSessionStore } from "../stores/session";
import {
  checkUsernameAvailable,
  loginWithPassword,
  registerAccount,
} from "../services/auth";

const { message } = AntApp.useApp();
const router = useRouter();
const route = useRoute();
const sessionStore = useSessionStore();
const account = ref("");
const password = ref("");
const authMode = ref<"login" | "register">("login");
const registerAccountId = ref("");
const registerName = ref("");
const registerPassword = ref("");
const showPassword = ref(false);
const accountError = ref("");
const registerAccountError = ref("");
const registerNameError = ref("");
const registerPasswordError = ref("");
const loading = ref(false);
const registerLoading = ref(false);
const passwordError = ref("");
const accountInputRef = ref<HTMLInputElement>();
const passwordInputRef = ref<HTMLInputElement>();
const registerAccountInputRef = ref<HTMLInputElement>();
const registerNameInputRef = ref<HTMLInputElement>();
const registerPasswordInputRef = ref<HTMLInputElement>();

const headingTitle = computed(() =>
  authMode.value === "login" ? "欢迎回到工作台" : "创建企业账号",
);
const headingDescription = computed(() =>
  authMode.value === "login"
    ? "请使用企业账号登录"
    : "注册成功后，账号会进入管理中心的用户管理",
);

const redirectTarget = (): string => {
  const redirect = route.query.redirect;
  if (
    typeof redirect === "string" &&
    redirect.startsWith("/") &&
    !redirect.startsWith("/login")
  ) {
    return redirect;
  }
  return "/";
};

const metrics = [
  { value: "检索", label: "关键词与向量", icon: UsersRound },
  { value: "问答", label: "带引用回答", icon: Database },
  { value: "审计", label: "访问留痕", icon: ShieldCheck },
  { value: "导出", label: "多格式任务", icon: Network },
] as const;

const complianceBadges = [
  { label: "HttpOnly 会话", icon: ShieldCheck },
  { label: "细粒度权限", icon: Award },
  { label: "审计日志", icon: Lock },
] as const;

const productValues = [
  {
    title: "AI 智能问答",
    description: "让经验主动找人，快速获得可追溯的企业答案。",
    icon: Bot,
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

  loading.value = true;
  try {
    const user = await loginWithPassword({
      username: account.value.trim(),
      password: password.value,
    });
    sessionStore.setUser(user);
    message.success("登录成功");
    await router.replace(redirectTarget());
  } catch (err) {
    const publicError = toPublicApiError(err);
    message.error(
      publicError.status === 401
        ? "账号或密码错误，请重新尝试"
        : publicError.message,
    );
  } finally {
    loading.value = false;
  }
};

const validateRegisterAccount = async (): Promise<boolean> => {
  const username = registerAccountId.value.trim();
  if (username === "") {
    registerAccountError.value = "请输入账号 ID";
    return false;
  }
  try {
    const available = await checkUsernameAvailable(username);
    registerAccountError.value = available ? "" : "账号 ID 已存在，请更换";
    return available;
  } catch (err) {
    registerAccountError.value = toPublicApiError(err).message;
    return false;
  }
};

const submitRegister = async (): Promise<void> => {
  registerNameError.value =
    registerName.value.trim() === "" ? "请输入姓名或展示名称" : "";
  registerPasswordError.value =
    registerPassword.value.length < 7 ? "密码至少 7 位" : "";
  const accountOk = await validateRegisterAccount();

  if (
    !accountOk ||
    registerNameError.value !== "" ||
    registerPasswordError.value !== ""
  ) {
    await nextTick();
    if (!accountOk) registerAccountInputRef.value?.focus();
    else if (registerNameError.value !== "")
      registerNameInputRef.value?.focus();
    else registerPasswordInputRef.value?.focus();
    return;
  }

  registerLoading.value = true;
  try {
    await registerAccount({
      username: registerAccountId.value.trim(),
      display_name: registerName.value.trim(),
      password: registerPassword.value,
    });
    message.success("注册成功，请使用新账号登录");
    account.value = registerAccountId.value.trim();
    password.value = "";
    authMode.value = "login";
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    registerLoading.value = false;
  }
};
</script>

<template>
  <main class="login-page-v2">
    <section class="login-brand-panel" aria-labelledby="login-brand-title">
      <div class="login-brand-bg" aria-hidden="true">
        <div class="login-brand-glow login-brand-glow-1"></div>
        <div class="login-brand-glow login-brand-glow-2"></div>
        <div class="login-brand-orb">
          <div class="login-brand-orb-ring"></div>
          <div class="login-brand-orb-ring login-brand-orb-ring-2"></div>
          <div class="login-brand-orb-core"></div>
        </div>
      </div>

      <header class="login-brand-top">
        <PlatformLogo inverse />
        <ul class="login-compliance" aria-label="已实现的安全能力">
          <li v-for="badge in complianceBadges" :key="badge.label">
            <component :is="badge.icon" :size="13" :stroke-width="2" />
            <span>{{ badge.label }}</span>
          </li>
        </ul>
      </header>

      <div class="login-brand-content">
        <p class="login-brand-kicker">企业知识基础设施 · AI Native</p>
        <h1 id="login-brand-title">
          <span>让组织的知识，</span><br />
          <span>活在每一次决策里</span>
        </h1>

        <ul class="login-metric-strip" aria-label="平台核心能力">
          <li v-for="metric in metrics" :key="metric.label">
            <span class="login-metric-icon" aria-hidden="true">
              <component :is="metric.icon" :size="16" :stroke-width="1.8" />
            </span>
            <strong class="login-metric-value">{{ metric.value }}</strong>
            <span class="login-metric-label">{{ metric.label }}</span>
          </li>
        </ul>

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
        <span>2026 © 智能知识库平台</span>
        <span>本地与私有化部署</span>
        <span>应用版本 0.1.0</span>
      </footer>
    </section>

    <section class="login-form-panel" aria-labelledby="login-title">
      <div class="login-form-container">
        <header class="login-form-heading">
          <span class="mobile-login-mark" aria-hidden="true">
            <BookOpen :size="20" />
          </span>
          <h2 id="login-title">{{ headingTitle }}</h2>
          <p>{{ headingDescription }}</p>
        </header>

        <div class="auth-mode-switch" aria-label="认证方式">
          <button
            type="button"
            :class="{ active: authMode === 'login' }"
            @click="authMode = 'login'"
          >
            登录
          </button>
          <button
            type="button"
            :class="{ active: authMode === 'register' }"
            @click="authMode = 'register'"
          >
            注册
          </button>
        </div>

        <form v-if="authMode === 'login'" novalidate @submit.prevent="submit">
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
            <span>会话时长由服务端安全策略统一管理</span>
            <button
              class="text-button"
              type="button"
              @click="showUpcomingNotice('企业 SSO 登录')"
            >
              企业 SSO 登录
            </button>
          </div>

          <button
            class="primary-button login-submit-button"
            type="submit"
            :disabled="loading"
          >
            {{ loading ? "正在登录" : "进入工作区" }}
          </button>
        </form>

        <form v-else novalidate @submit.prevent="submitRegister">
          <div class="form-field">
            <label for="register-account">账号 ID</label>
            <input
              id="register-account"
              ref="registerAccountInputRef"
              v-model="registerAccountId"
              type="text"
              autocomplete="username"
              placeholder="例如 liuhaiwang"
              :aria-invalid="registerAccountError !== ''"
              :aria-describedby="
                registerAccountError === ''
                  ? undefined
                  : 'register-account-error'
              "
              @blur="validateRegisterAccount"
              @input="registerAccountError = ''"
            />
            <p
              v-if="registerAccountError !== ''"
              id="register-account-error"
              class="field-error"
            >
              {{ registerAccountError }}
            </p>
          </div>

          <div class="form-field">
            <label for="register-name">姓名</label>
            <input
              id="register-name"
              ref="registerNameInputRef"
              v-model="registerName"
              type="text"
              autocomplete="name"
              placeholder="请输入姓名或展示名称"
              :aria-invalid="registerNameError !== ''"
              :aria-describedby="
                registerNameError === '' ? undefined : 'register-name-error'
              "
              @input="registerNameError = ''"
            />
            <p
              v-if="registerNameError !== ''"
              id="register-name-error"
              class="field-error"
            >
              {{ registerNameError }}
            </p>
          </div>

          <div class="form-field password-field">
            <label for="register-password">密码</label>
            <div class="password-input-wrap">
              <input
                id="register-password"
                ref="registerPasswordInputRef"
                v-model="registerPassword"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="至少 7 位"
                :aria-invalid="registerPasswordError !== ''"
                :aria-describedby="
                  registerPasswordError === ''
                    ? undefined
                    : 'register-password-error'
                "
                @input="registerPasswordError = ''"
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
              v-if="registerPasswordError !== ''"
              id="register-password-error"
              class="field-error"
            >
              {{ registerPasswordError }}
            </p>
          </div>

          <button
            class="primary-button login-submit-button"
            type="submit"
            :disabled="registerLoading"
          >
            {{ registerLoading ? "正在注册" : "创建账号" }}
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
