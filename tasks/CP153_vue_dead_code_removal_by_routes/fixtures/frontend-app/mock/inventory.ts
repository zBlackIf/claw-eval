import { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/api/inventory/stock",
    method: "get",
    response: () => ({
      success: true,
      data: { list: [], total: 0 }
    })
  },
  {
    url: "/api/inventory/stock-in",
    method: "post",
    response: () => ({
      success: true,
      message: "Stock in successful"
    })
  }
] as MockMethod[];
