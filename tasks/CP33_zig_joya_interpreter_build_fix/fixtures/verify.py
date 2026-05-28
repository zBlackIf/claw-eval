#!/usr/bin/env python3
"""In-container verifier for CP33_zig_joya_interpreter_build_fix.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    def read_file(relpath: str) -> str:
        p = workspace / relpath
        return p.read_text(errors="ignore") if p.exists() else ""

    build_zig = read_file("build.zig")
    lexer_zig = read_file("src/lexer.zig")
    parser_zig = read_file("src/parser.zig")
    interp_zig = read_file("src/interpreter.zig")

    # build.zig fixed (removed old API, uses new root_module or equivalent)
    has_old_api = bool(re.search(r"\.root_source_file\s*=\s*b\.path", build_zig))
    has_new_api = bool(re.search(r"(\.root_module\s*=|createModule\s*\(|addExecutable\s*\(\s*\.?\{)", build_zig))
    if has_new_api and not has_old_api:
        scores["build_zig_fixed"] = 1.0
    elif has_new_api:
        scores["build_zig_fixed"] = 0.75
    elif not has_old_api:
        scores["build_zig_fixed"] = 0.5
    else:
        scores["build_zig_fixed"] = 0.0

    # lexer compiles (looks clean)
    lexer_looks_clean = (
        "pub fn tokenize" in lexer_zig
        and "return" in lexer_zig
        and lexer_zig.strip() != ""
    )
    scores["lexer_compiles"] = 1.0 if lexer_looks_clean else 0.0

    # parser fixes. Accept equivalent names and whitespace instead of one exact
    # hidden solution shape.
    has_var_tok = bool(re.search(r"\bvar\s+\w+\s*=\s*self\.peek", parser_zig))
    has_const_tok = bool(re.search(r"\bconst\s+\w+\s*=\s*self\.peek", parser_zig))
    fixed_deinit = bool(re.search(r"(pub fn deinit\([^)]*_\s*:|_ = self|self\.\w+)", parser_zig))
    score = 0.0
    if fixed_deinit:
        score += 0.5
    if has_const_tok and not has_var_tok:
        score += 0.5
    elif not has_var_tok:
        score += 0.25
    scores["parser_compiles"] = min(1.0, score)

    # interpreter exists
    if interp_zig.strip():
        has_execute = bool(re.search(r"(pub fn execute|pub fn run|pub fn eval)", interp_zig))
        has_print = bool(re.search(r"(print|std\.debug\.print|stdout)", interp_zig))
        feature_count = sum([has_execute, has_print])
        scores["interpreter_exists"] = min(1.0, feature_count / 2.0)
    else:
        scores["interpreter_exists"] = 0.0

    # example preserved
    example = read_file("examples/hello.joya")
    if example.strip():
        has_let = "let " in example
        has_print = "print(" in example
        scores["example_preserved"] = 1.0 if (has_let and has_print) else 0.5
    else:
        scores["example_preserved"] = 0.0

    # If Zig is available in the sandbox, prefer the real build signal. Keep it
    # optional so verifier remains portable in stripped-down runners.
    if shutil.which("zig") and (workspace / "build.zig").exists():
        try:
            proc = subprocess.run(
                ["zig", "build"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=30,
            )
            scores["zig_build_passes"] = 1.0 if proc.returncode == 0 else 0.0
        except Exception:
            scores["zig_build_passes"] = 0.0
    else:
        scores["zig_build_passes"] = 1.0 if (
            scores["build_zig_fixed"] >= 0.75
            and scores["lexer_compiles"] >= 1.0
            and scores["parser_compiles"] >= 0.75
        ) else 0.0

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
