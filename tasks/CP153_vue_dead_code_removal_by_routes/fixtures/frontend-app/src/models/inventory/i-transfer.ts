export interface ITransfer {
  id: string;
  fromWarehouse: string;
  toWarehouse: string;
  productId: string;
  quantity: number;
  status: "pending" | "in-transit" | "completed";
}
