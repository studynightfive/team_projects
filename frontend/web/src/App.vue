<script setup lang="ts">
import { storeToRefs } from "pinia";
import {
  App as AntApp,
  ConfigProvider,
  theme as antTheme,
} from "ant-design-vue";
import { computed, onBeforeUnmount } from "vue";

import { useThemeStore } from "./stores/theme";

const themeStore = useThemeStore();
const { resolvedTheme } = storeToRefs(themeStore);

themeStore.startSystemThemeListener();
onBeforeUnmount(themeStore.stopSystemThemeListener);

const themeConfig = computed(() => {
  const dark = resolvedTheme.value === "dark";

  return {
    algorithm: dark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
    token: {
      colorPrimary: dark ? "#60A5FA" : "#2B6CB0",
      colorSuccess: dark ? "#4ADE80" : "#16A34A",
      colorWarning: dark ? "#FBBF24" : "#D97706",
      colorError: dark ? "#F87171" : "#DC2626",
      colorText: dark ? "#F1F5F9" : "#0F172A",
      colorTextSecondary: dark ? "#CBD5E1" : "#64748B",
      colorBorder: dark ? "#334155" : "#E2E8F0",
      colorBgBase: dark ? "#111827" : "#FFFFFF",
      colorBgLayout: dark ? "#0B1120" : "#F8FAFC",
      borderRadius: 8,
      fontFamily:
        '"Inter", -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei UI", "Source Han Sans SC", sans-serif',
    },
  };
});
</script>

<template>
  <ConfigProvider :theme="themeConfig">
    <AntApp>
      <RouterView />
    </AntApp>
  </ConfigProvider>
</template>
