<template>
  <div class="chart-panel">
    <div ref="chartRef" :style="{ width: '100%', height: height + 'px' }"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";

defineProps<{ height?: number }>();

const chartRef = ref<HTMLElement | null>(null);

onMounted(() => {
  // Initialize chart
});
</script>
