<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, reactive, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { localPageData } from "../../data/local-pages";

type UserItem = (typeof localPageData.users)[number];

const { message, modal } = AntApp.useApp();
const users = ref<UserItem[]>(
  localPageData.users.map((user) => ({ ...user, roles: [...user.roles] })),
);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedUserId = ref<string>();
const isCreating = ref(false);
const editor = reactive({
  name: "",
  email: "",
  department: "",
  role: "普通用户",
});

const selectedUser = computed(() =>
  users.value.find((user) => user.id === selectedUserId.value),
);

const filteredUsers = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return users.value.filter((user) => {
    const matchesQuery =
      keyword.length === 0 ||
      [user.name, user.email, user.department, ...user.roles].some((value) =>
        value.toLowerCase().includes(keyword),
      );
    const matchesStatus =
      statusFilter.value === "全部状态" || user.status === statusFilter.value;
    return matchesQuery && matchesStatus;
  });
});

const statusTone = (status: string): string =>
  ({ 正常: "success", 待激活: "warning", 已停用: "danger" })[status] ??
  "neutral";

const startCreate = (): void => {
  selectedUserId.value = undefined;
  isCreating.value = true;
  Object.assign(editor, {
    name: "",
    email: "",
    department: "",
    role: "普通用户",
  });
};

const startEdit = (id: string): void => {
  const user = users.value.find((item) => item.id === id);
  if (user === undefined) return;

  isCreating.value = false;
  selectedUserId.value = id;
  Object.assign(editor, {
    name: user.name,
    email: user.email,
    department: user.department,
    role: user.roles[0] ?? "普通用户",
  });
};

const closeEditor = (): void => {
  selectedUserId.value = undefined;
  isCreating.value = false;
};

const savePreview = (): void => {
  if (
    editor.name.trim().length === 0 ||
    editor.email.trim().length === 0 ||
    editor.department.trim().length === 0
  ) {
    void message.warning("请填写姓名、邮箱和部门");
    return;
  }

  if (isCreating.value) {
    users.value.unshift({
      id: "user-local-preview-" + String(users.value.length + 1),
      name: editor.name.trim(),
      email: editor.email.trim(),
      department: editor.department.trim(),
      roles: [editor.role],
      status: "待激活",
      lastActive: "尚未登录",
    });
  } else {
    const user = selectedUser.value;
    if (user !== undefined) {
      const remainingRoles = user.roles.slice(1);
      Object.assign(user, {
        name: editor.name.trim(),
        email: editor.email.trim(),
        department: editor.department.trim(),
        roles: Array.from(new Set([editor.role, ...remainingRoles])),
      });
    }
  }

  void message.success("本地预览已更新，刷新页面后恢复固定数据");
  closeEditor();
};

const confirmStatusChange = (id: string): void => {
  const user = users.value.find((item) => item.id === id);
  if (user === undefined) return;

  const nextStatus = user.status === "已停用" ? "正常" : "已停用";
  modal.confirm({
    title: nextStatus === "已停用" ? "停用用户" : "启用用户",
    content: "此操作只更新当前页面的本地预览状态，不会发送请求。",
    okText: "确认本地预览",
    cancelText: "取消",
    onOk: () => {
      user.status = nextStatus;
      void message.success("本地预览状态已更新");
    },
  });
};

const confirmPasswordReset = (name: string): void => {
  modal.confirm({
    title: "重置密码预览",
    content:
      "仅验证确认流程；不会生成、读取、发送或保存任何密码，也不会通知用户。",
    okText: "确认本地预览",
    cancelText: "取消",
    onOk: () => {
      void message.info(name + " 的密码重置流程已完成本地预览");
    },
  });
};
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="身份治理"
      title="用户管理"
      description="查看用户状态、角色与最近活动；所有写操作仅影响当前页面预览。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
        <button class="admin-primary-button" type="button" @click="startCreate">
          新建用户
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="用户列表"
      :description="'当前显示 ' + String(filteredUsers.length) + ' 位演示用户'"
    >
      <div class="filter-bar" aria-label="用户筛选">
        <label>
          <span>搜索用户</span>
          <input
            v-model="query"
            type="search"
            placeholder="姓名、邮箱、部门或角色"
          />
        </label>
        <label>
          <span>账号状态</span>
          <select v-model="statusFilter">
            <option>全部状态</option>
            <option>正常</option>
            <option>待激活</option>
            <option>已停用</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="filteredUsers.length === 0"
        kind="empty"
        title="没有匹配的用户"
        description="请调整关键词或账号状态。"
      />
      <div
        v-else
        class="data-table-scroll"
        tabindex="0"
        aria-label="用户表格，可横向滚动"
      >
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">用户</th>
              <th scope="col">部门</th>
              <th scope="col">角色</th>
              <th scope="col">状态</th>
              <th scope="col">最近活动</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredUsers" :key="user.id">
              <td>
                <strong>{{ user.name }}</strong>
                <small>{{ user.email }}</small>
              </td>
              <td>{{ user.department }}</td>
              <td>{{ user.roles.join("、") }}</td>
              <td>
                <span class="status-chip" :class="statusTone(user.status)">
                  {{ user.status }}
                </span>
              </td>
              <td>{{ user.lastActive }}</td>
              <td>
                <div class="table-actions">
                  <button
                    class="text-button"
                    type="button"
                    @click="startEdit(user.id)"
                  >
                    编辑
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmPasswordReset(user.name)"
                  >
                    重置密码
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmStatusChange(user.id)"
                  >
                    {{ user.status === "已停用" ? "启用" : "停用" }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </ResourcePanel>

    <Drawer
      :open="isCreating || selectedUser !== undefined"
      :title="isCreating ? '新建用户（本地预览）' : '编辑用户（本地预览）'"
      width="420"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form" @submit.prevent="savePreview">
        <label>
          <span>姓名</span>
          <input
            v-model="editor.name"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <label>
          <span>企业邮箱</span>
          <input
            v-model="editor.email"
            type="email"
            autocomplete="off"
            placeholder="name@example.com"
            required
          />
        </label>
        <label>
          <span>部门</span>
          <input
            v-model="editor.department"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <label>
          <span>主要角色</span>
          <select v-model="editor.role">
            <option>平台管理员</option>
            <option>知识库编辑者</option>
            <option>普通用户</option>
          </select>
        </label>
        <p class="preview-note">
          保存只更新当前页面内存；已有附加角色会保留，不创建账号、不发送邀请，也不触发真实权限变更。
        </p>
        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="closeEditor">
            取消
          </button>
          <button class="admin-primary-button" type="submit">
            保存本地预览
          </button>
        </div>
      </form>
    </Drawer>
  </div>
</template>
