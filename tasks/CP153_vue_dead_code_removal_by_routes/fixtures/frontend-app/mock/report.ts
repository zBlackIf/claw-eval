import { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/api/report/sales",
    method: "get",
    response: () => ({
      success: true,
      data: { totalOrders: 0, totalRevenue: 0, topProducts: [] }
    })
  }
] as MockMethod[];
