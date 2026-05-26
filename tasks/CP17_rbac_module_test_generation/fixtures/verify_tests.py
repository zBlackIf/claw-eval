#!/usr/bin/env python3
"""Verify CP17 generated pytest files.

Outputs one JSON line. Kept hidden from the agent via sandbox_grader_files.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path


TEST_FILES = {
    "role_service": Path("/workspace/tests/test_role_service.py"),
    "user_role_binding": Path("/workspace/tests/test_user_role_binding.py"),
    "access_check": Path("/workspace/tests/test_access_check.py"),
}

SEMANTIC_TERMS = {
    "role_service": [
        "create_role", "delete_role", "effective_permissions",
        "cyclic", "parent", "ValueError",
    ],
    "user_role_binding": [
        "grant", "revoke", "list_active_roles", "tenant", "expires_at",
        "already has active",
    ],
    "access_check": [
        "check_access", "deny_overrides", "tenant", "stale", "has_permission",
    ],
}


def compile_score(files: dict[str, Path]) -> tuple[float, dict[str, str]]:
    errors: dict[str, str] = {}
    ok = 0
    for name, path in files.items():
        try:
            py_compile.compile(str(path), doraise=True)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            errors[name] = str(exc)
    return ok / len(files), errors


def semantic_score(files: dict[str, Path]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for name, path in files.items():
        text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        lower = text.lower()
        has_pytest = "pytest" in lower or "def test_" in lower
        has_assert = "assert " in lower
        test_count = len(re.findall(r"\bdef\s+test_", text))
        term_hits = sum(1 for term in SEMANTIC_TERMS[name] if term.lower() in lower)
        scores[name] = min(
            1.0,
            0.20 * (1.0 if has_pytest else 0.0)
            + 0.20 * (1.0 if has_assert else 0.0)
            + 0.25 * min(test_count / 3.0, 1.0)
            + 0.35 * min(term_hits / 4.0, 1.0),
        )
    return scores


def run_pytest(files: dict[str, Path]) -> tuple[float, str]:
    existing = [str(p) for p in files.values() if p.exists()]
    if not existing:
        return 0.0, "no test files"

    env = os.environ.copy()
    env["PYTHONPATH"] = "/workspace/fixtures/code:" + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *existing],
            cwd="/workspace",
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        return 0.0, str(exc)

    output = (proc.stdout + "\n" + proc.stderr).strip()[-2000:]
    if proc.returncode == 0:
        return 1.0, output
    if "collected 0 items" in output:
        return 0.0, output
    return 0.35, output


def main() -> dict:
    files_present = {name: path.exists() for name, path in TEST_FILES.items()}
    file_score = sum(files_present.values()) / len(TEST_FILES)
    if file_score == 0:
        return {
            "files_present": files_present,
            "compile_score": 0.0,
            "pytest_score": 0.0,
            "semantic_scores": {},
            "overall_score": 0.0,
            "reason": "no test files",
        }

    compile_result, compile_errors = compile_score({
        name: path for name, path in TEST_FILES.items() if path.exists()
    })
    semantic_scores = semantic_score(TEST_FILES)
    semantic_avg = sum(semantic_scores.values()) / len(semantic_scores)
    pytest_score, pytest_output = run_pytest(TEST_FILES)

    overall = (
        0.20 * file_score
        + 0.15 * compile_result
        + 0.25 * pytest_score
        + 0.40 * semantic_avg
    )
    return {
        "files_present": files_present,
        "compile_score": round(compile_result, 4),
        "compile_errors": compile_errors,
        "pytest_score": round(pytest_score, 4),
        "pytest_output": pytest_output,
        "semantic_scores": {k: round(v, 4) for k, v in semantic_scores.items()},
        "overall_score": round(min(max(overall, 0.0), 1.0), 4),
    }


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False))
