"""Hidden verifier for CP169 - iBATIS SQL field truncation bug fix.

The core issue: SELECT query returns 'costCenter' and 'wce' and 'stNo' as
concatenated strings (CODE-DESCRIPTION), but INSERT/UPDATE writes those values
directly back to narrow DB columns (COST_CENTER=4 chars, WCE=5 chars).

The fix must strip the description portion before writing to DB in both
INSERT and UPDATE statements. Multiple valid approaches:
- Use SQL function to extract code before '-' (LEFT/LOCATE or SUBSTR)
- Use iBATIS inline parameter with expression
- Strip in Java service layer before calling SQL
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


def _find_xml(ws: Path) -> Path | None:
    """Find the JHSM3110.xml file anywhere under workspace."""
    for candidate in [
        ws / "fixtures" / "jhsm-app" / "java" / "com" / "baosight" / "egdw" / "jh" / "sm" / "sql" / "JHSM3110.xml",
        ws / "jhsm-app" / "java" / "com" / "baosight" / "egdw" / "jh" / "sm" / "sql" / "JHSM3110.xml",
    ]:
        if candidate.exists():
            return candidate
    # Fallback: search recursively
    for p in ws.rglob("JHSM3110.xml"):
        return p
    return None


def _find_service(ws: Path) -> Path | None:
    """Find ServiceJHSM3110.java anywhere under workspace."""
    for candidate in [
        ws / "fixtures" / "jhsm-app" / "java" / "com" / "baosight" / "egdw" / "jh" / "sm" / "service" / "ServiceJHSM3110.java",
        ws / "jhsm-app" / "java" / "com" / "baosight" / "egdw" / "jh" / "sm" / "service" / "ServiceJHSM3110.java",
    ]:
        if candidate.exists():
            return candidate
    for p in ws.rglob("ServiceJHSM3110.java"):
        return p
    return None


def _extract_sql_block(xml_content: str, block_id: str) -> str:
    """Extract content of a specific SQL block (insert/update) from iBATIS XML."""
    pattern = rf'<{block_id}[^>]*>(.*?)</{block_id}>'
    match = re.search(pattern, xml_content, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""


def _has_truncation_fix(sql_text: str, field_name: str, require_dynamic: bool = False) -> bool:
    """Check if the SQL text applies truncation/extraction to a field before writing.

    Valid fixes include:
    - LEFT(#field#, LOCATE('-', #field#) - 1)  -- dynamic, strips at '-'
    - SUBSTR(#field#, 1, LOCATE('-', ...) - 1)
    - CASE WHEN LOCATE('-', ...) pattern
    - Any expression that extracts the code portion before '-'

    If require_dynamic=True, only accept patterns that use LOCATE/CHARINDEX/INSTR
    to find the '-' delimiter (not static LEFT(field, N) with a constant).
    """
    field_pattern = field_name.lower()
    sql_lower = sql_text.lower()

    # Pattern 3: LOCATE('-', #field#) based extraction -- strongest signal
    # Matches: LOCATE('-', #field#) or LOCATE('-', #field:VARCHAR#)
    locate_pattern = rf"locate\s*\(\s*'[^']*-[^']*'\s*,\s*#{field_pattern}"
    has_locate = bool(re.search(locate_pattern, sql_lower))

    # Pattern 4: CASE WHEN with LOCATE for the field
    case_pattern = rf"case\s+when.*locate.*#{field_pattern}"
    has_case_locate = bool(re.search(case_pattern, sql_lower, re.DOTALL))

    # Pattern 5: CHARINDEX or INSTR pattern (alternative DB functions)
    charindex_pattern = rf"(?:charindex|instr)\s*\(.*#{field_pattern}"
    has_charindex = bool(re.search(charindex_pattern, sql_lower))

    # Pattern 6: split_part or similar
    split_pattern = rf"split_part\s*\(\s*#{field_pattern}"
    has_split = bool(re.search(split_pattern, sql_lower))

    # If any dynamic delimiter-based extraction is found, it's a proper fix
    if has_locate or has_case_locate or has_charindex or has_split:
        return True

    # If we require dynamic (e.g. stNo), static LEFT is not enough
    if require_dynamic:
        return False

    # Pattern 1: LEFT(#field#, N) or SUBSTR(#field#, 1, N) with a CONSTANT
    # This is acceptable for costCenter/wce where we know the exact column width
    left_pattern = rf"left\s*\(\s*#{field_pattern}(?::varchar)?#\s*,\s*\d+"
    if re.search(left_pattern, sql_lower):
        return True

    # Pattern 2: SUBSTR(#field#, 1, N) or SUBSTRING with constant
    substr_pattern = rf"substr(?:ing)?\s*\(\s*#{field_pattern}(?::varchar)?#\s*,\s*1\s*,\s*\d+"
    if re.search(substr_pattern, sql_lower):
        return True

    return False


def _check_service_strips(service_content: str, field_name: str) -> bool:
    """Check if the Java service layer strips description before SQL call.

    Valid fixes include stripping in Java before passing to DAO:
    - field.split("-")[0]
    - field.substring(0, field.indexOf("-"))
    - StringUtils-based extraction
    """
    content_lower = service_content.lower()
    field_lower = field_name.lower()

    # Check for split("-")[0] or split("-", 2)[0]
    if re.search(rf'{field_lower}.*split\s*\(\s*["\'][\-]', service_content):
        return True

    # Check for substring(0, indexOf("-"))
    if re.search(rf'{field_lower}.*substring\s*\(\s*0\s*,.*indexof\s*\(\s*["\'][\-]', service_content, re.IGNORECASE):
        return True

    # Check for substringBefore or left equivalent
    if re.search(rf'substringbefore.*{field_lower}|{field_lower}.*substringbefore', content_lower):
        return True

    # Generic: any put() call that modifies the field with split/substring logic
    if re.search(rf'put\s*\(\s*["\']' + field_name + rf'["\'].*split|substring.*indexof.*[\-]', service_content, re.IGNORECASE):
        return True

    return False


def grade_workspace(ws: Path) -> dict:
    xml_path = _find_xml(ws)
    service_path = _find_service(ws)

    components = {
        "costCenter_insert_fixed": 0.0,
        "costCenter_update_fixed": 0.0,
        "wce_insert_fixed": 0.0,
        "wce_update_fixed": 0.0,
        "stNo_insert_fixed": 0.0,
        "query_select_preserved": 0.0,
    }

    xml_content = _read(xml_path) if xml_path else ""
    service_content = _read(service_path) if service_path else ""

    if not xml_content:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "JHSM3110.xml not found or empty",
        }

    insert_sql = _extract_sql_block(xml_content, "insert")
    update_sql = _extract_sql_block(xml_content, "update")
    select_sql = _extract_sql_block(xml_content, "select")

    # Dimension 1: costCenter truncation in INSERT
    # The fix must ensure only the code part (before '-') goes to COST_CENTER column
    if _has_truncation_fix(insert_sql, "costCenter"):
        components["costCenter_insert_fixed"] = 1.0
    elif _check_service_strips(service_content, "costCenter"):
        components["costCenter_insert_fixed"] = 1.0
    elif "#costCenter" not in insert_sql:
        # Field was removed entirely (not ideal but prevents the error)
        components["costCenter_insert_fixed"] = 0.3

    # Dimension 2: costCenter truncation in UPDATE
    if _has_truncation_fix(update_sql, "costCenter"):
        components["costCenter_update_fixed"] = 1.0
    elif _check_service_strips(service_content, "costCenter"):
        components["costCenter_update_fixed"] = 1.0
    elif "cost_center" not in update_sql.lower() or "#costCenter" not in update_sql:
        components["costCenter_update_fixed"] = 0.3

    # Dimension 3: wce truncation in INSERT
    if _has_truncation_fix(insert_sql, "wce"):
        components["wce_insert_fixed"] = 1.0
    elif _check_service_strips(service_content, "wce"):
        components["wce_insert_fixed"] = 1.0
    elif "#wce" not in insert_sql:
        components["wce_insert_fixed"] = 0.3

    # Dimension 4: wce truncation in UPDATE
    if _has_truncation_fix(update_sql, "wce"):
        components["wce_update_fixed"] = 1.0
    elif _check_service_strips(service_content, "wce"):
        components["wce_update_fixed"] = 1.0
    elif "wce" not in update_sql.lower() or "#wce" not in update_sql:
        components["wce_update_fixed"] = 0.3

    # Dimension 5: stNo truncation in INSERT (hidden - the stNo field also has
    # '-' concatenation in the query but it's embedded inside PRODUCT_CODE_4)
    # The original LEFT(#stNo:VARCHAR#, 8) does NOT handle the bug correctly:
    # if stNo code is shorter than 8 chars (e.g. "1234-低合金钢"), LEFT gives "1234-低合"
    # which corrupts data. A proper fix must dynamically strip at '-' boundary.
    if _has_truncation_fix(insert_sql, "stNo", require_dynamic=True):
        components["stNo_insert_fixed"] = 1.0
    elif _check_service_strips(service_content, "stNo"):
        components["stNo_insert_fixed"] = 1.0
    else:
        # Static LEFT(#stNo, 8) is the original buggy baseline - give partial credit
        # only if agent explicitly added a constant LEFT that wasn't there before,
        # or uses a different constant width
        if re.search(r"left\s*\(\s*#stNo", insert_sql, re.IGNORECASE):
            # Check if it also has LOCATE nearby (almost proper fix)
            if re.search(r"locate.*stNo|stNo.*locate", insert_sql, re.IGNORECASE):
                components["stNo_insert_fixed"] = 0.9
            else:
                # Static LEFT(, 8) is the original code - no credit
                components["stNo_insert_fixed"] = 0.0
        elif "#stNo" in insert_sql:
            components["stNo_insert_fixed"] = 0.0

    # Dimension 6: SELECT query still returns descriptions for display
    # The SELECT should KEEP the concatenation (CODE || '-' || DESC) for display purposes
    if "cost_center_dscr" in select_sql.lower() or "coalesce(b." in select_sql.lower():
        components["query_select_preserved"] = 1.0
    elif "||" in select_sql and "'-'" in select_sql:
        components["query_select_preserved"] = 0.8
    elif select_sql:
        # SELECT exists but may have been modified
        components["query_select_preserved"] = 0.4

    weights = {
        "costCenter_insert_fixed": 0.25,
        "costCenter_update_fixed": 0.25,
        "wce_insert_fixed": 0.15,
        "wce_update_fixed": 0.15,
        "stNo_insert_fixed": 0.10,
        "query_select_preserved": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    # Try fixtures subdir first, then workspace root
    if (ws / "fixtures" / "jhsm-app").exists():
        result = grade_workspace(ws)
    elif (ws / "jhsm-app").exists():
        result = grade_workspace(ws)
    else:
        result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
