"""Hidden verifier for CP97 — Spring Boot WebFlux → WebMVC refactor."""
from __future__ import annotations

import json
import re
from pathlib import Path


REACTIVE_IMPORTS = [
    r"import\s+reactor\.",
    r"import\s+org\.springframework\.web\.reactive\.",
    r"import\s+org\.springframework\.web\.reactive\.function\.client\.WebClient",
]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _has_reactive(content: str) -> bool:
    return any(re.search(p, content) for p in REACTIVE_IMPORTS)


def grade_workspace(ws: Path) -> dict:
    base = ws / "src" / "main" / "java" / "live" / "os" / "godspace" / "service"
    seedance = base / "SeeDanceProvider.java"
    wanxiang = base / "WanxiangVideoProvider.java"

    components = {k: 0.0 for k in [
        "seedance_no_reactive", "seedance_uses_resttemplate",
        "seedance_no_webclient", "seedance_sync_poll",
        "wanxiang_no_reactive", "wanxiang_uses_resttemplate",
        "wanxiang_no_webclient", "interface_intact",
    ]}

    sc = _read(seedance)
    if sc:
        components["seedance_no_reactive"] = 0.0 if _has_reactive(sc) else 1.0
        has_field = bool(re.search(r"RestTemplate\s+\w+", sc))
        has_import = bool(re.search(r"import\s+org\.springframework\.web\.client\.RestTemplate", sc))
        has_use = bool(re.search(r"restTemplate\.", sc, re.I))
        if has_field and has_import and has_use:
            components["seedance_uses_resttemplate"] = 1.0
        elif has_field and has_use:
            components["seedance_uses_resttemplate"] = 0.75
        elif has_field or has_use:
            components["seedance_uses_resttemplate"] = 0.25
        components["seedance_no_webclient"] = 0.0 if "WebClient" in sc else 1.0
        has_while = bool(re.search(r"while\s*\(", sc))
        has_sleep = bool(re.search(r"Thread\.sleep", sc))
        no_defer = "Mono.defer" not in sc
        no_repeat = "repeatWhenEmpty" not in sc
        if has_while and has_sleep and no_defer and no_repeat:
            components["seedance_sync_poll"] = 1.0
        elif has_while and has_sleep:
            components["seedance_sync_poll"] = 0.5

    wc = _read(wanxiang)
    if wc:
        components["wanxiang_no_reactive"] = 0.0 if _has_reactive(wc) else 1.0
        has_field = bool(re.search(r"RestTemplate\s+\w+", wc))
        has_use = bool(re.search(r"restTemplate\.", wc, re.I))
        if has_field and has_use:
            components["wanxiang_uses_resttemplate"] = 1.0
        elif has_field or has_use:
            components["wanxiang_uses_resttemplate"] = 0.5
        components["wanxiang_no_webclient"] = 0.0 if "WebClient" in wc else 1.0

    interface_file = base / "VideoProvider.java"
    if interface_file.exists():
        ic = _read(interface_file)
        if "interface VideoProvider" in ic:
            components["interface_intact"] = 1.0
    else:
        components["interface_intact"] = 0.5

    weights = {
        "seedance_no_reactive": 0.15,
        "seedance_uses_resttemplate": 0.15,
        "seedance_no_webclient": 0.10,
        "seedance_sync_poll": 0.20,
        "wanxiang_no_reactive": 0.15,
        "wanxiang_uses_resttemplate": 0.10,
        "wanxiang_no_webclient": 0.10,
        "interface_intact": 0.05,
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
