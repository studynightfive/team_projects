<script setup lang="ts">
import { foundationData } from "../data/foundation";

const fileType = (fileName: string): string => {
  const extension = fileName.split(".").at(-1);
  return extension?.slice(0, 3).toUpperCase() ?? "FILE";
};
</script>

<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">工作台</div>
      <h1>今天从哪里开始？</h1>
      <p class="muted">查看知识库概况，或继续最近的知识工作。</p>
    </div>
    <button class="button primary" type="button">新建问答</button>
  </div>

  <section class="summary-grid" aria-label="工作区摘要">
    <article
      v-for="item in foundationData.userView.summary"
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
    <section class="panel" aria-labelledby="kb-title">
      <div class="panel-header">
        <h2 id="kb-title">最近知识库</h2>
        <a class="link-action" href="#" @click.prevent>查看全部</a>
      </div>
      <div class="rows">
        <div
          v-for="collection in foundationData.userView.knowledgeCollections"
          :key="collection.name"
          class="data-row"
        >
          <div class="row-title">
            {{ collection.name }}
          </div>
          <span class="tag">{{ collection.type }}</span>
          <div class="row-meta">
            {{ collection.documents }} 个文档 · {{ collection.updated }}
          </div>
        </div>
      </div>
    </section>

    <section class="panel" aria-labelledby="recent-title">
      <div class="panel-header">
        <h2 id="recent-title">最近文档</h2>
      </div>
      <ul class="document-list">
        <li
          v-for="document in foundationData.userView.recentDocuments"
          :key="document.name"
          class="document-item"
        >
          <span class="file-icon" aria-hidden="true">{{
            fileType(document.name)
          }}</span>
          <div class="document-copy">
            <div class="document-name" :title="document.name">
              {{ document.name }}
            </div>
            <div class="document-meta">
              {{ document.context }} · {{ document.updated }}
            </div>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>
