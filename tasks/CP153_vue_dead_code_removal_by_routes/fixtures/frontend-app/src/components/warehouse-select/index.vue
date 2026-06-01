<template>
  <el-select v-model="selectedWarehouse" placeholder="Select Warehouse">
    <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
  </el-select>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getWarehouseList } from "@/api/inventory";

const selectedWarehouse = ref("");
const warehouses = ref([]);

onMounted(async () => {
  // warehouses.value = await getWarehouseList();
});
</script>
