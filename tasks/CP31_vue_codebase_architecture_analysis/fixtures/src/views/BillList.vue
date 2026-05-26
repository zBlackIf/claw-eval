<template>
  <div class="bill-list">
    <div v-if="loading" class="loading">Loading...</div>
    <div v-if="error" class="error">{{ error }}</div>
    <table v-if="!loading && !error">
      <tr v-for="bill in list" :key="bill.id">
        <td>{{ bill.name }}</td>
        <td>{{ bill.amount }}</td>
      </tr>
    </table>
    <div class="pagination">
      <button @click="prevPage" :disabled="page <= 1">Prev</button>
      <span>Page {{ page }} / {{ totalPages }}</span>
      <button @click="nextPage" :disabled="page >= totalPages">Next</button>
    </div>
  </div>
</template>

<script>
import { getBillList } from '@/api/bills'

export default {
  data() {
    return { list: [], loading: false, error: null, page: 1, total: 0, pageSize: 20 }
  },
  computed: {
    totalPages() { return Math.ceil(this.total / this.pageSize) }
  },
  mounted() { this.loadData() },
  methods: {
    async loadData() {
      this.loading = true
      this.error = null
      try {
        const res = await getBillList({ page: this.page, pageSize: this.pageSize })
        this.list = res.data
        this.total = res.total
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    prevPage() { this.page--; this.loadData() },
    nextPage() { this.page++; this.loadData() },
  }
}
</script>
