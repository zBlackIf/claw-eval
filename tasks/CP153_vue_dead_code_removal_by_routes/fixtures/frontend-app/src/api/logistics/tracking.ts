import { http } from "@/utils/http";

export function getTrackingInfo(trackingNo: string) {
  return http.get(`/api/logistics/tracking/${trackingNo}`);
}
