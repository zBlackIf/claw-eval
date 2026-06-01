export interface IInventoryReport {
  warehouseId: string;
  totalItems: number;
  lowStockItems: number;
  overStockItems: number;
}
