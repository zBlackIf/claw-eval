"""Hidden verifier for CP124 — Rails schema.rb circular dependency fix.

Checks that:
1. The view `compound_open_data_locals` is defined BEFORE the functions that reference it
2. The fix preserves all original definitions (no content loss)
3. The fix doesn't break the schema structure (valid Ruby syntax preserved)
4. Functions still reference compound_open_data_locals correctly
5. Admin seed file is intact (bonus: identifies default credentials)
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


def grade_workspace(ws: Path) -> dict:
    # Look for schema.rb in expected locations
    schema_path = None
    for candidate in [
        ws / "fixtures" / "chemotion-eln" / "db" / "schema.rb",
        ws / "chemotion-eln" / "db" / "schema.rb",
    ]:
        if candidate.exists():
            schema_path = candidate
            break

    if not schema_path:
        return {
            "overall_score": 0.0,
            "components": {"error": "schema.rb not found"},
            "weights": {},
        }

    schema_content = _read(schema_path)

    components = {k: 0.0 for k in [
        "view_before_functions",
        "view_definition_preserved",
        "function_definitions_preserved",
        "schema_structure_valid",
        "no_content_loss",
    ]}

    # 1. Check ordering: view must come before functions that reference it
    view_pattern = r'create_view\s+["\']compound_open_data_locals["\']'
    func_com_xvial_pattern = r'create_function\s+:com_xvial\b'
    func_com_xvial_count_pattern = r'create_function\s+:com_xvial_count\b'

    view_match = re.search(view_pattern, schema_content)
    func_xvial_match = re.search(func_com_xvial_pattern, schema_content)
    func_count_match = re.search(func_com_xvial_count_pattern, schema_content)

    if view_match and func_xvial_match:
        view_pos = view_match.start()
        func_pos = func_xvial_match.start()
        if view_pos < func_pos:
            components["view_before_functions"] = 1.0
        else:
            components["view_before_functions"] = 0.0
    elif view_match and not func_xvial_match:
        # If functions were removed entirely, that's partial credit
        components["view_before_functions"] = 0.3
    else:
        components["view_before_functions"] = 0.0

    # 2. Check view definition is preserved
    if view_match:
        # Verify the view SQL content is preserved
        if "compound_open_data.x_id" in schema_content and "x_released" in schema_content:
            components["view_definition_preserved"] = 1.0
        elif "compound_open_data" in schema_content:
            components["view_definition_preserved"] = 0.5
        else:
            components["view_definition_preserved"] = 0.0
    else:
        components["view_definition_preserved"] = 0.0

    # 3. Check function definitions are preserved
    funcs_preserved = 0.0
    if func_xvial_match:
        # Check com_xvial function body is intact
        if "RETURNS SETOF compound_open_data_locals" in schema_content:
            funcs_preserved += 0.5
        elif "compound_open_data_locals" in schema_content and "com_xvial" in schema_content:
            funcs_preserved += 0.3
    if func_count_match:
        # Check com_xvial_count function body is intact
        if "com_xvial_count" in schema_content and "v_count" in schema_content:
            funcs_preserved += 0.5
        elif "com_xvial_count" in schema_content:
            funcs_preserved += 0.3
    components["function_definitions_preserved"] = min(funcs_preserved, 1.0)

    # 4. Check schema structure validity
    structure_score = 0.0
    # Must have ActiveRecord::Schema define block
    if "ActiveRecord::Schema" in schema_content and ".define" in schema_content:
        structure_score += 0.3
    # Must have enable_extension calls
    if "enable_extension" in schema_content:
        structure_score += 0.2
    # Must have create_table calls
    if "create_table" in schema_content:
        structure_score += 0.2
    # Must still have proper end statements (basic Ruby syntax)
    open_blocks = schema_content.count("do |")
    end_count = len(re.findall(r'^\s*end\s*$', schema_content, re.MULTILINE))
    if end_count >= open_blocks:
        structure_score += 0.3
    components["schema_structure_valid"] = min(structure_score, 1.0)

    # 5. No content loss - key tables must still be present
    required_tables = ["users", "molecules", "samples", "reactions", "collections", "compound_open_data"]
    tables_found = sum(1 for t in required_tables if f'create_table "{t}"' in schema_content)
    components["no_content_loss"] = tables_found / len(required_tables)

    weights = {
        "view_before_functions": 0.40,
        "view_definition_preserved": 0.20,
        "function_definitions_preserved": 0.15,
        "schema_structure_valid": 0.15,
        "no_content_loss": 0.10,
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
