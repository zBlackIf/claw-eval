"""Hidden verifier for CP189 — Futures News Commodity Classifier Enhancement.

Scoring tiers designed for maximum discrimination:
  Hidden-Easy (15%): trivial checks every model that attempts the task passes
  Tier 1 (Basic, 15%): things most models get right
  Tier 2 (Structural, 18%): correct architecture, not just text presence
  Hidden-Hard (20%): subtle correctness checks only strong models pass
  Tier 3 (Deep, 32%): logic correctness, domain expertise, integration quality
"""
from __future__ import annotations

import json
import sys
import ast
import importlib.util
import re
from pathlib import Path
from typing import Any, Optional


def _load_module(path: Path, name: str):
    """Dynamically load a Python module from file path."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_ast(source: str) -> Optional[ast.Module]:
    """Parse source code into AST, return None on failure."""
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _find_function(tree: ast.Module, func_name: str) -> Optional[ast.FunctionDef]:
    """Find a top-level or class-level function in the AST."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node
    return None


def _find_function_in_class(tree: ast.Module, func_name: str) -> Optional[ast.FunctionDef]:
    """Find a function inside any class in the AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == func_name:
                    return item
    return None


def _ast_has_sql_create_table(source: str, table_name: str) -> dict:
    """Check SQL CREATE TABLE statement for a specific table, return column info."""
    pattern = rf'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table_name}\s*\((.*?)\)'
    matches = re.findall(pattern, source, re.DOTALL | re.IGNORECASE)
    if not matches:
        return {"exists": False, "columns": []}
    cols_text = matches[0]
    columns = []
    for line in cols_text.split(","):
        line = line.strip()
        if line and not line.upper().startswith(("PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT")):
            parts = line.split()
            if parts:
                columns.append(parts[0].strip('"\'`'))
    return {"exists": True, "columns": columns, "raw": cols_text}


def grade_workspace(ws: Path) -> dict:
    # Try multiple locations for the futures_news directory
    candidates = [
        ws / "fixtures" / "futures_news",
        ws / "futures_news",
    ]
    base = None
    for c in candidates:
        if c.exists() and (c / "config.py").exists():
            base = c
            break

    if base is None:
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "futures_news directory not found"
        }

    config_text = _read(base / "config.py")
    parser_text = _read(base / "parser.py")
    db_text = _read(base / "database.py")
    all_text = config_text + parser_text + db_text

    components = {}

    # =========================================================================
    # HIDDEN-EASY: Trivial checks that ALL models pass (15% total)
    # Any model that reads the prompt and modifies files will score here.
    # =========================================================================

    # HE-1. Files still exist and are non-empty (any attempt means these pass)
    files_exist_score = 0.0
    if config_text.strip():
        files_exist_score += 0.34
    if parser_text.strip():
        files_exist_score += 0.33
    if db_text.strip():
        files_exist_score += 0.33
    components["hidden_easy_files_exist"] = round(min(1.0, files_exist_score), 4)

    # HE-2. At least one new commodity mentioned ANYWHERE across all files
    has_any_new_commodity = ("纯碱" in all_text) or ("玻璃" in all_text)
    components["hidden_easy_commodity_mentioned"] = 1.0 if has_any_new_commodity else 0.0

    # HE-3. At least one new table (weekly or monthly) defined in database.py
    has_any_report_table = bool(re.search(
        r'CREATE\s+TABLE.*(?:weekly|monthly)', db_text, re.IGNORECASE | re.DOTALL
    ))
    components["hidden_easy_report_table"] = 1.0 if has_any_report_table else 0.0

    # =========================================================================
    # TIER 1: Basic checks (easy) — 15% total weight
    # =========================================================================

    # 1a. Varieties added (basic text presence)
    has_soda_ash = "纯碱" in config_text or "纯碱" in parser_text
    has_glass = "玻璃" in config_text or "玻璃" in parser_text
    components["varieties_added"] = (0.5 if has_soda_ash else 0.0) + (0.5 if has_glass else 0.0)

    # 1b. Basic keyword presence
    soda_keywords_basic = ["氨碱", "联碱", "天然碱", "远兴", "开工率"]
    glass_keywords_basic = ["浮法", "光伏玻璃", "日熔量", "冷修", "点火", "产线"]
    soda_basic_count = sum(1 for kw in soda_keywords_basic if kw in all_text)
    glass_basic_count = sum(1 for kw in glass_keywords_basic if kw in all_text)
    components["keywords_present"] = round(
        min(1.0, (soda_basic_count / 3.0) * 0.5 + (glass_basic_count / 3.0) * 0.5), 4
    )

    # 1c. New 7-category scheme present as dict keys
    new_categories = ["价格", "供给", "需求", "库存", "成本", "利润", "市场消息"]
    cat_as_key_count = 0
    for cat in new_categories:
        if re.search(rf'["\']' + re.escape(cat) + rf'["\']\s*:', all_text):
            cat_as_key_count += 1
    components["category_scheme"] = round(min(1.0, cat_as_key_count / 6.0), 4)

    # =========================================================================
    # TIER 2: Structural checks (medium) — 18%
    # =========================================================================

    # 2a. Parser variety-aware: AST check for correct function signature + routing
    parser_ast = _parse_ast(parser_text)
    parser_variety_score = 0.0
    if parser_ast:
        extract_cat_fn = _find_function(parser_ast, "extract_category") or \
                         _find_function_in_class(parser_ast, "extract_category")
        if extract_cat_fn:
            args = extract_cat_fn.args
            all_arg_names = [a.arg for a in args.args + args.kwonlyargs]
            if "variety" in all_arg_names:
                parser_variety_score += 0.25
            fn_source = ast.get_source_segment(parser_text, extract_cat_fn)
            if fn_source:
                if ("if" in fn_source and "variety" in fn_source) or \
                   (".get(" in fn_source and "variety" in fn_source):
                    parser_variety_score += 0.25
            # Check parse_message passes variety to extract_category
            parse_msg_fn = _find_function(parser_ast, "parse_message") or \
                           _find_function_in_class(parser_ast, "parse_message")
            if parse_msg_fn:
                fn_src = ast.get_source_segment(parser_text, parse_msg_fn) or ""
                if re.search(r'extract_category\s*\([^)]*variety', fn_src):
                    parser_variety_score += 0.5
    else:
        # AST parse failed — heavy penalty (only 0.2 max)
        if re.search(r'def\s+extract_category\s*\([^)]*variety', parser_text):
            parser_variety_score += 0.1
        if "纯碱" in parser_text and "玻璃" in parser_text:
            parser_variety_score += 0.1

    components["parser_variety_aware"] = round(min(1.0, parser_variety_score), 4)

    # 2b. Weekly reports table schema correctness
    weekly_info = _ast_has_sql_create_table(db_text, "weekly_reports")
    weekly_score = 0.0
    if weekly_info["exists"]:
        weekly_score += 0.2
        cols = [c.lower() for c in weekly_info["columns"]]
        if any(c in cols for c in ["week_number", "week_num", "week_of_year", "week"]):
            weekly_score += 0.3
        if "variety" in cols:
            weekly_score += 0.3
        if any(c in cols for c in ["year", "week_year", "year_week"]):
            weekly_score += 0.1
        if any(c in cols for c in ["content", "summary", "report_content"]):
            weekly_score += 0.1
    components["weekly_table"] = round(min(1.0, weekly_score), 4)

    # 2c. Monthly reports table schema correctness
    monthly_info = _ast_has_sql_create_table(db_text, "monthly_reports")
    monthly_score = 0.0
    if monthly_info["exists"]:
        monthly_score += 0.2
        cols = [c.lower() for c in monthly_info["columns"]]
        if "month" in cols:
            monthly_score += 0.3
        if "variety" in cols:
            monthly_score += 0.3
        if any(c in cols for c in ["year", "report_year"]):
            monthly_score += 0.1
        if any(c in cols for c in ["content", "summary", "report_content"]):
            monthly_score += 0.1
    components["monthly_table"] = round(min(1.0, monthly_score), 4)

    # =========================================================================
    # HIDDEN-HARD: Subtle correctness checks only strong models pass (20%)
    # These test proper engineering practices that weak models skip.
    # =========================================================================

    # HH-1. Parameterized SQL queries in ALL new DB methods (no f-string/format injection)
    # Strong models use ? placeholders; weak models use string interpolation
    hh_sql_safety_score = 0.0
    db_ast = _parse_ast(db_text)
    if db_ast:
        new_methods_count = 0
        safe_methods_count = 0
        for node in ast.walk(db_ast):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name_lower = node.name.lower()
                # Only check NEW methods (not original ones)
                if name_lower in ("get_messages_by_date", "insert_message", "get_varieties",
                                  "init_tables", "_get_connection", "__init__"):
                    continue
                fn_src = ast.get_source_segment(db_text, node) or ""
                if "execute" in fn_src or "SELECT" in fn_src or "INSERT" in fn_src:
                    new_methods_count += 1
                    # Check for SQL injection vulnerability patterns
                    has_fstring_sql = bool(re.search(r'f["\'].*(?:SELECT|INSERT|WHERE|FROM)', fn_src))
                    has_format_sql = bool(re.search(r'\.format\s*\(', fn_src)) and "SQL" not in fn_src.upper().split("FORMAT")[0][-20:]
                    has_concat_sql = bool(re.search(r'["\'].*(?:SELECT|WHERE).*["\']\s*\+\s*\w+', fn_src))
                    # Safe if uses parameterized (?) and no unsafe patterns
                    uses_params = bool(re.search(r'\?', fn_src))
                    if uses_params and not has_fstring_sql and not has_concat_sql:
                        safe_methods_count += 1
                    elif not has_fstring_sql and not has_format_sql and not has_concat_sql:
                        # No SQL at all in this method, or using params via %s
                        safe_methods_count += 1

        if new_methods_count > 0:
            hh_sql_safety_score = min(1.0, safe_methods_count / new_methods_count)
        else:
            # No new methods found — partial credit if db_text has no f-string SQL
            if not re.search(r'f["\'].*(?:SELECT|INSERT|WHERE)', db_text):
                hh_sql_safety_score = 0.5
    components["hidden_hard_sql_safety"] = round(hh_sql_safety_score, 4)

    # HH-2. Default/fallback category handling in extract_category
    # Strong models return a meaningful fallback ("其他" or "市场消息") when no keyword matches.
    # Weak models may crash, return None, or forget the fallback entirely.
    hh_fallback_score = 0.0
    if parser_ast:
        extract_cat_fn = _find_function(parser_ast, "extract_category") or \
                         _find_function_in_class(parser_ast, "extract_category")
        if extract_cat_fn:
            fn_src = ast.get_source_segment(parser_text, extract_cat_fn) or ""
            # Must have an explicit return for the no-match case
            # Pattern: return "其他" or return "市场消息" at end of function
            has_default_return = bool(re.search(
                r'return\s+["\'](?:其他|市场消息|未分类|其它|unknown|other)["\']',
                fn_src, re.IGNORECASE
            ))
            if has_default_return:
                hh_fallback_score += 0.5
            # Must preserve fallback for BOTH new varieties AND original logic
            # Check: function handles the case where variety is None/unknown
            has_none_handling = bool(re.search(
                r'(?:if\s+(?:not\s+)?variety|variety\s*(?:is\s+None|==\s*None|\s*is\s+None)|else\s*:)',
                fn_src
            ))
            if has_none_handling:
                hh_fallback_score += 0.5
    components["hidden_hard_fallback_category"] = round(min(1.0, hh_fallback_score), 4)

    # HH-3. VARIETIES list is actually updated (not just keywords added)
    # The task explicitly requires "品种列表加入纯碱和玻璃".
    # Strong models update the VARIETIES list constant; weak models only add keyword dicts.
    hh_varieties_list_score = 0.0
    # Check config.py has VARIETIES containing both new commodities
    varieties_match = re.search(r'VARIETIES\s*[=:]\s*\[(.*?)\]', config_text, re.DOTALL)
    if varieties_match:
        varieties_content = varieties_match.group(1)
        if "纯碱" in varieties_content:
            hh_varieties_list_score += 0.5
        if "玻璃" in varieties_content:
            hh_varieties_list_score += 0.5
    else:
        # Maybe VARIETIES defined differently (e.g. appended)
        if re.search(r'VARIETIES.*(?:append|extend|\+=).*纯碱', config_text):
            hh_varieties_list_score += 0.5
        if re.search(r'VARIETIES.*(?:append|extend|\+=).*玻璃', config_text):
            hh_varieties_list_score += 0.5
    components["hidden_hard_varieties_list"] = round(min(1.0, hh_varieties_list_score), 4)

    # HH-4. Conditional SQL building in date range query (dynamic WHERE clause)
    # Strong models build SQL dynamically: base query + optional variety filter.
    # Weak models either always filter by variety (breaking None case) or never filter.
    hh_conditional_sql_score = 0.0
    if db_ast:
        # Find the date range function
        date_range_fn = None
        for node in ast.walk(db_ast):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name_lower = node.name.lower()
                if name_lower == "get_messages_by_date":
                    continue
                arg_names = [a.arg for a in node.args.args + node.args.kwonlyargs]
                if any("start" in a or "begin" in a for a in arg_names) and \
                   any("end" in a for a in arg_names):
                    date_range_fn = node
                    break
        if date_range_fn:
            fn_src = ast.get_source_segment(db_text, date_range_fn) or ""
            arg_names = [a.arg for a in date_range_fn.args.args + date_range_fn.args.kwonlyargs]

            # Has variety as optional param (default None)
            has_variety_optional = False
            for i, arg in enumerate(date_range_fn.args.args + date_range_fn.args.kwonlyargs):
                if arg.arg == "variety":
                    # Check if it has a default value of None
                    defaults = date_range_fn.args.defaults + date_range_fn.args.kw_defaults
                    # kwonlyargs use kw_defaults; positional use defaults (aligned from right)
                    has_variety_optional = True  # presence alone counts
                    break

            if has_variety_optional:
                hh_conditional_sql_score += 0.25

            # Dynamic query building: if variety then add AND clause
            has_dynamic_build = bool(re.search(
                r'if\s+variety.*(?:AND|params|append|WHERE|\+)',
                fn_src, re.DOTALL
            )) or bool(re.search(
                r'variety\s*(?:is\s+not\s+None|!=\s*None)',
                fn_src
            ))
            if has_dynamic_build:
                hh_conditional_sql_score += 0.5

            # Params list is also dynamically extended (not static tuple)
            has_dynamic_params = bool(re.search(
                r'(?:params|args)\s*(?:\.\s*append|\+\s*=|\.\s*extend)',
                fn_src
            )) or bool(re.search(
                r'(?:params|args)\s*=.*\+\s*\[',
                fn_src
            )) or bool(re.search(
                r'tuple\s*\(|list\s*\(',
                fn_src
            ))
            if has_dynamic_params:
                hh_conditional_sql_score += 0.25

    components["hidden_hard_conditional_sql"] = round(min(1.0, hh_conditional_sql_score), 4)

    # =========================================================================
    # TIER 3: Deep logic checks (hard) — 32%
    # =========================================================================

    # 3a. Keyword mapping ISOLATION: separate data structures per commodity
    # Strong models create distinct named structures; weak models dump everything together
    isolation_score = 0.0

    # Must have TWO SEPARATE dict/mapping structures in config (not just one giant dict)
    soda_mapping_patterns = [
        r'SODA_ASH_\w*(?:CATEGORY|KEYWORD|MAPPING)',
        r'(?:纯碱|soda_ash)_\w*(?:category|keyword|mapping)',
    ]
    glass_mapping_patterns = [
        r'GLASS_\w*(?:CATEGORY|KEYWORD|MAPPING)',
        r'(?:玻璃|glass)_\w*(?:category|keyword|mapping)',
    ]
    # Also accept nested dict pattern: {"纯碱": {categories...}, "玻璃": {categories...}}
    nested_pattern = r'["\']纯碱["\']\s*:\s*\{[^}]*["\']供给["\']\s*:'
    nested_pattern_glass = r'["\']玻璃["\']\s*:\s*\{[^}]*["\']供给["\']\s*:'

    soda_has_mapping = any(re.search(p, all_text, re.IGNORECASE) for p in soda_mapping_patterns) or \
                       re.search(nested_pattern, all_text, re.DOTALL)
    glass_has_mapping = any(re.search(p, all_text, re.IGNORECASE) for p in glass_mapping_patterns) or \
                        re.search(nested_pattern_glass, all_text, re.DOTALL)
    if soda_has_mapping:
        isolation_score += 0.5
    if glass_has_mapping:
        isolation_score += 0.5
    components["keyword_isolation"] = round(isolation_score, 4)

    # 3b. Date range query: must be a NEW function (not the existing get_messages_by_date)
    # that takes BOTH start and end date parameters (range query)
    date_range_score = 0.0
    if db_ast:
        date_range_fn = None
        for node in ast.walk(db_ast):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name_lower = node.name.lower()
                # Must be specifically a "range" function, not the pre-existing get_messages_by_date
                if name_lower == "get_messages_by_date":
                    continue  # Skip the original function
                if "range" in name_lower or ("start" in name_lower and "end" in name_lower) or \
                   ("date" in name_lower and name_lower != "get_messages_by_date"):
                    # Verify it actually has both start and end parameters
                    arg_names = [a.arg for a in node.args.args + node.args.kwonlyargs]
                    if any("start" in a or "begin" in a for a in arg_names) and \
                       any("end" in a for a in arg_names):
                        date_range_fn = node
                        break
        if date_range_fn:
            fn_src = ast.get_source_segment(db_text, date_range_fn) or ""
            arg_names = [a.arg for a in date_range_fn.args.args + date_range_fn.args.kwonlyargs]
            # Has start+end date params (already verified above)
            date_range_score += 0.2
            # SQL uses BETWEEN or >= AND <=
            if "BETWEEN" in fn_src or (">=" in fn_src and "<=" in fn_src):
                date_range_score += 0.2
            # Has variety parameter
            has_variety_param = "variety" in arg_names
            if has_variety_param:
                date_range_score += 0.2
            # CRITICAL: Conditionally adds variety filter (not always filtering)
            if has_variety_param and re.search(
                r'if\s+variety|variety\s+is\s+not\s+None|variety\s*!=\s*None',
                fn_src
            ):
                date_range_score += 0.2
            # Uses parameterized queries (? or %s), not string formatting
            if re.search(r'\?\s*[,\)]|\%s', fn_src) and "format" not in fn_src.lower() and "f'" not in fn_src:
                date_range_score += 0.2
        else:
            # Check if there's at least a BETWEEN clause with range semantics somewhere new
            if "BETWEEN" in db_text and re.search(r'def\s+\w*range\w*', db_text):
                date_range_score += 0.15
    else:
        if "BETWEEN" in db_text and "range" in db_text.lower():
            date_range_score += 0.1

    components["date_range_query"] = round(min(1.0, date_range_score), 4)

    # 3c. Category keyword RICHNESS per commodity
    richness_score = 0.0
    soda_extra_keywords = [
        "纯碱厂", "碳酸钠", "重质纯碱", "轻质纯碱", "重质", "轻质",
        "浮法玻璃用", "光伏玻璃用",
        "氯化铵", "原盐", "蒸汽",
        "纯碱库存", "厂库库存",
        "吨碱利润", "碱厂利润",
        "纯碱现货", "纯碱期货",
    ]
    glass_extra_keywords = [
        "原片", "深加工率", "产能利用率", "窑龄",
        "石英砂", "纯碱用量", "燃料成本",
        "竣工面积", "施工面积", "开工面积",
        "玻璃库存", "贸易商库存",
        "玻璃现货", "玻璃期货",
        "产销率", "出库量",
    ]

    soda_extra_count = sum(1 for kw in soda_extra_keywords if kw in config_text)
    glass_extra_count = sum(1 for kw in glass_extra_keywords if kw in config_text)

    richness_score = min(1.0,
        (min(soda_extra_count, 5) / 5.0) * 0.5 +
        (min(glass_extra_count, 5) / 5.0) * 0.5
    )
    components["keyword_richness"] = round(richness_score, 4)

    # 3d. Cross-category coverage: commodity-specific keywords must span multiple categories
    coverage_score = 0.0

    soda_supply_specific = ["氨碱法", "联碱法", "天然碱", "远兴", "开工率", "纯碱产能", "碱厂"]
    soda_demand_specific = ["浮法玻璃", "光伏玻璃", "日化", "印染", "下游消费"]
    soda_cost_specific = ["原盐", "蒸汽", "煤炭", "天然气", "氯化铵"]
    soda_inventory_specific = ["纯碱库存", "厂库", "社库", "港口库存"]

    glass_supply_specific = ["浮法", "日熔量", "冷修", "点火", "产线", "窑龄", "光伏玻璃"]
    glass_demand_specific = ["房地产", "竣工", "施工", "汽车玻璃", "家电"]
    glass_cost_specific = ["纯碱成本", "天然气", "重油", "石英砂", "燃料"]
    glass_inventory_specific = ["玻璃库存", "厂库", "贸易商", "出库", "产销率"]

    soda_categories_covered = 0
    if any(kw in config_text for kw in soda_supply_specific):
        soda_categories_covered += 1
    if any(kw in config_text for kw in soda_demand_specific):
        soda_categories_covered += 1
    if any(kw in config_text for kw in soda_cost_specific):
        soda_categories_covered += 1
    if any(kw in config_text for kw in soda_inventory_specific):
        soda_categories_covered += 1

    glass_categories_covered = 0
    if any(kw in config_text for kw in glass_supply_specific):
        glass_categories_covered += 1
    if any(kw in config_text for kw in glass_demand_specific):
        glass_categories_covered += 1
    if any(kw in config_text for kw in glass_cost_specific):
        glass_categories_covered += 1
    if any(kw in config_text for kw in glass_inventory_specific):
        glass_categories_covered += 1

    coverage_score = min(1.0,
        (min(soda_categories_covered, 3) / 3.0) * 0.5 +
        (min(glass_categories_covered, 3) / 3.0) * 0.5
    )
    components["cross_category_coverage"] = round(coverage_score, 4)

    # 3e. Integration quality: extract_category must actually USE per-commodity mappings
    integration_score = 0.0

    if parser_ast:
        extract_cat_fn = _find_function(parser_ast, "extract_category") or \
                         _find_function_in_class(parser_ast, "extract_category")

        if extract_cat_fn:
            fn_src = ast.get_source_segment(parser_text, extract_cat_fn) or ""
            args = extract_cat_fn.args
            all_arg_names = [a.arg for a in args.args + args.kwonlyargs]

            # PREREQUISITE: must have variety parameter, otherwise 0
            if "variety" in all_arg_names:
                # Check 1: References to BOTH commodity-specific mappings
                refs_soda = bool(re.search(r'纯碱|soda_ash|SODA_ASH', fn_src))
                refs_glass = bool(re.search(r'玻璃|glass|GLASS', fn_src))
                if refs_soda and refs_glass:
                    integration_score += 0.35
                elif refs_soda or refs_glass:
                    integration_score += 0.15

                # Check 2: Has a fallback/default path for other varieties
                has_else = "else" in fn_src
                has_default = "default" in fn_src.lower() or "通用" in fn_src or "common" in fn_src.lower()
                if has_else or has_default:
                    integration_score += 0.3

                # Check 3: Iterates over keywords per category (actual classification logic)
                has_iteration = bool(re.search(r'for\s+\w+.*in\s+', fn_src))
                has_keyword_check = ("in " in fn_src or "keyword" in fn_src.lower())
                if has_iteration and has_keyword_check:
                    integration_score += 0.35

    components["integration_quality"] = round(min(1.0, integration_score), 4)

    # 3f. Code quality: all files parse + proper imports + database init includes new varieties
    code_quality_score = 0.0
    files_to_check = ["config.py", "parser.py", "database.py"]
    syntax_ok_count = 0
    for fname in files_to_check:
        src = _read(base / fname)
        if src and _parse_ast(src) is not None:
            syntax_ok_count += 1
    if syntax_ok_count == len(files_to_check):
        code_quality_score += 0.4
    elif syntax_ok_count >= 2:
        code_quality_score += 0.15

    # Parser imports from config (proper module structure)
    if re.search(r'(?:from|import)\s+config', parser_text):
        code_quality_score += 0.2

    # Database default_varieties includes new commodities
    if "纯碱" in db_text and "玻璃" in db_text:
        code_quality_score += 0.2

    # report_generator.py still parseable (didn't break it)
    rg_text = _read(base / "report_generator.py")
    if rg_text and _parse_ast(rg_text) is not None:
        code_quality_score += 0.2

    components["code_quality"] = round(min(1.0, code_quality_score), 4)

    # =========================================================================
    # Weight tiers — Hidden checks >= 35% for discrimination
    # =========================================================================
    weights = {
        # Hidden-Easy (15%) — every model that attempts the task gets these
        "hidden_easy_files_exist": 0.05,
        "hidden_easy_commodity_mentioned": 0.05,
        "hidden_easy_report_table": 0.05,
        # Tier 1: Basic (15%) — most models get these
        "varieties_added": 0.05,
        "keywords_present": 0.05,
        "category_scheme": 0.05,
        # Tier 2: Structural (18%) — medium difficulty
        "parser_variety_aware": 0.08,
        "weekly_table": 0.05,
        "monthly_table": 0.05,
        # Hidden-Hard (20%) — only strong models pass these
        "hidden_hard_sql_safety": 0.05,
        "hidden_hard_fallback_category": 0.05,
        "hidden_hard_varieties_list": 0.05,
        "hidden_hard_conditional_sql": 0.05,
        # Tier 3: Deep (32%) — strong discrimination
        "keyword_isolation": 0.07,
        "date_range_query": 0.07,
        "keyword_richness": 0.05,
        "cross_category_coverage": 0.05,
        "integration_quality": 0.05,
        "code_quality": 0.03,
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
