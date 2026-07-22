import { computed, ref, watch, type ComputedRef, type Ref } from "vue";

export interface ListPaginationState<T> {
  readonly page: Ref<number>;
  readonly pageSize: Ref<number>;
  readonly total: ComputedRef<number>;
  readonly pagedItems: ComputedRef<readonly T[]>;
  readonly setPage: (page: number, pageSize: number) => void;
}

export const useListPagination = <T>(
  items: ComputedRef<readonly T[]>,
  initialPageSize = 10,
): ListPaginationState<T> => {
  const page = ref(1);
  const pageSize = ref(initialPageSize);
  const total = computed(() => items.value.length);
  const pagedItems = computed(() => {
    const start = (page.value - 1) * pageSize.value;
    return items.value.slice(start, start + pageSize.value);
  });

  watch(items, () => {
    page.value = 1;
  });

  watch([total, pageSize], ([nextTotal, nextPageSize]) => {
    const lastPage = Math.max(1, Math.ceil(nextTotal / nextPageSize));
    if (page.value > lastPage) page.value = lastPage;
  });

  const setPage = (nextPage: number, nextPageSize: number): void => {
    pageSize.value = nextPageSize;
    const lastPage = Math.max(1, Math.ceil(total.value / nextPageSize));
    page.value = Math.min(Math.max(nextPage, 1), lastPage);
  };

  return { page, pageSize, total, pagedItems, setPage };
};
