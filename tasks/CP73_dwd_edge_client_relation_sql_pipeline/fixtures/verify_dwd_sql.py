"""Hidden verifier for CP73 — DWD edge-PP client relation SQL pipeline."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _find_sql(ws: Path) -> Path | None:
    target = ws / "dwd_gu_user_gdb_edge_client_to_meta.sql"
    if target.exists():
        return target
    for p in ws.rglob("*.sql"):
        n = p.name.lower()
        if "edge" in n or "client" in n or "meta" in n:
            return p
    for p in ws.rglob("*.sql"):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    sql_file = _find_sql(ws)
    components = {k: 0.0 for k in [
        "sql_file_created", "correct_joins", "node_type_filter",
        "recent_time_correct", "json_unx_fields", "edge_pp_client_filter",
        "non_stub",
    ]}
    if not sql_file or not sql_file.exists():
        return {"overall_score": 0.0, "components": components}

    sql = sql_file.read_text(errors="ignore")
    sql_upper = sql.upper()
    if not sql.strip():
        return {"overall_score": 0.0, "components": components}

    components["sql_file_created"] = 1.0
    components["non_stub"] = 1.0 if len(sql.strip()) >= 400 else 0.4

    # Joins
    join_count = len(re.findall(r"\bJOIN\b", sql_upper))
    has_source_join = bool(re.search(
        r"(source_node\s*=\s*\w*\.?node_id|node_id\s*=\s*\w*\.?source_node)",
        sql, re.I))
    has_target_join = bool(re.search(
        r"(target_node\s*=\s*\w*\.?node_id|node_id\s*=\s*\w*\.?target_node)",
        sql, re.I))
    if has_source_join and has_target_join and join_count >= 2:
        components["correct_joins"] = 1.0
    elif has_source_join or has_target_join:
        components["correct_joins"] = 0.5

    # Node type filter
    has_edge_pp = bool(re.search(r"edge_pp_client", sql, re.I))
    has_pp = bool(re.search(r"(node_type\s*=\s*'pp_client'|='pp_client')", sql, re.I))
    if has_edge_pp and has_pp:
        components["edge_pp_client_filter"] = 1.0
    elif has_edge_pp or has_pp:
        components["edge_pp_client_filter"] = 0.5

    components["node_type_filter"] = components["edge_pp_client_filter"]

    # recent_time: GREATEST + FROM_UNIXTIME + 3 args
    has_greatest = bool(re.search(r"(GREATEST|MAX\s*\()", sql_upper))
    has_from_unixtime = bool(re.search(r"FROM_UNIXTIME", sql_upper))
    has_three_args = bool(re.search(r"(GREATEST|MAX)\s*\([^)]*,[^)]*,", sql, re.I))
    if has_greatest and has_from_unixtime and has_three_args:
        components["recent_time_correct"] = 1.0
    elif has_greatest and (has_from_unixtime or has_three_args):
        components["recent_time_correct"] = 0.7
    elif has_greatest:
        components["recent_time_correct"] = 0.4

    # json_value + unx_value
    has_json_col = "json_value" in sql.lower()
    has_unx_col = "unx_value" in sql.lower()
    has_json_merge = bool(re.search(r"(CONCAT|JSON_ARRAY|COALESCE|json_value\s*[:=])", sql, re.I))
    has_unx_max = bool(re.search(r"(GREATEST|MAX)\s*\([^)]*unx_value", sql, re.I))
    if has_json_col and has_unx_col and has_json_merge and has_unx_max:
        components["json_unx_fields"] = 1.0
    elif has_json_col and has_unx_col:
        components["json_unx_fields"] = 0.5
    elif has_json_col or has_unx_col:
        components["json_unx_fields"] = 0.25

    weights = {
        "sql_file_created": 0.10,
        "non_stub": 0.10,
        "correct_joins": 0.20,
        "node_type_filter": 0.10,
        "edge_pp_client_filter": 0.10,
        "recent_time_correct": 0.20,
        "json_unx_fields": 0.20,
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
