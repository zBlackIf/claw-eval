"""Hidden verifier for CP96 — Mobile video operation page."""
from __future__ import annotations

import json
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    vue_files = list(ws.rglob("*.vue"))
    components = {k: 0.0 for k in [
        "page_created", "video_element", "fullscreen_api",
        "video_list", "typescript_typed", "uno_or_tailwind",
    ]}

    video_pages = [f for f in vue_files if "video" in f.stem.lower() or "video" in str(f.parent).lower()]
    if video_pages:
        components["page_created"] = 1.0

    all_vue = ""
    for f in vue_files:
        try:
            all_vue += f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    if "<video" in all_vue:
        components["video_element"] = 1.0

    fs = ["requestfullscreen", "fullscreenElement", "webkitRequestFullscreen",
          "requestFullscreen", "fullscreen"]
    if any(p.lower() in all_vue.lower() for p in fs):
        components["fullscreen_api"] = 1.0

    if "v-for" in all_vue and "video" in all_vue.lower():
        components["video_list"] = 1.0

    ts_files = list(ws.rglob("*.ts")) + vue_files
    all_ts = ""
    for f in ts_files:
        try:
            all_ts += f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    if any(k in all_ts for k in ["interface ", "type ", ": string", ": number",
                                   "Ref<", "ref<", 'lang="ts"', "VideoItem"]):
        components["typescript_typed"] = 1.0

    if "unocss" in all_vue.lower() or "tailwind" in all_vue.lower() or "uno-" in all_vue.lower():
        components["uno_or_tailwind"] = 1.0
    elif "class=" in all_vue:
        components["uno_or_tailwind"] = 0.5

    weights = {
        "page_created": 0.15,
        "video_element": 0.20,
        "fullscreen_api": 0.25,
        "video_list": 0.20,
        "typescript_typed": 0.10,
        "uno_or_tailwind": 0.10,
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
