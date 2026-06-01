/**
 * Refund allocation engine — Strategy 1: Full Reversal & Recharge.
 *
 * Business rules (from architecture doc):
 * 1. Red-reverse ALL active payment records on the checkout order (accounting only).
 * 2. Execute gateway refund(s) per customer-chosen channel(s).
 * 3. Create new "recharge" records from scratch for the remaining amounts.
 *    - Recharge records are internal adjustments (is_internal_adjustment = true).
 *    - They preserve original_transaction_id from the original payment.
 *    - No separate "调账" (internal transfer) step is needed in Strategy 1.
 *
 * Channel capacity constraint:
 *   The cumulative refund on any channel cannot exceed that channel's
 *   original total payment amount.
 *
 * TODO: Implement the processRefund function below.
 */

import type {
  PaymentRecord,
  ItemPaymentAllocation,
  RefundRequest,
  RefundResult,
} from './types';

/**
 * Compute the refund result using Strategy 1 (Full Reversal & Recharge).
 *
 * @param activeRecords - All ACTIVE payment records on the checkout order.
 * @param allocations  - Current item → payment allocation table.
 * @param request      - The refund request (items + customer channel choices).
 * @returns RefundResult with reversal records, gateway refunds, and recharge records.
 *
 * Validation requirements:
 * - Total refund_channels amounts must equal total refund_items amounts.
 * - Each refund channel amount must not exceed that channel's original payment total
 *   (channel capacity constraint).
 * - All refund items must belong to the checkout order (exist in allocations).
 *
 * On validation failure, return { success: false, error: "..." }.
 */
export function processRefund(
  activeRecords: PaymentRecord[],
  allocations: ItemPaymentAllocation[],
  request: RefundRequest,
): RefundResult {
  // TODO: Implement Strategy 1 refund logic
  throw new Error('Not implemented');
}
