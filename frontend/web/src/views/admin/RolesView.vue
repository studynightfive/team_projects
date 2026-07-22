<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, onMounted, reactive, ref } from "vue";

import { toPublicApiError } from "../../api/client";
import InlineState from "../../components/InlineState.vue";
import ListPagination from "../../components/ListPagination.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { useListPagination } from "../../composables/useListPagination";
import {
  createAdminRole,
  getAdminRole,
  listAdminRoles,
  listAdminUsers,
  listPermissions,
  setAdminRolePermissions,
  updateAdminRole,
  type AdminRole,
  type PermissionItem,
} from "../../services/admin";

const { message } = AntApp.useApp();
const roles = ref<readonly AdminRole[]>([]);
const permissions = ref<readonly PermissionItem[]>([]);
const roleMemberCounts = ref<Readonly<Record<string, number>>>({});
const query = ref("");
const selectedRoleId = ref<string>();
const isCreating = ref(false);
const selectedPermissions = ref<string[]>([]);
const loading = ref(false);
const saving = ref(false);
const editor = reactive({
  name: "",
  description: "",
});
const moduleLabels: Readonly<Record<string, string>> = {
  admin: "管理中心",
  chat: "AI 问答",
  retrieval: "知识检索",
  knowledge_base: "知识库",
  document: "文档",
  conversation: "历史会话",
  export: "下载导出",
  favorite: "收藏",
  model: "模型配置",
  retrieval_test: "检索评测",
};

const selectedRole = computed(() =>
  roles.value.find((role) => role.id === selectedRoleId.value),
);

const filteredRoles = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  if (keyword.length === 0) return roles.value;
  return roles.value.filter((role) =>
    [role.name, role.description ?? "", role.status].some((value) =>
      value.toLowerCase().includes(keyword),
    ),
  );
});

const {
  page: rolesPage,
  pageSize: rolesPageSize,
  pagedItems: pagedRoles,
  setPage: setRolesPage,
} = useListPagination(filteredRoles);

const groupedPermissions = computed(() => {
  const groups: Record<string, PermissionItem[]> = {};
  for (const permission of permissions.value) {
    groups[permission.module] = [
      ...(groups[permission.module] ?? []),
      permission,
    ];
  }
  return Object.entries(groups);
});
const selectedPermissionSet = computed(() => new Set(selectedPermissions.value));
const selectedPermissionCount = computed(() => selectedPermissions.value.length);
const totalPermissionCount = computed(() => permissions.value.length);
const moduleLabel = (module: string): string => moduleLabels[module] ?? module;
const moduleSelectedCount = (items: readonly PermissionItem[]): number =>
  items.filter((item) => selectedPermissionSet.value.has(item.id)).length;
const isModuleAllSelected = (items: readonly PermissionItem[]): boolean =>
  items.length > 0 && moduleSelectedCount(items) === items.length;
const toggleModulePermissions = (items: readonly PermissionItem[]): void => {
  const ids = items.map((item) => item.id);
  const current = new Set(selectedPermissions.value);
  if (isModuleAllSelected(items)) {
    for (const id of ids) current.delete(id);
  } else {
    for (const id of ids) current.add(id);
  }
  selectedPermissions.value = [...current];
};

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const [rolePage, permissionItems, userPage] = await Promise.all([
      listAdminRoles(),
      listPermissions(),
      listAdminUsers(),
    ]);
    roles.value = rolePage.items;
    permissions.value = permissionItems;
    const counts: Record<string, number> = {};
    for (const user of userPage.items) {
      for (const role of user.roles) {
        counts[role.id] = (counts[role.id] ?? 0) + 1;
      }
    }
    roleMemberCounts.value = counts;
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    loading.value = false;
  }
};

const startCreate = (): void => {
  selectedRoleId.value = undefined;
  isCreating.value = true;
  selectedPermissions.value = [];
  Object.assign(editor, { name: "", description: "" });
};

const startEdit = async (id: string): Promise<void> => {
  const role = roles.value.find((item) => item.id === id);
  if (role === undefined) return;

  selectedRoleId.value = id;
  isCreating.value = false;
  Object.assign(editor, {
    name: role.name,
    description: role.description ?? "",
  });
  try {
    const detail = await getAdminRole(id);
    selectedPermissions.value = detail.permissions.map(
      (permission) => permission.id,
    );
  } catch (err) {
    message.error(toPublicApiError(err).message);
  }
};

const closeEditor = (): void => {
  selectedRoleId.value = undefined;
  isCreating.value = false;
  selectedPermissions.value = [];
};

const saveRole = async (): Promise<void> => {
  if (editor.name.trim() === "" || editor.description.trim() === "") {
    message.warning("请填写角色名称和说明");
    return;
  }

  saving.value = true;
  try {
    if (isCreating.value) {
      await createAdminRole({
        name: editor.name.trim(),
        description: editor.description.trim(),
        permission_ids: selectedPermissions.value,
      });
      message.success("角色已创建");
    } else if (selectedRole.value !== undefined) {
      await updateAdminRole(selectedRole.value.id, {
        name: editor.name.trim(),
        description: editor.description.trim(),
      });
      await setAdminRolePermissions(
        selectedRole.value.id,
        selectedPermissions.value,
      );
      message.success("角色权限已保存");
    }
    closeEditor();
    await loadData();
  } catch (err) {
    message.error(toPublicApiError(err).message);
  } finally {
    saving.value = false;
  }
};

onMounted(loadData);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="身份治理"
      title="角色管理"
      description="维护真实角色与权限码，用户管理中的角色来源于这里。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
        <button class="admin-primary-button" type="button" @click="startCreate">
          新建角色
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="角色与授权"
      :description="'当前显示 ' + String(filteredRoles.length) + ' 个角色'"
    >
      <div class="filter-bar" aria-label="角色筛选">
        <label>
          <span>搜索角色</span>
          <input
            v-model="query"
            type="search"
            placeholder="角色名称、说明或状态"
          />
        </label>
      </div>

      <InlineState
        v-if="loading"
        kind="loading"
        title="正在加载角色"
        description="请稍候。"
      />
      <InlineState
        v-else-if="filteredRoles.length === 0"
        kind="empty"
        title="没有匹配的角色"
        description="请调整搜索关键词。"
      />
      <div v-else class="role-grid">
        <article v-for="role in pagedRoles" :key="role.id" class="role-card">
          <header>
            <div>
              <h3>{{ role.name }}</h3>
              <p>{{ role.description }}</p>
            </div>
            <span class="status-chip info">
              {{ role.status === "active" ? "启用" : "停用" }}
            </span>
          </header>
          <dl class="role-metrics">
            <div>
              <dt>成员</dt>
              <dd>{{ roleMemberCounts[role.id] ?? 0 }}</dd>
            </div>
            <div>
              <dt>权限项</dt>
              <dd>{{ role.permissions_count }}</dd>
            </div>
          </dl>
          <button
            class="secondary-button"
            type="button"
            @click="startEdit(role.id)"
          >
            编辑授权
          </button>
        </article>
      </div>
      <ListPagination
        v-if="filteredRoles.length > 0"
        :page="rolesPage"
        :page-size="rolesPageSize"
        :total="filteredRoles.length"
        @change="setRolesPage"
      />
    </ResourcePanel>

    <Drawer
      :open="isCreating || selectedRole !== undefined"
      :title="isCreating ? '新建角色' : '角色授权'"
      width="760"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form role-editor-form" @submit.prevent="saveRole">
        <section class="role-editor-hero" aria-label="角色授权摘要">
          <div>
            <span>{{ isCreating ? "新建角色" : selectedRole?.name }}</span>
            <h3>{{ editor.name || "未命名角色" }}</h3>
            <p>{{ editor.description || "填写职责说明后，成员可按该角色获得对应功能权限。" }}</p>
          </div>
          <dl>
            <div>
              <dt>已选权限</dt>
              <dd>{{ selectedPermissionCount }}</dd>
            </div>
            <div>
              <dt>全部权限</dt>
              <dd>{{ totalPermissionCount }}</dd>
            </div>
            <div>
              <dt>关联成员</dt>
              <dd>
                {{
                  selectedRole === undefined
                    ? 0
                    : (roleMemberCounts[selectedRole.id] ?? 0)
                }}
              </dd>
            </div>
          </dl>
        </section>

        <div class="role-editor-fields">
          <label>
            <span>角色名称</span>
            <input
              v-model="editor.name"
              type="text"
              autocomplete="off"
              required
            />
          </label>
          <label>
            <span>职责说明</span>
            <textarea v-model="editor.description" rows="3" required />
          </label>
        </div>

        <fieldset class="permission-groups">
          <legend>功能权限</legend>
          <section
            v-for="[module, items] in groupedPermissions"
            :key="module"
            class="permission-module-card"
          >
            <header>
              <div>
                <h4>{{ moduleLabel(module) }}</h4>
                <p>{{ moduleSelectedCount(items) }} / {{ items.length }} 项已授权</p>
              </div>
              <button
                class="text-button"
                type="button"
                @click="toggleModulePermissions(items)"
              >
                {{ isModuleAllSelected(items) ? "清空本组" : "全选本组" }}
              </button>
            </header>
            <div class="permission-item-grid">
              <label
                v-for="permission in items"
                :key="permission.id"
                class="permission-item"
              >
                <input
                  v-model="selectedPermissions"
                  type="checkbox"
                  :value="permission.id"
                />
                <span>
                  <strong>{{ permission.name }}</strong>
                  <small>{{ permission.code }}</small>
                </span>
              </label>
            </div>
          </section>
        </fieldset>
        <p class="preview-note">
          保存会同步角色基础信息和权限码；权限仍由后端接口最终校验。
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

<style scoped>
.role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}

.role-card {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.role-card header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
}

.role-card h3,
.role-card p {
  margin: 0;
}

.role-card p {
  margin-top: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--font-size-13);
}

.role-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  margin: 0;
}

.role-metrics div {
  padding: var(--space-3);
  border-radius: var(--radius-8);
  background: var(--color-surface-muted);
}

.role-metrics dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.role-metrics dd {
  margin: var(--space-1) 0 0;
  color: var(--color-text);
  font-size: var(--font-size-24);
  font-weight: var(--font-weight-semibold);
}

.role-editor-form {
  gap: var(--space-5);
}

.role-editor-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 0.7fr);
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-muted);
}

.role-editor-hero span,
.role-editor-hero dt,
.permission-module-card p,
.permission-item small {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.role-editor-hero h3 {
  margin: var(--space-1) 0 var(--space-2);
  font-size: var(--font-size-22);
}

.role-editor-hero p {
  margin: 0;
  color: var(--color-text-secondary);
}

.role-editor-hero dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
  margin: 0;
}

.role-editor-hero dl div {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.role-editor-hero dd {
  margin: var(--space-1) 0 0;
  color: var(--color-admin);
  font-size: var(--font-size-24);
  font-weight: var(--font-weight-semibold);
}

.role-editor-fields {
  display: grid;
  grid-template-columns: minmax(180px, 0.7fr) minmax(0, 1.3fr);
  gap: var(--space-4);
}

.permission-groups {
  display: grid;
  max-height: 52vh;
  gap: var(--space-3);
  padding: 0;
  overflow: auto;
  border: 0;
}

.permission-groups h4 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-15);
}

.permission-module-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface);
}

.permission-module-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.permission-module-card p {
  margin: var(--space-1) 0 0;
}

.permission-item-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}

.permission-item {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  align-items: start;
  gap: var(--space-2);
  min-height: 58px;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-8);
  background: var(--color-surface-muted);
}

.permission-item span {
  display: grid;
  min-width: 0;
  gap: var(--space-1);
}

.permission-item strong,
.permission-item small {
  overflow-wrap: anywhere;
}

@media (max-width: 1180px) {
  .role-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .role-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .role-editor-hero,
  .role-editor-fields,
  .permission-item-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .role-editor-hero dl {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
