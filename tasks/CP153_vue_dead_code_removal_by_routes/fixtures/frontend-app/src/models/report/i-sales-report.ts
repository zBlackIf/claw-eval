export interface ISalesReport {
  date: string;
  totalOrders: number;
  totalRevenue: number;
  topProducts: Array<{ name: string; quantity: number }>;
}
