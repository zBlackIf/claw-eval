"""Hidden verifier for CP55 quant strategy lab architecture plan.

Checks /workspace/PLAN.md and /workspace/strategy_lab.py for:
- PLAN.md has architecture / data-flow / phases / risk sections
- PLAN.md references existing types from strategy_base.py
- strategy_lab.py defines Backtester, ParameterOptimizer, PerformanceMetrics classes
- Methods have type hints + docstrings
- All metrics (sharpe_ratio, max_drawdown, win_rate, profit_factor) named
- Chinese content present
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _classes_with_methods(tree: ast.AST) -> dict:
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for n in node.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "name": n.name,
                        "has_args_annot": any(a.annotation for a in n.args.args[1:]),
                        "has_return_annot": n.returns is not None,
                        "has_docstring": ast.get_docstring(n) is not None,
                    })
            out[node.name] = methods
    return out


def grade_workspace(ws: Path) -> dict:
    components = {}

    plan = _read(ws / "PLAN.md")
    plan_lower = plan.lower()

    # 1. Plan exists + substantive
    plan_len_ok = len(plan.strip()) > 800
    components["plan_substantive"] = 1.0 if plan_len_ok else (0.5 if len(plan.strip()) > 300 else 0.0)

    # 2. Plan sections
    section_hits = 0
    expected_sections = [
        (r"现状|architecture|架构", "architecture"),
        (r"实验|功能清单|lab", "feature_list"),
        (r"数据流|data\s*flow|流程", "dataflow"),
        (r"phase|阶段|实施", "phases"),
        (r"风险|risk|应对", "risk"),
        (r"backtest|回测|参数优化|optimizer", "lab_capability"),
    ]
    for pat, _ in expected_sections:
        if re.search(pat, plan, re.I):
            section_hits += 1
    components["plan_sections"] = min(section_hits / 5.0, 1.0)

    # 3. References to strategy_base.py existing types
    refs = ["StrategyBase", "strategy_base", "Signal", "MarketData", "OrderSide"]
    ref_hits = sum(1 for r in refs if r in plan)
    components["plan_references_code"] = min(ref_hits / 2.0, 1.0)

    # 4. strategy_lab.py skeleton
    lab = ws / "strategy_lab.py"
    lab_src = _read(lab)
    lab_tree = None
    if lab_src.strip():
        try:
            lab_tree = ast.parse(lab_src)
        except SyntaxError:
            pass

    if lab_tree:
        classes = _classes_with_methods(lab_tree)
    else:
        classes = {}

    required_classes = ["Backtester", "ParameterOptimizer", "PerformanceMetrics"]
    class_hits = sum(1 for c in required_classes if c in classes)
    components["lab_classes"] = class_hits / len(required_classes)

    # 5. Type hints + docstrings on methods
    if classes:
        all_methods = [m for c in classes.values() for m in c]
        with_annot = sum(1 for m in all_methods if m["has_args_annot"] or m["has_return_annot"])
        with_doc = sum(1 for m in all_methods if m["has_docstring"])
        total = max(len(all_methods), 1)
        components["lab_type_hints"] = with_annot / total
        components["lab_docstrings"] = with_doc / total
    else:
        components["lab_type_hints"] = 0.0
        components["lab_docstrings"] = 0.0

    # 6. Metric names in PerformanceMetrics or in lab src
    metrics = ["sharpe_ratio", "max_drawdown", "win_rate", "profit_factor"]
    metric_hits = sum(1 for m in metrics if m in lab_src)
    components["lab_metrics"] = metric_hits / len(metrics)

    # 7. Chinese content (the plan + docstrings should be CN)
    chinese_chars = len(re.findall(r"[一-鿿]", plan + lab_src))
    components["chinese_content"] = 1.0 if chinese_chars >= 300 else (chinese_chars / 300.0)

    weights = {
        "plan_substantive": 0.15,
        "plan_sections": 0.20,
        "plan_references_code": 0.10,
        "lab_classes": 0.20,
        "lab_type_hints": 0.10,
        "lab_docstrings": 0.10,
        "lab_metrics": 0.10,
        "chinese_content": 0.05,
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
