// Mock backend dynamic route generation
import { MockMethod } from "vite-plugin-mock";

const orderManagementRouter: DynamicRouteConfigsTable = {
  path: "/order",
  meta: {
    title: "Order Management",
    icon: "list",
    rank: 1
  },
  children: [
    {
      path: "/order/list",
      name: "order-list",
      component: "order/order-list/index",
      meta: {
        title: "Order List"
      }
    },
    {
      path: "/order/detail/:id",
      name: "order-detail",
      component: "order/order-detail/index",
      meta: {
        title: "Order Detail",
        showLink: false
      }
    }
  ]
};

const productRouter: DynamicRouteConfigsTable = {
  path: "/product",
  meta: {
    title: "Product",
    icon: "goods",
    rank: 2
  },
  children: [
    {
      path: "/product/catalog",
      name: "product-catalog",
      component: "product/catalog/index",
      meta: {
        title: "Product Catalog"
      }
    },
    {
      path: "/product/pricing",
      name: "product-pricing",
      component: "product/pricing/index",
      meta: {
        title: "Pricing Rules"
      }
    }
  ]
};

const settingsRouter: DynamicRouteConfigsTable = {
  path: "/settings",
  meta: {
    title: "Settings",
    icon: "setting",
    rank: 3
  },
  children: [
    {
      path: "/settings/user",
      name: "settings-user",
      component: "settings/user/index",
      meta: {
        title: "User Management"
      }
    },
    {
      path: "/settings/role",
      name: "settings-role",
      component: "settings/role/index",
      meta: {
        title: "Role Management"
      }
    }
  ]
};

export default [
  {
    url: "/get-async-routes",
    method: "get",
    response: () => {
      return {
        success: true,
        data: [
          orderManagementRouter,
          productRouter,
          settingsRouter
        ]
      };
    }
  }
] as MockMethod[];
