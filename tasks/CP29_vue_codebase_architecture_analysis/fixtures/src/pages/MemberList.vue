<template>
  <div>
    <el-table :data="members" v-loading="loading">
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="role" label="角色" />
      <el-table-column prop="email" label="邮箱" />
    </el-table>
  </div>
</template>
<script>
import { getMemberList } from '@/api/members'
export default {
  data() { return { members: [], loading: false } },
  methods: {
    async loadMembers() {
      this.loading = true
      try {
        const res = await getMemberList({ page: 1, size: 20 })
        this.members = res.data.list
      } catch(e) { this.$message.error('加载失败') }
      finally { this.loading = false }
    }
  },
  mounted() { this.loadMembers() }
}
</script>
