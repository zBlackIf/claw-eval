"""Hidden verifier for CP166 — dotnet refund API Java migration."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_comments(code: str) -> str:
    """Remove Java single-line (//) and multi-line (/* */) comments."""
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Remove single-line comments
    code = re.sub(r'//.*', '', code)
    return code


def _find_java_files(base: Path, pattern: str) -> list[Path]:
    """Find Java files matching a glob pattern recursively."""
    results = []
    if base.exists():
        for p in base.rglob(pattern):
            if p.is_file():
                results.append(p)
    return results


def _has_method_declaration(code: str, method_name: str) -> bool:
    """Check if code contains an actual method declaration (not just a reference in comment)."""
    # Look for pattern like: returnType methodName(
    pattern = rf'(?:public|private|protected|default)?\s+\w[\w<>,\s]*\s+{method_name}\s*\('
    return bool(re.search(pattern, code))


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for correct dotnet-to-Java migration."""
    base = ws / "myky-finance-manage"

    # Fallback: try fixtures path
    if not base.exists():
        base = ws / "fixtures" / "myky-finance-manage"

    src = base / "src" / "main" / "java"

    components = {k: 0.0 for k in [
        "controller_endpoint",
        "request_dto",
        "service_interface_method",
        "service_impl_order_type_branch",
        "rpc_client_method",
        "fallback_method",
        "route_convention",
    ]}

    # 1. Controller has /financial-system-refund endpoint with actual method
    controller_files = _find_java_files(src, "*Controller*.java")
    for cf in controller_files:
        raw = _read(cf)
        c = _strip_comments(raw)
        if "financial-system-refund" in c:
            # Must have actual @PostMapping annotation on a real method
            has_post_mapping = bool(re.search(
                r'@PostMapping\s*\(\s*["\'].*financial-system-refund.*["\']\s*\)',
                c
            ))
            has_method = _has_method_declaration(c, r'financialSystemRefund|financial[Ss]ystem[Rr]efund\w*')
            has_requestbody = "@RequestBody" in c and "financial-system-refund" in c
            has_result = "Result" in c

            score = 0.0
            if has_post_mapping:
                score += 0.4
            if has_method or has_post_mapping:
                score += 0.2
            if has_requestbody:
                score += 0.2
            if has_result:
                score += 0.2
            components["controller_endpoint"] = min(1.0, score)
            break

    # 2. Request DTO with proper fields - must be a NEW class (not RefundReq which exists)
    # Need a DTO that has orderType field (key differentiator from existing RefundReq)
    dto_files = _find_java_files(src, "*.java")
    for df in dto_files:
        raw = _read(df)
        c = _strip_comments(raw)
        # Must be a class with orderType field (the key new field)
        if "class" in c and ("controller" not in df.name.lower()) and ("service" not in df.name.lower()):
            has_order_type = bool(re.search(r'(?:private|protected|public)\s+\w+\s+orderType', c))
            if not has_order_type:
                has_order_type = bool(re.search(r'OrderType\s+\w+|String\s+orderType|Integer\s+orderType', c))
            if has_order_type:
                has_order_code = bool(re.search(r'(?:private|protected|public)\s+\w+\s+orderCode', c))
                has_refund_amount = bool(re.search(r'(?:private|protected|public)\s+\w+\s+refundAmount', c))
                has_refund_reason = bool(re.search(r'(?:private|protected|public)\s+\w+\s+refundReason', c))
                has_operator = bool(re.search(r'(?:private|protected|public)\s+\w+\s+operator', c))
                field_count = sum([True, has_order_code, has_refund_amount, has_refund_reason, has_operator])
                components["request_dto"] = min(1.0, field_count / 5.0 + 0.2)
                break

    # 3. Service interface declares the method (actual method signature, not comment)
    service_ifaces = _find_java_files(src, "*Service.java")
    for sf in service_ifaces:
        raw = _read(sf)
        c = _strip_comments(raw)
        if "interface" in c:
            # Look for actual method declaration
            if _has_method_declaration(c, "financialSystemRefund"):
                components["service_interface_method"] = 1.0
                break

    # 4. Service impl has order-type branching logic (THE KEY DISCRIMINATION POINT)
    impl_files = _find_java_files(src, "*ServiceImpl*.java")
    impl_files += _find_java_files(src, "*Impl*.java")
    for imf in impl_files:
        raw = _read(imf)
        c = _strip_comments(raw)
        if _has_method_declaration(c, "financialSystemRefund"):
            # Check for order type branching
            has_branch = False
            branch_patterns = [
                r'if\s*\(.*orderType.*==',
                r'if\s*\(.*OrderType.*==',
                r'if\s*\(.*getOrderType\(\)',
                r'switch\s*\(.*orderType',
                r'switch\s*\(.*OrderType',
                r'if\s*\(.*[Aa]ppointment',
                r'if\s*\(.*[Ss]hop',
                r'case\s+.*APPOINTMENT',
                r'case\s+.*SHOP',
                r'equals\s*\(\s*.*[Aa]ppointment',
                r'equals\s*\(\s*.*[Ss]hop',
            ]
            for pat in branch_patterns:
                if re.search(pat, c):
                    has_branch = True
                    break

            # Check for two different refund channels
            has_huifu = bool(re.search(r'refundPartially|huifu|scanPay|PaymentScanPay', c, re.IGNORECASE))
            has_wechat = bool(re.search(r'wechat|wxRefund|WeChatRefund|wechatRefund', c, re.IGNORECASE))

            # Check for status update after refund
            has_status_update = bool(re.search(r'[Rr]efunded|updateOrder|setOrderStatus|setStatus', c))

            # Check for error handling
            has_error = "throw" in c and "Exception" in c

            score = 0.0
            if has_branch:
                score += 0.35
            if has_huifu or has_wechat:
                score += 0.25
            if has_huifu and has_wechat:
                score += 0.15  # Both channels = extra credit
            if has_status_update:
                score += 0.15
            if has_error:
                score += 0.10

            components["service_impl_order_type_branch"] = min(1.0, score)
            break

    # 5. RPC client has the method with @PostExchange
    rpc_files = _find_java_files(src, "*RpcClient*.java")
    rpc_files += _find_java_files(src, "*Client*.java")
    for rf in rpc_files:
        raw = _read(rf)
        c = _strip_comments(raw)
        if "interface" in c or "Exchange" in c:
            # Must have @PostExchange with the correct path
            has_exchange = bool(re.search(
                r'@PostExchange\s*\(\s*["\'].*financial-system-refund.*["\']\s*\)',
                c
            ))
            has_method = _has_method_declaration(c, "financialSystemRefund")
            if has_exchange or has_method:
                score = 0.0
                if has_method:
                    score += 0.5
                if has_exchange:
                    score += 0.5
                components["rpc_client_method"] = min(1.0, score)
                break

    # 6. Fallback factory has the method implementation
    fallback_files = _find_java_files(src, "*Fallback*.java")
    for ff in fallback_files:
        raw = _read(ff)
        c = _strip_comments(raw)
        if _has_method_declaration(c, "financialSystemRefund"):
            components["fallback_method"] = 1.0
            break

    # 7. Route convention check
    for cf in controller_files:
        raw = _read(cf)
        c = _strip_comments(raw)
        if "financial-system-refund" in c:
            has_correct_base = bool(re.search(r'@RequestMapping\s*\(\s*["\'].*/api/web/hospital-ten-pay.*["\']\s*\)', c))
            has_kebab_case = "financial-system-refund" in c
            # The endpoint should NOT use PascalCase dotnet route
            uses_pascal = "FinancialSystemRefundInfo" in c and "financial-system-refund" not in c

            score = 0.0
            if has_correct_base:
                score += 0.4
            if has_kebab_case:
                score += 0.4
            if not uses_pascal:
                score += 0.2
            components["route_convention"] = min(1.0, score)
            break

    weights = {
        "controller_endpoint": 0.15,
        "request_dto": 0.10,
        "service_interface_method": 0.10,
        "service_impl_order_type_branch": 0.30,  # Main discrimination
        "rpc_client_method": 0.15,
        "fallback_method": 0.10,
        "route_convention": 0.10,
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
    if not (ws / "myky-finance-manage").exists() and (ws / "fixtures" / "myky-finance-manage").exists():
        result = grade_workspace(ws / "fixtures")
    else:
        result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
