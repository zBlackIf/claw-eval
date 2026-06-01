import { http } from "@/utils/http";

export function createShipment(data: any) {
  return http.post("/api/logistics/shipment", { data });
}

export function getShipmentList(params: any) {
  return http.get("/api/logistics/shipment", { params });
}
