import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";

// Static routes available to all users
const staticRoutes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/login/index.vue"),
  },
  {
    path: "/",
    redirect: "/order/list",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes,
});

export default router;
