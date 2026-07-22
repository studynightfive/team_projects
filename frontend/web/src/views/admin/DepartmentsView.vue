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
  createDepartment,
  listAdminUsers,
  listDepartments,
  updateDepartment,
  type AdminUser,
  type DepartmentRecord,
} from "../../services/admin";

const { message } = AntApp.useApp();
const departments = ref<readonly DepartmentRecord[]>([]);
const users = ref<readonly AdminUser[]>([]);
const loading = ref(false);
const saving = ref(false);
const selectedId = ref<string>();
const creating = ref(false);
const editor = reactive({ name: "", description: "", adminUserId: "" });

const selectedDepartment = computed(() =>
  departments.value.find((item) => item.id === selectedId.value),
);
const activeUsers = computed(() =>
  users.value.filter((item) => item.status === "active"),
);
const departmentItems = computed(() => departments.value);
const {
  page: departmentsPage,
  pageSize: departmentsPageSize,
  pagedItems: pagedDepartments,
  setPage: setDepartmentsPage,
} = useListPagination(departmentItems);

const loadData = async (): Promise<void> => {
  loading.value = true;
  try {
    const [departmentItems, userPage] = await Promise.all([
      listDepartments(),
      listAdminUsers(),
    ]);
    departments.value = departmentItems;
    users.value = userPage.items;
  } catch (error: unknown) {
    message.error(toPublicApiError(error).message);
  } finally {
    loading.value = false;
  }
};

const startCreate = (): void => {
  creating.value = true;
  selectedId.value = undefined;
  Object.assign(editor, { name: "", description: "", adminUserId: "" });
};

const startEdit = (item: DepartmentRecord): void => {
  creating.value = false;
  selectedId.value = item.id;
  Object.assign(editor, {
    name: item.name,
    description: item.description ?? "",
    adminUserId: item.admin_user_id ?? "",
  });
};

const closeEditor = (): void => {
  creating.value = false;
  selectedId.value = undefined;
};

const saveDepartment = async (): Promise<void> => {
  if (editor.name.trim() === "" || editor.adminUserId === "") {
    message.warning("请填写部门名称并指定部门管理员");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: editor.name.trim(),
      description: editor.description.trim() || null,
      admin_user_id: editor.adminUserId,
    };
    if (creating.value) {
      await createDepartment(payload);
      message.success("部门已创建");
    } else if (selectedDepartment.value) {
      await updateDepartment(selectedDepartment.value.id, payload);
      message.success("部门配置已保存");
    }
    closeEditor();
    await loadData();
  } catch (error: unknown) {
    message.error(toPublicApiError(error).message);
  } finally {
    saving.value = false;
  }
};

onMounted(loadData);
</script>

<template>
  <div class="business-page dashboard-page admin-local-page">
    <PageHeader
      eyebrow="组织治理"
      title="部门管理"
      description="创建部门、指定部门管理员，并查看部门用户与知识库规模。"
    >
      <template #actions>
        <button class="secondary-button" type="button" @click="loadData">
          刷新
        </button>
        <button class="admin-primary-button" type="button" @click="startCreate">
          新建部门
        </button>
      </template>
    </PageHeader>

    <ResourcePanel
      title="部门清单"
      :description="`当前共有 ${departments.length} 个部门`"
    >
      <InlineState
        v-if="loading"
        kind="loading"
        title="正在加载部门"
        description="请稍候。"
      />
      <InlineState
        v-else-if="departments.length === 0"
        kind="empty"
        title="暂无部门"
        description="创建第一个部门后即可分配用户和知识库。"
      />
      <div v-else class="data-table-scroll" tabindex="0">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">部门</th>
              <th scope="col">部门管理员</th>
              <th scope="col">用户数</th>
              <th scope="col">知识库数</th>
              <th scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pagedDepartments" :key="item.id">
              <td>
                <strong>{{ item.name }}</strong>
                <small>{{ item.description || "暂无说明" }}</small>
              </td>
              <td>
                {{ item.admin_display_name || "待指定" }}
                <small>{{ item.admin_username || "-" }}</small>
              </td>
              <td>{{ item.user_count }}</td>
              <td>{{ item.knowledge_base_count }}</td>
              <td>
                <button class="text-button" type="button" @click="startEdit(item)">
                  编辑
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <ListPagination
        v-if="departments.length > 0"
        :page="departmentsPage"
        :page-size="departmentsPageSize"
        :total="departments.length"
        @change="setDepartmentsPage"
      />
    </ResourcePanel>

    <Drawer
      :open="creating || selectedDepartment !== undefined"
      :title="creating ? '新建部门' : '编辑部门'"
      width="460"
      root-class-name="variant-admin"
      @close="closeEditor"
    >
      <form class="drawer-form" @submit.prevent="saveDepartment">
        <label>
          <span>部门名称</span>
          <input v-model="editor.name" required />
        </label>
        <label>
          <span>部门说明</span>
          <textarea v-model="editor.description" rows="3" />
        </label>
        <label>
          <span>部门管理员</span>
          <select v-model="editor.adminUserId" required>
            <option value="" disabled>请选择启用账号</option>
            <option v-for="user in activeUsers" :key="user.id" :value="user.id">
              {{ user.display_name }}（{{ user.username }}）
            </option>
          </select>
        </label>
        <p class="preview-note">
          保存后，该管理员归属本部门并获得知识库维护能力；已有登录会话会失效。
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
