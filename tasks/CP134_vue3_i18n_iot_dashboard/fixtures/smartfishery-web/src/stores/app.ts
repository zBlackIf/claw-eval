import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const username = ref('admin')
  const theme = ref<'dark' | 'light'>('dark')
  const sidebarCollapsed = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { username, theme, sidebarCollapsed, toggleSidebar }
})
