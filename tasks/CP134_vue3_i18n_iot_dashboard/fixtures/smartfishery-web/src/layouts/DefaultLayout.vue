<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const router = useRouter()
const isCollapsed = ref(false)

const menuItems = [
  { path: '/dashboard', title: '数据看板', icon: 'Monitor' },
  { path: '/devices', title: '设备管理', icon: 'Cpu' },
  { path: '/monitor', title: '实时监控', icon: 'VideoCamera' },
  { path: '/alerts', title: '告警中心', icon: 'Bell' },
  { path: '/control', title: '远程控制', icon: 'Setting' },
  { path: '/reports', title: '报表分析', icon: 'DataAnalysis' },
]
</script>

<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="layout-aside">
      <div class="logo">
        <img src="@/assets/logo.svg" alt="logo" />
        <span v-show="!isCollapsed">智慧渔业</span>
      </div>
      <el-menu
        :default-active="router.currentRoute.value.path"
        :collapse="isCollapsed"
        router
        background-color="#0c1929"
        text-color="#b0bec5"
        active-text-color="#4fc3f7"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapsed = !isCollapsed">
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
        </div>
        <div class="header-right">
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32" />
              <span class="username">{{ appStore.username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人设置</el-dropdown-item>
                <el-dropdown-item divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
}
.layout-aside {
  background-color: #0c1929;
  transition: width 0.3s;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #4fc3f7;
  font-size: 18px;
  font-weight: bold;
}
.logo img {
  width: 32px;
  height: 32px;
}
.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #0f2136;
  border-bottom: 1px solid #1a3a5c;
  color: #e0e0e0;
}
.collapse-btn {
  cursor: pointer;
  font-size: 20px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #e0e0e0;
}
.layout-main {
  background: #0a1628;
}
</style>
