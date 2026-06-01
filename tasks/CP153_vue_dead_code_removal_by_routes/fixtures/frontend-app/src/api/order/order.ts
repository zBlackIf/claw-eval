import { http } from "@/utils/http";

export function getOrderList(params: any) {
  return http.get("/api/order/list", { params });
}

export function getOrderDetail(id: string) {
  return http.get(`/api/order/${id}`);
}

export function createOrder(data: any) {
  return http.post("/api/order", { data });
}
