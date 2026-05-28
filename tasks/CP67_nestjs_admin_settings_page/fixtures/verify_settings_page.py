"""Hidden verifier for CP67 — admin Settings page (React/Antd)."""
from __future__ import annotations

import json
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    targets = [
        ws / "apps" / "admin-web" / "src" / "pages" / "Settings.tsx",
        ws / "Settings.tsx",
        ws / "src" / "pages" / "Settings.tsx",
        ws / "src" / "Settings.tsx",
        ws / "pages" / "Settings.tsx",
    ]
    settings = next((p for p in targets if p.exists()), None)
    components = {k: 0.0 for k in [
        "file_present", "substantive", "tabs_layout",
        "basic_settings", "feature_switches", "system_info",
    ]}
    if not settings:
        return {"overall_score": 0.0, "components": components}

    content = _read(settings)
    components["file_present"] = 1.0
    components["substantive"] = 1.0 if len(content.strip()) > 600 else (0.4 if len(content) > 200 else 0.0)

    has_tabs = any(kw in content for kw in ["Tabs", "Tab.TabPane", "TabPane", "items="])
    components["tabs_layout"] = 1.0 if has_tabs and components["substantive"] > 0 else 0.0

    lower = content.lower()
    has_form = "Form" in content
    has_site_name = any(kw in lower for kw in ["site", "name", "title", "sitename", "站点"])
    has_phone = any(kw in lower for kw in ["phone", "contact", "telephone", "电话"])
    if has_form and has_site_name and has_phone:
        components["basic_settings"] = 1.0
    elif has_form and (has_site_name or has_phone):
        components["basic_settings"] = 0.5

    has_switch = "Switch" in content
    has_ai = any(kw in lower for kw in ["ai", "classify", "auto", "分派", "分类"])
    if has_switch and has_ai:
        components["feature_switches"] = 1.0
    elif has_switch:
        components["feature_switches"] = 0.5

    has_system = any(kw in lower for kw in ["system", "cache", "version", "clear", "maintenance", "缓存", "系统信息"])
    has_button = "Button" in content
    if has_system and has_button and components["substantive"] > 0:
        components["system_info"] = 1.0
    elif has_system:
        components["system_info"] = 0.5

    weights = {
        "file_present": 0.10,
        "substantive": 0.15,
        "tabs_layout": 0.20,
        "basic_settings": 0.20,
        "feature_switches": 0.20,
        "system_info": 0.15,
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
