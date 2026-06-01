"""Hidden verifier for CP82 — Flutter trading dashboard multi-screen fix."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
    except Exception:
        return ""


def _is_fixture_path(ws: Path, p: Path) -> bool:
    try:
        rel = p.relative_to(ws)
    except ValueError:
        rel = p
    return "fixtures" in rel.parts


def _find(ws: Path, name: str):
    target = ws / "lib" / "screens" / name
    if target.exists():
        return target
    for f in ws.rglob(name):
        if f.is_file() and not _is_fixture_path(ws, f):
            return f
    return None


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "dashboard_not_empty", "dashboard_metrics",
        "risk_not_empty", "risk_controls",
        "order_not_empty", "order_table",
        "alert_encoding_fixed",
        "strategy_has_version", "strategy_has_weights",
        "strategy_no_add_button", "strategy_has_version_add",
        "material_widgets",
    ]}

    dash = _find(ws, "dashboard_screen.dart")
    dash_txt = _read(dash) if dash else ""
    if dash_txt:
        is_empty = bool(re.search(r"return\s+Container\s*\(\s*\)\s*;", dash_txt))
        components["dashboard_not_empty"] = 0.0 if is_empty else 1.0
        kw = ["asset", "pnl", "profit", "position", "strategy", "总资产", "盈亏", "持仓", "策略"]
        components["dashboard_metrics"] = min(1.0, sum(1 for k in kw if k.lower() in dash_txt.lower()) / 3.0)

    risk = _find(ws, "risk_screen.dart")
    risk_txt = _read(risk) if risk else ""
    if risk_txt:
        is_empty = bool(re.search(r"return\s+Container\s*\(\s*\)\s*;", risk_txt))
        components["risk_not_empty"] = 0.0 if is_empty else 1.0
        kw = ["drawdown", "loss.*limit", "concentration", "max.*drawdown",
              "回撤", "亏损", "限额", "集中度", "风险等级"]
        components["risk_controls"] = min(1.0, sum(1 for k in kw if re.search(k, risk_txt, re.I)) / 3.0)

    order = _find(ws, "order_screen.dart")
    order_txt = _read(order) if order else ""
    if order_txt:
        is_empty = bool(re.search(r"return\s+Container\s*\(\s*\)\s*;", order_txt))
        components["order_not_empty"] = 0.0 if is_empty else 1.0
        components["order_table"] = 1.0 if re.search(r"DataTable|ListView|DataColumn|DataRow", order_txt) else 0.0

    alert = _find(ws, "alert_screen.dart")
    alert_txt = _read(alert) if alert else ""
    if alert_txt:
        has_escaped = bool(re.search(r"'\\u[0-9a-fA-F]{4}", alert_txt))
        has_readable = bool(re.search(r"[一-鿿]{2,}", alert_txt))
        if has_readable and not has_escaped:
            components["alert_encoding_fixed"] = 1.0
        elif has_readable:
            components["alert_encoding_fixed"] = 0.5

    strat = _find(ws, "strategy_screen.dart")
    strat_txt = _read(strat) if strat else ""
    if strat_txt:
        version_in_widget = bool(re.search(r"Text\s*\([^)]*version", strat_txt, re.I))
        version_in_data = bool(re.search(r"['\"]version['\"]|['\"]版本['\"]", strat_txt))
        components["strategy_has_version"] = 1.0 if (version_in_widget or version_in_data) else 0.0

        weight_kw = ["weight", "权重", "winRate", "win_rate", "胜率"]
        w_widget = sum(1 for k in weight_kw if re.search(rf"Text\s*\([^)]*{re.escape(k)}", strat_txt, re.I))
        w_data = sum(1 for k in weight_kw if re.search(rf"['\"].*{re.escape(k)}.*['\"]", strat_txt))
        components["strategy_has_weights"] = min(1.0, max(w_widget, w_data) / 2.0)

        has_add_strategy = bool(re.search(r"[Aa]dd\s*[Ss]trategy|addStrategy|新增策略|_addStrategy", strat_txt))
        components["strategy_no_add_button"] = 0.0 if has_add_strategy else 1.0

        version_add_kw = ["addVersion", "add.*version", "newVersion", "createVersion",
                          "新增版本", "添加版本"]
        components["strategy_has_version_add"] = 1.0 if any(re.search(k, strat_txt, re.I) for k in version_add_kw) else 0.0

    all_dart = ""
    for f in ws.rglob("*.dart"):
        if "screen" in f.name and not _is_fixture_path(ws, f):
            all_dart += _read(f)
    mw = ["Scaffold", "Card", "DataTable", "AppBar", "ListView", "Column", "Row"]
    components["material_widgets"] = min(1.0, sum(1 for w in mw if w in all_dart) / 4.0)

    weights = {
        "dashboard_not_empty": 0.08,
        "dashboard_metrics": 0.08,
        "risk_not_empty": 0.08,
        "risk_controls": 0.08,
        "order_not_empty": 0.08,
        "order_table": 0.08,
        "alert_encoding_fixed": 0.12,
        "strategy_has_version": 0.10,
        "strategy_has_weights": 0.10,
        "strategy_no_add_button": 0.08,
        "strategy_has_version_add": 0.06,
        "material_widgets": 0.06,
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
