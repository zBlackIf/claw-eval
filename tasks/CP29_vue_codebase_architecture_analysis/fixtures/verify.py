#!/usr/bin/env python3
"""In-container verifier for CP31_vue_codebase_architecture_analysis.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    # Check CRUD API factory
    crud_api = workspace / "src" / "api" / "createCrudApi.ts"
    if not crud_api.exists():
        for f in workspace.rglob("*crud*api*"):
            crud_api = f
            break

    if crud_api and crud_api.exists():
        content = crud_api.read_text(encoding="utf-8", errors="ignore")
        scores["crud_api_created"] = 1.0
        has_generic = "<T>" in content or "T extends" in content
        has_crud = all(m in content.lower() for m in ["list", "create", "update", "delete"])
        scores["crud_api_quality"] = 1.0 if (has_generic and has_crud) else (0.5 if has_crud else 0.0)
        supports_extensions = any(k in content for k in ["export", "stats", "permissions", "custom", "extra", "actions"])
        uses_request = "request" in content and re.search(r"method\s*:", content)
        scores["crud_api_extensible"] = 1.0 if supports_extensions and uses_request else (0.5 if supports_extensions else 0.0)
    else:
        scores["crud_api_created"] = 0.0
        scores["crud_api_quality"] = 0.0
        scores["crud_api_extensible"] = 0.0

    # Check useListPage composable
    composable = workspace / "src" / "composables" / "useListPage.ts"
    if not composable.exists():
        for f in workspace.rglob("*useListPage*"):
            composable = f
            break

    if composable and composable.exists():
        content = composable.read_text(encoding="utf-8", errors="ignore")
        scores["composable_created"] = 1.0
        has_loading = "loading" in content
        has_pagination = "page" in content.lower() or "pagination" in content.lower()
        has_error = "error" in content
        scores["composable_quality"] = sum([has_loading, has_pagination, has_error]) / 3.0
        uses_vue_composition = any(k in content for k in ["ref(", "reactive(", "computed(", "onMounted"])
        accepts_loader = bool(re.search(r"useListPage\s*\([^)]*(api|fetch|loader|service|list)", content, re.IGNORECASE | re.DOTALL))
        scores["composable_reusable"] = (float(uses_vue_composition) + float(accepts_loader)) / 2.0
    else:
        scores["composable_created"] = 0.0
        scores["composable_quality"] = 0.0
        scores["composable_reusable"] = 0.0

    # Check type definitions
    types_file = workspace / "src" / "types" / "index.ts"
    if not types_file.exists():
        for f in workspace.rglob("*types*"):
            if f.suffix in (".ts", ".d.ts"):
                types_file = f
                break

    if types_file and types_file.exists():
        content = types_file.read_text(encoding="utf-8", errors="ignore")
        scores["types_created"] = 1.0
        has_interface = "interface" in content or "type" in content
        scores["types_quality"] = 1.0 if has_interface else 0.0
        domain_hits = sum(1 for k in ["Bill", "Member", "Budget", "Pagination", "ApiResponse", "List"] if k in content)
        scores["domain_types_coverage"] = min(domain_hits / 4.0, 1.0)
    else:
        scores["types_created"] = 0.0
        scores["types_quality"] = 0.0
        scores["domain_types_coverage"] = 0.0

    # Check REFACTOR_PLAN.md
    plan_file = workspace / "REFACTOR_PLAN.md"
    if not plan_file.exists():
        for f in workspace.rglob("*REFACTOR*"):
            plan_file = f
            break
        if not plan_file or not plan_file.exists():
            for f in workspace.rglob("*refactor*plan*"):
                plan_file = f
                break

    if plan_file and plan_file.exists():
        content = plan_file.read_text(encoding="utf-8", errors="ignore")
        scores["plan_created"] = 1.0
        has_priority = bool(re.search(r"(优先|priority|步骤|step|phase)", content, re.IGNORECASE))
        has_risk = bool(re.search(r"(风险|risk|兼容|compat)", content, re.IGNORECASE))
        scores["plan_quality"] = (1.0 if has_priority else 0.0) * 0.5 + (1.0 if has_risk else 0.0) * 0.5
        existing_code_refs = sum(1 for k in ["request.js", "401", "exportBills", "permissions", "Options API", "Composition API"] if k in content)
        scores["plan_uses_project_evidence"] = min(existing_code_refs / 4.0, 1.0)
    else:
        scores["plan_created"] = 0.0
        scores["plan_quality"] = 0.0
        scores["plan_uses_project_evidence"] = 0.0

    return scores


def main() -> dict:
    try:
        scores = automated_score(WORKSPACE)
    except Exception as exc:  # noqa: BLE001
        return {"scores": {}, "overall_score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    overall = sum(numeric) / len(numeric) if numeric else 0.0
    return {"scores": scores, "overall_score": round(overall, 4)}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(main(), ensure_ascii=False) + "\n")
