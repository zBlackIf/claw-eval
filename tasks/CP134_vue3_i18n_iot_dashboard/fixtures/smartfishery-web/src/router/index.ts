import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/dashboard/Dashboard.vue'),
    },
    {
      path: '/devices',
      name: 'Devices',
      component: () => import('@/views/dashboard/Dashboard.vue'),
    },
    {
      path: '/monitor',
      name: 'Monitor',
      component: () => import('@/views/dashboard/Dashboard.vue'),
    },
    {
      path: '/alerts',
      name: 'Alerts',
      component: () => import('@/views/dashboard/Dashboard.vue'),
    },
    {
      path: '/control',
      name: 'Control',
      component: () => import('@/views/dashboard/Dashboard.vue'),
    },
  ],
})

export default router
