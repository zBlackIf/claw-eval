import { http } from "@/utils/http";

export function getProductCatalog(params: any) {
  return http.get("/api/product/catalog", { params });
}

export function getProductDetail(id: string) {
  return http.get(`/api/product/${id}`);
}
