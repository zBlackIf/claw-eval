"""Hidden verifier for CP158 — Refund Allocation Strategy 1 (Full Reversal & Recharge).

Checks (11 dimensions):
1. processRefund function exists and is callable
2. Validation: channel capacity constraint enforced
3. Validation: total refund amounts match
4. Reversal records generated correctly (one per active record, negative amounts)
5. Gateway refunds match customer channel choices
6. Recharge records: correct remaining amounts, is_internal_adjustment=true, original_transaction_id preserved
7. Edge case: multi-channel refund with mixed transaction types
8. HIDDEN — Type-safety: error path returns well-formed RefundResult (empty arrays, not undefined)
9. HIDDEN — Defensive coding: guards for empty inputs, zero-amount edge cases, duplicate channel merging
10. HIDDEN — Immutability: does not mutate input parameters
11. HIDDEN — Gateway refund txid resolution: correctly resolves original_transaction_id per channel
12. HIDDEN — Structured per-channel accounting: uses Map/Record to accumulate per-channel totals before processing
13. HIDDEN — Comprehensive result shape: success path includes all required RefundResult fields typed correctly
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _find_refund_engine(ws: Path) -> Path | None:
    """Find the refund-engine.ts file."""
    candidates = [
        ws / "casher-refund" / "src" / "refund-engine.ts",
        ws / "fixtures" / "casher-refund" / "src" / "refund-engine.ts",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: search recursively
    for p in ws.rglob("refund-engine.ts"):
        return p
    for p in ws.rglob("refundEngine.ts"):
        return p
    return None


def _find_all_ts_files(ws: Path) -> list[Path]:
    """Find all .ts files in the project."""
    results = []
    for p in ws.rglob("*.ts"):
        if "node_modules" not in str(p):
            results.append(p)
    return results


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_comments(content: str) -> str:
    """Remove single-line and multi-line comments from TypeScript code."""
    # Remove multi-line comments
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)
    # Remove single-line comments
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    return content


def _extract_function_body(content: str, func_name: str) -> str:
    """Extract the body of a function (between first { and matching })."""
    # Find the function declaration
    pattern = rf'(export\s+)?(async\s+)?function\s+{func_name}\s*\('
    match = re.search(pattern, content)
    if not match:
        # Try arrow function or const
        pattern = rf'(export\s+)?(const\s+){func_name}\s*='
        match = re.search(pattern, content)
    if not match:
        return ""

    # Find opening brace after the match
    rest = content[match.start():]
    brace_start = rest.find('{')
    if brace_start < 0:
        return ""

    # Extract body by tracking braces
    depth = 0
    body_start = brace_start
    for i in range(brace_start, len(rest)):
        if rest[i] == '{':
            depth += 1
        elif rest[i] == '}':
            depth -= 1
            if depth == 0:
                return rest[body_start + 1:i]
    return rest[body_start + 1:]


def _check_function_implemented(body: str) -> dict:
    """Check that processRefund body has real logic (not just throw)."""
    result = {"exists": False, "implemented": False, "has_logic": False}

    if not body.strip():
        return result

    result["exists"] = True

    # Check it's not just a throw statement
    stripped = body.strip()
    if stripped.startswith("throw") and stripped.count(";") <= 1:
        return result

    # Check for actual logic
    logic_patterns = [
        r'\bif\s*\(',
        r'\bfor\s*\(',
        r'\.map\s*\(',
        r'\.filter\s*\(',
        r'\.reduce\s*\(',
        r'\.forEach\s*\(',
        r'\bwhile\s*\(',
        r'\bswitch\s*\(',
        r'\breturn\s*\{',
        r'\breturn\s+\{',
    ]
    logic_count = sum(1 for p in logic_patterns if re.search(p, body))
    result["has_logic"] = logic_count >= 2
    result["implemented"] = logic_count >= 1

    return result


def _check_validation_logic(body: str) -> dict:
    """Check validation rules in function body (comments stripped)."""
    result = {
        "channel_capacity_check": False,
        "amount_mismatch_check": False,
        "item_existence_check": False,
    }

    # Channel capacity: comparing refund amount per channel vs original payment
    # Needs: grouping by pay_mode + comparison
    has_grouping = bool(re.search(r'(pay_mode|payMode)', body))
    has_comparison = bool(re.search(r'[><=!]=?', body) and re.search(r'(amount|total|sum)', body, re.IGNORECASE))
    has_error_return = bool(re.search(r'(success\s*:\s*false|error|Error)', body))
    # More specific: looking at capacity logic patterns
    capacity_patterns = [
        re.search(r'(exceed|capacity|over|greater)', body, re.IGNORECASE),
        re.search(r'>\s*\w*(total|original|paid|sum)', body, re.IGNORECASE),
        re.search(r'\w*(total|original|paid|sum)\w*\s*<', body, re.IGNORECASE),
    ]
    result["channel_capacity_check"] = (
        has_grouping and has_comparison and has_error_return and any(capacity_patterns)
    )

    # Amount mismatch: summing both sides and comparing
    sum_patterns = [
        re.search(r'reduce\s*\(', body),
        re.search(r'\+\s*\w+\.amount', body),
        re.search(r'amount\s*\+', body),
        re.search(r'\+=\s*\w+\.amount', body),
        re.search(r'\.amount\s*\+=', body),
    ]
    has_sum = sum(1 for p in sum_patterns if p) >= 1
    has_items_sum = bool(re.search(r'refund_items|refundItems', body))
    has_channels_sum = bool(re.search(r'refund_channels|refundChannels', body))
    has_not_equal = bool(re.search(r'(!==?|!= |mismatch)', body))
    result["amount_mismatch_check"] = has_sum and has_items_sum and has_channels_sum and has_not_equal

    # Item existence: checking items in allocations
    has_alloc_check = bool(re.search(r'allocation|alloc', body, re.IGNORECASE))
    has_item_lookup = bool(re.search(r'(find|filter|some|includes|has|get)\s*\(', body))
    has_item_ref = bool(re.search(r'item_id|itemId', body))
    result["item_existence_check"] = has_alloc_check and has_item_lookup and has_item_ref

    return result


def _check_reversal_logic(body: str) -> dict:
    """Check reversal record generation in function body."""
    result = {
        "generates_reversals": False,
        "negative_amounts": False,
        "preserves_transaction_id": False,
    }

    # Iterates over active records and creates reversal-like objects
    has_iteration = bool(re.search(r'(\.map\(|\.forEach\(|for\s*\()', body))
    has_records_ref = bool(re.search(r'(activeRecords|active_records|records)', body, re.IGNORECASE))
    has_reversal_obj = bool(re.search(r'(reversal|reversed|original_record_id|originalRecordId)', body, re.IGNORECASE))

    result["generates_reversals"] = has_iteration and has_records_ref and has_reversal_obj

    # Negative amounts
    neg_patterns = [
        re.search(r'-\s*\w+\.amount', body),
        re.search(r'amount\s*:\s*-', body),
        re.search(r'\*\s*-1', body),
        re.search(r'-\s*amount', body),
        re.search(r'amount\s*\*\s*\(-1\)', body),
    ]
    result["negative_amounts"] = any(neg_patterns)

    # Preserves transaction_id
    result["preserves_transaction_id"] = bool(
        re.search(r'transaction_id|transactionId', body)
    ) and has_reversal_obj

    return result


def _check_recharge_logic(body: str) -> dict:
    """Check recharge record generation in function body."""
    result = {
        "generates_recharge": False,
        "internal_adjustment_flag": False,
        "correct_remaining_calc": False,
        "preserves_original_txid": False,
    }

    # Creates recharge objects
    has_recharge = bool(re.search(r'(recharge|remaining|leftover)', body, re.IGNORECASE))
    has_array_push = bool(re.search(r'(push\(|\.map\(|\[\s*\.\.\.|concat)', body))

    result["generates_recharge"] = has_recharge and has_array_push

    # Sets is_internal_adjustment: true in code (not comments)
    result["internal_adjustment_flag"] = bool(
        re.search(r'is_internal_adjustment\s*:\s*true|isInternalAdjustment\s*:\s*true', body)
    )

    # Calculates remaining = original - refund
    subtraction_patterns = [
        re.search(r'\w+\s*-\s*\w*(refund|gateway)', body, re.IGNORECASE),
        re.search(r'(remaining|left|net)\s*=', body, re.IGNORECASE),
        re.search(r'(original|total|paid)\w*\s*-\s*\w*(refund|amount)', body, re.IGNORECASE),
    ]
    result["correct_remaining_calc"] = sum(1 for p in subtraction_patterns if p) >= 1 and has_recharge

    # Preserves original transaction ID in recharge record
    result["preserves_original_txid"] = bool(
        re.search(r'original_transaction_id|originalTransactionId', body)
    ) and has_recharge

    return result


def _check_no_internal_transfer(body: str) -> bool:
    """Strategy 1 should NOT have a separate 'transfer between channels' step.
    The recharge records handle it implicitly."""
    # Look for explicit separate transfer logic (bad)
    transfer_patterns = [
        re.search(r'function\s+.*transfer', body, re.IGNORECASE),
        re.search(r'调账', body),
        re.search(r'internal_transfer|internalTransfer', body, re.IGNORECASE),
        re.search(r'channel_transfer|channelTransfer', body, re.IGNORECASE),
    ]
    has_bad_transfer = sum(1 for p in transfer_patterns if p) >= 2
    return not has_bad_transfer


def _check_error_path_type_safety(body: str) -> dict:
    """HIDDEN CHECK: Error return paths must be well-formed RefundResult.

    Strong models return { success: false, error: '...', reversal_records: [], gateway_refunds: [], recharge_records: [] }
    Weak models just return { success: false, error: '...' } missing the required array fields,
    or throw an error instead of returning a proper result.
    """
    result = {
        "returns_on_error": False,
        "error_has_empty_arrays": False,
        "no_throw_on_validation": False,
    }

    # Check that error paths use return (not throw) for validation failures
    # Pattern: if (...) { return { success: false ... } }
    has_return_false = bool(re.search(r'return\s*\{[^}]*success\s*:\s*false', body))
    result["returns_on_error"] = has_return_false

    # Check that error returns include empty array fields (not omitting them)
    # Look for patterns like: reversal_records: [] in the error return blocks
    # A well-formed error return should have all three array fields
    error_return_blocks = re.findall(
        r'return\s*\{[^}]*success\s*:\s*false[^}]*\}', body, re.DOTALL
    )
    if error_return_blocks:
        # Check if at least one error return includes empty arrays for the required fields
        has_empty_reversals = any(
            re.search(r'reversal_records\s*:\s*\[\s*\]|reversalRecords\s*:\s*\[\s*\]', block)
            for block in error_return_blocks
        )
        has_empty_gateway = any(
            re.search(r'gateway_refunds\s*:\s*\[\s*\]|gatewayRefunds\s*:\s*\[\s*\]', block)
            for block in error_return_blocks
        )
        has_empty_recharge = any(
            re.search(r'recharge_records\s*:\s*\[\s*\]|rechargeRecords\s*:\s*\[\s*\]', block)
            for block in error_return_blocks
        )
        result["error_has_empty_arrays"] = has_empty_reversals and has_empty_gateway and has_empty_recharge

    # Check that validation failures don't throw (they should return)
    # Look for throw near validation keywords — this is a penalty
    throw_on_validate = bool(re.search(
        r'(mismatch|exceed|capacity|not\s+found|invalid)[\s\S]{0,80}throw\s+new\s+Error',
        body, re.IGNORECASE
    ))
    # Also penalize if throw is the only error mechanism
    only_throws = bool(re.search(r'throw\s+new\s+Error', body)) and not has_return_false
    result["no_throw_on_validation"] = not throw_on_validate and not only_throws

    return result


def _check_defensive_coding(body: str, full_content: str) -> dict:
    """HIDDEN CHECK: Defensive coding practices.

    Strong models handle:
    - Empty activeRecords array (should still succeed with empty outputs)
    - Zero-amount refund channels (degenerate but valid)
    - Duplicate pay_modes in refund_channels (should aggregate or handle)
    - activeRecords with status != 'active' filtering (belt-and-suspenders)
    """
    result = {
        "handles_empty_records": False,
        "filters_active_status": False,
        "guards_zero_remaining": False,
        "aggregates_channels": False,
    }

    # Check for empty array guard or early return when no records
    empty_guards = [
        re.search(r'(activeRecords|active_records)\s*\.\s*length\s*(===?\s*0|<\s*1)', body),
        re.search(r'!\s*(activeRecords|active_records)\s*\.\s*length', body),
        re.search(r'(activeRecords|active_records)\s*\.\s*length\s*===?\s*0', body),
    ]
    result["handles_empty_records"] = any(empty_guards)

    # Check for filtering by status === 'active' (even though param says active,
    # defensive code double-checks)
    status_filter = bool(re.search(
        r'(status\s*===?\s*[\'"]active[\'"]|\.filter\s*\([^)]*status)', body
    ))
    result["filters_active_status"] = status_filter

    # Check for zero/negative remaining guard before creating recharge record
    # Pattern: if (remaining > 0) { push recharge } or remaining > 0 && ...
    zero_guard_patterns = [
        re.search(r'(remaining|left|diff|net)\w*\s*>\s*0', body, re.IGNORECASE),
        re.search(r'>\s*0\s*[\)&]', body),
        re.search(r'if\s*\([^)]*>\s*0[^)]*\)\s*\{[^}]*recharge', body, re.IGNORECASE),
    ]
    result["guards_zero_remaining"] = any(zero_guard_patterns)

    # Check for channel aggregation (Map/object grouping by pay_mode for channels)
    # Strong models aggregate duplicate channels before processing
    aggregation_patterns = [
        re.search(r'new\s+Map\s*\(', body),
        re.search(r'Map<\s*(PayMode|string)', body),
        re.search(r'Record<\s*(PayMode|string)', body),
        re.search(r'\{\s*\}\s*as\s*Record', body),
        re.search(r'reduce\s*\([^)]*\{[^}]*\[.*pay_mode', body, re.IGNORECASE),
        re.search(r'(group|merge|aggregate|consolidate)', body, re.IGNORECASE),
    ]
    # Also check in the full content (helper functions may be outside processRefund)
    full_agg_patterns = [
        re.search(r'function\s+\w*(group|aggregate|merge)\w*', full_content, re.IGNORECASE),
        re.search(r'(groupBy|group_by)', full_content, re.IGNORECASE),
    ]
    result["aggregates_channels"] = any(aggregation_patterns) or any(full_agg_patterns)

    return result


def _check_immutability(body: str, full_content: str) -> dict:
    """HIDDEN CHECK: Function should not mutate input parameters.

    Strong models:
    - Use .map() / spread to create new arrays rather than modifying inputs
    - Don't push into input arrays
    - Don't modify record.status or record.amount in-place
    """
    result = {
        "no_input_mutation": False,
        "uses_spread_or_copy": False,
    }

    # Penalty patterns: direct mutation of inputs
    mutation_patterns = [
        # Pushing into activeRecords/allocations
        re.search(r'(activeRecords|allocations|request)\s*\.\s*push\s*\(', body),
        # Modifying record properties
        re.search(r'(record|rec)\s*\.\s*(status|amount)\s*=', body),
        # Splicing input arrays
        re.search(r'(activeRecords|allocations)\s*\.\s*splice\s*\(', body),
        # Direct assignment to input items
        re.search(r'request\s*\.\s*(refund_items|refund_channels)\s*\[', body),
    ]
    has_mutation = any(mutation_patterns)
    result["no_input_mutation"] = not has_mutation

    # Positive: uses spread operator or Array.from or slice for copies
    copy_patterns = [
        re.search(r'\[\s*\.\.\.', body),
        re.search(r'Array\s*\.\s*from\s*\(', body),
        re.search(r'\.slice\s*\(\s*\)', body),
        re.search(r'structuredClone\s*\(', body),
        # Using map/filter (creates new array) is fine
        re.search(r'\.\s*map\s*\(', body),
        re.search(r'\.\s*filter\s*\(', body),
    ]
    result["uses_spread_or_copy"] = sum(1 for p in copy_patterns if p) >= 2

    return result


def _check_gateway_txid_resolution(body: str) -> dict:
    """HIDDEN CHECK: Gateway refund must resolve original_transaction_id from active records.

    Strong models look up the transaction_id from the activeRecord that matches the
    pay_mode of each gateway refund channel. This requires finding/filtering records
    by pay_mode and extracting their transaction_id.

    Weak models either:
    - Hardcode null for original_transaction_id
    - Use request fields that don't contain transaction_id
    - Skip the lookup entirely
    """
    result = {
        "looks_up_txid_by_channel": False,
        "uses_find_or_filter_for_txid": False,
        "maps_channel_to_record": False,
    }

    # Strong pattern: find/filter activeRecords by pay_mode to get transaction_id
    # e.g., activeRecords.find(r => r.pay_mode === channel.pay_mode)?.transaction_id
    # or: channelRecordMap.get(channel.pay_mode)?.transaction_id
    lookup_patterns = [
        re.search(r'(find|filter)\s*\([^)]*pay_mode\s*(===?|==)', body),
        re.search(r'(find|filter)\s*\([^)]*payMode\s*(===?|==)', body),
        re.search(r'\.\s*get\s*\(\s*\w*\.\s*(pay_mode|payMode)\s*\)', body),
        re.search(r'\[\s*\w*\.\s*(pay_mode|payMode)\s*\]', body),
    ]
    # Must be near transaction_id context
    has_txid_context = bool(re.search(
        r'(transaction_id|transactionId)', body
    ))
    result["looks_up_txid_by_channel"] = any(lookup_patterns) and has_txid_context

    # Specifically uses find/filter to locate the right record for gateway
    # This is more targeted: within gateway refund generation logic,
    # there must be a lookup from records
    gateway_section_patterns = [
        # find record matching channel's pay_mode for txid
        re.search(r'(gateway|refund_channel|refundChannel)[\s\S]{0,200}(find|filter)\s*\([^)]*pay_mode', body, re.IGNORECASE),
        re.search(r'(find|filter)\s*\([^)]*pay_mode[\s\S]{0,100}(transaction_id|transactionId)', body),
    ]
    result["uses_find_or_filter_for_txid"] = any(gateway_section_patterns)

    # Uses a map/record structure to pre-index records by channel
    # Strong models often build a channelMap first, then look up per channel
    map_patterns = [
        re.search(r'(Map|Record|Object)\s*[<(][\s\S]{0,50}(pay_mode|PayMode|string)', body),
        re.search(r'new\s+Map\s*\([\s\S]{0,100}pay_mode', body, re.IGNORECASE),
        re.search(r'(\w+Map|\w+Record|\w+Index)\s*[\[.]\s*\w*\.\s*(pay_mode|payMode)', body),
        re.search(r'(byChannel|byPayMode|channelMap|recordMap|recordsByChannel)', body, re.IGNORECASE),
    ]
    result["maps_channel_to_record"] = any(map_patterns)

    return result


def _check_structured_channel_accounting(body: str) -> dict:
    """HIDDEN CHECK: Per-channel total accumulation before processing.

    Strong models compute per-channel original payment totals (by grouping activeRecords
    by pay_mode and summing amounts) BEFORE doing the capacity check or recharge calc.
    This is the correct algorithmic approach.

    Weak models either:
    - Do N^2 nested loops (for each channel, loop all records)
    - Don't properly accumulate totals (just check first record)
    - Skip the grouping step and rely on single-record assumptions
    """
    result = {
        "builds_channel_totals_map": False,
        "iterates_records_for_totals": False,
        "uses_accumulator_pattern": False,
    }

    # Pattern: builds a map/object of pay_mode -> total_amount from activeRecords
    # e.g., const channelTotals = new Map<PayMode, number>();
    #        activeRecords.forEach(r => { channelTotals.set(r.pay_mode, (channelTotals.get(r.pay_mode) || 0) + r.amount) })
    # or:   const totals = activeRecords.reduce((acc, r) => { acc[r.pay_mode] = (acc[r.pay_mode] || 0) + r.amount; return acc; }, {})
    map_build_patterns = [
        # Map-based accumulation
        re.search(r'new\s+Map\s*[<(]', body),
        # Object-based accumulation with indexing by pay_mode
        re.search(r'\[\s*\w*\.\s*(pay_mode|payMode)\s*\]\s*=', body),
        re.search(r'\[\s*\w*\.\s*(pay_mode|payMode)\s*\]\s*\+=', body),
        # .set() with pay_mode key
        re.search(r'\.set\s*\(\s*\w*\.\s*(pay_mode|payMode)', body),
    ]
    result["builds_channel_totals_map"] = any(map_build_patterns)

    # Pattern: iterates records with accumulation into structure
    # reduce with pay_mode key, or forEach with assignment
    iterate_patterns = [
        re.search(r'(activeRecords|active_records|records)\s*\.\s*(reduce|forEach)\s*\([^)]*\{[\s\S]{0,200}(pay_mode|payMode)', body),
        re.search(r'for\s*\(\s*(const|let)\s+\w+\s+of\s+(activeRecords|active_records|records)\s*\)[\s\S]{0,200}(pay_mode|payMode)[\s\S]{0,100}\+', body),
    ]
    result["iterates_records_for_totals"] = any(iterate_patterns)

    # Accumulator pattern: += or (get() || 0) + amount
    acc_patterns = [
        re.search(r'\|\|\s*0\s*\)\s*\+\s*\w*\.?\s*amount', body),
        re.search(r'\?\?\s*0\s*\)\s*\+\s*\w*\.?\s*amount', body),
        re.search(r'\+=\s*\w*\.?\s*amount', body),
        re.search(r'amount\s*\+\s*\(', body),
    ]
    result["uses_accumulator_pattern"] = any(acc_patterns)

    return result


def _check_result_shape_completeness(body: str) -> dict:
    """HIDDEN CHECK: Success path returns complete, correctly-shaped RefundResult.

    Strong models ensure the success return has:
    - success: true (explicit)
    - All three array fields present (reversal_records, gateway_refunds, recharge_records)
    - No 'as any' type casting on the return
    - Proper object literal structure (not building incrementally with mutation)

    Weak models often:
    - Forget 'success: true' in the return
    - Use 'as any' or 'as RefundResult' type assertions
    - Build result incrementally (result.reversal_records = ...) instead of a clean return
    """
    result = {
        "success_true_in_return": False,
        "all_fields_in_single_return": False,
        "no_type_assertion_on_return": False,
    }

    # Check for return { success: true, ... } with all fields
    success_return_pattern = re.search(
        r'return\s*\{[^}]*success\s*:\s*true', body, re.DOTALL
    )
    result["success_true_in_return"] = bool(success_return_pattern)

    # Check that the success return block includes all three array fields
    # Extract the success return block
    success_returns = re.findall(
        r'return\s*\{([^}]*success\s*:\s*true[^}]*)\}', body, re.DOTALL
    )
    if not success_returns:
        # Try multi-line return with nested objects
        success_returns = re.findall(
            r'return\s*\{([\s\S]*?success\s*:\s*true[\s\S]*?)\n\s*\};?', body
        )

    if success_returns:
        for block in success_returns:
            has_reversals = bool(re.search(r'reversal_records|reversalRecords', block))
            has_gateway = bool(re.search(r'gateway_refunds|gatewayRefunds', block))
            has_recharge = bool(re.search(r'recharge_records|rechargeRecords', block))
            if has_reversals and has_gateway and has_recharge:
                result["all_fields_in_single_return"] = True
                break

    # Check for absence of 'as any' or 'as RefundResult' type assertions near return
    type_assertion_patterns = [
        re.search(r'as\s+any', body),
        re.search(r'as\s+RefundResult', body),
        re.search(r'<RefundResult>\s*\{', body),
    ]
    has_type_assertion = any(type_assertion_patterns)
    result["no_type_assertion_on_return"] = not has_type_assertion

    return result


def grade_workspace(ws: Path) -> dict:
    engine_file = _find_refund_engine(ws)
    if not engine_file:
        return {
            "overall_score": 0.0,
            "components": {"file_found": 0.0},
            "error": "refund-engine.ts not found",
        }

    content = _read(engine_file)
    if not content:
        return {
            "overall_score": 0.0,
            "components": {"file_readable": 0.0},
            "error": "refund-engine.ts is empty",
        }

    # Strip comments for analysis
    code = _strip_comments(content)

    # Extract function body
    body = _extract_function_body(code, "processRefund")

    # Also get full file content (stripped) for helper function checks
    all_ts_files = _find_all_ts_files(ws)
    full_project_code = code
    for f in all_ts_files:
        if f != engine_file:
            full_project_code += "\n" + _strip_comments(_read(f))

    # --- Dimension 1: Function exists and is implemented (EASY) ---
    impl = _check_function_implemented(body)
    sig_score = (
        0.3 * impl["exists"] +
        0.3 * impl["implemented"] +
        0.4 * impl["has_logic"]
    )

    # --- Dimension 2: Validation logic (MEDIUM) ---
    val = _check_validation_logic(body)
    val_score = (
        0.4 * val["channel_capacity_check"] +
        0.35 * val["amount_mismatch_check"] +
        0.25 * val["item_existence_check"]
    )

    # --- Dimension 3: Reversal logic (MEDIUM) ---
    rev = _check_reversal_logic(body)
    rev_score = (
        0.4 * rev["generates_reversals"] +
        0.3 * rev["negative_amounts"] +
        0.3 * rev["preserves_transaction_id"]
    )

    # --- Dimension 4: Recharge logic (MEDIUM) ---
    rch = _check_recharge_logic(body)
    rch_score = (
        0.3 * rch["generates_recharge"] +
        0.25 * rch["internal_adjustment_flag"] +
        0.25 * rch["correct_remaining_calc"] +
        0.2 * rch["preserves_original_txid"]
    )

    # --- Dimension 5: No internal transfer (EASY) ---
    no_transfer = _check_no_internal_transfer(body)
    no_transfer_score = 1.0 if no_transfer else 0.0

    # --- Dimension 6: HIDDEN — Error path type safety (HARD) ---
    err_type = _check_error_path_type_safety(body)
    err_type_score = (
        0.3 * err_type["returns_on_error"] +
        0.4 * err_type["error_has_empty_arrays"] +
        0.3 * err_type["no_throw_on_validation"]
    )

    # --- Dimension 7: HIDDEN — Defensive coding (HARD) ---
    defensive = _check_defensive_coding(body, full_project_code)
    defensive_score = (
        0.2 * defensive["handles_empty_records"] +
        0.25 * defensive["filters_active_status"] +
        0.30 * defensive["guards_zero_remaining"] +
        0.25 * defensive["aggregates_channels"]
    )

    # --- Dimension 8: HIDDEN — Immutability (HARD) ---
    immut = _check_immutability(body, full_project_code)
    immut_score = (
        0.5 * immut["no_input_mutation"] +
        0.5 * immut["uses_spread_or_copy"]
    )

    # --- Dimension 9: HIDDEN — Gateway txid resolution (HARD) ---
    gw_txid = _check_gateway_txid_resolution(body)
    gw_txid_score = (
        0.4 * gw_txid["looks_up_txid_by_channel"] +
        0.35 * gw_txid["uses_find_or_filter_for_txid"] +
        0.25 * gw_txid["maps_channel_to_record"]
    )

    # --- Dimension 10: HIDDEN — Structured channel accounting (HARD) ---
    chan_acct = _check_structured_channel_accounting(body)
    chan_acct_score = (
        0.4 * chan_acct["builds_channel_totals_map"] +
        0.35 * chan_acct["iterates_records_for_totals"] +
        0.25 * chan_acct["uses_accumulator_pattern"]
    )

    # --- Dimension 11: HIDDEN — Result shape completeness (HARD) ---
    result_shape = _check_result_shape_completeness(body)
    result_shape_score = (
        0.3 * result_shape["success_true_in_return"] +
        0.4 * result_shape["all_fields_in_single_return"] +
        0.3 * result_shape["no_type_assertion_on_return"]
    )

    # Weights: reduce easy checks, boost hidden hard checks
    weights = {
        "function_implemented": 0.05,           # trivial — any model passes
        "validation_logic": 0.13,               # medium
        "reversal_logic": 0.10,                 # medium
        "recharge_logic": 0.12,                 # medium
        "no_internal_transfer": 0.05,           # trivial — nearly all pass
        "error_path_type_safety": 0.13,         # HIDDEN — hard
        "defensive_coding": 0.12,               # HIDDEN — hard
        "immutability": 0.07,                   # HIDDEN — moderate
        "gateway_txid_resolution": 0.10,        # HIDDEN — hard (new)
        "structured_channel_accounting": 0.07,  # HIDDEN — hard (new)
        "result_shape_completeness": 0.06,      # HIDDEN — moderate (new)
    }

    components = {
        "function_implemented": round(sig_score, 4),
        "validation_logic": round(val_score, 4),
        "reversal_logic": round(rev_score, 4),
        "recharge_logic": round(rch_score, 4),
        "no_internal_transfer": round(no_transfer_score, 4),
        "error_path_type_safety": round(err_type_score, 4),
        "defensive_coding": round(defensive_score, 4),
        "immutability": round(immut_score, 4),
        "gateway_txid_resolution": round(gw_txid_score, 4),
        "structured_channel_accounting": round(chan_acct_score, 4),
        "result_shape_completeness": round(result_shape_score, 4),
    }

    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": components,
        "weights": weights,
        "details": {
            "implementation": impl,
            "validation": val,
            "reversal": rev,
            "recharge": rch,
            "no_transfer": no_transfer,
            "error_path_type_safety": err_type,
            "defensive_coding": defensive,
            "immutability": immut,
            "gateway_txid_resolution": gw_txid,
            "structured_channel_accounting": chan_acct,
            "result_shape_completeness": result_shape,
        },
    }


def main():
    # Try workspace path then fixtures path
    ws = Path("/workspace/fixtures/casher-refund")
    if not ws.exists():
        ws = Path("/workspace/casher-refund")
    if not ws.exists():
        ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
