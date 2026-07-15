<script setup lang="ts">
import { foundationData } from "../data/foundation";
</script>

<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">系统概览</div>
      <h1>平台运行概况</h1>
      <p class="muted">用于验证管理壳层与信息密度，不代表真实监控数据。</p>
    </div>
    <button class="button admin-primary" type="button">刷新概览</button>
  </div>

  <section class="summary-grid" aria-label="管理摘要">
    <article
      v-for="item in foundationData.adminView.summary"
      :key="item.label"
      class="summary-card"
    >
      <div class="summary-label">
        {{ item.label }}
      </div>
      <div class="summary-value">
        {{ item.value }}
      </div>
      <div class="summary-note">
        {{ item.note }}
      </div>
    </article>
  </section>

  <div class="workspace-grid">
    <section class="panel" aria-labelledby="queue-title">
      <div class="panel-header">
        <h2 id="queue-title">治理队列</h2>
        <a class="link-action" href="#" @click.prevent>查看任务</a>
      </div>
      <div class="rows">
        <div
          v-for="item in foundationData.adminView.governanceQueue"
          :key="item.name"
          class="data-row"
        >
          <div class="row-title">
            {{ item.name }}
          </div>
          <span class="tag" :class="{ warning: item.status === '待确认' }">
            {{ item.status }}
          </span>
          <div class="row-meta">{{ item.scope }} · {{ item.time }}</div>
        </div>
      </div>
    </section>

    <section class="panel" aria-labelledby="health-title">
      <div class="panel-header">
        <h2 id="health-title">服务状态</h2>
      </div>
      <div class="rows">
        <div
          v-for="item in foundationData.adminView.serviceHealth"
          :key="item.name"
          class="data-row"
        >
          <div class="row-title">
            {{ item.name }}
          </div>
          <span class="tag success">{{ item.status }}</span>
          <div class="row-meta">
            {{ item.detail }}
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
