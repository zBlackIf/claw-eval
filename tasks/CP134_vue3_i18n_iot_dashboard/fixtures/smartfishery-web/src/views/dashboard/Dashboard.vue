<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

interface SensorData {
  id: string
  name: string
  value: number
  unit: string
  status: 'normal' | 'warning' | 'critical'
}

const sensors = ref<SensorData[]>([
  { id: 'temp-01', name: '水温', value: 23.5, unit: '°C', status: 'normal' },
  { id: 'ph-01', name: 'pH值', value: 7.2, unit: '', status: 'normal' },
  { id: 'do-01', name: '溶氧量', value: 6.8, unit: 'mg/L', status: 'normal' },
  { id: 'turb-01', name: '浊度', value: 45, unit: 'NTU', status: 'warning' },
  { id: 'nh3-01', name: '氨氮', value: 0.8, unit: 'mg/L', status: 'critical' },
])

const alertCount = ref(3)
const deviceOnline = ref(28)
const deviceTotal = ref(32)

onMounted(() => {
  // Simulate real-time data updates
  setInterval(() => {
    sensors.value = sensors.value.map(s => ({
      ...s,
      value: +(s.value + (Math.random() - 0.5) * 0.1).toFixed(2),
    }))
  }, 5000)
})
</script>

<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h2>数据看板</h2>
      <span class="update-time">最后更新: {{ new Date().toLocaleTimeString() }}</span>
    </div>

    <el-row :gutter="16" class="stat-cards">
      <el-col :span="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">在线设备</div>
          <div class="stat-value">{{ deviceOnline }} / {{ deviceTotal }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">今日告警</div>
          <div class="stat-value warning">{{ alertCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">数据采集点</div>
          <div class="stat-value">{{ sensors.length }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="sensor-table-card">
      <template #header>
        <span>传感器实时数据</span>
      </template>
      <el-table :data="sensors" stripe>
        <el-table-column prop="name" label="传感器" />
        <el-table-column prop="value" label="当前值">
          <template #default="{ row }">
            {{ row.value }} {{ row.unit }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'normal' ? 'success' : row.status === 'warning' ? 'warning' : 'danger'">
              {{ row.status === 'normal' ? '正常' : row.status === 'warning' ? '告警' : '严重' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 16px;
}
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.dashboard-header h2 {
  color: #e0e0e0;
  margin: 0;
}
.update-time {
  color: #78909c;
  font-size: 13px;
}
.stat-cards {
  margin-bottom: 16px;
}
.stat-card {
  background: #112240;
  border: 1px solid #1a3a5c;
}
.stat-label {
  color: #78909c;
  font-size: 13px;
}
.stat-value {
  color: #4fc3f7;
  font-size: 28px;
  font-weight: bold;
  margin-top: 8px;
}
.stat-value.warning {
  color: #ffa726;
}
.sensor-table-card {
  background: #112240;
  border: 1px solid #1a3a5c;
}
</style>
