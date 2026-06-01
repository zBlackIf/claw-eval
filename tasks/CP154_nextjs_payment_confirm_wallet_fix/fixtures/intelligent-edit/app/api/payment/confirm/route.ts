import { NextRequest, NextResponse } from "next/server";
import pool from "@/lib/server/db";
import { addCreditsToWallet } from "@/lib/server/wallet-service";

/**
 * POST /api/payment/confirm
 * Body: { order_id: string, provider_trade_no: string }
 *
 * Called by the payment provider webhook or frontend polling after user pays.
 * Should:
 *   1. Verify the payment_order exists and is still 'pending'
 *   2. Update payment_order status to 'paid' and record provider_trade_no
 *   3. Add credits to user's wallet (credits_to_add from order)
 *   4. Return updated balance
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { order_id, provider_trade_no } = body;

    if (!order_id) {
      return NextResponse.json({ error: "order_id is required" }, { status: 400 });
    }

    // BUG 1: Uses wrong column name 'amount_credits' instead of 'credits_to_add'
    // BUG 2: Uses wrong column name 'trade_no' instead of 'provider_trade_no'
    const orderRes = await pool.query(
      `SELECT id, user_id, amount_credits, status FROM payment_order WHERE id = $1`,
      [order_id]
    );

    if (orderRes.rows.length === 0) {
      return NextResponse.json({ error: "Order not found" }, { status: 404 });
    }

    const order = orderRes.rows[0];

    if (order.status !== "pending") {
      return NextResponse.json(
        { error: "Order already processed", status: order.status },
        { status: 409 }
      );
    }

    // BUG 3: Updates with wrong column name 'trade_no'
    await pool.query(
      `UPDATE payment_order SET status = 'paid', trade_no = $1, updated_at = NOW() WHERE id = $2`,
      [provider_trade_no || "", order_id]
    );

    // BUG 4: Uses 'amount_credits' which doesn't exist (should be credits_to_add)
    const idempotencyKey = `payment:${order_id}`;
    await addCreditsToWallet(
      order.user_id,
      order.amount_credits,
      "payment",
      order_id,
      idempotencyKey
    );

    // Return new balance
    const balRes = await pool.query(
      `SELECT balance_credits FROM user_wallet WHERE user_id = $1`,
      [order.user_id]
    );

    return NextResponse.json({
      ok: true,
      order_id,
      credits_added: order.amount_credits,
      new_balance: balRes.rows[0]?.balance_credits ?? 0,
    });
  } catch (err: any) {
    console.error("[payment/confirm] Error:", err);
    return NextResponse.json(
      { error: "Internal server error", detail: err.message },
      { status: 500 }
    );
  }
}
