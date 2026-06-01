"""Hidden verifier for CP70 — VikingBot skill manager refactoring."""
from __future__ import annotations

import json
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_skill_dir(skills_dir: Path, aliases: list[str], contains: list[str] | None = None) -> Path | None:
    for name in aliases:
        p = skills_dir / name
        if (p / "SKILL.md").exists():
            return p
    contains = contains or []
    if skills_dir.exists():
        for p in sorted(skills_dir.iterdir()):
            if not p.is_dir() or not (p / "SKILL.md").exists():
                continue
            lower = p.name.lower()
            if all(token in lower for token in contains):
                return p
    return None


def _find_python_script(skill_dir: Path | None, preferred: list[str]) -> Path | None:
    if not skill_dir:
        return None
    for rel in preferred:
        p = skill_dir / rel
        if p.exists():
            return p
    scripts = [p for p in skill_dir.rglob("*.py") if p.is_file()]
    return sorted(scripts)[0] if scripts else None


def grade_workspace(ws: Path) -> dict:
    skills_dir = ws / "skills"
    components = {k: 0.0 for k in [
        "handler_skill", "handler_script",
        "recognizer_skill", "recognizer_script",
        "old_skills_removed", "aes_decrypt", "path_based_recognition",
    ]}

    handler_dir = _find_skill_dir(skills_dir, ["wecom-media-handler", "media-handler"], ["media", "handler"])
    components["handler_skill"] = 1.0 if handler_dir and (handler_dir / "SKILL.md").exists() else 0.0

    handler_script = _find_python_script(handler_dir, ["scripts/handler.py", "handler.py"])
    components["handler_script"] = 1.0 if handler_script and handler_script.exists() else 0.0

    recog_dir = _find_skill_dir(
        skills_dir,
        ["image-recognizer", "wecom-image-recognizer"],
        ["image", "recognizer"],
    )
    components["recognizer_skill"] = 1.0 if recog_dir and (recog_dir / "SKILL.md").exists() else 0.0

    recog_script = _find_python_script(recog_dir, ["scripts/recognizer.py", "recognizer.py"])
    components["recognizer_script"] = 1.0 if recog_script and recog_script.exists() else 0.0

    old_proc = skills_dir / "wecom-media-processor" / "SKILL.md"
    old_dl = skills_dir / "wecom-media-downloader" / "SKILL.md"
    old_exists = old_proc.exists() or old_dl.exists()
    new_handler_exists = handler_dir is not None
    new_recog_exists = recog_dir is not None
    if new_handler_exists and new_recog_exists and not old_exists:
        components["old_skills_removed"] = 1.0
    elif new_handler_exists and new_recog_exists:
        components["old_skills_removed"] = 0.5

    if handler_script and handler_script.exists():
        content = _read(handler_script)
        has_aes = "AES" in content or "aes" in content
        has_cbc = "CBC" in content or "cbc" in content
        has_decrypt = "decrypt" in content
        if has_aes and has_cbc and has_decrypt:
            components["aes_decrypt"] = 1.0
        elif has_aes and has_decrypt:
            components["aes_decrypt"] = 0.75
        elif has_decrypt:
            components["aes_decrypt"] = 0.5

    if recog_script and recog_script.exists():
        content = _read(recog_script)
        has_path = "path" in content.lower() or "file" in content.lower()
        has_cli = "argparse" in content or "sys.argv" in content or "--path" in content
        if has_path and has_cli:
            components["path_based_recognition"] = 1.0
        elif has_path:
            components["path_based_recognition"] = 0.5

    weights = {
        "handler_skill": 0.15,
        "handler_script": 0.15,
        "recognizer_skill": 0.15,
        "recognizer_script": 0.15,
        "old_skills_removed": 0.15,
        "aes_decrypt": 0.15,
        "path_based_recognition": 0.10,
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
