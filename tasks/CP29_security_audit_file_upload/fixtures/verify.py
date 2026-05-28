#!/usr/bin/env python3
"""In-container verifier for CP29_security_audit_file_upload.

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

    # Find audit report
    report = None
    for pattern in ["audit_report*", "*audit*", "*security*report*"]:
        matches = list(workspace.rglob(pattern))
        if matches:
            report = matches[0]
            break

    if not report:
        for f in workspace.rglob("*.md"):
            if f.name not in ("project_structure.txt",):
                report = f
                break

    if report and report.exists():
        content = report.read_text(encoding="utf-8", errors="ignore")
        scores["report_created"] = 1.0

        # Check vulnerability identification
        vuln_checks = {
            "path_traversal": bool(re.search(
                r"path.?traversal|路径穿越|目录遍历|\.\./", content, re.IGNORECASE
            )),
            "no_size_limit": bool(re.search(
                r"size.?limit|大小限制|file.?size|无限制", content, re.IGNORECASE
            )),
            "web_root": bool(re.search(
                r"web.?root|uploads/|存储路径|accessible|可访问", content, re.IGNORECASE
            )),
            "no_extension": bool(re.search(
                r"extension|扩展名|白名单|whitelist", content, re.IGNORECASE
            )),
            "filename_sanitize": bool(re.search(
                r"sanitiz|净化|文件名|filename|注入", content, re.IGNORECASE
            )),
        }
        found = sum(1 for v in vuln_checks.values() if v)
        scores["vulns_identified"] = round(found / 5.0, 2)
        control_checks = {
            "canonical_path": bool(re.search(r"canonical|normalize|realpath|标准化", content, re.I)),
            "extension_allowlist": bool(re.search(r"allowlist|whitelist|白名单|扩展名", content, re.I)),
            "size_limit": bool(re.search(r"max.*size|size.*limit|大小限制", content, re.I)),
            "outside_webroot": bool(re.search(r"outside.*web|非web|private|不可直接访问|web.?root", content, re.I)),
            "auth_or_csrf": bool(re.search(r"auth|鉴权|csrf|token|permission", content, re.I)),
            "virus_or_content_scan": bool(re.search(r"scan|virus|mime|content.?type|内容校验", content, re.I)),
        }
        scores["security_controls_covered"] = sum(control_checks.values()) / len(control_checks)

        # Has risk level classification
        has_risk_level = bool(re.search(
            r"高|中|低|critical|high|medium|low|严重", content, re.IGNORECASE
        ))
        scores["risk_rated"] = 1.0 if has_risk_level else 0.0

        # Has fix recommendations
        has_fix = bool(re.search(
            r"修复|建议|recommend|fix|remediat|方案", content, re.IGNORECASE
        ))
        scores["has_recommendations"] = 1.0 if has_fix else 0.0
    else:
        scores["report_created"] = 0.0
        scores["vulns_identified"] = 0.0
        scores["risk_rated"] = 0.0
        scores["has_recommendations"] = 0.0

    # Check fix code exists
    fix_files = list(workspace.rglob("*fix*")) + list(workspace.rglob("*secure*"))
    java_fix = [f for f in fix_files if f.suffix in (".java", ".ts")]
    fix_text = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in java_fix[:5])
    code_controls = [
        bool(re.search(r"normalize|canonical|Paths\.get|getCanonical", fix_text, re.I)),
        bool(re.search(r"MAX_|max.*size|contentLength|size", fix_text, re.I)),
        bool(re.search(r"allow|white|extension|mime|contentType", fix_text, re.I)),
        bool(re.search(r"uuid|random|sanitize|clean", fix_text, re.I)),
    ]
    scores["fix_code_present"] = min(sum(code_controls) / 3.0, 1.0) if java_fix else 0.0

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
