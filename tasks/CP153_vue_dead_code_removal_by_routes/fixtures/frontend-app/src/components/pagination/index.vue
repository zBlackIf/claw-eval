<template>
  <div class="pagination-wrapper">
    <el-pagination
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @current-change="handlePageChange"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  currentPage: number;
  pageSize: number;
  total: number;
}>();

const emit = defineEmits(["update:currentPage"]);

function handlePageChange(page: number) {
  emit("update:currentPage", page);
}
</script>
