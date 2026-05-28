"""Hidden verifier for CP81 — R Shiny navigation dashboard."""
from __future__ import annotations

import json
import re
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    app = ws / "shiny" / "shiny-dashboard" / "app.R"
    components = {k: 0.0 for k in [
        "dashboard_created", "bslib_used", "sidebar_collapsed",
        "reactable_used", "launch_buttons", "base64_favicon",
        "package_prefixes", "single_file",
    ]}
    if not app.exists():
        return {"overall_score": 0.0, "components": components}

    components["dashboard_created"] = 1.0
    content = app.read_text(encoding="utf-8", errors="ignore")

    # bslib
    has_page_sidebar = "page_sidebar" in content
    has_sidebar = "sidebar(" in content or "sidebar (" in content
    if has_page_sidebar and has_sidebar:
        components["bslib_used"] = 1.0
    elif has_page_sidebar or has_sidebar:
        components["bslib_used"] = 0.5

    # sidebar collapsed
    if re.search(r'open\s*=\s*["\']closed["\']', content):
        components["sidebar_collapsed"] = 1.0
    elif "collapsed" in content and "TRUE" in content:
        components["sidebar_collapsed"] = 0.25

    # reactable
    has_reactable = "reactable" in content
    has_filterable = "filterable" in content
    if has_reactable and has_filterable:
        components["reactable_used"] = 1.0
    elif has_reactable:
        components["reactable_used"] = 0.5

    # launch buttons
    has_target_blank = "target" in content and "_blank" in content
    has_window_open = "window.open" in content
    has_onclick = "onclick" in content.lower() or "observeEvent" in content
    if has_target_blank:
        components["launch_buttons"] = 1.0
    elif has_window_open:
        components["launch_buttons"] = 0.7
    elif has_onclick:
        components["launch_buttons"] = 0.5

    # base64 favicon
    has_b64 = "base64" in content and "data:" in content
    has_favicon = "favicon" in content.lower() or "shortcut icon" in content.lower()
    if has_b64 and has_favicon:
        components["base64_favicon"] = 1.0
    elif has_b64:
        components["base64_favicon"] = 0.5

    # package prefixes
    prefix_calls = len(re.findall(r"\w+::\w+", content))
    unprefixed = 0
    for fn in ["reactable", "page_sidebar", "sidebar", "accordion"]:
        unprefixed += len(re.findall(r"(?<!\w::)" + fn + r"\s*\(", content))
    if prefix_calls >= 5 and unprefixed == 0:
        components["package_prefixes"] = 1.0
    elif prefix_calls >= 3:
        components["package_prefixes"] = 0.75
    elif prefix_calls >= 1:
        components["package_prefixes"] = 0.5

    # single file (no www/)
    www_dir = ws / "shiny" / "shiny-dashboard" / "www"
    if not www_dir.exists():
        components["single_file"] = 1.0
    else:
        favicons = list(www_dir.glob("*icon*")) + list(www_dir.glob("*favicon*"))
        components["single_file"] = 0.0 if favicons else 0.5

    weights = {
        "dashboard_created": 0.10,
        "bslib_used": 0.15,
        "sidebar_collapsed": 0.10,
        "reactable_used": 0.20,
        "launch_buttons": 0.15,
        "base64_favicon": 0.10,
        "package_prefixes": 0.10,
        "single_file": 0.10,
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
