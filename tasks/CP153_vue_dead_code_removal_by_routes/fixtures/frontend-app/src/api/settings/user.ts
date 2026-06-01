import { http } from "@/utils/http";

export function getUserList(params: any) {
  return http.get("/api/settings/user", { params });
}

export function updateUser(id: string, data: any) {
  return http.put(`/api/settings/user/${id}`, { data });
}
