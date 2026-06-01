import { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/api/logistics/shipment",
    method: "get",
    response: () => ({
      success: true,
      data: { list: [], total: 0 }
    })
  }
] as MockMethod[];
