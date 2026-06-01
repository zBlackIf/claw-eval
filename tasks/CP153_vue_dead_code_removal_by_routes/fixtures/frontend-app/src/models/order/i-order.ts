export interface IOrder {
  id: string;
  orderNo: string;
  customerName: string;
  totalAmount: number;
  status: "pending" | "confirmed" | "shipped" | "completed";
  createdAt: string;
}

export interface IOrderListReq {
  page: number;
  pageSize: number;
  status?: string;
  keyword?: string;
}
