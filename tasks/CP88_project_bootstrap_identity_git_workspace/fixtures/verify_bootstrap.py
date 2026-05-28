"""Hidden verifier for CP88 — Project bootstrap identity + git workspace."""
from __future__ import annotations

import json
import os
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "git_initialized", "directory_structure",
        "gitignore", "readme", "editorconfig", "prettierrc",
        "workspace_info", "git_committed", "bootstrap_followed",
    ]}

    # Git initialized
    if (ws / ".git").is_dir():
        components["git_initialized"] = 1.0

    # Directory structure (src/, tests/, docs/, scripts/)
    dirs = ["src", "tests", "docs", "scripts"]
    found_dirs = sum(1 for d in dirs if (ws / d).is_dir())
    components["directory_structure"] = found_dirs / len(dirs)

    # Config files
    if (ws / ".gitignore").exists():
        components["gitignore"] = 1.0
    if (ws / "README.md").exists():
        components["readme"] = 1.0
    if (ws / ".editorconfig").exists():
        components["editorconfig"] = 1.0
    if (ws / ".prettierrc").exists() or (ws / ".prettierrc.json").exists():
        components["prettierrc"] = 1.0

    # WORKSPACE_INFO
    workspace_info = ws / "WORKSPACE_INFO.md"
    if workspace_info.exists():
        content = workspace_info.read_text(encoding="utf-8", errors="ignore")
        # Reasonable env snapshot has node/python/git mentions
        info_score = 0.4
        for kw in ["node", "python", "git"]:
            if kw in content.lower():
                info_score += 0.2
        components["workspace_info"] = min(info_score, 1.0)

    # Git committed (HEAD exists pointing to a commit)
    head = ws / ".git" / "HEAD"
    if head.exists():
        try:
            head_text = head.read_text(encoding="utf-8", errors="ignore").strip()
            if head_text.startswith("ref:"):
                ref_path = ws / ".git" / head_text.split(":", 1)[1].strip()
                if ref_path.exists() and ref_path.read_text(encoding="utf-8", errors="ignore").strip():
                    components["git_committed"] = 1.0
            elif len(head_text) >= 7:
                components["git_committed"] = 1.0
        except Exception:
            pass

    # Bootstrap followed: README or WORKSPACE_INFO references bootstrap
    bootstrap_refs = []
    for fname in ["README.md", "WORKSPACE_INFO.md", "CONTRIBUTING.md"]:
        f = ws / fname
        if f.exists():
            try:
                if "bootstrap" in f.read_text(encoding="utf-8", errors="ignore").lower():
                    bootstrap_refs.append(fname)
            except Exception:
                pass
    components["bootstrap_followed"] = 1.0 if bootstrap_refs else 0.5

    weights = {
        "git_initialized": 0.15,
        "directory_structure": 0.15,
        "gitignore": 0.10,
        "readme": 0.10,
        "editorconfig": 0.05,
        "prettierrc": 0.05,
        "workspace_info": 0.20,
        "git_committed": 0.15,
        "bootstrap_followed": 0.05,
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
