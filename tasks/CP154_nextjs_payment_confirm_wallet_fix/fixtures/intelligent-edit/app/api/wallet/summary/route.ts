import { NextRequest, NextResponse } from "next/server";
import { getWalletBalance, getWalletLedger } from "@/lib/server/wallet-service";

/**
 * GET /api/wallet/summary?user_id=<id>
 * Returns the user's current balance and recent transactions.
 */
export async function GET(request: NextRequest) {
  const userId = request.nextUrl.searchParams.get("user_id");
  if (!userId) {
    return NextResponse.json({ error: "user_id required" }, { status: 400 });
  }

  try {
    const balance = await getWalletBalance(Number(userId));
    const ledger = await getWalletLedger(Number(userId));

    return NextResponse.json({
      user_id: Number(userId),
      ...balance,
      recent_transactions: ledger,
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: "Failed to fetch wallet summary", detail: err.message },
      { status: 500 }
    );
  }
}
