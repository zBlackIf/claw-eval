<template>
  <div class="customer-card">
    <h3>{{ customer.name }}</h3>
    <p>{{ customer.company }}</p>
    <el-tag :type="levelTagType">{{ customer.level }}</el-tag>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ICustomer } from "@/models/crm";

const props = defineProps<{ customer: ICustomer }>();

const levelTagType = computed(() => {
  switch (props.customer.level) {
    case "vip": return "danger";
    case "regular": return "primary";
    default: return "info";
  }
});
</script>
