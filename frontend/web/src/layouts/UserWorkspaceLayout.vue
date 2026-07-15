<script setup lang="ts">
import WorkspaceShell from "../components/WorkspaceShell.vue";
import { userMobileNavigation, userNavigation } from "../data/foundation";
</script>

<template>
  <WorkspaceShell
    variant="user"
    area-title="用户工作区"
    :navigation="userNavigation"
    navigation-label="用户工作区"
    navigation-aria-label="普通用户主导航"
    :mobile-navigation="userMobileNavigation"
    identity-name="演示用户"
    identity-role="design-only 固定状态"
    identity-initial="演"
    :workspace-switch="{
      label: '管理中心',
      mobileLabel: '进入管理中心',
      to: '/admin',
    }"
  >
    <RouterView />
  </WorkspaceShell>
</template>
