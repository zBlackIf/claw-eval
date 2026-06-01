"""Hidden verifier for CP121 — TypeScript adaptor permission filter refactor."""
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
    """Grade the workspace modifications for the adaptor permission refactor task."""

    # Look for the viewImagesDialog file
    dialog_file = ws / "emp-app" / "src" / "pages" / "merchInfo" / "merchInfoSearch" / "components" / "viewImagesDialog.ts"
    detail_file = ws / "emp-app" / "src" / "pages" / "merchInfo" / "merchInfoSearch" / "basicInfo" / "detail.ts"

    # Fallback paths (agent might place files at workspace root)
    if not dialog_file.exists():
        dialog_file = ws.parent / "emp-app" / "src" / "pages" / "merchInfo" / "merchInfoSearch" / "components" / "viewImagesDialog.ts"
    if not detail_file.exists():
        detail_file = ws.parent / "emp-app" / "src" / "pages" / "merchInfo" / "merchInfoSearch" / "basicInfo" / "detail.ts"

    components = {k: 0.0 for k in [
        "import_btn_permission",
        "adaptor_uses_permission",
        "adaptor_filters_list",
        "adaptor_optional_param",
        "dialog_passes_permission",
        "caller_passes_permission_field",
        "general_panel_no_permission",
        "filter_logic_correctness",
        "no_original_array_mutation",
        "type_annotation_quality",
        "adaptor_closure_correctness",
        "naming_preservation",
        "detail_closure_wrapping",
        "guard_clause_structure",
    ]}

    dialog_content = _read(dialog_file) if dialog_file.exists() else ""
    detail_content = _read(detail_file) if detail_file.exists() else ""

    # 1. Check that btnPermission is imported in viewImagesDialog.ts
    if dialog_content:
        if re.search(r"import\s*\{[^}]*btnPermission[^}]*\}\s*from", dialog_content):
            components["import_btn_permission"] = 1.0
        elif "btnPermission" in dialog_content and ("require" in dialog_content or "import" in dialog_content):
            components["import_btn_permission"] = 0.7

    # 2. Check that imagesQueryAdaptor uses btnPermission for conditional filtering
    if dialog_content:
        # Look for: if (permissFeild && !btnPermission(permissFeild)) or similar pattern
        if re.search(r"btnPermission\s*\(\s*permiss[Ff]", dialog_content):
            components["adaptor_uses_permission"] = 1.0
        elif "btnPermission" in dialog_content and "permiss" in dialog_content.lower():
            components["adaptor_uses_permission"] = 0.5

    # 3. Check that the adaptor filters the list (removes items based on permission)
    if dialog_content:
        # Look for filter logic: newList.filter(...) or filterList = ...
        if re.search(r"\.filter\s*\(", dialog_content) and "pic_type" in dialog_content:
            components["adaptor_filters_list"] = 1.0
        elif re.search(r"\.filter\s*\(", dialog_content):
            components["adaptor_filters_list"] = 0.7
        elif "filterList" in dialog_content or "filteredList" in dialog_content:
            components["adaptor_filters_list"] = 0.4

    # 4. Check that permissFeild is optional (has ? or default value)
    if dialog_content:
        # Look for: permissFeild? or permissFeild = '' or permissFeild?: string
        if re.search(r"permiss[Ff]e[i]?ld\s*[\?:]|\bpermiss[Ff]e[i]?ld\s*=\s*['\"]", dialog_content):
            components["adaptor_optional_param"] = 1.0
        elif re.search(r"permiss[Ff]e[i]?ld\s*\?", dialog_content):
            components["adaptor_optional_param"] = 1.0
        # Check for default parameter value pattern
        elif re.search(r"permiss[Ff]e[i]?ld\s*=", dialog_content):
            components["adaptor_optional_param"] = 0.8

    # 5. Check that viewImagesDialog passes permissFeild to imagesQueryAdaptor
    if dialog_content:
        # Look for: adaptor: payload => imagesQueryAdaptor(payload, null, permissFeild)
        # or adaptor: (payload) => imagesQueryAdaptor(payload, ..., permiss...)
        if re.search(r"imagesQueryAdaptor\s*\([^)]*permiss[Ff]", dialog_content):
            # Also check that viewImagesDialog accepts permissFeild parameter
            if re.search(r"viewImagesDialog\s*=\s*\([^)]*permiss[Ff]", dialog_content) or \
               re.search(r"const\s+viewImagesDialog\s*=\s*\([^)]*permiss", dialog_content) or \
               re.search(r"function\s+viewImagesDialog\s*\([^)]*permiss", dialog_content) or \
               re.search(r"viewImagesDialog\s*\(\s*url\s*,\s*params\s*,\s*title[^)]*permiss", dialog_content):
                components["dialog_passes_permission"] = 1.0
            else:
                components["dialog_passes_permission"] = 0.5

    # 6. Check that the detail.ts caller passes the permission field for settlement panel
    if detail_content:
        # Look for imagesQueryAdaptor call with permission arg like 'viewCustomerSettleInfo'
        if re.search(r"imagesQueryAdaptor\s*\([^)]*['\"]view", detail_content):
            components["caller_passes_permission_field"] = 1.0
        elif re.search(r"imagesQueryAdaptor\s*\([^)]*,\s*['\"]", detail_content):
            components["caller_passes_permission_field"] = 0.7
        # Or via viewImagesDialog with permission param
        elif re.search(r"viewImagesDialog\s*\([^)]*['\"]view", detail_content):
            components["caller_passes_permission_field"] = 0.8

    # 7. Check that the general panel does NOT apply permission filtering
    # (only settlement-specific panels should filter)
    if detail_content:
        # Look for the general panel adaptor - it should NOT have a permission field
        # or should pass empty/undefined
        general_section = ""
        if "generalPanel" in detail_content or "General" in detail_content:
            # Find the general panel section
            lines = detail_content.split("\n")
            in_general = False
            brace_count = 0
            for line in lines:
                if "general" in line.lower() and ("panel" in line.lower() or "Panel" in line):
                    in_general = True
                if in_general:
                    general_section += line + "\n"
                    brace_count += line.count("{") - line.count("}")
                    if brace_count <= 0 and len(general_section) > 50:
                        break

        if general_section:
            # General panel should use adaptor without permission or with empty permission
            has_permission_in_general = re.search(r"imagesQueryAdaptor\s*\([^)]*['\"]view", general_section)
            if not has_permission_in_general:
                components["general_panel_no_permission"] = 1.0
            else:
                components["general_panel_no_permission"] = 0.0
        else:
            # If we can't find distinct general section, check if settlement is the only one with permission
            settle_has_perm = re.search(r"[Ss]ettle.*imagesQueryAdaptor\s*\([^)]*['\"]view|imagesQueryAdaptor\s*\([^)]*['\"]view.*[Ss]ettle", detail_content)
            if settle_has_perm:
                components["general_panel_no_permission"] = 0.8

    # --- HIDDEN CHECKS (harder, test code quality and correctness) ---

    # 8. Filter logic correctness: the negation must be correct.
    #    When permission is DENIED (!btnPermission), filter OUT A10 items.
    #    Common mistake: filtering when permission IS granted (wrong direction),
    #    or keeping only A10 instead of removing A10.
    if dialog_content:
        # Correct pattern: !btnPermission(...) combined with !== 'A10' filter
        # This means: when user does NOT have permission, remove A10 items
        has_negation = re.search(r"!\s*btnPermission\s*\(", dialog_content)
        has_exclude_a10 = re.search(r"pic_type\s*!==\s*['\"]A10['\"]", dialog_content)
        has_include_a10 = re.search(r"pic_type\s*===\s*['\"]A10['\"]", dialog_content)

        if has_negation and has_exclude_a10 and not has_include_a10:
            # Perfect: negation + exclusion filter (item.pic_type !== 'A10')
            components["filter_logic_correctness"] = 1.0
        elif has_negation and has_exclude_a10:
            # Has both !== and === patterns, partial credit
            components["filter_logic_correctness"] = 0.6
        elif has_negation and has_include_a10:
            # Using === in filter with negation outside is ambiguous/possibly wrong
            # e.g. filter(item => item.pic_type === 'A10') removes non-A10, which is inverted
            components["filter_logic_correctness"] = 0.2
        elif not has_negation and has_exclude_a10:
            # Missing the negation on btnPermission — filters when user HAS permission (wrong)
            components["filter_logic_correctness"] = 0.1
        else:
            components["filter_logic_correctness"] = 0.0

    # 9. No original array mutation: the adaptor should not mutate the source array.
    #    Good practice: use .filter() which creates a new array, not splice/pop/shift
    #    or direct index deletion. Also the filtered result should be assigned to a
    #    new variable rather than overwriting newList directly.
    if dialog_content:
        # Check for mutation anti-patterns inside the adaptor function
        adaptor_match = re.search(
            r"(const|let|var|function)\s+imagesQueryAdaptor\b(.*?)(?=\n(?:const|let|var|function|export)\b|\Z)",
            dialog_content, re.DOTALL
        )
        adaptor_body = adaptor_match.group(0) if adaptor_match else dialog_content

        has_splice = "splice(" in adaptor_body
        has_pop = ".pop(" in adaptor_body
        has_shift = ".shift(" in adaptor_body
        has_delete = "delete " in adaptor_body
        uses_filter = ".filter(" in adaptor_body

        # Also check that filter result is stored in a separate variable
        # (not re-assigning newList = newList.filter(...))
        reassigns_newlist = re.search(r"\bnewList\s*=\s*newList\.filter\b", adaptor_body)
        # Match: const/let filterX = ...filter(...) OR filterX = someVar.filter(...)
        uses_separate_var = re.search(
            r"(const|let)\s+(filter|filtered|result)\w*\s*=\s*\w+\.filter\b", adaptor_body
        ) or re.search(
            r"(filter|filtered|result)\w*\s*=\s*\w+\.filter\b", adaptor_body
        )
        # Also check if the return uses a different variable name from newList
        returns_filtered_var = re.search(
            r"picList1\s*:\s*(filter|filtered|result)\w*", adaptor_body
        )

        if uses_filter and not has_splice and not has_pop and not has_shift and not has_delete:
            if uses_separate_var and returns_filtered_var:
                # Best: separate variable for filtered result AND returns it
                components["no_original_array_mutation"] = 1.0
            elif uses_separate_var:
                # Good: uses separate variable but might not return it properly
                components["no_original_array_mutation"] = 0.7
            elif reassigns_newlist:
                # Reassigning const is a TS error, reassigning let is ok but not great
                components["no_original_array_mutation"] = 0.4
            else:
                # Uses filter inline or in return — acceptable
                components["no_original_array_mutation"] = 0.35
        elif has_splice or has_pop or has_shift or has_delete:
            # Mutates the array — bad practice
            components["no_original_array_mutation"] = 0.0
        else:
            components["no_original_array_mutation"] = 0.2

    # 10. Type annotation quality: the refactored code should add proper TypeScript types
    #     for the new optional parameter. Strong models add type annotations; weak ones don't.
    #     Specifically we check that the NEW parameter is typed (not just existing params).
    if dialog_content:
        score_type = 0.0

        # Check imagesQueryAdaptor has typed permissFeild parameter
        # Best: permissFeild?: string
        has_typed_adaptor_param = re.search(
            r"permiss[Ff]e[i]?ld\s*\?\s*:\s*string", dialog_content
        )
        # Acceptable: permissFeild: string = '' (typed with default)
        has_default_typed = re.search(
            r"permiss[Ff]e[i]?ld\s*:\s*string\s*=", dialog_content
        )
        # Also acceptable: permissFeild?: string | undefined
        has_union_typed = re.search(
            r"permiss[Ff]e[i]?ld\s*\?\s*:\s*string\s*\|\s*undefined", dialog_content
        )

        if has_typed_adaptor_param or has_default_typed or has_union_typed:
            score_type += 0.5

        # Check viewImagesDialog also has typed permissFeild parameter
        dialog_fn_match = re.search(
            r"viewImagesDialog\s*=?\s*\([^)]*permiss[Ff]e[i]?ld\s*[\?:]?\s*:?\s*string",
            dialog_content
        )
        if dialog_fn_match:
            score_type += 0.25

        # Check if payload AND response params both have explicit types in imagesQueryAdaptor
        # (not just relying on `any` everywhere — strong models might use more specific types)
        has_both_params_typed = re.search(
            r"imagesQueryAdaptor\s*=\s*\(\s*payload\s*:\s*\w+\s*,\s*response\s*:\s*\w+",
            dialog_content
        )
        if has_both_params_typed:
            score_type += 0.25

        components["type_annotation_quality"] = min(score_type, 1.0)

    # 11. Adaptor closure correctness: viewImagesDialog must wrap imagesQueryAdaptor
    #     in a closure/arrow function to properly capture permissFeild. If the original
    #     `adaptor: imagesQueryAdaptor` pattern is kept without wrapping, permissFeild
    #     won't be passed through. This is a subtle but critical correctness issue.
    if dialog_content:
        # Extract the viewImagesDialog function body
        dialog_fn_match = re.search(
            r"(const|let|var|function)\s+viewImagesDialog\b(.*?)(?=\n(?:const|let|var|function|export)\b|\Z)",
            dialog_content, re.DOTALL
        )
        dialog_fn_body = dialog_fn_match.group(0) if dialog_fn_match else ""

        if dialog_fn_body:
            # Check if adaptor is wrapped in an arrow/function (closure captures permissFeild)
            # Good: adaptor: (payload) => imagesQueryAdaptor(payload, null, permissFeild)
            # Good: adaptor: function(payload) { return imagesQueryAdaptor(payload, null, permissFeild) }
            has_closure_wrap = re.search(
                r"adaptor\s*:\s*(\(?\w+\)?\s*=>|function\s*\()\s*.*imagesQueryAdaptor",
                dialog_fn_body
            )
            # Bad: adaptor: imagesQueryAdaptor (no closure — permissFeild not captured)
            has_bare_ref = re.search(
                r"adaptor\s*:\s*imagesQueryAdaptor\s*[,\n}]",
                dialog_fn_body
            )

            if has_closure_wrap and not has_bare_ref:
                components["adaptor_closure_correctness"] = 1.0
            elif has_closure_wrap:
                components["adaptor_closure_correctness"] = 0.7
            elif has_bare_ref:
                # Still using bare reference — permissFeild won't be captured
                components["adaptor_closure_correctness"] = 0.0
            else:
                components["adaptor_closure_correctness"] = 0.3

    # --- HIDDEN CHECKS (continued) ---

    # 12. Naming preservation: the original code uses the TYPO "permissFeild" (not "permissField").
    #     Strong models preserve the existing naming convention to avoid breaking callers.
    #     Weak models might silently "fix" the typo to "permissField" which breaks the interface.
    #     Only score this if permission filtering was actually implemented.
    if dialog_content and "btnPermission" in dialog_content:
        # Count occurrences of the original typo vs the "corrected" spelling
        original_typo_count = len(re.findall(r"permissFeild", dialog_content))
        corrected_count = len(re.findall(r"permissField", dialog_content))
        # Also check detail.ts for consistency
        detail_typo_count = len(re.findall(r"permissFeild", detail_content))
        detail_corrected_count = len(re.findall(r"permissField", detail_content))

        total_original = original_typo_count + detail_typo_count
        total_corrected = corrected_count + detail_corrected_count

        if total_original > 0 and total_corrected == 0:
            # Perfect: preserved the existing naming convention throughout
            components["naming_preservation"] = 1.0
        elif total_original > 0 and total_corrected > 0:
            # Mixed: partially fixed, partially kept — inconsistent and risky
            ratio = total_original / (total_original + total_corrected)
            components["naming_preservation"] = round(ratio * 0.4, 2)
        elif total_corrected > 0 and total_original == 0:
            # Completely renamed — breaks the interface contract
            components["naming_preservation"] = 0.0
        else:
            # Neither found — probably didn't implement the feature
            components["naming_preservation"] = 0.0

    # 13. Detail.ts closure wrapping: in detail.ts, the settlement panel's adaptor must
    #     be wrapped in a closure to pass the permission field. The original code uses
    #     `adaptor: imagesQueryAdaptor` (bare reference). After refactoring, it should be
    #     `adaptor: (payload) => imagesQueryAdaptor(payload, null, 'viewCustomerSettleInfo')`
    #     or call via viewImagesDialog. Weak models forget to update detail.ts callers.
    if detail_content:
        # Check if settlement panel adaptor is wrapped in a closure (not bare reference)
        settle_section = ""
        lines = detail_content.split("\n")
        in_settle = False
        brace_count = 0
        for line in lines:
            if "settlementPanel" in line or "settlement" in line.lower():
                in_settle = True
            if in_settle:
                settle_section += line + "\n"
                brace_count += line.count("{") - line.count("}")
                if brace_count <= 0 and len(settle_section) > 80:
                    break

        if settle_section:
            # Good: adaptor wrapped in arrow function with permission arg
            has_settle_closure = re.search(
                r"adaptor\s*:\s*(\(?\s*\w+\s*\)?\s*=>|function\s*\()\s*.*imagesQueryAdaptor",
                settle_section
            )
            # Bad: still using bare reference (adaptor: imagesQueryAdaptor)
            has_settle_bare = re.search(
                r"adaptor\s*:\s*imagesQueryAdaptor\s*[,\n}]",
                settle_section
            )
            # Check that the permission string is actually passed in the closure
            has_perm_string_in_closure = re.search(
                r"imagesQueryAdaptor\s*\([^)]*['\"]viewCustomerSettleInfo['\"]",
                settle_section
            )

            if has_settle_closure and has_perm_string_in_closure and not has_settle_bare:
                components["detail_closure_wrapping"] = 1.0
            elif has_settle_closure and not has_settle_bare:
                # Wrapped but might not pass the right permission string
                components["detail_closure_wrapping"] = 0.6
            elif has_settle_bare:
                # Didn't update — bare reference remains
                components["detail_closure_wrapping"] = 0.0
            else:
                # Restructured in some other way (e.g., uses viewImagesDialog)
                if re.search(r"viewImagesDialog\s*\([^)]*viewCustomerSettleInfo", settle_section):
                    components["detail_closure_wrapping"] = 0.9
                else:
                    components["detail_closure_wrapping"] = 0.2
        else:
            # Can't find settlement section at all — check whole file
            if re.search(r"adaptor\s*:\s*(\(?\s*\w+\s*\)?\s*=>)\s*.*imagesQueryAdaptor\s*\([^)]*['\"]viewCustomerSettleInfo", detail_content):
                components["detail_closure_wrapping"] = 1.0
            elif re.search(r"adaptor\s*:\s*imagesQueryAdaptor\s*[,\n}]", detail_content):
                components["detail_closure_wrapping"] = 0.0
            else:
                components["detail_closure_wrapping"] = 0.3

    # 14. Guard clause structure: the permission filtering logic should use a guard clause
    #     (early check and short-circuit) rather than deeply nested if-else. Strong models
    #     write: `if (!permissFeild) return {..., picList1: newList}` or
    #     `let result = newList; if (permissFeild && !btnPermission(permissFeild)) { result = ... }`
    #     Weak models over-nest: `if (permissFeild) { if (!btnPermission(permissFeild)) { ... } else { ... } } else { ... }`
    #     Only score this if permission logic was actually implemented (btnPermission used).
    if dialog_content and "btnPermission" in dialog_content:
        adaptor_match2 = re.search(
            r"(const|let|var|function)\s+imagesQueryAdaptor\b(.*?)(?=\n(?:const|let|var|function|export)\b|\Z)",
            dialog_content, re.DOTALL
        )
        adaptor_body2 = adaptor_match2.group(0) if adaptor_match2 else ""

        if adaptor_body2 and "btnPermission" in adaptor_body2:
            # Extract the permission-related logic block (starts at if/condition with permiss/btnPermission)
            perm_section = ""
            in_perm = False
            for line in adaptor_body2.split("\n"):
                if not in_perm and ("btnPermission" in line or re.search(r"\bif\b.*permiss", line)):
                    in_perm = True
                if in_perm:
                    perm_section += line + "\n"
                    if "}" in line and perm_section.count("{") <= perm_section.count("}"):
                        break

            if perm_section:
                # Count how many nested if/else pairs exist
                if_count = len(re.findall(r"\bif\b", perm_section))
                else_count = len(re.findall(r"\belse\b", perm_section))

                # Best: single compound condition `if (permissFeild && !btnPermission(permissFeild))`
                has_compound_condition = re.search(
                    r"if\s*\(\s*permiss\w*\s*&&\s*!?\s*btnPermission",
                    perm_section
                )

                if has_compound_condition and if_count <= 1:
                    # Single compound if — clean guard clause pattern
                    components["guard_clause_structure"] = 1.0
                elif has_compound_condition and if_count == 2:
                    # Compound condition but with an extra if (maybe null check)
                    components["guard_clause_structure"] = 0.7
                elif if_count == 1 and else_count == 0:
                    # Single if without else — simple conditional assignment
                    components["guard_clause_structure"] = 0.8
                elif if_count <= 2 and else_count <= 1:
                    # Moderate nesting — acceptable but not ideal
                    components["guard_clause_structure"] = 0.5
                elif if_count >= 3 or else_count >= 2:
                    # Deep nesting — weak pattern
                    components["guard_clause_structure"] = 0.2
                else:
                    components["guard_clause_structure"] = 0.4
            else:
                # No permission section found in adaptor — didn't implement
                components["guard_clause_structure"] = 0.0

    # --- SCORING with adjusted weights ---
    # Basic checks (reduced weight): ~20% total
    # Hidden checks (harder, quality-focused): ~80% total
    weights = {
        "import_btn_permission": 0.03,
        "adaptor_uses_permission": 0.03,
        "adaptor_filters_list": 0.04,
        "adaptor_optional_param": 0.03,
        "dialog_passes_permission": 0.03,
        "caller_passes_permission_field": 0.02,
        "general_panel_no_permission": 0.02,
        "filter_logic_correctness": 0.18,
        "no_original_array_mutation": 0.12,
        "type_annotation_quality": 0.14,
        "adaptor_closure_correctness": 0.12,
        "naming_preservation": 0.10,
        "detail_closure_wrapping": 0.08,
        "guard_clause_structure": 0.06,
    }
    overall = sum(weights[k] * components.get(k, 0.0) for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try both /workspace/fixtures and /workspace as base paths
    ws = Path("/workspace/fixtures")
    if not (ws / "emp-app").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
