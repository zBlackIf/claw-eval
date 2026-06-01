#!/usr/bin/env python3
"""In-container verifier for CP41_gateway_router_modularization.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")

EXPECTED_BRIDGES = ["express_bridge.py", "train_bridge.py", "reminder_bridge.py", "chat_bridge.py"]
ROUTE_KEYWORDS = ["express", "train", "remind", "chat"]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    router_path = workspace / "gateway" / "router.py"
    router_content = ""
    if router_path.exists():
        router_content = router_path.read_text(encoding="utf-8")
    else:
        for f in workspace.rglob("router.py"):
            router_content = f.read_text(encoding="utf-8")
            break

    if router_content and len(router_content) > 50:
        lower = router_content.lower()
        found = sum(1 for kw in ROUTE_KEYWORDS if kw in lower)
        scores["router_present"] = 1.0 if found >= 3 else (0.5 if found >= 1 else 0.0)

        bridge_refs = sum(
            1 for name in ["express_bridge", "train_bridge", "reminder_bridge", "chat_bridge"]
            if name in lower
        )
        scores["router_uses_bridges"] = bridge_refs / 4.0
        has_priority = bool(re.search(r"(priority|order|routes\s*=|\[.*express.*train.*remind.*chat)", lower, re.DOTALL))
        scores["router_priority_clear"] = 1.0 if has_priority else 0.0
    else:
        scores["router_present"] = 0.0
        scores["router_uses_bridges"] = 0.0
        scores["router_priority_clear"] = 0.0

    weixin_path = workspace / "gateway" / "platforms" / "weixin.py"
    if weixin_path.exists():
        weixin = weixin_path.read_text(encoding="utf-8")
        business_patterns = [
            r"tracking_pattern\s*=",
            r"if.*any.*kw.*in.*\[.*火车",
            r"if.*any.*kw.*in.*\[.*提醒",
            r"_query_express",
        ]
        remaining = sum(1 for p in business_patterns if re.search(p, weixin, re.IGNORECASE))
        if remaining == 0:
            scores["weixin_simplified"] = 1.0
        elif remaining <= 1:
            scores["weixin_simplified"] = 0.5
        else:
            scores["weixin_simplified"] = 0.0

        if "router" in weixin.lower() or "route" in weixin.lower():
            scores["weixin_simplified"] = max(scores["weixin_simplified"], 0.5)
        delegates = bool(re.search(r"(router|route_message|dispatch|route)\s*\(", weixin, re.IGNORECASE))
        sends_message = any(k in weixin for k in ["send", "reply", "response", "xml", "encrypt"])
        scores["weixin_delegates_to_router"] = 1.0 if delegates and sends_message else 0.5 if delegates else 0.0
    else:
        scores["weixin_simplified"] = 0.0
        scores["weixin_delegates_to_router"] = 0.0

    bridges_dir = workspace / "gateway" / "bridges"
    found_bridges = 0
    if bridges_dir.exists():
        for name in EXPECTED_BRIDGES:
            if (bridges_dir / name).exists():
                found_bridges += 1
    scores["four_bridges"] = found_bridges / len(EXPECTED_BRIDGES)

    has_handle = 0
    typed_handle = 0
    total = 0
    if bridges_dir and bridges_dir.exists():
        for name in EXPECTED_BRIDGES:
            p = bridges_dir / name
            if p.exists():
                total += 1
                content = p.read_text(encoding="utf-8")
                if "async def handle" in content or "def handle" in content:
                    has_handle += 1
                if re.search(r"async\s+def\s+handle\s*\(\s*user_id\s*:\s*str\s*,\s*message\s*:\s*str\s*\)\s*->\s*str", content):
                    typed_handle += 1
    scores["uniform_interface"] = (has_handle / total) if total > 0 else 0.0
    scores["typed_async_interface"] = (typed_handle / len(EXPECTED_BRIDGES)) if total > 0 else 0.0

    express_path = bridges_dir / "express_bridge.py" if bridges_dir else None
    if express_path and express_path.exists():
        express = express_path.read_text(encoding="utf-8").lower()
        api_indicators = ["aiohttp", "requests", "httpx", "fetch", "alicloud", "appcode", "wuliu", "api"]
        found = sum(1 for ind in api_indicators if ind in express)
        scores["express_connected"] = 1.0 if found >= 2 else (0.5 if found >= 1 else 0.0)
    else:
        scores["express_connected"] = 0.0

    py_files = [
        workspace / "gateway" / "router.py",
        workspace / "gateway" / "platforms" / "weixin.py",
    ]
    if bridges_dir and bridges_dir.exists():
        py_files.extend(bridges_dir / name for name in EXPECTED_BRIDGES)
    syntax_ok = 0
    existing = [p for p in py_files if p.exists()]
    for path in existing:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            syntax_ok += 1
        except SyntaxError:
            pass
    scores["python_syntax_valid"] = syntax_ok / len(existing) if existing else 0.0

    docs = router_content + "\n"
    if bridges_dir and bridges_dir.exists():
        docs += "\n".join(
            (bridges_dir / name).read_text(encoding="utf-8", errors="ignore")
            for name in EXPECTED_BRIDGES
            if (bridges_dir / name).exists()
        )
    troubleshooting = all(k in docs for k in ["入口", "路由", "bridge"]) or "entry" in docs.lower() and "router" in docs.lower() and "bridge" in docs.lower()
    scores["troubleshooting_order_documented"] = 1.0 if troubleshooting else 0.0

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
