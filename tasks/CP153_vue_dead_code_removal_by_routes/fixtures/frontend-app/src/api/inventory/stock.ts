import { http } from "@/utils/http";

export function getStockList(params: any) {
  return http.get("/api/inventory/stock", { params });
}

export function stockIn(data: any) {
  return http.post("/api/inventory/stock-in", { data });
}

export function stockOut(data: any) {
  return http.post("/api/inventory/stock-out", { data });
}
