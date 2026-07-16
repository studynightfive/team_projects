<script setup lang="ts">
import { App as AntApp } from "ant-design-vue";
import { computed } from "vue";
import { RouterLink } from "vue-router";

import StatCard from "../components/StatCard.vue";
import { BookOpen, FileUp, MessageSquarePlus } from "../components/icons";
import { foundationData, userMetricIcons } from "../data/foundation";
import { localPageData } from "../data/local-pages";

const { message } = AntApp.useApp();

const WEEKDAY_LABELS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 6) return "晚上好";
  if (hour < 9) return "早上好";
  if (hour < 12) return "上午好";
  if (hour < 18) return "下午好";
  return "晚上好";
});

const todayLabel = computed(() => {
  const now = new Date();
  const month = now.getMonth() + 1;
  const day = now.getDate();
  return {
    monthDay: `${month}月${day}日`,
    weekday: WEEKDAY_LABELS[now.getDay()],
  };
});

const showUpcomingNotice = (feature: string): void => {
  void message.info(`${feature}将在对应业务里程碑开放`);
};

const knowledgeRouteByName = new Map(
  localPageData.knowledgeBases.map((item) => [
    item.name,
    `/knowledge/${item.id}`,
  ]),
);
</script>

<template>
  <div class="dashboard-page user-dashboard">
    <header class="dashboard-heading">
      <div>
        <div class="dashboard-heading-greeting">
          <h1>{{ greeting }}，{{ foundationData.userView.profile.name }}</h1>
          <span class="dashboard-heading-date">
            今天是<span class="dashboard-heading-date-accent">{{
              todayLabel.monthDay
            }}</span>
            {{ todayLabel.weekday }}
          </span>
        </div>
        <p>今天有 3 个新文档等你审阅，2 个问题等待你的回答。</p>
      </div>
      <div class="dashboard-heading-actions">
        <RouterLink class="primary-button" to="/chat">
          <MessageSquarePlus :size="17" aria-hidden="true" />
          新建问答
        </RouterLink>
        <button
          class="secondary-button"
          type="button"
          @click="showUpcomingNotice('导入文档')"
        >
          <FileUp :size="17" aria-hidden="true" />
          导入文档
        </button>
      </div>
    </header>

    <section class="stat-grid user-stat-grid" aria-label="工作区指标">
      <StatCard
        v-for="item in foundationData.userView.summary"
        :key="item.label"
        :label="item.label"
        :value="item.value"
        :trend="item.trend"
        :tone="item.tone"
        :icon="userMetricIcons[item.icon]"
      />
    </section>

    <div class="user-content-grid">
      <section
        class="content-card knowledge-card"
        aria-labelledby="knowledge-title"
      >
        <header class="card-heading">
          <h2 id="knowledge-title">最近访问的知识库</h2>
          <RouterLink class="text-button" to="/knowledge">
            查看全部
          </RouterLink>
        </header>
        <div class="knowledge-list">
          <RouterLink
            v-for="collection in foundationData.userView.knowledgeCollections"
            :key="collection.name"
            class="knowledge-row"
            :to="knowledgeRouteByName.get(collection.name) ?? '/knowledge'"
            :title="collection.name"
          >
            <span
              class="collection-icon"
              :class="`tone-${collection.tone}`"
              aria-hidden="true"
            >
              <BookOpen :size="20" :stroke-width="1.8" />
            </span>
            <span class="knowledge-copy">
              <strong>{{ collection.name }}</strong>
              <span class="knowledge-meta">
                <span class="type-badge" :class="`tone-${collection.tone}`">
                  {{ collection.type }}
                </span>
                <span>{{ collection.documents }} 个文档</span>
              </span>
            </span>
            <span class="knowledge-updated">{{ collection.updated }}</span>
          </RouterLink>
        </div>
      </section>

      <section
        class="content-card activity-card"
        aria-labelledby="activity-title"
      >
        <header class="card-heading">
          <h2 id="activity-title">团队动态</h2>
        </header>
        <ul
          v-if="foundationData.userView.teamActivities.length > 0"
          class="activity-list"
        >
          <li
            v-for="activity in foundationData.userView.teamActivities"
            :key="`${activity.name}-${activity.time}`"
          >
            <span
              class="activity-avatar"
              :class="`tone-${activity.tone}`"
              aria-hidden="true"
            >
              {{ activity.initial }}
            </span>
            <p>
              <strong>{{ activity.name }}</strong>
              <span>{{ activity.action }}</span>
              <button
                type="button"
                :title="activity.target"
                @click="showUpcomingNotice(activity.target)"
              >
                {{ activity.target }}
              </button>
            </p>
            <time>{{ activity.time }}</time>
          </li>
        </ul>
        <div v-else class="inline-empty-state">暂无团队动态</div>
        <button
          class="activity-more text-button"
          type="button"
          @click="showUpcomingNotice('更多团队动态')"
        >
          查看更多
        </button>
      </section>
    </div>
  </div>
</template>
