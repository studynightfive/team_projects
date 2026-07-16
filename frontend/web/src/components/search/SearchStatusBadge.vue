<script setup lang="ts">
import { computed } from "vue";

import type {
  DataSourceConnectionStatus,
  PermissionStatus,
  ResearchStatus,
  SearchStatus,
  VerifiedStatus,
} from "../../types/ai-search";
import {
  BadgeCheck,
  CheckCircle2,
  CircleDashed,
  CircleX,
  Clock3,
  LoaderCircle,
  LockKeyhole,
  TriangleAlert,
  WifiOff,
} from "../icons";

type BadgeStatus =
  | VerifiedStatus
  | PermissionStatus
  | DataSourceConnectionStatus
  | ResearchStatus
  | SearchStatus;

const props = defineProps<{
  status: BadgeStatus;
  label?: string;
}>();

const statusPresentation = computed(() => {
  const map = {
    verified: { label: "已验证", tone: "success", icon: BadgeCheck },
    pending: { label: "待确认", tone: "warning", icon: Clock3 },
    expired: { label: "已过期", tone: "danger", icon: TriangleAlert },
    restricted: { label: "权限受限", tone: "neutral", icon: LockKeyhole },
    available: { label: "权限正常", tone: "success", icon: CheckCircle2 },
    connected: { label: "已连接", tone: "success", icon: CheckCircle2 },
    syncing: { label: "正在同步", tone: "info", icon: LoaderCircle },
    failed: { label: "同步失败", tone: "danger", icon: CircleX },
    disconnected: { label: "未连接", tone: "neutral", icon: WifiOff },
    "permission-error": {
      label: "权限异常",
      tone: "warning",
      icon: LockKeyhole,
    },
    waiting: { label: "等待执行", tone: "neutral", icon: CircleDashed },
    running: { label: "正在执行", tone: "info", icon: LoaderCircle },
    completed: { label: "已完成", tone: "success", icon: CheckCircle2 },
    idle: { label: "等待搜索", tone: "neutral", icon: CircleDashed },
    searching: { label: "正在检索", tone: "info", icon: LoaderCircle },
    success: { label: "生成完成", tone: "success", icon: CheckCircle2 },
    partial: { label: "部分来源不可用", tone: "warning", icon: TriangleAlert },
    error: { label: "生成失败", tone: "danger", icon: CircleX },
  } as const;

  return map[props.status];
});
</script>

<template>
  <span class="search-status-badge" :class="`tone-${statusPresentation.tone}`">
    <component
      :is="statusPresentation.icon"
      :size="14"
      :class="{
        spinning:
          status === 'syncing' ||
          status === 'running' ||
          status === 'searching',
      }"
      aria-hidden="true"
    />
    {{ label ?? statusPresentation.label }}
  </span>
</template>

<style scoped>
.search-status-badge {
  display: inline-flex;
  min-height: 26px;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-2);
  border-radius: var(--radius-4);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.tone-success {
  color: var(--color-success-text);
  background: var(--color-success-soft);
}

.tone-warning {
  color: var(--color-warning-text);
  background: var(--color-warning-soft);
}

.tone-danger {
  color: var(--color-danger-text);
  background: var(--color-danger-soft);
}

.tone-info {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.tone-neutral {
  color: var(--color-text-muted);
  background: var(--color-surface-subtle);
}

.spinning {
  animation: status-spin 1s linear infinite;
}

@keyframes status-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
