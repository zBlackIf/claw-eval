<template>
  <div class="member-list">
    <div v-if="loading" class="loading">Loading...</div>
    <div v-if="error" class="error">{{ error }}</div>
    <table v-if="!loading && !error">
      <tr v-for="member in list" :key="member.id">
        <td>{{ member.name }}</td>
        <td>{{ member.role }}</td>
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
import { getMemberList } from '@/api/members'

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
        const res = await getMemberList({ page: this.page, pageSize: this.pageSize })
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
