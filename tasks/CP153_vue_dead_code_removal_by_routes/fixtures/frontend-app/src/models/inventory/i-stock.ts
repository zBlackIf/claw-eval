export interface IStock {
  id: string;
  productId: string;
  warehouseId: string;
  quantity: number;
  lastUpdated: string;
}

export interface IStockInReq {
  productId: string;
  quantity: number;
  warehouseId: string;
}
