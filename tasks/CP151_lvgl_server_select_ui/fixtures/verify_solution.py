"""Hidden verifier for CP151 — LVGL Server Selection UI.

Tiered scoring with discrimination:
- EASY checks (30%): file exists, includes, basic structure — all agents pass these
- VISIBLE checks (30%): key handling, URLs, config write — most agents pass
- HIDDEN/HARD checks (40%): deep semantic correctness that only strong agents get right
  These test nuanced embedded systems patterns that weak agents overlook.

Hidden checks >= 30% of total weight to ensure discrimination.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(root: Path, pattern: str) -> Path | None:
    """Recursively find a file matching pattern."""
    for p in root.rglob(pattern):
        return p
    return None


def _extract_function_body(src: str, func_name_pattern: str) -> str:
    """Extract the body of a function matching the pattern (brace counting)."""
    match = re.search(func_name_pattern + r'\s*\([^)]*\)\s*\{', src)
    if not match:
        return ""
    start = match.end() - 1  # the opening brace
    depth = 0
    i = start
    while i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[start:i+1]
        i += 1
    return src[start:]


def _count_lines_in_function(src: str, func_name_pattern: str) -> int:
    """Count non-empty lines in a function body."""
    body = _extract_function_body(src, func_name_pattern)
    if not body:
        return 0
    return sum(1 for line in body.splitlines() if line.strip() and not line.strip().startswith("//"))


def grade_workspace(ws: Path) -> dict:
    """Grade the server selection UI implementation with tiered discrimination."""
    # Look in multiple possible locations
    main_dir = None
    for candidate in [
        ws / "fixtures" / "ai_lamp" / "main",
        ws / "ai_lamp" / "main",
        ws / "main",
    ]:
        if candidate.exists():
            main_dir = candidate
            break

    if main_dir is None:
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "Cannot find main/ directory",
        }

    # =====================================================================
    # EASY CHECKS (30% total) — All reasonable attempts pass these
    # These verify that the agent created the right files with basic content.
    # =====================================================================
    easy = {
        "header_exists": 0.0,       # 0.08
        "impl_exists": 0.0,         # 0.10
        "basic_includes": 0.0,      # 0.07
        "has_lv_calls": 0.0,        # 0.05
    }

    # Find header file
    header = None
    for pat in ["*server_select*.h", "*srv_select*.h", "*server_sel*.h"]:
        header = _find_file(main_dir, pat)
        if header:
            break
    if header:
        hc = _read(header)
        has_guard = "#ifndef" in hc or "#pragma once" in hc
        has_func_decl = bool(re.search(r"(void|esp_err_t|int)\s+\w*(server|srv).*\w*\s*\(", hc, re.IGNORECASE))
        easy["header_exists"] = min(1.0, (0.5 if has_guard else 0.0) + (0.5 if has_func_decl else 0.0))

    # Find implementation file
    impl = None
    for pat in ["*server_select*.c", "*srv_select*.c", "*server_sel*.c"]:
        impl = _find_file(main_dir, pat)
        if impl:
            break

    ic = ""
    if impl:
        ic = _read(impl)
        easy["impl_exists"] = 1.0
        # Check includes
        has_config = "app_config" in ic
        has_key = "drv_key" in ic
        has_lvgl = "lvgl.h" in ic or "lv_" in ic
        easy["basic_includes"] = min(1.0, sum([has_config, has_key, has_lvgl]) / 3.0)
        # Any LVGL API calls present
        lv_call_count = len(re.findall(r"lv_\w+\s*\(", ic))
        easy["has_lv_calls"] = min(1.0, lv_call_count / 5.0)

    # =====================================================================
    # VISIBLE CHECKS (30% total) — Most agents pass, verifies core logic
    # =====================================================================
    visible = {
        "key_nav_logic": 0.0,       # 0.10 - proper up/down/confirm handling
        "server_urls": 0.0,         # 0.08 - both URLs present
        "config_write_api": 0.0,    # 0.07 - proper config setter
        "app_main_integration": 0.0,  # 0.05 - included and called in app_main
    }

    if ic:
        # Key navigation
        has_key_up = bool(re.search(r"(case\s+DRV_KEY_UP|==\s*DRV_KEY_UP)", ic))
        has_key_down = bool(re.search(r"(case\s+DRV_KEY_DOWN|==\s*DRV_KEY_DOWN)", ic))
        has_key_middle = bool(re.search(r"(case\s+DRV_KEY_MIDDLE|==\s*DRV_KEY_MIDDLE|case\s+DRV_KEY_OK|==\s*DRV_KEY_OK)", ic))
        has_switch_key = bool(re.search(r"(switch\s*\(\s*\w*key\w*\s*\)|if\s*\(\s*\w*key\w*\s*==)", ic, re.IGNORECASE))
        visible["key_nav_logic"] = min(1.0, (
            (0.25 if has_key_up else 0.0) +
            (0.25 if has_key_down else 0.0) +
            (0.25 if has_key_middle else 0.0) +
            (0.25 if has_switch_key else 0.0)
        ))

        # Both server URLs
        has_url1 = "20.tcp.vip.cpolar.cn:10244" in ic
        has_url2 = "192.168.50.233:61032" in ic
        visible["server_urls"] = (0.5 if has_url1 else 0.0) + (0.5 if has_url2 else 0.0)

        # Config write mechanism
        has_url_write = bool(re.search(
            r"(app_config_set\w*|strncpy|strcpy)\s*\(",
            ic, re.IGNORECASE
        )) and ("url" in ic.lower() or "cfg" in ic.lower() or "server" in ic.lower())
        visible["config_write_api"] = 1.0 if has_url_write else 0.0

    # Check app_config.h setter
    config_h = main_dir / "app_config.h"
    if config_h.exists():
        ch = _read(config_h)
        if re.search(r"(app_config_set_ws_url|app_config_set_url)\s*\(", ch):
            visible["config_write_api"] = min(1.0, visible["config_write_api"] + 0.3)

    # app_main.c integration
    app_main = main_dir / "app_main.c"
    mc = ""
    main_body = ""
    if app_main.exists():
        mc = _read(app_main)
        has_include_header = bool(re.search(r'#include\s*".*server_select.*"', mc, re.IGNORECASE))
        main_body = _extract_function_body(mc, r"void\s+app_main")
        sel_match = re.search(r"\w*(server|srv).*select\w*\s*\(", main_body, re.IGNORECASE) if main_body else None
        visible["app_main_integration"] = min(1.0, (
            (0.5 if has_include_header else 0.0) +
            (0.5 if sel_match else 0.0)
        ))

    # =====================================================================
    # HIDDEN/HARD CHECKS (40% total) — Only strong agents pass these
    # These test deep embedded systems correctness that require real
    # understanding of LVGL event loops, FreeRTOS patterns, and proper
    # startup sequencing. Weak agents typically miss >= 3 of these.
    # =====================================================================
    hidden = {
        "blocking_loop_correctness": 0.0,   # 0.08 - while loop with proper exit condition
        "call_ordering_strict": 0.0,        # 0.07 - after ui_init, before ws task
        "lv_timer_in_loop": 0.0,            # 0.06 - must call lv_timer_handler in poll loop
        "freertos_yield": 0.0,              # 0.05 - must yield CPU (vTaskDelay/pdMS_TO_TICKS)
        "index_boundary_safety": 0.0,       # 0.04 - wrapping or clamping on nav indices
        "style_highlight_update": 0.0,      # 0.04 - must update visual highlight on selection change
        "screen_lifecycle_complete": 0.0,   # 0.03 - create screen + load + cleanup after confirm
        "url_array_not_hardcoded_twice": 0.0,  # 0.03 - URLs defined once in array, not scattered
    }

    if ic:
        # --- H1: Blocking loop correctness (0.08) ---
        # Must have a while loop that: (a) has a boolean exit condition,
        # (b) contains key reading, (c) sets the exit flag on confirm
        has_blocking_loop = bool(re.search(
            r"while\s*\([^)]*\)\s*\{.*?(drv_key_read|DRV_KEY).*?(break|confirmed|selected|done)",
            ic, re.DOTALL | re.IGNORECASE
        ))
        if not has_blocking_loop:
            has_blocking_loop = bool(re.search(
                r"while\s*\([^)]*(!|==\s*false|==\s*0|==\s*pdFALSE)[^)]*\)\s*\{",
                ic
            )) and ("drv_key_read" in ic or "DRV_KEY" in ic)
        # Extra: the loop must have an exit mechanism tied to the confirm key
        has_exit_on_confirm = bool(re.search(
            r"(DRV_KEY_MIDDLE|DRV_KEY_OK).*?(break|=\s*true|=\s*1|=\s*pdTRUE)",
            ic, re.DOTALL | re.IGNORECASE
        ))
        hidden["blocking_loop_correctness"] = min(1.0, (
            (0.6 if has_blocking_loop else 0.0) +
            (0.4 if has_exit_on_confirm else 0.0)
        ))

        # --- H2: Strict call ordering in app_main (0.07) ---
        # Must be: ui_common_init() -> server_select() -> xTaskCreate(ws)
        if main_body:
            sel_match = re.search(r"\w*(server|srv).*select\w*\s*\(", main_body, re.IGNORECASE)
            ws_match = re.search(r"(xTaskCreate|xTaskCreatePinnedToCore)\s*\(\s*\w*task_ws", main_body, re.IGNORECASE)
            ui_init_match = re.search(r"ui_common_init", main_body)

            after_ui_init = (sel_match and ui_init_match and sel_match.start() > ui_init_match.start()) if sel_match and ui_init_match else False
            before_ws = (sel_match and ws_match and sel_match.start() < ws_match.start()) if sel_match and ws_match else False
            # If ws task not found but select is called, give partial credit
            if sel_match and not ws_match:
                before_ws = True

            hidden["call_ordering_strict"] = min(1.0, (
                (0.5 if after_ui_init else 0.0) +
                (0.5 if before_ws else 0.0)
            ))

        # --- H3: lv_timer_handler in the polling loop (0.06) ---
        # Critical LVGL requirement: display won't update without this in the loop.
        # The timer handler must be INSIDE the while loop body, not just anywhere.
        found_timer_in_loop = bool(re.search(
            r"while\s*\([^)]*\)\s*\{[^}]*lv_timer_handler\s*\(\s*\)",
            ic, re.DOTALL
        ))
        # Also accept lv_task_handler (older LVGL API name)
        if not found_timer_in_loop:
            found_timer_in_loop = bool(re.search(
                r"while\s*\([^)]*\)\s*\{[^}]*lv_task_handler\s*\(\s*\)",
                ic, re.DOTALL
            ))
        # Handle switch/case inside while (common pattern)
        if not found_timer_in_loop:
            found_timer_in_loop = bool(re.search(
                r"while\s*\([^)]*\)\s*\{.*?lv_timer_handler\s*\(\s*\)",
                ic, re.DOTALL
            )) and ("drv_key" in ic.lower() or "DRV_KEY" in ic)
        hidden["lv_timer_in_loop"] = 1.0 if found_timer_in_loop else 0.0

        # --- H4: FreeRTOS CPU yield (0.05) ---
        # Must yield CPU in the selection loop. Without this, watchdog triggers on ESP32.
        # Accept vTaskDelay with pdMS_TO_TICKS or raw tick value
        found_delay_in_loop = bool(re.search(
            r"while\s*\([^)]*\)\s*\{.*?(vTaskDelay|usleep|esp_timer_get_time)\s*\(",
            ic, re.DOTALL
        ))
        # Stronger: uses pdMS_TO_TICKS for proper timing
        uses_pd_ms = "pdMS_TO_TICKS" in ic or "portTICK_PERIOD_MS" in ic
        hidden["freertos_yield"] = min(1.0, (
            (0.6 if found_delay_in_loop else 0.0) +
            (0.4 if uses_pd_ms else 0.0)
        ))

        # --- H5: Index boundary safety (0.04) ---
        # Navigation index must wrap or clamp. Without this, out-of-bounds on 2-item list.
        has_modulo = bool(re.search(r"(%\s*\d+|%\s*\w*(NUM|COUNT|SIZE|LEN|num|count))", ic, re.IGNORECASE))
        has_bounds_check = bool(re.search(
            r"(if\s*\(\s*\w*(idx|index|sel|cur|current|choice)\w*\s*(>=|>|<|<=)\s*)|"
            r"(\w*(idx|index|sel|cur|current|choice)\w*\s*=\s*\w*(idx|index|sel|cur|current|choice)\w*\s*%)",
            ic, re.IGNORECASE
        ))
        has_clamp = bool(re.search(
            r"(if\s*\(\s*\w*(idx|index|sel|cur|current|choice)\w*\s*<\s*0)|"
            r"(if\s*\(\s*\w*(idx|index|sel|cur|current|choice)\w*\s*>=?\s*\w*(NUM|COUNT|MAX|SIZE|num|count))",
            ic, re.IGNORECASE
        ))
        hidden["index_boundary_safety"] = min(1.0, max(
            1.0 if has_modulo else 0.0,
            (0.5 if has_bounds_check else 0.0) + (0.5 if has_clamp else 0.0),
        ))

        # --- H6: Visual highlight update on selection change (0.04) ---
        # When user presses UP/DOWN, the UI must visually indicate the new selection.
        # Strong impl updates border/bg color or moves an indicator.
        has_style_set = bool(re.search(r"lv_obj_set_style_(bg|border|outline)_(color|opa)\s*\(", ic))
        has_style_add_remove = bool(re.search(r"lv_obj_(add|remove)_style\s*\(", ic))
        has_color_update_in_nav = bool(re.search(
            r"(DRV_KEY_UP|DRV_KEY_DOWN).*?(lv_obj_set_style|lv_obj_add_style|lv_obj_remove_style|lv_label_set_text_color)",
            ic, re.DOTALL | re.IGNORECASE
        ))
        # Alternative: re-render by function call
        has_update_func = bool(re.search(r"(update_highlight|update_selection|refresh_ui|set_selected)\s*\(", ic, re.IGNORECASE))

        hidden["style_highlight_update"] = min(1.0, max(
            1.0 if has_color_update_in_nav else 0.0,
            (0.4 if has_style_set else 0.0) + (0.3 if has_style_add_remove else 0.0) + (0.3 if has_update_func else 0.0),
        ))

        # --- H7: Screen lifecycle complete (0.03) ---
        # Must: create screen/container, load it, AND clean up after confirm
        has_screen_create = bool(re.search(r"lv_obj_create\s*\(\s*(NULL|lv_scr_act\s*\(\s*\))", ic))
        has_screen_load = bool(re.search(r"lv_scr_load|lv_disp_load_scr", ic))
        has_cleanup = bool(re.search(r"lv_obj_del|lv_obj_clean", ic))
        # All three must be present for full marks
        hidden["screen_lifecycle_complete"] = min(1.0, (
            (0.35 if has_screen_create else 0.0) +
            (0.30 if has_screen_load else 0.0) +
            (0.35 if has_cleanup else 0.0)
        ))

        # --- H8: URL array defined once, not hardcoded multiple times (0.03) ---
        # Good practice: define URLs in a const array, reference by index.
        # Bad: hardcoding the full URL string in multiple places.
        url1_count = ic.count("20.tcp.vip.cpolar.cn:10244")
        url2_count = ic.count("192.168.50.233:61032")
        # If each URL appears exactly once (in array definition), that's clean.
        # If they appear 2+ times each, it's scattered hardcoding.
        has_array_def = bool(re.search(
            r"(const\s+)?char\s*\*\s*\w*(url|server|option)\w*\s*\[\s*\]",
            ic, re.IGNORECASE
        ))
        urls_defined_once = (url1_count == 1 and url2_count == 1)
        hidden["url_array_not_hardcoded_twice"] = min(1.0, (
            (0.5 if has_array_def else 0.0) +
            (0.5 if urls_defined_once else (0.2 if url1_count <= 2 and url2_count <= 2 else 0.0))
        ))

    # =====================================================================
    # COMPUTE WEIGHTED SCORE
    # Easy: 30%, Visible: 30%, Hidden: 40% (>= 30% requirement met)
    # =====================================================================
    easy_weights = {
        "header_exists": 0.08,
        "impl_exists": 0.10,
        "basic_includes": 0.07,
        "has_lv_calls": 0.05,
    }
    visible_weights = {
        "key_nav_logic": 0.10,
        "server_urls": 0.08,
        "config_write_api": 0.07,
        "app_main_integration": 0.05,
    }
    hidden_weights = {
        "blocking_loop_correctness": 0.08,
        "call_ordering_strict": 0.07,
        "lv_timer_in_loop": 0.06,
        "freertos_yield": 0.05,
        "index_boundary_safety": 0.04,
        "style_highlight_update": 0.04,
        "screen_lifecycle_complete": 0.03,
        "url_array_not_hardcoded_twice": 0.03,
    }

    all_components = {}
    all_components.update(easy)
    all_components.update(visible)
    all_components.update(hidden)

    all_weights = {}
    all_weights.update(easy_weights)
    all_weights.update(visible_weights)
    all_weights.update(hidden_weights)

    overall = sum(all_weights[k] * min(1.0, all_components[k]) for k in all_weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in all_components.items()},
        "weights": all_weights,
        "tier_scores": {
            "easy": round(sum(easy_weights[k] * min(1.0, easy[k]) for k in easy_weights), 4),
            "visible": round(sum(visible_weights[k] * min(1.0, visible[k]) for k in visible_weights), 4),
            "hidden": round(sum(hidden_weights[k] * min(1.0, hidden[k]) for k in hidden_weights), 4),
        },
        "discrimination_info": {
            "hidden_weight_pct": 40,
            "hidden_checks": list(hidden_weights.keys()),
        },
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
