import { http } from "@/utils/http";

export function getPricingRules(params: any) {
  return http.get("/api/product/pricing", { params });
}

export function updatePricingRule(id: string, data: any) {
  return http.put(`/api/product/pricing/${id}`, { data });
}
