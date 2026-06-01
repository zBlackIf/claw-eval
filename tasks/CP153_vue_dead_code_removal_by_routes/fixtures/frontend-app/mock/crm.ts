import { MockMethod } from "vite-plugin-mock";

export default [
  {
    url: "/api/crm/customer",
    method: "get",
    response: () => ({
      success: true,
      data: { list: [], total: 0 }
    })
  }
] as MockMethod[];
