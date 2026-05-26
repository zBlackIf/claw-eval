#!/usr/bin/env python3
"""In-container verifier for CP22_php_url_proxy_path_format.

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

    # Check index.php exists and has URL parsing logic
    index_php = workspace / "project" / "index.php"
    if index_php.exists():
        content = index_php.read_text()
        scores["index_php_present"] = 1.0
        # Check for PATH_INFO or REQUEST_URI extraction
        has_path_parsing = any(k in content for k in [
            "PATH_INFO", "REQUEST_URI", "path_info", "request_uri"
        ])
        scores["path_info_extraction"] = 1.0 if has_path_parsing else 0.0
        # Check for http/https URL detection
        has_url_detection = bool(re.search(
            r'(https?://|preg_match.*https?|strpos.*https?)', content
        ))
        scores["url_scheme_detection"] = 1.0 if has_url_detection else 0.0
        # Check no dangerous functions
        dangerous = ["eval(", "system(", "exec(", "shell_exec(", "passthru("]
        has_dangerous = any(d in content for d in dangerous)
        scores["no_dangerous_functions"] = 0.0 if has_dangerous else 1.0
        # Check backward compatibility preserved (?q= still works)
        has_q_param = "$_GET['q']" in content or '$_GET["q"]' in content or "_GET['q']" in content
        scores["backward_compatible"] = 1.0 if has_q_param else 0.0
    else:
        scores["index_php_present"] = 0.0
        scores["path_info_extraction"] = 0.0
        scores["url_scheme_detection"] = 0.0
        scores["no_dangerous_functions"] = 0.0
        scores["backward_compatible"] = 0.0

    # Check .htaccess
    htaccess = workspace / "project" / ".htaccess"
    if htaccess.exists():
        content = htaccess.read_text()
        scores["htaccess_present"] = 1.0
        scores["accept_path_info"] = 1.0 if "AcceptPathInfo" in content else 0.0
        scores["rewrite_rule"] = 1.0 if "RewriteRule" in content else 0.0
    else:
        scores["htaccess_present"] = 0.0
        scores["accept_path_info"] = 0.0
        scores["rewrite_rule"] = 0.0

    # Check Apache config
    vhost = workspace / "apache2" / "sites-available" / "url-proxy.conf"
    if vhost.exists():
        scores["vhost_present"] = 1.0
    else:
        scores["vhost_present"] = 0.0

    # Check CHANGES.md
    changes = workspace / "project" / "CHANGES.md"
    if changes.exists():
        content = changes.read_text()
        scores["changes_md_present"] = 1.0
        scores["changes_explains_usage"] = 1.0 if "proxy/" in content.lower() or "/https" in content else 0.0
    else:
        scores["changes_md_present"] = 0.0
        scores["changes_explains_usage"] = 0.0

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
