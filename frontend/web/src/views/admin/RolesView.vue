<script setup lang="ts">
import { App as AntApp, Drawer } from "ant-design-vue";
import { computed, reactive, ref } from "vue";

import InlineState from "../../components/InlineState.vue";
import PageHeader from "../../components/PageHeader.vue";
import ResourcePanel from "../../components/ResourcePanel.vue";
import { localPageData } from "../../data/local-pages";

type RoleItem = (typeof localPageData.roles)[number];

const availablePermissions = [
  "浏览授权知识库",
  "预览授权文档",
  "执行知识检索",
  "发起智能问答",
  "创建导出任务",
  "上传文档",
  "维护文档",
  "维护知识库与文档",
  "查看管理中心",
  "管理用户",
  "分配角色",
  "维护角色",
  "配置模型",
  "查看处理任务",
  "重试失败任务",
  "执行命中率测试",
  "查看审计日志",
  "维护平台治理设置",
] as const;

const { message } = AntApp.useApp();
const roles = ref<RoleItem[]>(localPageData.roles.map((role) => ({ ...role })));
const query = ref("");
const selectedRoleId = ref<string>();
const isCreating = ref(false);
const selectedPermissions = ref<string[]>([]);
const editor = reactive({
  name: "",
  description: "",
  scope: "按数据权限",
});

const selectedRole = computed(() =>
  roles.value.find((role) => role.id === selectedRoleId.value),
);

const filteredRoles = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  if (keyword.length === 0) return roles.value;
  return roles.value.filter((role) =>
    [role.name, role.description, role.scope].some((value) =>
      value.toLowerCase().includes(keyword),
    ),
  );
});

const startCreate = (): void => {
  selectedRoleId.value = undefined;
  isCreating.value = true;
  selectedPermissions.value = [];
  Object.assign(editor, {
    name: "",
    description: "",
    scope: "按数据权限",
  });
};

const startEdit = (id: string): void => {
  const role = roles.value.find((item) => item.id === id);
  if (role === undefined) return;

  selectedRoleId.value = id;
  isCreating.value = false;
  selectedPermissions.value = availablePermissions.slice(
    0,
    Math.min(role.permissions, availablePermissions.length),
  );
  Object.assign(editor, {
    name: role.name,
    description: role.description,
    scope: role.scope,
  });
};

const closeEditor = (): void => {
  selectedRoleId.value = undefined;
  isCreating.value = false;
  selectedPermissions.value = [];
};

const savePreview = (): void => {
  if (
    editor.name.trim().length === 0 ||
    editor.description.trim().length === 0
  ) {
    void message.warning("请填写角色名称和说明");
    return;
  }

  if (isCreating.value) {
    roles.value.push({
      id: "role-local-preview-" + String(roles.value.length + 1),
      name: editor.name.trim(),
      description: editor.description.trim(),
      members: 0,
      permissions: selectedPermissions.value.length,
      scope: editor.scope,
    });
  } else {
    const role = selectedRole.value;
    if (role !== undefined) {
      Object.assign(role, {
        name: editor.name.trim(),
        description: editor.description.trim(),
        permissions: selectedPermissions.value.length,
        scope: editor.scope,
      });
    }
  }

  void message.success("角色与授权已更新为本地预览状态");
  closeEditor();
};
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="身份治理"
      title="角色管理"
      description="预览角色职责、成员规模、功能权限和知识库授权范围。"
    >
      <template #actions>
        <span class="local-preview-badge">本地预览</span>
        <button class="admin-primary-button" type="button" @click="startCreate">
          新建角色
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="角色与授权"
      description="权限名称仅用于界面信息架构，不代表后端权限码。"
    >
      <div class="filter-bar" aria-label="角色筛选">
        <label>
          <span>搜索角色</span>
          <input
            v-model="query"
            type="search"
            placeholder="角色名称、说明或授权范围"
          />
        </label>
      </div>

      <InlineState
        v-if="filteredRoles.length === 0"
        kind="empty"
        title="没有匹配的角色"
        description="请调整搜索关键词。"
      />
      <div v-else class="role-grid">
        <article v-for="role in filteredRoles" :key="role.id" class="role-card">
          <header>
            <div>
              <h3>{{ role.name }}</h3>
              <p>{{ role.description }}</p>
            </div>
            <span class="status-chip info">{{ role.scope }}</span>
          </header>
          <dl class="role-metrics">
            <div>
              <dt>成员</dt>
              <dd>{{ role.members }}</dd>
            </div>
            <div>
              <dt>权限项</dt>
              <dd>{{ role.permissions }}</dd>
            </div>
          </dl>
          <button
            class="secondary-button"
            type="button"
            @click="startEdit(role.id)"
          >
            编辑授权预览
          </button>
        </article>
      </div>
    </ResourcePanel>

    <Drawer
      :open="isCreating || selectedRole !== undefined"
      :title="isCreating ? '新建角色（本地预览）' : '角色授权（本地预览）'"
      width="460"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form" @submit.prevent="savePreview">
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
        <label>
          <span>知识库授权范围</span>
          <select v-model="editor.scope">
            <option>全部知识库</option>
            <option>指定知识库</option>
            <option>按数据权限</option>
          </select>
        </label>
        <fieldset class="checkbox-list">
          <legend>功能权限预览</legend>
          <label v-for="permission in availablePermissions" :key="permission">
            <input
              v-model="selectedPermissions"
              type="checkbox"
              :value="permission"
            />
            <span>{{ permission }}</span>
          </label>
        </fieldset>
        <p class="preview-note">
          18
          项固定能力只用于无损验证本地选择，不生成权限码，也不会同步角色、成员或知识库授权。
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
  border-radius: var(--radius-12);
  background: var(--color-surface);
}

.role-card header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.role-card h3 {
  margin: 0;
  font-size: var(--font-size-16);
}

.role-card p {
  margin: var(--space-2) 0 0;
  color: var(--color-text-muted);
  font-size: var(--font-size-13);
}

.role-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}

.role-metrics div {
  display: grid;
  gap: var(--space-1);
}

.role-metrics dt {
  color: var(--color-text-muted);
  font-size: var(--font-size-12);
}

.role-metrics dd {
  margin: 0;
  font-size: var(--font-size-20);
  font-weight: var(--font-weight-semibold);
}

@media (max-width: 1180px) {
  .role-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
