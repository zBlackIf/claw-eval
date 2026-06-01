import { http } from "@/utils/http";

export function getRoleList(params: any) {
  return http.get("/api/settings/role", { params });
}

export function assignRole(data: any) {
  return http.post("/api/settings/role/assign", { data });
}
