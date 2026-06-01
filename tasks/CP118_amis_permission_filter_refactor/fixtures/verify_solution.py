"""Hidden verifier for CP118 — AMIS Permission Filter Refactor & visibleOn Bug Fix."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for correct implementation of:
    1. imagesQueryAdaptor using permissField for filtering
    2. visibleOn bug fix (data.sign_info -> sign_info in input-table rows)
    3. onClick handler refactoring into reusable functions
    """
    base = ws / "merch-info-app" / "src"

    # Try alternate path
    if not base.exists():
        base = ws / "fixtures" / "merch-info-app" / "src"
    if not base.exists():
        # Try finding it
        for candidate in [
            ws / "merch-info-app" / "src",
            ws / "fixtures" / "merch-info-app" / "src",
            ws / "src",
        ]:
            if candidate.exists():
                base = candidate
                break

    components = {k: 0.0 for k in [
        "permiss_field_filtering",
        "backward_compatible",
        "visible_on_fix",
        "handler_refactored",
        "no_data_prefix_in_visible_on",
    ]}

    # --- Check 1: imagesQueryAdaptor uses permissField for filtering ---
    dialog_file = None
    for candidate in [
        base / "pages" / "merchInfo" / "merchInfoSearch" / "components" / "viewImagesDialog.ts",
        base / "pages" / "merchInfo" / "components" / "viewImagesDialog.ts",
    ]:
        if candidate.exists():
            dialog_file = candidate
            break

    # Also search recursively
    if not dialog_file and base.exists():
        for p in base.rglob("viewImagesDialog.ts"):
            dialog_file = p
            break

    if dialog_file:
        content = _read(dialog_file)

        # Check if permissField is actually used for filtering logic INSIDE
        # the imagesQueryAdaptor function body (not just imported/declared).
        # The key pattern: btnPermission(permissField) call + .filter() on the list
        # Must be inside the adaptor function, not just anywhere in the file.

        # Find the adaptor function body
        adaptor_match = re.search(
            r'(imagesQueryAdaptor|adaptor)\s*[=:]\s*\(?[^)]*permiss\w*[^)]*\)?\s*=>\s*\{(.*?)\n\}',
            content, re.DOTALL
        )
        adaptor_body = adaptor_match.group(2) if adaptor_match else ""

        # Also check for standalone function pattern
        if not adaptor_body:
            adaptor_match2 = re.search(
                r'function\s+imagesQueryAdaptor[^{]*\{(.*?)\n\}',
                content, re.DOTALL
            )
            adaptor_body = adaptor_match2.group(1) if adaptor_match2 else ""

        # If still empty, look for any function containing both permiss and filter
        if not adaptor_body:
            # Broader search: any block that uses permissField AND filter
            blocks = re.findall(r'\{[^{}]*(?:permiss\w*)[^{}]*filter[^{}]*\}', content, re.DOTALL)
            adaptor_body = "\n".join(blocks)

        has_permission_call_in_adaptor = bool(
            re.search(r'btnPermission\s*\(\s*permiss\w*\s*\)', adaptor_body)
        )
        has_filter_in_adaptor = bool(
            re.search(r'\.filter\s*\(', adaptor_body)
            and re.search(r'pic_type', adaptor_body)
        )
        has_conditional = bool(
            re.search(r'if\s*\(', adaptor_body)
            and re.search(r'permiss\w*', adaptor_body)
        )

        if has_permission_call_in_adaptor and has_filter_in_adaptor and has_conditional:
            components["permiss_field_filtering"] = 1.0
        elif has_permission_call_in_adaptor and has_filter_in_adaptor:
            components["permiss_field_filtering"] = 0.8
        elif has_filter_in_adaptor and has_conditional:
            components["permiss_field_filtering"] = 0.6
        elif has_permission_call_in_adaptor or has_filter_in_adaptor:
            components["permiss_field_filtering"] = 0.3
        else:
            components["permiss_field_filtering"] = 0.0

        # Check 2: Backward compatibility - when no permissField, show all images
        # The filtering logic must be conditional on permissField being present.
        # A correct implementation has: if (permissField) { ... filter ... } else { ... show all ... }
        # OR: early-return / ternary that bypasses filter when permissField is falsy.
        # We only give credit if the FILTERING code path is guarded.
        if adaptor_body:
            has_guarded_filter = bool(
                re.search(r'if\s*\(\s*!?\s*permiss\w*\s*\)', adaptor_body)
                or re.search(r'permiss\w*\s*\?\s', adaptor_body)
                or re.search(r'if\s*\(\s*permiss\w*\s*&&', adaptor_body)
            )
            if has_guarded_filter:
                components["backward_compatible"] = 1.0
            elif re.search(r'permiss\w*', adaptor_body) and re.search(r'filter', adaptor_body):
                # Has both but not clearly guarded
                components["backward_compatible"] = 0.5
            else:
                components["backward_compatible"] = 0.0
        else:
            components["backward_compatible"] = 0.0

    # --- Check 3: visibleOn bug fix in detail.ts ---
    detail_file = None
    for candidate in [
        base / "pages" / "merchInfo" / "merchInfoSearch" / "basicInfo" / "detail.ts",
        base / "pages" / "merchInfo" / "basicInfo" / "detail.ts",
    ]:
        if candidate.exists():
            detail_file = candidate
            break

    if not detail_file and base.exists():
        for p in base.rglob("detail.ts"):
            if "basicInfo" in str(p) or "merchInfo" in str(p):
                detail_file = p
                break

    if detail_file:
        content = _read(detail_file)

        # Check: settlement protocol (agreement_type "2") visibleOn should
        # NOT use "data.sign_info" prefix. In input-table row context,
        # the correct reference is just "sign_info" (row-level scope).
        #
        # Bug pattern: ARRAYSOME(data.sign_info, ...) in settlement section
        # Fixed pattern: ARRAYSOME(sign_info, ...) without data. prefix

        # Find all visibleOn expressions related to agreement_type "2"
        settlement_visible_ons = re.findall(
            r"visibleOn[^']*'([^']*agreement_type\s*===?\s*[\"']2[\"'][^']*)'",
            content
        )

        if settlement_visible_ons:
            # Check if any still use data.sign_info (the bug)
            bug_present = any("data.sign_info" in expr for expr in settlement_visible_ons)
            all_fixed = all("data.sign_info" not in expr for expr in settlement_visible_ons)
            uses_sign_info = any("sign_info" in expr for expr in settlement_visible_ons)

            if all_fixed and uses_sign_info:
                components["visible_on_fix"] = 1.0
            elif not bug_present:
                components["visible_on_fix"] = 0.8
            else:
                components["visible_on_fix"] = 0.0
        else:
            # If no settlement visibleOn found at all, check if restructured
            has_settlement = "agreement_type" in content and '"2"' in content
            if has_settlement and "data.sign_info" not in content:
                components["visible_on_fix"] = 0.8
            elif has_settlement:
                components["visible_on_fix"] = 0.3

        # Check 4: onClick handlers refactored into reusable functions
        # The original has 4 inline `script:` blocks with nearly identical logic.
        # A proper refactor means: extracted named function(s) AND inline scripts
        # replaced by calls to those functions (or removed entirely if using
        # AMIS actionType approach).
        #
        # Key signal: The inline scripts should CALL an extracted function rather
        # than contain the full open-protocol logic themselves.

        # Count inline script blocks with full protocol-opening logic
        # "Full" means the script contains window.open AND filter/if logic
        full_inline_scripts = re.findall(
            r'script:\s*`[^`]*window\.open[^`]*`',
            content
        )

        # Check for extracted reusable functions that encapsulate the logic
        extracted_funcs = re.findall(
            r'(?:function|const|let|var)\s+(\w*(?:open|handle|view)\w*(?:[Pp]rotocol|[Aa]greement|[Ss]ign)\w*)',
            content, re.IGNORECASE
        )
        # Also check for functions that take agreementType as parameter
        generic_handlers = re.findall(
            r'(?:function|const|let|var)\s+(\w+)\s*\([^)]*agreement[Tt]ype',
            content
        )
        all_extracted = set(extracted_funcs + generic_handlers)

        # Check if extracted functions are actually CALLED in the event handlers
        func_calls_in_scripts = 0
        all_scripts = re.findall(r'script:\s*`([^`]*)`', content)
        for script_body in all_scripts:
            for func_name in all_extracted:
                if func_name in script_body:
                    func_calls_in_scripts += 1
                    break

        if len(all_extracted) >= 1 and len(full_inline_scripts) == 0 and func_calls_in_scripts >= 2:
            components["handler_refactored"] = 1.0
        elif len(all_extracted) >= 1 and len(full_inline_scripts) <= 1 and func_calls_in_scripts >= 1:
            components["handler_refactored"] = 0.8
        elif len(all_extracted) >= 1 and len(full_inline_scripts) <= 2:
            components["handler_refactored"] = 0.5
        elif len(full_inline_scripts) < 4:
            # Some reduction but no clear extraction
            components["handler_refactored"] = 0.2
        else:
            components["handler_refactored"] = 0.0

        # Check 5: No remaining data.sign_info in visibleOn (comprehensive check)
        # ALL visibleOn expressions in input-table columns should use row scope
        all_visible_ons = re.findall(r"visibleOn[^']*'([^']*)'", content)
        bad_scopes = [v for v in all_visible_ons if "data.sign_info" in v]
        if not bad_scopes:
            components["no_data_prefix_in_visible_on"] = 1.0
        elif len(bad_scopes) <= 1:
            components["no_data_prefix_in_visible_on"] = 0.5
        else:
            components["no_data_prefix_in_visible_on"] = 0.0

    weights = {
        "permiss_field_filtering": 0.30,
        "backward_compatible": 0.10,
        "visible_on_fix": 0.30,
        "handler_refactored": 0.15,
        "no_data_prefix_in_visible_on": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try /workspace/fixtures first, then /workspace
    ws = Path("/workspace/fixtures")
    if not (ws / "merch-info-app").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
