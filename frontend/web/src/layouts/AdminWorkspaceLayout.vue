<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { ref } from "vue";
import { RouterLink } from "vue-router";

import WorkspaceShell from "../components/WorkspaceShell.vue";
import { Bell, ChevronDown } from "../components/icons";
import {
  adminMobileNavigation,
  adminNavigation,
  foundationData,
} from "../data/foundation";

const { message } = AntApp.useApp();
const environment = ref("演示");

const showNotificationNotice = (): void => {
  void message.info("当前有 6 项治理通知，详细通知中心将在后续里程碑开放");
};

const showAccountNotice = (): void => {
  void message.info("账号菜单将在认证与个人中心里程碑开放");
};
</script>

<template>
  <WorkspaceShell
    variant="admin"
    area-title="管理中心"
    :navigation="adminNavigation"
    navigation-label="管理中心"
    :mobile-navigation="adminMobileNavigation"
    :identity-name="foundationData.adminView.profile.name"
    :identity-role="foundationData.adminView.profile.department"
    :identity-initial="foundationData.adminView.profile.initial"
    :workspace-switch="{
      label: '返回用户工作区',
      mobileLabel: '返回用户工作区',
      to: '/',
    }"
  >
    <template #topbar>
      <div class="topbar-layout admin-topbar-layout">
        <div class="admin-topbar-title">
          <strong>管理中心</strong>
          <span aria-hidden="true">/</span>
          <span>平台总览</span>
        </div>
        <div class="topbar-actions admin-topbar-actions">
          <label class="environment-select">
            <span class="visually-hidden">运行环境</span>
            <select v-model="environment" aria-label="运行环境">
              <option>演示</option>
              <option>生产</option>
            </select>
            <ChevronDown :size="14" aria-hidden="true" />
          </label>
          <button
            class="icon-button notification-button"
            type="button"
            aria-label="查看通知，当前有 6 项待处理"
            @click="showNotificationNotice"
          >
            <Bell :size="20" aria-hidden="true" />
            <span class="notification-dot" aria-hidden="true" />
          </button>
          <button
            class="avatar topbar-avatar admin-avatar"
            type="button"
            :aria-label="`${foundationData.adminView.profile.name}的账号菜单`"
            @click="showAccountNotice"
          >
            {{ foundationData.adminView.profile.initial }}
          </button>
          <RouterLink class="secondary-button compact" to="/">
            返回用户工作区
          </RouterLink>
        </div>
      </div>
    </template>

    <RouterView />
  </WorkspaceShell>
</template>
