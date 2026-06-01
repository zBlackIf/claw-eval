<template>
  <div class="search-bar">
    <el-input v-model="keyword" placeholder="Search..." @keyup.enter="handleSearch" />
    <el-button type="primary" @click="handleSearch">Search</el-button>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

const keyword = ref("");
const emit = defineEmits(["search"]);

function handleSearch() {
  emit("search", keyword.value);
}
</script>
