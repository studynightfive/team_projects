<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, reactive, ref } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import {
  createAdminUser,
  listAdminRoles,
  listAdminUsers,
  resetAdminUserPassword,
  updateAdminUser,
  type AdminRole,
  type AdminUser,
} from "../../services/admin";

const { message, modal } = AntApp.useApp();
const users = ref<readonly AdminUser[]>([]);
const roles = ref<readonly AdminRole[]>([]);
const query = ref("");
const statusFilter = ref("全部状态");
const selectedUserId = ref<string>();
const isCreating = ref(false);
const loading = ref(false);
const saving = ref(false);
const editor = reactive({
  username: "",
  displayName: "",
  password: "1234567",
  roleId: "",
});

const selectedUser = computed(() =>
  users.value.find((user) => user.id === selectedUserId.value),
);

const filteredUsers = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return users.value.filter((user) => {
    const matchesQuery =
      keyword.length === 0 ||
      [
        user.username,
        user.display_name,
        ...user.roles.map((role) => role.name),
      ].some((value) => value.toLowerCase().includes(keyword));
    const label = statusLabel(user.status);
    return (
      matchesQuery &&
      (statusFilter.value === "全部状态" || label === statusFilter.value)
    );
  });
});

const statusLabel = (status: string): string =>
  status === "active" ? "正常" : "已停用";

const statusTone = (status: string): string =>
  status === "active" ? "success" : "danger";

const formatDate = (value: string | null): string =>
  value === null ? "尚未登录" : new Date(value).toLocaleString("zh-CN");

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const [userPage, rolePage] = await Promise.all([
      listAdminUsers(),
      listAdminRoles(),
    ]);
    users.value = userPage.items;
    roles.value = rolePage.items;
    if (editor.roleId === "" && rolePage.items.length > 0) {
      editor.roleId = rolePage.items[0]?.id ?? "";
    }
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

const startCreate = (): void => {
  selectedUserId.value = undefined;
  isCreating.value = true;
  Object.assign(editor, {
    username: "",
    displayName: "",
    password: "1234567",
    roleId:
      roles.value.find((role) => role.name === "普通用户")?.id ??
      roles.value[0]?.id ??
      "",
  });
};

const startEdit = (id: string): void => {
  const user = users.value.find((item) => item.id === id);
  if (user === undefined) return;

  isCreating.value = false;
  selectedUserId.value = id;
  Object.assign(editor, {
    username: user.username,
    displayName: user.display_name,
    password: "1234567",
    roleId: user.roles[0]?.id ?? roles.value[0]?.id ?? "",
  });
};

const closeEditor = (): void => {
  selectedUserId.value = undefined;
  isCreating.value = false;
};

const saveUser = async (): Promise<void> => {
  if (editor.roleId === "") {
    message.warning("请选择角色");
    return;
  }
  if (isCreating.value && editor.displayName.trim() === "") {
    message.warning("请填写姓名");
    return;
  }
  if (isCreating.value && editor.username.trim() === "") {
    message.warning("请填写账号 ID");
    return;
  }
  if (isCreating.value && editor.password.length < 7) {
    message.warning("密码至少 7 位");
    return;
  }

  saving.value = true;
  try {
    if (isCreating.value) {
      await createAdminUser({
        username: editor.username.trim(),
        display_name: editor.displayName.trim(),
        password: editor.password,
        role_ids: [editor.roleId],
      });
      message.success("用户已创建");
    } else if (selectedUser.value !== undefined) {
      await updateAdminUser(selectedUser.value.id, {
        role_ids: [editor.roleId],
      });
      message.success("用户角色已保存");
    }
    closeEditor();
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    saving.value = false;
  }
};

const confirmStatusChange = (user: AdminUser): void => {
  const nextStatus = user.status === "active" ? "disabled" : "active";
  modal.confirm({
    title: nextStatus === "disabled" ? "停用用户" : "启用用户",
    content: `确认${nextStatus === "disabled" ? "停用" : "启用"}账号 ${user.username}？`,
    okText: "确认",
    cancelText: "取消",
    onOk: async () => {
      await updateAdminUser(user.id, { status: nextStatus });
      message.success("账号状态已更新");
      await loadData();
    },
  });
};

const confirmPasswordReset = (user: AdminUser): void => {
  modal.confirm({
    title: "重置密码",
    content: `将 ${user.username} 的密码重置为演示密码 1234567。`,
    okText: "确认重置",
    cancelText: "取消",
    onOk: async () => {
      await resetAdminUserPassword(user.id, "1234567");
      message.success("密码已重置");
    },
  });
};

onMounted(loadData);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="身份治理"
      title="用户管理"
      description="管理真实用户账号、状态和角色；注册页创建的账号会出现在这里。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
        <button class="admin-primary-button" type="button" @click="startCreate">
          新建用户
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="用户列表"
      :description="'当前显示 ' + String(filteredUsers.length) + ' 位用户'"
    >
      <div class="filter-bar" aria-label="用户筛选">
        <label>
          <span>搜索用户</span>
          <input
            v-model="query"
            type="search"
            placeholder="账号 ID、姓名或角色"
          />
        </label>
        <label>
          <span>账号状态</span>
          <select v-model="statusFilter">
            <option>全部状态</option>
            <option>正常</option>
            <option>已停用</option>
          </select>
        </label>
      </div>

      <InlineState
        v-if="loading"
        kind="loading"
        title="正在加载用户"
        description="请稍候。"
      />
      <InlineState
        v-else-if="filteredUsers.length === 0"
        kind="empty"
        title="没有匹配的用户"
        description="请调整关键词或账号状态。"
      />
      <div v-else class="data-table-scroll" tabindex="0">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">用户</th>
              <th scope="col">角色</th>
              <th scope="col">状态</th>
              <th scope="col">最近登录</th>
              <th scope="col">创建时间</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredUsers" :key="user.id">
              <td>
                <strong>{{ user.display_name }}</strong>
                <small>{{ user.username }}</small>
              </td>
              <td>{{ user.roles.map((role) => role.name).join("、") }}</td>
              <td>
                <span class="status-chip" :class="statusTone(user.status)">
                  {{ statusLabel(user.status) }}
                </span>
              </td>
              <td>{{ formatDate(user.last_login_at) }}</td>
              <td>{{ formatDate(user.created_at) }}</td>
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
                    @click="confirmPasswordReset(user)"
                  >
                    重置密码
                  </button>
                  <button
                    class="text-button"
                    type="button"
                    @click="confirmStatusChange(user)"
                  >
                    {{ user.status === "active" ? "停用" : "启用" }}
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
      :title="isCreating ? '新建用户' : '编辑用户'"
      width="420"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form" @submit.prevent="saveUser">
        <label v-if="isCreating">
          <span>账号 ID</span>
          <input
            v-model="editor.username"
            type="text"
            autocomplete="off"
            :disabled="!isCreating"
            required
          />
        </label>
        <label v-if="isCreating">
          <span>姓名</span>
          <input
            v-model="editor.displayName"
            type="text"
            autocomplete="off"
            required
          />
        </label>
        <div v-else class="preview-note" role="note">
          <strong>{{ selectedUser?.display_name }}</strong>
          <span>{{ selectedUser?.username }}</span>
          <p>账号 ID 与姓名由用户注册或身份源维护，管理员这里只调整角色。</p>
        </div>
        <label v-if="isCreating">
          <span>初始密码</span>
          <input
            v-model="editor.password"
            type="password"
            autocomplete="new-password"
            required
          />
        </label>
        <label>
          <span>角色</span>
          <select v-model="editor.roleId" required>
            <option v-for="role in roles" :key="role.id" :value="role.id">
              {{ role.name }}
            </option>
          </select>
        </label>
        <p class="preview-note">
          {{
            isCreating
              ? "保存会写入真实后端；账号 ID 由后端唯一约束兜底，不能重复。"
              : "保存只会更新该用户的角色，不修改账号 ID 或姓名。"
          }}
        </p>
        <div class="drawer-actions">
          <button class="secondary-button" type="button" @click="closeEditor">
            取消
          </button>
          <button class="admin-primary-button" type="submit" :disabled="saving">
            {{ saving ? "保存中" : "保存" }}
          </button>
        </div>
      </form>
    </Drawer>
  </div>
</template>
