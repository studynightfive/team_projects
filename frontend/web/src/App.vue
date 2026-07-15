<script setup lang="ts">
import { App as AntApp, ConfigProvider } from "ant-design-vue";

const theme = {
  token: {
    colorPrimary: "#2B6CB0",
    colorSuccess: "#16A34A",
    colorWarning: "#D97706",
    colorError: "#DC2626",
    colorText: "#0F172A",
    colorTextSecondary: "#64748B",
    colorBorder: "#E2E8F0",
    colorBgLayout: "#F8FAFC",
    borderRadius: 8,
    fontFamily:
      '"Inter", -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei UI", "Source Han Sans SC", sans-serif',
  },
};
</script>

<template>
  <ConfigProvider :theme="theme">
    <AntApp>
      <RouterView />
    </AntApp>
  </ConfigProvider>
</template>
