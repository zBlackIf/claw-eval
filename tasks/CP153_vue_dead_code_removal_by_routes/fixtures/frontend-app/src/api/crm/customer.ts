import { http } from "@/utils/http";

export function getCustomerList(params: any) {
  return http.get("/api/crm/customer", { params });
}

export function getCustomerDetail(id: string) {
  return http.get(`/api/crm/customer/${id}`);
}

export function updateCustomer(id: string, data: any) {
  return http.put(`/api/crm/customer/${id}`, { data });
}
