"""Hidden verifier for CP154 — Next.js Payment Confirm + Wallet Service Fix.

Checks that the payment confirmation route and wallet service correctly use
the actual database schema columns instead of non-existent ones.

Database schema (ground truth):
  payment_order: id, user_id, out_trade_no, provider, amount_cents, credits_to_add,
                 status, provider_trade_no, created_at, updated_at
  user_wallet: user_id, balance_credits, updated_at
  wallet_ledger: id, user_id, change_type, delta_credits, balance_after,
                 source_type, source_id, idempotency_key, created_at
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(root: Path, pattern: str) -> Path | None:
    """Find a file matching pattern recursively."""
    for p in root.rglob(pattern):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for correct DB column usage."""

    # Try multiple possible locations
    base = ws / "intelligent-edit"
    if not base.exists():
        base = ws / "fixtures" / "intelligent-edit"
    if not base.exists():
        # Fallback: search for key files
        base = ws

    components = {k: 0.0 for k in [
        "confirm_route_correct_select",
        "confirm_route_correct_update",
        "wallet_service_correct_update",
        "wallet_service_correct_ledger_insert",
        "wallet_service_correct_ledger_query",
        "idempotency_handling",
        "transaction_safety",
    ]}

    # --- 1. Payment confirm route: correct SELECT columns ---
    confirm_route = _find_file(base, "*/api/payment/confirm/route.ts")
    if not confirm_route:
        confirm_route = _find_file(base, "route.ts")
        # Filter to only payment/confirm
        if confirm_route and "payment" not in str(confirm_route):
            confirm_route = None

    if confirm_route:
        c = _read(confirm_route)

        # Check: uses 'credits_to_add' (correct) instead of 'amount_credits' (wrong)
        uses_credits_to_add = "credits_to_add" in c
        no_amount_credits_in_select = "amount_credits" not in c or (
            # Allow it in response JSON but not in SQL query
            c.count("amount_credits") <= c.count("credits_added")
        )

        # Check SELECT query uses correct column names
        has_correct_select = uses_credits_to_add and no_amount_credits_in_select
        components["confirm_route_correct_select"] = 1.0 if has_correct_select else (
            0.3 if uses_credits_to_add else 0.0
        )

        # Check: UPDATE uses 'provider_trade_no' (correct) instead of 'trade_no' (wrong)
        uses_provider_trade_no_update = bool(
            re.search(r"provider_trade_no\s*=", c)
        )
        no_wrong_trade_no = not bool(
            re.search(r"(?<!provider_)trade_no\s*=", c)
        )
        components["confirm_route_correct_update"] = (
            1.0 if (uses_provider_trade_no_update and no_wrong_trade_no) else
            0.5 if uses_provider_trade_no_update else 0.0
        )

    # --- 2. Wallet service: correct UPDATE query ---
    wallet_svc = _find_file(base, "wallet-service.ts")
    if not wallet_svc:
        wallet_svc = _find_file(base, "wallet_service.ts")
    if not wallet_svc:
        wallet_svc = _find_file(base, "walletService.ts")

    if wallet_svc:
        c = _read(wallet_svc)

        # Check: uses 'balance_credits' (correct) instead of 'amount' (wrong)
        uses_balance_credits_update = bool(
            re.search(r"balance_credits\s*=\s*balance_credits\s*\+", c) or
            re.search(r"SET\s+balance_credits", c, re.IGNORECASE)
        )
        no_wrong_amount = "SET amount" not in c and "SET `amount`" not in c
        components["wallet_service_correct_update"] = (
            1.0 if (uses_balance_credits_update and no_wrong_amount) else
            0.5 if uses_balance_credits_update else 0.0
        )

        # Check: ledger INSERT uses correct columns (change_type, delta_credits)
        uses_delta_credits = "delta_credits" in c
        uses_change_type = "change_type" in c
        no_wrong_order_id = "order_id" not in c.split("wallet_ledger")[1] if "wallet_ledger" in c else True
        no_wrong_change_credits = "change_credits" not in c

        ledger_score = 0.0
        if uses_delta_credits:
            ledger_score += 0.4
        if uses_change_type:
            ledger_score += 0.3
        if no_wrong_order_id and no_wrong_change_credits:
            ledger_score += 0.3
        components["wallet_service_correct_ledger_insert"] = min(ledger_score, 1.0)

        # Check: ledger SELECT query uses correct columns
        ledger_query_section = ""
        if "getWalletLedger" in c or "getLedger" in c or "wallet_ledger" in c:
            # Find the query part for reading ledger
            select_match = re.search(
                r"SELECT\s+.*?FROM\s+wallet_ledger",
                c, re.IGNORECASE | re.DOTALL
            )
            if select_match:
                ledger_query_section = select_match.group(0)

        if ledger_query_section:
            has_delta = "delta_credits" in ledger_query_section
            has_change_type = "change_type" in ledger_query_section
            has_source_type = "source_type" in ledger_query_section
            no_wrong_cols = (
                "order_id" not in ledger_query_section and
                "change_credits" not in ledger_query_section
            )
            components["wallet_service_correct_ledger_query"] = (
                1.0 if (has_delta and has_change_type and no_wrong_cols) else
                0.5 if (has_delta or has_change_type) else 0.0
            )
        elif "delta_credits" in c and "change_type" in c:
            # Might have restructured the query - partial credit
            components["wallet_service_correct_ledger_query"] = 0.7

    # --- 3. Idempotency handling ---
    all_code = ""
    if confirm_route:
        all_code += _read(confirm_route)
    if wallet_svc:
        all_code += _read(wallet_svc)

    has_idempotency_key = "idempotency_key" in all_code
    has_idempotency_check = bool(
        re.search(r"(ON\s+CONFLICT|WHERE.*idempotency|duplicate|UNIQUE)", all_code, re.IGNORECASE)
    ) or "idempotency" in all_code.lower()
    components["idempotency_handling"] = (
        1.0 if (has_idempotency_key and has_idempotency_check) else
        0.5 if has_idempotency_key else 0.0
    )

    # --- 4. Transaction safety ---
    if wallet_svc:
        c = _read(wallet_svc)
        has_begin = "BEGIN" in c
        has_commit = "COMMIT" in c
        has_rollback = "ROLLBACK" in c
        has_try_catch = "try" in c and "catch" in c
        has_release = "release" in c

        tx_score = 0.0
        if has_begin and has_commit:
            tx_score += 0.4
        if has_rollback:
            tx_score += 0.2
        if has_try_catch:
            tx_score += 0.2
        if has_release:
            tx_score += 0.2
        components["transaction_safety"] = min(tx_score, 1.0)

    weights = {
        "confirm_route_correct_select": 0.20,
        "confirm_route_correct_update": 0.15,
        "wallet_service_correct_update": 0.20,
        "wallet_service_correct_ledger_insert": 0.20,
        "wallet_service_correct_ledger_query": 0.10,
        "idempotency_handling": 0.05,
        "transaction_safety": 0.10,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try workspace root first, then fixtures subdirectory
    ws = Path("/workspace")
    result = grade_workspace(ws)

    # If score is 0 and fixtures subdir exists, try that
    if result["overall_score"] == 0.0 and (ws / "fixtures" / "intelligent-edit").exists():
        result = grade_workspace(ws / "fixtures")

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
