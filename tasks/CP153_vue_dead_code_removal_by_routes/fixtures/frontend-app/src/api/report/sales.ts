import { http } from "@/utils/http";

export function getSalesReport(params: any) {
  return http.get("/api/report/sales", { params });
}

export function exportSalesReport(params: any) {
  return http.get("/api/report/sales/export", { params, responseType: "blob" });
}
