<script setup lang="ts">
import { Pagination } from "ant-design-vue";

defineProps<{
  readonly page: number;
  readonly pageSize: number;
  readonly total: number;
}>();

const emit = defineEmits<{
  change: [page: number, pageSize: number];
}>();

const pageSizeOptions = ["10", "20", "50"];
const showTotal = (total: number, range: [number, number]): string =>
  `第 ${range[0]}-${range[1]} 条，共 ${total} 条`;

const handleChange = (page: number, pageSize: number): void => {
  emit("change", page, pageSize);
};
</script>

<template>
  <div class="list-pagination" aria-label="列表分页">
    <Pagination
      :current="page"
      :page-size="pageSize"
      :page-size-options="pageSizeOptions"
      :show-size-changer="true"
      :show-total="showTotal"
      :total="total"
      @change="handleChange"
      @show-size-change="handleChange"
    />
  </div>
</template>

<style scoped>
.list-pagination {
  display: flex;
  min-height: 40px;
  justify-content: flex-end;
  align-items: center;
  padding-top: var(--space-4);
  overflow-x: auto;
}

.list-pagination :deep(.ant-pagination) {
  display: flex;
  max-width: 100%;
  align-items: center;
}

@media (max-width: 767px) {
  .list-pagination {
    justify-content: flex-start;
  }

  .list-pagination :deep(.ant-pagination-item),
  .list-pagination :deep(.ant-pagination-prev),
  .list-pagination :deep(.ant-pagination-next),
  .list-pagination :deep(.ant-pagination-jump-prev),
  .list-pagination :deep(.ant-pagination-jump-next),
  .list-pagination :deep(.ant-select-selector) {
    min-width: 44px;
    min-height: 44px;
  }

  .list-pagination :deep(.ant-pagination-item),
  .list-pagination :deep(.ant-select-selection-item) {
    line-height: 42px;
  }

  .list-pagination :deep(.ant-pagination-total-text) {
    width: 100%;
  }
}
</style>
