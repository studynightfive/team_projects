<script setup lang="ts">
import WorkspaceShell from "../components/WorkspaceShell.vue";
import { adminMobileNavigation, adminNavigation } from "../data/foundation";
</script>

<template>
  <WorkspaceShell
    variant="admin"
    area-title="管理中心"
    :navigation="adminNavigation"
    navigation-label="管理中心"
    navigation-aria-label="管理中心主导航"
    :mobile-navigation="adminMobileNavigation"
    identity-name="演示管理员"
    identity-role="design-only 固定状态"
    identity-initial="管"
    :workspace-switch="{
      label: '返回用户工作区',
      mobileLabel: '返回用户工作区',
      to: '/',
    }"
  >
    <RouterView />
  </WorkspaceShell>
</template>
