export interface IPricingRule {
  id: string;
  productId: string;
  minQty: number;
  maxQty: number;
  discountRate: number;
}
