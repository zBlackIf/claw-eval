"""Hidden verifier for CP187 — MySQL query_database refactoring to modular design."""
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
    """Grade the refactored MySQL utility code."""
    # Look for files in both possible locations
    base = ws / "fixtures" / "railsurface"
    if not base.exists():
        base = ws / "railsurface"
    if not base.exists():
        # Try finding mysql_util.h anywhere
        for p in ws.rglob("mysql_util.h"):
            base = p.parent.parent
            break

    inc_dir = base / "inc" if base.exists() else Path("/nonexistent")
    src_dir = base / "src" if base.exists() else Path("/nonexistent")

    header_file = inc_dir / "mysql_util.h"
    impl_file = src_dir / "mysql_util.cpp"

    header = _read(header_file)
    impl = _read(impl_file)

    components = {k: 0.0 for k in [
        "return_type_structured",
        "column_mapping_configurable",
        "safe_parse_helpers",
        "query_builder_separated",
        "row_parser_extracted",
    ]}

    # 1. Return type changed from std::string to structured (vector<defectInfo> or vector<DefectInfo>)
    # Check header for new function signature
    if header:
        # Should NOT have the old signature returning string
        old_sig = re.search(r'std::string\s+query_database\s*\(', header)
        # Should have new signature returning vector
        new_sig = re.search(
            r'std::vector\s*<\s*(defectInfo|DefectInfo|Defect\w*)\s*>\s+\w+\s*\(',
            header
        )
        if new_sig and not old_sig:
            components["return_type_structured"] = 1.0
        elif new_sig and old_sig:
            # Both exist - partial credit
            components["return_type_structured"] = 0.5
        elif not old_sig:
            # Old removed but no clear vector return found - check impl
            if impl:
                impl_new_sig = re.search(
                    r'std::vector\s*<\s*(defectInfo|DefectInfo|Defect\w*)\s*>',
                    impl
                )
                if impl_new_sig:
                    components["return_type_structured"] = 0.8
    elif impl:
        # No header changes, check impl only
        impl_new_sig = re.search(
            r'std::vector\s*<\s*(defectInfo|DefectInfo|Defect\w*)\s*>',
            impl
        )
        old_sig_impl = re.search(r'std::string\s+myMYSQL::query_database\s*\(', impl)
        if impl_new_sig and not old_sig_impl:
            components["return_type_structured"] = 0.7

    # 2. Column mapping - should have a struct/map for column indices instead of magic numbers
    all_code = header + "\n" + impl
    has_column_struct = bool(re.search(
        r'struct\s+\w*(Column|Col|Mapping|Index)\w*\s*\{', all_code, re.IGNORECASE
    ))
    has_column_map = bool(re.search(
        r'(std::unordered_map|std::map|enum)\s*[<{]\s*.*?(column|col|index|field)',
        all_code, re.IGNORECASE
    ))
    has_named_constants = len(re.findall(
        r'(const|constexpr|static)\s+int\s+\w*(col|column|idx|index|field)\w*\s*=',
        all_code, re.IGNORECASE
    )) >= 3

    if has_column_struct:
        components["column_mapping_configurable"] = 1.0
    elif has_column_map:
        components["column_mapping_configurable"] = 0.9
    elif has_named_constants:
        components["column_mapping_configurable"] = 0.7
    else:
        # Check if magic numbers are still present (row[26], row[28], etc.)
        magic_numbers = re.findall(r'row\[\d{2,}\]', impl)
        if len(magic_numbers) == 0 and "row[" in impl:
            # Uses row[] but no 2+ digit indices - may have named vars
            components["column_mapping_configurable"] = 0.3

    # 3. Safe parse helpers - functions to safely parse int/double/string from row
    safe_parse_patterns = [
        r'safe\w*Parse\w*Int|safeInt|parseIntSafe|safe_parse_int|safe_int',
        r'safe\w*Parse\w*Double|safeDouble|parseDoubleSafe|safe_parse_double|safe_double|safe_parse_float',
        r'safe\w*Parse\w*String|safeString|parseStringSafe|safe_parse_string|safe_str',
    ]
    safe_parse_count = 0
    for pat in safe_parse_patterns:
        if re.search(pat, all_code, re.IGNORECASE):
            safe_parse_count += 1

    # Alternative: using try-catch or null checks in a dedicated helper function
    has_null_check_helper = bool(re.search(
        r'(static|inline)\s+\w+\s+\w*(get|parse|read|extract)\w*\s*\([^)]*MYSQL_ROW',
        all_code, re.IGNORECASE
    ))

    if safe_parse_count >= 2:
        components["safe_parse_helpers"] = 1.0
    elif safe_parse_count == 1:
        components["safe_parse_helpers"] = 0.6
    elif has_null_check_helper:
        components["safe_parse_helpers"] = 0.8
    # Note: inline ternary null checks (row[x] ? ...) in the original code
    # do NOT count as "safe parse helpers" - they must be extracted into
    # reusable functions/methods to earn credit.

    # 4. Query builder separated from execution
    # Look for a separate method/function that builds the SQL query
    query_builder_patterns = [
        r'(std::string|void)\s+\w*(build|construct|make|create|compose)\w*(Query|Sql|SQL|Condition|Where)\w*\s*\(',
        r'(buildQuery|buildSql|buildCondition|constructQuery|makeQuery|build_query|build_sql)',
    ]
    has_query_builder = False
    for pat in query_builder_patterns:
        if re.search(pat, all_code, re.IGNORECASE):
            has_query_builder = True
            break

    # Also check for parameterized queries / prepared statements
    has_prepared_stmt = bool(re.search(
        r'mysql_stmt_prepare|mysql_stmt_bind|MYSQL_STMT|prepared_statement',
        all_code, re.IGNORECASE
    ))

    if has_query_builder and has_prepared_stmt:
        components["query_builder_separated"] = 1.0
    elif has_query_builder:
        components["query_builder_separated"] = 0.9
    elif has_prepared_stmt:
        components["query_builder_separated"] = 0.7
    # Note: merely having multiple class methods does NOT count as
    # "query builder separated" - there must be a dedicated method
    # whose sole purpose is constructing the SQL query string.

    # 5. Row parser extracted as separate function
    row_parser_patterns = [
        r'(DefectInfo|defectInfo|Defect\w*)\s+\w*(parse|extract|read|from|convert)\w*\s*\([^)]*MYSQL_ROW',
        r'(parse|extract|read|convert)\w*(Row|Record|Defect)\w*\s*\(',
    ]
    has_row_parser = False
    for pat in row_parser_patterns:
        if re.search(pat, all_code, re.IGNORECASE):
            has_row_parser = True
            break

    # Alternative: lambda or local function that parses a row
    has_row_lambda = bool(re.search(
        r'auto\s+\w*(parse|extract|convert)\w*\s*=\s*\[',
        all_code, re.IGNORECASE
    ))

    if has_row_parser:
        components["row_parser_extracted"] = 1.0
    elif has_row_lambda:
        components["row_parser_extracted"] = 0.8
    else:
        # Check if the while loop body is short (< 10 lines) suggesting extraction
        # Look for the fetch loop
        fetch_match = re.search(
            r'while\s*\(\s*\(\s*row\s*=\s*mysql_fetch_row',
            impl
        )
        if fetch_match:
            # Find the loop body length
            start = fetch_match.end()
            brace_count = 0
            loop_lines = 0
            for ch in impl[start:]:
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        break
                elif ch == '\n':
                    loop_lines += 1
            if loop_lines <= 5:
                components["row_parser_extracted"] = 0.6

    weights = {
        "return_type_structured": 0.25,
        "column_mapping_configurable": 0.25,
        "safe_parse_helpers": 0.20,
        "query_builder_separated": 0.15,
        "row_parser_extracted": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
