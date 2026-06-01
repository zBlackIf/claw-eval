"""Hidden verifier for CP109 — NOTAM Text Wrap Tokenizer.

Checks 5 dimensions:
1. English word integrity: English words are not split mid-word
2. Connector merging: connectors (-, ', /) between letters form single tokens
3. CJK width handling: CJK characters counted as width 2
4. Semantic newline preservation: existing \n tokens force line breaks
5. Line width compliance: no output line exceeds the configured width
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _try_import_formatter():
    """Try to import the formatter module from various locations.

    Uses importlib to load from file directly, avoiding namespace package
    conflicts when the directory has the same name as the module.
    """
    import importlib.util

    # Determine the directory containing this verifier script
    _this_dir = Path(__file__).resolve().parent

    candidates = [
        # Standard sandbox layout: verify_solution.py and notam_formatter/ are siblings
        _this_dir / "notam_formatter" / "notam_formatter.py",
        # Absolute workspace paths
        Path("/workspace/fixtures/notam_formatter/notam_formatter.py"),
        Path("/workspace/notam_formatter/notam_formatter.py"),
        Path("/workspace/notam_formatter.py"),
        Path("/workspace/fixtures/notam_formatter.py"),
    ]
    # Also check relative paths from cwd (for various agent behaviors)
    candidates.extend([
        Path("fixtures/notam_formatter/notam_formatter.py"),
        Path("notam_formatter/notam_formatter.py"),
        Path("notam_formatter.py"),
    ])

    module_file = None
    for candidate in candidates:
        if candidate.exists():
            module_file = candidate
            break

    if module_file is None:
        return None

    try:
        spec = importlib.util.spec_from_file_location("notam_formatter", str(module_file))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules["notam_formatter"] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (
        (0x4E00 <= cp <= 0x9FFF) or
        (0x3400 <= cp <= 0x4DBF) or
        (0x20000 <= cp <= 0x2A6DF) or
        (0x2A700 <= cp <= 0x2B73F) or
        (0xF900 <= cp <= 0xFAFF)
    )


def measure_width(text: str) -> int:
    """Measure display width: CJK=2, others=1."""
    w = 0
    for ch in text:
        w += 2 if is_cjk(ch) else 1
    return w


def grade() -> dict:
    components = {
        "english_word_integrity": 0.0,
        "connector_merging": 0.0,
        "cjk_width_handling": 0.0,
        "semantic_newline_preservation": 0.0,
        "line_width_compliance": 0.0,
    }

    fmt = _try_import_formatter()
    if fmt is None:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "Could not import notam_formatter module",
        }

    # Check that required functions exist
    has_tokenize = hasattr(fmt, 'tokenize') and callable(getattr(fmt, 'tokenize'))
    has_wrap = hasattr(fmt, 'wrap_lines') and callable(getattr(fmt, 'wrap_lines'))
    has_token_width = hasattr(fmt, 'token_width') and callable(getattr(fmt, 'token_width'))

    if not has_tokenize or not has_wrap:
        return {
            "overall_score": 0.1,
            "components": components,
            "error": f"Missing functions: tokenize={has_tokenize}, wrap_lines={has_wrap}",
        }

    # --- Dimension 1: English word integrity ---
    # English words should NOT be split character-by-character
    test_cases_word = [
        ("available", ["available"]),
        ("navigation", ["navigation"]),
        ("MAINTENANCE", ["MAINTENANCE"]),
        ("frequency", ["frequency"]),
    ]
    word_score = 0.0
    for word, expected in test_cases_word:
        try:
            tokens = fmt.tokenize(word)
            # The word should appear as a single token
            if word in tokens:
                word_score += 1.0
            elif len(tokens) == 1 and tokens[0] == word:
                word_score += 1.0
            else:
                # Partial credit if less fragmented than char-by-char
                if len(tokens) < len(word):
                    word_score += 0.3
        except Exception:
            pass
    components["english_word_integrity"] = word_score / len(test_cases_word)

    # --- Dimension 2: Connector merging ---
    # Connectors between letters should form single tokens
    test_cases_conn = [
        ("VOR/DME", "VOR/DME"),
        ("U/S", "U/S"),
        ("co-ordinate", "co-ordinate"),
        ("don't", "don't"),
        ("ILS/DME", "ILS/DME"),
        ("09L/27R", None),  # digits involved - may or may not merge, partial credit
    ]
    conn_score = 0.0
    for text_in, expected_token in test_cases_conn:
        try:
            tokens = fmt.tokenize(text_in)
            if expected_token is None:
                # Partial credit case (digit+connector): fewer tokens = better
                if len(tokens) <= 2:
                    conn_score += 1.0
                elif len(tokens) <= 3:
                    conn_score += 0.5
            else:
                if expected_token in tokens:
                    conn_score += 1.0
                elif len(tokens) == 1:
                    conn_score += 1.0
                elif len(tokens) <= 3:
                    conn_score += 0.3
        except Exception:
            pass
    components["connector_merging"] = conn_score / len(test_cases_conn)

    # --- Dimension 3: CJK width handling ---
    # CJK characters should be counted as width 2
    test_cases_cjk = [
        ("跑道", 4),           # 2 CJK chars = width 4
        ("RWY跑道", 7),        # 3 ASCII + 2 CJK = 3 + 4 = 7
        ("频率108.9MHZ", 12),  # 频(2)+率(2)+1(1)+0(1)+8(1)+.(1)+9(1)+M(1)+H(1)+Z(1) = 12
    ]
    cjk_score = 0.0
    if has_token_width:
        for text_in, expected_width in test_cases_cjk:
            try:
                # tokenize and sum widths
                tokens = fmt.tokenize(text_in)
                total_w = sum(fmt.token_width(t) for t in tokens)
                if total_w == expected_width:
                    cjk_score += 1.0
                elif abs(total_w - expected_width) <= 1:
                    cjk_score += 0.5
            except Exception:
                pass
        components["cjk_width_handling"] = cjk_score / len(test_cases_cjk)
    else:
        # If token_width doesn't exist, check via wrap output
        # CJK lines should break earlier than pure ASCII lines
        try:
            cjk_text = "滑行道关闭通知各航空器注意安全运行规定"  # 19 CJK chars = 38 width
            result = fmt.wrap_lines(cjk_text, 20)
            # At width 20, should break after ~10 CJK chars
            lines = result.split('\n')
            if len(lines) >= 2:
                cjk_score = 0.7
                # Check no line exceeds width
                for line in lines:
                    if measure_width(line) <= 22:  # slight tolerance
                        cjk_score += 0.1
        except Exception:
            pass
        components["cjk_width_handling"] = min(1.0, cjk_score)

    # --- Dimension 4: Semantic newline preservation ---
    # Existing \n in input should be preserved as forced line breaks
    test_cases_newline = [
        (
            "TWY A CLSD\nTWY B CLSD\nAPRON NORTH CLSD",
            3,  # should produce 3 lines
        ),
        (
            "RWY 09L/27R CLSD.\nILS U/S.\nVOR SVC.",
            3,
        ),
        (
            "单行不换行测试内容",
            1,
        ),
    ]
    nl_score = 0.0
    for text_in, expected_lines in test_cases_newline:
        try:
            result = fmt.wrap_lines(text_in, 80)  # wide enough to not auto-wrap
            actual_lines = len(result.split('\n'))
            if actual_lines == expected_lines:
                nl_score += 1.0
            elif actual_lines >= expected_lines:
                nl_score += 0.5  # extra wrapping but preserved semantics
        except Exception:
            pass
    components["semantic_newline_preservation"] = nl_score / len(test_cases_newline)

    # --- Dimension 5: Line width compliance ---
    # No output line should exceed the configured width (with small tolerance)
    test_cases_width = [
        (
            "RWY 09L/27R CLSD FOR MAINT DLY 0800-1600. ILS RWY 09L frequency adjusted.",
            40,
        ),
        (
            "TWY A BTN RWY AND APRON CLSD DLY 0600-1200 UNTIL FURTHER NOTICE.",
            30,
        ),
        (
            "VOR and DME are available for navigation during the maintenance period and all aircraft should note.",
            35,
        ),
    ]
    width_score = 0.0
    for text_in, max_w in test_cases_width:
        try:
            result = fmt.wrap_lines(text_in, max_w)
            lines = result.split('\n')
            if not lines or (len(lines) == 1 and lines[0] == ''):
                continue
            violations = 0
            for line in lines:
                lw = measure_width(line)
                if lw > max_w + 2:  # tolerance of 2 for edge cases
                    violations += 1
            if violations == 0:
                width_score += 1.0
            elif violations == 1:
                width_score += 0.5
        except Exception:
            pass
    components["line_width_compliance"] = width_score / len(test_cases_width)

    # Compute overall score
    weights = {
        "english_word_integrity": 0.30,
        "connector_merging": 0.25,
        "cjk_width_handling": 0.15,
        "semantic_newline_preservation": 0.15,
        "line_width_compliance": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    try:
        result = grade()
    except Exception as e:
        result = {
            "overall_score": 0.0,
            "components": {
                "english_word_integrity": 0.0,
                "connector_merging": 0.0,
                "cjk_width_handling": 0.0,
                "semantic_newline_preservation": 0.0,
                "line_width_compliance": 0.0,
            },
            "error": f"Grading crashed: {type(e).__name__}: {e}",
        }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
