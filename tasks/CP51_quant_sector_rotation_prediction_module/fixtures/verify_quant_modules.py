"""Hidden verifier for CP51 quant sector rotation modules.

Runs in the sandbox after agent finishes. Inspects a same-directory set of
the four expected modules under /workspace via AST + content checks (NOT
importing them — avoid network/akshare deps).

Emits a single-line JSON to stdout with overall_score and per-criterion scores.

Hidden scoring rationale (do NOT leak in prompt):
- Module presence (file + non-empty + parseable) ............ 20%
- Class architecture (each module has a real class) ......... 15%
- akshare integration breadth (≥3 modules use ≥1 of expected api) 15%
- Robustness (try/except in ≥4 modules, not just stubs) ..... 10%
- Leader scoring dimensions (≥5 distinct factors) ........... 15%
- Fund flow segmentation (主力/北向/超大单/大单 etc) ........ 10%
- Rotation prediction signal (feature engineering present) .. 15%
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


MODULES = [
    "sector_monitor.py",
    "leader_tracker.py",
    "fund_flow_analyzer.py",
    "sector_rotation_predictor.py",
]

EXPECTED_AKSHARE_APIS = {
    "sector_monitor.py": {"sw_index_first_info", "sw_index_spot", "stock_sector_spot", "stock_zh_a_spot_em"},
    "leader_tracker.py": {"stock_zt_pool_em", "stock_zt_pool_zbgc_em", "stock_zt_pool_previous_em", "stock_zh_a_spot_em"},
    "fund_flow_analyzer.py": {"stock_individual_fund_flow", "stock_sector_fund_flow_rank", "stock_hsgt_hist_em", "stock_hsgt_individual_em"},
    "sector_rotation_predictor.py": {"sw_index_spot", "stock_sector_spot", "stock_sector_fund_flow_rank"},
}

LEADER_DIMENSION_HINTS = [
    r"\bvolume|\b成交量|换手率|turnover",
    r"\blimit[_ ]?up|涨停|封板",
    r"\b连板|consecutive",
    r"\bmomentum|动量|涨幅|return",
    r"\bmarket[_ ]?cap|流通市值|总市值|float",
    r"\bvolatility|波动",
    r"\bfund[_ ]?flow|资金流|主力净",
    r"\b人气|popularity|attention",
    r"\bsentiment",
]

FUND_FLOW_CATEGORIES = [
    (r"main|主力", "main"),
    (r"super[_ ]?large|超大单|超级大单", "super_large"),
    (r"large[_ ]?net|大单", "large"),
    (r"medium|中单", "medium"),
    (r"small|散户|小单", "small"),
    (r"northbound|北向|沪深港通|hsgt", "north"),
]

ROTATION_FEATURE_HINTS = [
    r"\bma[_ ]?\d+|moving[_ ]?average|均线",
    r"\brsi|相对强弱",
    r"\bz[_ ]?score|标准化|standardize|normaliz",
    r"\brolling|滚动",
    r"\bcorrelation|相关系数|corr",
    r"\bpct[_ ]?change|环比|涨跌幅",
    r"\bregression|回归|linear|logistic",
    r"\bcluster|kmeans|聚类",
    r"\brank|排名|排序",
]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _has_real_class(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            method_count = sum(1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            if method_count >= 1:
                return True
    return False


def _try_except_count(tree: ast.AST) -> int:
    return sum(1 for n in ast.walk(tree) if isinstance(n, ast.Try))


def _parse_safe(src: str) -> ast.AST | None:
    if not src.strip():
        return None
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def _ignored(path: Path) -> bool:
    return any(part in {"fixtures", "__pycache__", ".git"} for part in path.parts)


def _candidate_dirs(ws: Path) -> list[Path]:
    dirs: dict[Path, int] = {}
    for name in MODULES:
        for p in ws.rglob(name):
            if not p.is_file():
                continue
            try:
                rel = p.relative_to(ws)
            except ValueError:
                rel = p
            if _ignored(rel):
                continue
            dirs[p.parent] = dirs.get(p.parent, 0) + 1
    if not dirs:
        return [ws]
    return sorted(dirs, key=lambda d: (-dirs[d], len(d.relative_to(ws).parts) if d != ws else 0, str(d)))


def _collect_file_data(base_dir: Path) -> dict:
    file_data = {}
    for name in MODULES:
        p = base_dir / name
        src = _read(p) if p.exists() else ""
        tree = _parse_safe(src)
        file_data[name] = {
            "exists": p.exists(),
            "size": len(src),
            "parseable": tree is not None,
            "tree": tree,
            "src": src,
            "lower": src.lower(),
        }
    return file_data


def _score_file_data(file_data: dict) -> dict:
    # Criterion 1: module presence (file + ≥80 chars + parseable)
    presence_hits = sum(
        1 for d in file_data.values()
        if d["exists"] and d["size"] >= 80 and d["parseable"]
    )
    c_presence = presence_hits / len(MODULES)

    # Criterion 2: class architecture
    class_hits = sum(1 for d in file_data.values() if d["tree"] and _has_real_class(d["tree"]))
    c_class = class_hits / len(MODULES)

    # Criterion 3: akshare API breadth
    akshare_module_hits = 0
    for name, d in file_data.items():
        if not d["parseable"]:
            continue
        expected = EXPECTED_AKSHARE_APIS.get(name, set())
        if any(api in d["src"] for api in expected):
            akshare_module_hits += 1
    c_akshare = min(akshare_module_hits / 3.0, 1.0)

    # Criterion 4: robustness via try/except in ≥4 modules
    robust_hits = sum(1 for d in file_data.values() if d["tree"] and _try_except_count(d["tree"]) >= 1)
    c_robust = robust_hits / len(MODULES)

    # Criterion 5: leader scoring dimensions ≥5 distinct hints
    leader_src = file_data["leader_tracker.py"]["lower"]
    dim_hits = sum(1 for pat in LEADER_DIMENSION_HINTS if re.search(pat, leader_src))
    c_leader_dims = min(dim_hits / 5.0, 1.0)

    # Criterion 6: fund flow categorization ≥3 distinct categories incl. northbound
    fund_src = file_data["fund_flow_analyzer.py"]["lower"]
    cat_hits = set()
    for pat, label in FUND_FLOW_CATEGORIES:
        if re.search(pat, fund_src):
            cat_hits.add(label)
    has_main = "main" in cat_hits
    has_north = "north" in cat_hits
    distinct_cats = len(cat_hits)
    c_fund_cats = 0.0
    if has_main and has_north and distinct_cats >= 3:
        c_fund_cats = min(distinct_cats / 5.0, 1.0)
    elif distinct_cats >= 2:
        c_fund_cats = distinct_cats / 6.0

    # Criterion 7: rotation prediction features ≥3 distinct feature-eng signals
    pred_src = file_data["sector_rotation_predictor.py"]["lower"]
    feat_hits = sum(1 for pat in ROTATION_FEATURE_HINTS if re.search(pat, pred_src))
    c_features = min(feat_hits / 3.0, 1.0)

    weights = {
        "presence": 0.20,
        "class_arch": 0.15,
        "akshare": 0.15,
        "robust": 0.10,
        "leader_dims": 0.15,
        "fund_cats": 0.10,
        "features": 0.15,
    }
    components = {
        "presence": round(c_presence, 4),
        "class_arch": round(c_class, 4),
        "akshare": round(c_akshare, 4),
        "robust": round(c_robust, 4),
        "leader_dims": round(c_leader_dims, 4),
        "fund_cats": round(c_fund_cats, 4),
        "features": round(c_features, 4),
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": components,
        "weights": weights,
        "files_seen": {n: {"exists": d["exists"], "size": d["size"], "parseable": d["parseable"]}
                       for n, d in file_data.items()},
    }


def grade_workspace(ws: Path) -> dict:
    best = None
    for base_dir in _candidate_dirs(ws):
        result = _score_file_data(_collect_file_data(base_dir))
        try:
            result["module_dir"] = str(base_dir.relative_to(ws) if base_dir != ws else Path("."))
        except ValueError:
            result["module_dir"] = str(base_dir)
        if best is None or result["overall_score"] > best["overall_score"]:
            best = result
    return best or _score_file_data(_collect_file_data(ws))


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
