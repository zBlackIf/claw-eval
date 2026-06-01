import { http } from "@/utils/http";

export function getInventoryReport(params: any) {
  return http.get("/api/report/inventory", { params });
}
