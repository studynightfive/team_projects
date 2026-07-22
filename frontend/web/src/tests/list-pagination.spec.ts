import { computed, ref } from "vue";
import { describe, expect, it } from "vitest";

import { useListPagination } from "../composables/useListPagination";

describe("业务列表分页", () => {
  it("分页、切换每页数量并在筛选变化后回到第一页", async () => {
    const source = ref<readonly number[]>(Array.from({ length: 25 }, (_, i) => i + 1));
    const filtered = computed(() => source.value);
    const pagination = useListPagination(filtered, 10);

    expect(pagination.pagedItems.value).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    pagination.setPage(3, 10);
    expect(pagination.pagedItems.value).toEqual([21, 22, 23, 24, 25]);

    pagination.setPage(2, 20);
    expect(pagination.pagedItems.value).toEqual([21, 22, 23, 24, 25]);

    source.value = [1, 2, 3];
    await Promise.resolve();
    expect(pagination.page.value).toBe(1);
    expect(pagination.pagedItems.value).toEqual([1, 2, 3]);
  });
});
