"""Hidden verifier for CP90 — incidence rate validation script fix."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_script(ws: Path) -> Path | None:
    preferred = [
        ws / "validate_incidence_rate.py",
        ws / "fixtures" / "validate_incidence_rate.py",
    ]
    for p in preferred:
        if p.exists():
            return p
    for p in ws.rglob("validate_incidence_rate.py"):
        if p.is_file() and "verify_incidence_fix.py" not in p.name:
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "script_present", "pad_code_fixed", "other_codes_intact",
        "csv_generated", "cvdeath_addressed", "analysis_notes",
    ]}

    script = _find_script(ws)
    content = _read(script) if script else ""
    if script:
        components["script_present"] = 1.0

        # PAD codes include I73 (the missing one)
        pad_match = re.search(
            r'"short_name"\s*:\s*"PAD".*?"codes"\s*:\s*\[(.*?)\]',
            content, re.DOTALL,
        )
        if pad_match:
            codes_str = pad_match.group(1)
            has_i70 = '"I70"' in codes_str or "'I70'" in codes_str
            has_i73 = '"I73"' in codes_str or "'I73'" in codes_str
            if has_i70 and has_i73:
                components["pad_code_fixed"] = 1.0
            elif has_i73:
                components["pad_code_fixed"] = 0.75
        elif "I73" in content and "PAD" in content:
            components["pad_code_fixed"] = 0.6

        # Other codes intact (CAD/Stroke/AF/VTE)
        cad_ok = all(f'"{c}"' in content or f"'{c}'" in content for c in ["I20", "I21", "I22", "I23", "I24", "I25"])
        stroke_ok = all(f'"{c}"' in content or f"'{c}'" in content for c in ["I60", "I61", "I62", "I63"])
        af_ok = '"I48"' in content or "'I48'" in content
        vte_ok = all(f'"{c}"' in content or f"'{c}'" in content for c in ["I26", "I80", "I81", "I82"])
        components["other_codes_intact"] = sum([cad_ok, stroke_ok, af_ok, vte_ok]) / 4

    # CSV generated
    csv_file = ws / "incidence_rate_comparison.csv"
    if not csv_file.exists():
        for p in ws.rglob("incidence_rate_comparison.csv"):
            csv_file = p
            break
    if csv_file.exists():
        try:
            lines = csv_file.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
            if len(lines) >= 5:
                components["csv_generated"] = 1.0
            elif len(lines) >= 2:
                components["csv_generated"] = 0.5
        except Exception:
            pass

    # CVDeath addressed
    if content and ("cvdeath" in content.lower() or "cv_death" in content.lower() or "cardiovascular death" in content.lower()):
        components["cvdeath_addressed"] = 1.0
    notes = ws / "analysis_notes.md"
    if notes.exists():
        ntxt = _read(notes).lower()
        if any(k in ntxt for k in ["cvdeath", "cv death", "cv_death", "cardiovascular death"]):
            components["cvdeath_addressed"] = max(components["cvdeath_addressed"], 1.0)

    # Analysis notes
    if notes.exists():
        ntxt = _read(notes)
        if len(ntxt) >= 300:
            components["analysis_notes"] = 1.0
        elif len(ntxt) >= 100:
            components["analysis_notes"] = 0.5

    weights = {
        "script_present": 0.05,
        "pad_code_fixed": 0.30,
        "other_codes_intact": 0.15,
        "csv_generated": 0.20,
        "cvdeath_addressed": 0.15,
        "analysis_notes": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "script_seen": str(script.relative_to(ws)) if script else None,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
