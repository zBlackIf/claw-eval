"""Hidden verifier for CP57 — LAMMPS sI hydrate data builder.

Reads /workspace/build_correct_hydrate.py and scores against 7 hidden
anchors from the original PinchBench grading script.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    script = _read(ws / "build_correct_hydrate.py")
    legacy = _read(ws / "step1_create_data.py")
    if not legacy:
        legacy = _read(ws / "fixtures" / "step1_create_data.py")

    components = {}

    # 1. Builder script exists + argparse + --out CLI
    if script and "argparse" in script and "--out" in script:
        components["builder_cli"] = 1.0
    elif script:
        components["builder_cli"] = 0.5
    else:
        components["builder_cli"] = 0.0

    # 2. numpy-only constraint
    has_numpy = bool(re.search(r"\b(?:import|from)\s+numpy\b", script))
    forbidden = any(re.search(rf"\b(?:import|from)\s+{lib}\b", script)
                    for lib in ("ase", "pymatgen", "MDAnalysis"))
    if has_numpy and not forbidden:
        components["numpy_only"] = 1.0
    elif has_numpy:
        components["numpy_only"] = 0.4
    else:
        components["numpy_only"] = 0.0

    # 3. atom-count self-check (192)
    has_atom_count = "192" in script or re.search(r"46\s*\*\s*4\s*\+\s*8", script) is not None
    components["atom_count_check"] = 1.0 if has_atom_count else 0.0

    # 4. box-bounds self-check
    has_box_const = "12.03" in script
    has_bound_check = bool(re.search(r"(?:assert|if|raise|exit|sys\.exit).*?(?:0\.1|a\s*\+|bound|out)", script, re.DOTALL))
    if has_box_const and has_bound_check:
        components["box_bounds_check"] = 1.0
    elif has_box_const:
        components["box_bounds_check"] = 0.5
    else:
        components["box_bounds_check"] = 0.0

    # 5. TIP4P/Ice charges
    has_h_charge = "0.5897" in script
    has_m_charge = "1.1794" in script
    if has_h_charge and has_m_charge:
        components["tip4p_charges"] = 1.0
    elif has_h_charge or has_m_charge:
        components["tip4p_charges"] = 0.5
    else:
        components["tip4p_charges"] = 0.0

    # 6. Bonds + Angles sections
    has_bonds_section = "Bonds" in script
    has_angles_section = "Angles" in script
    if has_bonds_section and has_angles_section:
        components["bonds_angles_sections"] = 1.0
    elif has_bonds_section or has_angles_section:
        components["bonds_angles_sections"] = 0.5
    else:
        components["bonds_angles_sections"] = 0.0

    # 7. Legacy file untouched (must contain original deprecation markers)
    legacy_untouched = bool(
        legacy
        and ("LEGACY" in legacy or "deprecated" in legacy or "BROKEN" in legacy.upper()
             or "step1_create_data.py is deprecated" in legacy
             or "rounding error" in legacy.lower())
    )
    # Soft pass if any meaningful content remains
    if not legacy_untouched and legacy and len(legacy) > 200:
        legacy_untouched = True
    components["legacy_untouched"] = 1.0 if legacy_untouched else 0.0

    weights = {
        "builder_cli": 0.15,
        "numpy_only": 0.10,
        "atom_count_check": 0.20,
        "box_bounds_check": 0.15,
        "tip4p_charges": 0.20,
        "bonds_angles_sections": 0.15,
        "legacy_untouched": 0.05,
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
