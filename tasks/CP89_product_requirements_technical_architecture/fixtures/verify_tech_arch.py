"""Hidden verifier for CP89 — Multi-agent product requirements → technical architecture."""
from __future__ import annotations

import json
import re
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "multi_tenant", "architecture_diagram", "database_schema_tables",
        "api_design_coverage", "tech_stack_rationale",
    ]}

    all_text = ""
    for f in ws.rglob("*"):
        if not f.is_file():
            continue
        if "fixtures/" in str(f) or "verify" in f.name:
            continue
        if f.suffix in (".md", ".sql", ".yaml", ".yml", ".json", ".txt"):
            try:
                all_text += f.read_text(errors="replace") + "\n"
            except Exception:
                pass

    if re.search(r"(tenant_id|multi.?tenant|tenant.?isolat|schema.?per.?tenant)", all_text, re.I):
        components["multi_tenant"] = 1.0

    arch = ws / "architecture.md"
    if arch.exists():
        atxt = arch.read_text(errors="replace")
        has_layers = bool(re.search(r"(layer|gateway|service|data|api)", atxt, re.I))
        has_diagram = bool(re.search(r"(-->|->|=>|mermaid|graph|flowchart|```)", atxt, re.I))
        svc_kw = ["F1", "F2", "F3", "F4", "F5", "task", "ai", "decompos", "priority", "collab"]
        has_services = sum(1 for k in svc_kw if re.search(k, atxt, re.I))
        components["architecture_diagram"] = 0.3 * has_layers + 0.3 * has_diagram + 0.4 * min(has_services / 5.0, 1.0)

    sql = ws / "database_schema.sql"
    sql_text = sql.read_text(errors="replace") if sql.exists() else ""
    tables = ["user", "team", "project", "task", "subtask", "comment"]
    tf = sum(1 for t in tables if re.search(rf"CREATE\s+TABLE\s+\w*{t}", sql_text + all_text, re.I))
    has_index = bool(re.search(r"(CREATE\s+INDEX|INDEX\s*\()", sql_text + all_text, re.I))
    components["database_schema_tables"] = 0.7 * min(tf / 5.0, 1.0) + 0.3 * has_index

    api = ws / "api_design.yaml"
    if not api.exists():
        api = ws / "api_design.yml"
    api_text = api.read_text(errors="replace") if api.exists() else ""
    api_kw = ["task", "decompos", "priority", "auth", "jwt", "sso", "team", "collab"]
    af = sum(1 for k in api_kw if re.search(k, api_text + all_text, re.I))
    has_crud = bool(re.search(r"(GET|POST|PUT|DELETE|PATCH)", api_text + all_text))
    has_pg = bool(re.search(r"(page|limit|offset|cursor|pagination)", api_text + all_text, re.I))
    components["api_design_coverage"] = 0.5 * min(af / 5.0, 1.0) + 0.3 * has_crud + 0.2 * has_pg

    rationale = ws / "tech_stack_rationale.md"
    if rationale.exists():
        rt = rationale.read_text(errors="replace")
        has_alts = bool(re.search(r"(altern|vs|compar|option|备选)", rt, re.I))
        has_cons = bool(re.search(r"(budget|team.?size|mvp|timeline|startup)", rt, re.I))
        has_evol = bool(re.search(r"(evolv|migrat|scale|future|phase|演进|扩展)", rt, re.I))
        components["tech_stack_rationale"] = (has_alts + has_cons + has_evol) / 3.0

    weights = {
        "multi_tenant": 0.20,
        "architecture_diagram": 0.20,
        "database_schema_tables": 0.20,
        "api_design_coverage": 0.20,
        "tech_stack_rationale": 0.20,
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
