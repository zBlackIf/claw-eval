"""Hidden verifier for CP167 — React FilterBox + MyPaginationV2 refactor."""
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
    """Grade the SalesPlan page refactoring."""
    # Try multiple possible paths
    sales_plan = None
    for candidate in [
        ws / "fixtures" / "salestable" / "src" / "pages" / "SalesPlan" / "index.tsx",
        ws / "salestable" / "src" / "pages" / "SalesPlan" / "index.tsx",
    ]:
        if candidate.exists():
            sales_plan = candidate
            break

    if not sales_plan:
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "SalesPlan/index.tsx not found",
        }

    content = _read(sales_plan)

    components = {k: 0.0 for k in [
        "filterbox_imported",
        "filterbox_used_in_jsx",
        "pagination_v2_imported",
        "pagination_v2_used_in_jsx",
        "resize_height_hook",
        "table_size_small",
        "extra_actions_configured",
        "collapsible_configured",
        "old_filter_removed",
        # Hidden harder checks
        "filter_items_completeness",
        "compid_consistency",
        "scroll_y_dynamic",
        "old_wrapper_cleanup",
        "pagination_table_disabled",
        # Hidden advanced checks (discriminators between strong/weak)
        "format_cascade_logic",
        "forwardref_cleanup",
        "filter_state_consolidation",
    ]}

    # 1. FilterBox imported
    if re.search(r"import\s+.*FilterBox.*from\s+['\"]@/components/commonTools/FilterBox", content):
        components["filterbox_imported"] = 1.0
    elif "FilterBox" in content and "import" in content:
        components["filterbox_imported"] = 0.5

    # 2. FilterBox used in JSX (check for <FilterBox ... /> or <FilterBox ...>)
    if re.search(r"<FilterBox[\s\n]", content):
        components["filterbox_used_in_jsx"] = 1.0
        # Check if filterItems prop is passed
        if "filterItems" not in content:
            components["filterbox_used_in_jsx"] = 0.6

    # 3. MyPaginationV2 imported
    if re.search(r"import\s+.*MyPaginationV2.*from\s+['\"]@/components/commonTools/MyPagination/MyPaginationV2", content) or \
       re.search(r"import\s+.*MyPaginationV2.*from\s+['\"]@/components/commonTools/MyPagination/MyPagintionV2", content):
        components["pagination_v2_imported"] = 1.0
    elif "MyPaginationV2" in content and "import" in content:
        components["pagination_v2_imported"] = 0.5

    # 4. MyPaginationV2 used in JSX
    if re.search(r"<MyPaginationV2[\s\n]", content):
        components["pagination_v2_used_in_jsx"] = 1.0
        # Check for correct props (current, total, pageSize, onChange)
        v2_section = content[content.find("<MyPaginationV2"):]
        v2_section = v2_section[:v2_section.find("/>") + 2] if "/>" in v2_section else v2_section[:500]
        has_current = "current=" in v2_section or "current =" in v2_section
        has_total = "total=" in v2_section or "total =" in v2_section
        has_onChange = "onChange=" in v2_section or "onChange =" in v2_section
        if has_current and has_total and has_onChange:
            components["pagination_v2_used_in_jsx"] = 1.0
        else:
            components["pagination_v2_used_in_jsx"] = 0.6

    # 5. useResizeHeight hook
    if re.search(r"import\s+.*useResizeHeight.*from\s+['\"]@/hooks/useResizeHeight", content):
        components["resize_height_hook"] = 0.5
        # Check if it's actually called
        if re.search(r"useResizeHeight\s*\(", content):
            components["resize_height_hook"] = 1.0
    elif "useResizeHeight" in content:
        components["resize_height_hook"] = 0.3

    # 6. Table size="small"
    if re.search(r'size\s*=\s*["\']small["\']', content) or re.search(r"size\s*=\s*\{['\"]small['\"]\}", content):
        components["table_size_small"] = 1.0

    # 7. extraActions configured (buttons in FilterBox extraActions)
    if "extraActions" in content:
        components["extra_actions_configured"] = 0.5
        # Check if both export and create buttons are associated with extraActions.
        # Look at a broad region after the extraActions prop starts.
        ea_start = content.find("extraActions")
        if ea_start >= 0:
            # Grab a generous region (extraActions content can be multi-line JSX)
            ea_content = content[ea_start:ea_start + 800]
            has_export = bool(re.search(r"(导出|export|Export|handleExport|postSalesPlanListExport)", ea_content, re.IGNORECASE))
            has_create = bool(re.search(r"(新建销售方案|新建|PlusOutlined|newSalesPlan)", ea_content, re.IGNORECASE))
            if has_export and has_create:
                components["extra_actions_configured"] = 1.0
            elif has_export or has_create:
                components["extra_actions_configured"] = 0.7

    # 8. collapsible and collapsedRows configured
    if "collapsible" in content:
        components["collapsible_configured"] = 0.5
        if re.search(r"collapsedRows\s*=\s*\{?\s*2\s*\}?", content):
            components["collapsible_configured"] = 1.0
        elif "collapsedRows" in content:
            components["collapsible_configured"] = 0.7

    # 9. Old filter pattern removed (no Form+Row+Col filter pattern, no MyPagination old-style)
    has_old_form_filter = bool(re.search(r"<Form[\s\S]*?<Row[\s\S]*?<Col[\s\S]*?<Form\.Item", content))
    has_old_pagination = bool(re.search(r"import\s+.*MyPagination[^V].*from", content)) or \
                         bool(re.search(r"<MyPagination[\s\n](?!V2)", content))
    has_more_filter_state = bool(re.search(r"useState.*moreFilter|moreFilter.*useState", content))

    old_indicators = [has_old_form_filter, has_old_pagination, has_more_filter_state]
    removed_count = sum(1 for x in old_indicators if not x)
    components["old_filter_removed"] = removed_count / len(old_indicators)

    # --- HIDDEN HARDER CHECKS ---

    # 10. Filter items completeness: SalesPlan has 5-6 filter fields (customer, sales, dateRange,
    #     firstFormat, secondFormat, mainPart). A strong model should migrate ALL to filterItems array.
    #     Weak models only do the 3 visible ones and miss the "moreFilter" fields.
    filter_items_match = re.search(r"filterItems[^=]*=\s*\[", content)
    if filter_items_match:
        # Extract the filterItems array content
        start_idx = filter_items_match.end()
        bracket_depth = 1
        end_idx = start_idx
        for i in range(start_idx, min(start_idx + 5000, len(content))):
            if content[i] == '[':
                bracket_depth += 1
            elif content[i] == ']':
                bracket_depth -= 1
                if bracket_depth == 0:
                    end_idx = i
                    break
        filter_items_content = content[start_idx:end_idx]

        # Count distinct filter item definitions (look for name: 'xxx' patterns)
        item_names = re.findall(r"name\s*:\s*['\"](\w+)['\"]", filter_items_content)
        # Also check for key fields from the original SalesPlan
        has_customer = any(n in ['customerName', 'customName', 'customer'] for n in item_names)
        has_sales = any(n in ['salesName', 'sales', 'salesValue'] for n in item_names)
        has_date = any(n in ['archiveTime', 'dateRange', 'createTime', 'time'] for n in item_names)
        has_first_format = any(n in ['firstFormat', 'firstFormatName', 'format1'] for n in item_names)
        has_second_format = any(n in ['secondFormat', 'secondFormatName', 'format2'] for n in item_names)
        has_main_part = any(n in ['mainPart', 'mainPartCode', 'salesBody'] for n in item_names)

        core_fields = [has_customer, has_sales, has_date]
        extended_fields = [has_first_format, has_second_format, has_main_part]

        core_count = sum(1 for x in core_fields if x)
        extended_count = sum(1 for x in extended_fields if x)

        # Core 3 fields = 0.4, each extended field adds 0.2 (max 0.6 from extended)
        components["filter_items_completeness"] = min(
            (core_count / 3.0) * 0.4 + (extended_count / 3.0) * 0.6,
            1.0
        )
    else:
        components["filter_items_completeness"] = 0.0

    # 11. compId consistency: The compId passed to FilterBox must match the elementId
    #     passed to useResizeHeight. This is a subtle integration requirement.
    comp_id_in_filterbox = re.search(r'compId\s*=\s*["\']([^"\']+)["\']', content)
    comp_id_in_resize = re.search(r'useResizeHeight\s*\(\s*["\']([^"\']+)["\']', content)
    if comp_id_in_filterbox and comp_id_in_resize:
        if comp_id_in_filterbox.group(1) == comp_id_in_resize.group(1):
            components["compid_consistency"] = 1.0
        else:
            components["compid_consistency"] = 0.2  # Both present but mismatched
    elif comp_id_in_filterbox or comp_id_in_resize:
        components["compid_consistency"] = 0.1  # Only one present
    else:
        components["compid_consistency"] = 0.0

    # 12. Dynamic scroll.y using filterH: The table scroll.y should reference the
    #     filterH state variable. Pattern: calc(100vh - ${filterH + ...}px) or similar.
    has_filter_h_state = bool(re.search(r"\[filterH\s*,\s*setFilterH\]", content)) or \
                         bool(re.search(r"filterH", content) and re.search(r"setFilterH", content))
    has_scroll_with_filter_h = bool(re.search(r"scroll\s*=\s*\{?\s*\{[^}]*filterH", content)) or \
                               bool(re.search(r"(scrollY|tableScrollY|scrollHeight)\s*=.*filterH", content, re.DOTALL)) or \
                               bool(re.search(r"y\s*:\s*[^,}]*filterH", content))

    if has_filter_h_state and has_scroll_with_filter_h:
        components["scroll_y_dynamic"] = 1.0
    elif has_filter_h_state:
        components["scroll_y_dynamic"] = 0.3  # Has state but doesn't use it in scroll
    else:
        components["scroll_y_dynamic"] = 0.0

    # 13. Old wrapper cleanup: The original code wraps filter in MyCard. With FilterBox,
    #     MyCard wrapper around filter is unnecessary and should be removed.
    #     Also check that the standalone buttons div is removed (now in extraActions).
    has_mycard_import = bool(re.search(r"import\s+.*MyCard.*from", content))
    has_mycard_jsx = bool(re.search(r"<MyCard", content))
    # Check if standalone button div is still present (outside FilterBox)
    has_standalone_buttons = bool(re.search(
        r"<div[^>]*style[^>]*flex[^>]*>[\s\S]*?(导出|handleExport)[\s\S]*?(新建销售方案|PlusOutlined)[\s\S]*?</div>",
        content, re.DOTALL
    ))

    cleanup_items = [not has_mycard_jsx, not has_standalone_buttons]
    components["old_wrapper_cleanup"] = sum(1 for x in cleanup_items if x) / len(cleanup_items)

    # 14. Table pagination={false} must be set (since pagination is handled by MyPaginationV2).
    #     The original code already had this but weak models might accidentally add antd pagination.
    resizable_table_match = re.search(r"<ResizableTable[\s\S]*?/>", content)
    if resizable_table_match:
        table_jsx = resizable_table_match.group(0)
        if "pagination={false}" in table_jsx or "pagination = {false}" in table_jsx:
            components["pagination_table_disabled"] = 1.0
        elif "pagination" not in table_jsx:
            # If pagination prop is missing entirely, partial credit (antd default is truthy)
            components["pagination_table_disabled"] = 0.3
        else:
            components["pagination_table_disabled"] = 0.0
    else:
        # Check without self-closing (multi-line table)
        table_section = re.search(r"<ResizableTable[\s\S]*?>", content)
        if table_section:
            table_jsx = table_section.group(0)
            if "pagination={false}" in table_jsx or "pagination = {false}" in table_jsx:
                components["pagination_table_disabled"] = 1.0
            elif "pagination" not in table_jsx:
                components["pagination_table_disabled"] = 0.3
            else:
                components["pagination_table_disabled"] = 0.0

    # --- HIDDEN ADVANCED CHECKS (strong vs weak discriminators) ---

    # 15. Format cascade logic: The original SalesPlan has a cascade where selecting
    #     一级业态 triggers loading 二级业态 options (getSecondFormatNameList call).
    #     A strong model must preserve this cascade in the FilterBox filterItems config,
    #     typically via onSelect callback or onChange that fetches second-level options.
    #     Weak models just create static Select items without the cascade.
    #     Key: the cascade must be wired INSIDE filterItems (not in old Form+Row+Col pattern).
    has_filterbox_component = bool(re.search(r"<FilterBox[\s\n]", content))
    has_cascade_fetch = bool(re.search(
        r"getSecondFormatNameList|secondFormat.*Options|setSecondFormatOptions",
        content
    ))
    has_dynamic_second_options = bool(re.search(
        r"secondFormatOptions", content
    ))
    # Check that cascade is wired inside filterItems definition (not old Form pattern)
    cascade_in_filter_items = False
    if filter_items_match:
        fi_content = content[filter_items_match.start():filter_items_match.start() + 5000]
        cascade_in_filter_items = bool(re.search(
            r"(firstFormat|一级业态)[\s\S]*?(onSelect|onChange)[\s\S]*?getSecondFormatNameList",
            fi_content
        )) or bool(re.search(
            r"getSecondFormatNameList", fi_content
        ))

    if has_filterbox_component and cascade_in_filter_items and has_dynamic_second_options:
        components["format_cascade_logic"] = 1.0
    elif has_filterbox_component and has_cascade_fetch and has_dynamic_second_options:
        # Has the state/fetch but cascade not clearly inside filterItems
        components["format_cascade_logic"] = 0.5
    elif has_cascade_fetch and has_dynamic_second_options and not has_filterbox_component:
        # Still using old pattern (no FilterBox) — no credit
        components["format_cascade_logic"] = 0.0
    elif has_dynamic_second_options or has_cascade_fetch:
        components["format_cascade_logic"] = 0.2
    else:
        components["format_cascade_logic"] = 0.0

    # 16. forwardRef cleanup: The original SalesPlan wraps in forwardRef which is
    #     unnecessary for the FilterBox pattern (insideApproval reference doesn't use it).
    #     A strong model removes forwardRef and simplifies the component signature.
    #     Weak models leave forwardRef intact because they only copy/paste mechanically.
    has_forwardref = bool(re.search(r"forwardRef\s*\(", content))
    has_simple_fc = bool(re.search(
        r"const\s+\w+\s*:\s*FunctionComponent\s*=\s*\(\s*\)\s*=>",
        content
    )) or bool(re.search(
        r"const\s+\w+\s*:\s*React\.FC\s*=\s*\(\s*\)\s*=>",
        content
    )) or bool(re.search(
        r"const\s+\w+\s*=\s*\(\s*\)\s*(?::\s*\w+\s*)?=>",
        content
    ))

    if not has_forwardref and has_simple_fc:
        components["forwardref_cleanup"] = 1.0
    elif not has_forwardref:
        # Removed forwardRef but signature not quite standard
        components["forwardref_cleanup"] = 0.7
    else:
        # Still has forwardRef — mechanical copy, no simplification
        components["forwardref_cleanup"] = 0.0

    # 17. Filter state consolidation: The reference insideApproval uses a single
    #     filterValues state object (useState<any>({})) to manage all filter field values.
    #     The original SalesPlan has scattered individual states (customerNameValue,
    #     salesValue, archiveTime). A strong model consolidates these into a single
    #     filterValues state, matching the reference pattern.
    #     Weak models keep the scattered states or only partially consolidate.
    has_filter_values_state = bool(re.search(
        r"\[\s*filterValues\s*,\s*setFilterValues\s*\]\s*=\s*useState",
        content
    ))
    # Check that old scattered states are removed
    has_old_customer_state = bool(re.search(r"customerNameValue|setCustomerNameValue", content))
    has_old_sales_state = bool(re.search(r"salesValue\b.*useState|setSalesValue", content))
    has_old_archive_state = bool(re.search(r"\[archiveTime\s*,\s*setArchiveTime\]", content))

    old_scattered_count = sum([has_old_customer_state, has_old_sales_state, has_old_archive_state])

    if has_filter_values_state and old_scattered_count == 0:
        components["filter_state_consolidation"] = 1.0
    elif has_filter_values_state and old_scattered_count <= 1:
        # Mostly consolidated, one leftover
        components["filter_state_consolidation"] = 0.6
    elif has_filter_values_state:
        # Has filterValues but didn't remove old states (duplicated)
        components["filter_state_consolidation"] = 0.3
    elif old_scattered_count == 0:
        # Removed old states but uses a different pattern (partial credit)
        components["filter_state_consolidation"] = 0.4
    else:
        components["filter_state_consolidation"] = 0.0

    # --- WEIGHTS ---
    # Easy checks get minimal weight, hard hidden checks dominate scoring.
    # Target: strong model 0.7-0.85, weak model 0.4-0.6
    weights = {
        "filterbox_imported": 0.04,
        "filterbox_used_in_jsx": 0.05,
        "pagination_v2_imported": 0.03,
        "pagination_v2_used_in_jsx": 0.05,
        "resize_height_hook": 0.05,
        "table_size_small": 0.03,
        "extra_actions_configured": 0.05,
        "collapsible_configured": 0.04,
        "old_filter_removed": 0.04,
        # Hidden harder checks (38% weight)
        "filter_items_completeness": 0.12,
        "compid_consistency": 0.08,
        "scroll_y_dynamic": 0.08,
        "old_wrapper_cleanup": 0.04,
        "pagination_table_disabled": 0.06,
        # Hidden advanced checks (22% weight — strong discriminators)
        "format_cascade_logic": 0.08,
        "forwardref_cleanup": 0.06,
        "filter_state_consolidation": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    # Try fixtures subdir first
    if (ws / "fixtures" / "salestable").exists():
        print(json.dumps(grade_workspace(ws), ensure_ascii=False))
    elif (ws / "salestable").exists():
        print(json.dumps(grade_workspace(ws), ensure_ascii=False))
    else:
        # Fallback: check if SalesPlan is directly in workspace
        print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
