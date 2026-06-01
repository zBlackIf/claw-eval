/**
 * Core types for the medical exam billing / refund module.
 */

/** Supported payment channels. */
export type PayMode = 'wechat' | 'alipay' | 'cash' | 'bank_card' | 'company_quota';

/** A single payment record on a checkout order. */
export interface PaymentRecord {
  id: string;
  checkout_order_id: string;
  pay_mode: PayMode;
  amount: number; // cents
  transaction_id: string | null;
  is_internal_adjustment: boolean;
  status: 'active' | 'reversed';
}

/** Allocation of an item's cost to a specific payment record. */
export interface ItemPaymentAllocation {
  item_id: string;
  payment_record_id: string;
  pay_mode: PayMode;
  allocated_amount: number; // cents
}

/** A refund request specifying which items to refund and the target channel. */
export interface RefundRequest {
  checkout_order_id: string;
  refund_items: RefundItem[];
  /** Customer-chosen channel(s) to receive the refund money. */
  refund_channels: RefundChannelChoice[];
}

export interface RefundItem {
  item_id: string;
  /** Amount to refund for this item (cents). */
  refund_amount: number;
}

/** How much to refund to each channel (customer's choice). */
export interface RefundChannelChoice {
  pay_mode: PayMode;
  amount: number; // cents
}

/** Result of refund allocation (Strategy 1: Full Reversal & Recharge). */
export interface RefundResult {
  /** Red-reversal records (one per original active payment record). */
  reversal_records: ReversalRecord[];
  /** Gateway refund instructions (actual money out to customer). */
  gateway_refunds: GatewayRefund[];
  /** New recharge records reflecting remaining amounts after refund. */
  recharge_records: RechargeRecord[];
  /** Whether the operation succeeded. */
  success: boolean;
  /** Error message if failed. */
  error?: string;
}

export interface ReversalRecord {
  original_record_id: string;
  pay_mode: PayMode;
  amount: number; // negative, in cents
  transaction_id: string | null;
}

export interface GatewayRefund {
  pay_mode: PayMode;
  amount: number; // positive, the actual refund to customer
  original_transaction_id: string | null;
}

export interface RechargeRecord {
  pay_mode: PayMode;
  amount: number; // positive, cents
  is_internal_adjustment: true;
  original_transaction_id: string | null;
}
