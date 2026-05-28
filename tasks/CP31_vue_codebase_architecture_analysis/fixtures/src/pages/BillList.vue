<template>
  <div>
    <el-button @click="handleExport">导出</el-button>
    <el-table :data="bills" v-loading="loading">
      <el-table-column prop="id" label="ID" />
      <el-table-column prop="amount" label="金额">
        <template #default="{row}">{{ formatMoney(row.amount) }}</template>
      </el-table-column>
      <el-table-column prop="category" label="分类" />
      <el-table-column prop="createdAt" label="日期">
        <template #default="{row}">{{ formatDate(row.createdAt) }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>
<script>
import { getBillList, exportBills } from '@/api/bills'
export default {
  data() { return { bills: [], loading: false } },
  methods: {
    async loadBills() {
      this.loading = true
      try {
        const res = await getBillList({ page: 1, size: 20 })
        this.bills = res.data.list
      } catch(e) { this.$message.error('加载失败') }
      finally { this.loading = false }
    },
    formatMoney(val) { return '¥' + Number(val).toFixed(2) },
    formatDate(val) { return new Date(val).toLocaleDateString('zh-CN') },
    async handleExport() {
      const blob = await exportBills({})
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = 'bills.xlsx'; a.click()
    }
  },
  mounted() { this.loadBills() }
}
</script>
