import pool from "./db";

/**
 * Wallet service — handles credit balance operations.
 * See docs/project-startup.md for the actual database schema.
 */

export async function getWalletBalance(userId: number) {
  const res = await pool.query(
    "SELECT balance_credits FROM user_wallet WHERE user_id = $1",
    [userId]
  );
  if (res.rows.length === 0) return { balance_credits: 0 };
  return res.rows[0];
}

export async function addCreditsToWallet(
  userId: number,
  credits: number,
  sourceType: string,
  sourceId: string,
  idempotencyKey?: string
) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    // BUG: uses wrong column name 'amount' instead of 'balance_credits'
    // and wrong table structure assumptions
    await client.query(
      `UPDATE user_wallet SET amount = amount + $1, updated_at = NOW() WHERE user_id = $2`,
      [credits, userId]
    );

    // BUG: uses wrong column names 'order_id' and 'change_credits'
    await client.query(
      `INSERT INTO wallet_ledger (user_id, order_id, change_credits, balance_after, source_type, created_at)
       VALUES ($1, $2, $3, (SELECT amount FROM user_wallet WHERE user_id = $1), $4, NOW())`,
      [userId, sourceId, credits, sourceType]
    );

    await client.query("COMMIT");
    return { success: true };
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

export async function getWalletLedger(userId: number, limit = 20) {
  // BUG: references non-existent columns 'order_id' and 'change_credits'
  const res = await pool.query(
    `SELECT id, user_id, order_id, change_credits, balance_after, source_type, created_at
     FROM wallet_ledger WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2`,
    [userId, limit]
  );
  return res.rows;
}
