import { http } from "@/utils/http";

export function createTransfer(data: any) {
  return http.post("/api/inventory/transfer", { data });
}

export function getTransferList(params: any) {
  return http.get("/api/inventory/transfer", { params });
}
