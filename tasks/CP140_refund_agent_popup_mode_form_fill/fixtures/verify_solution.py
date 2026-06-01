"""Hidden verifier for CP140 — Refund Agent Popup Mode + Form Fill."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_js_comments(code: str) -> str:
    """Strip single-line (//) and multi-line (/* */) JS comments."""
    # Remove multi-line comments
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    # Remove single-line comments (but not URLs like http://)
    code = re.sub(r'(?<!:)//[^\n]*', '', code)
    return code


def grade_workspace(ws: Path) -> dict:
    """Grade the refund agent workspace modifications."""
    # Look for agent.js in expected locations
    agent_js_raw = ""
    candidates = [
        ws / "fixtures" / "refund-system" / "agent.js",
        ws / "refund-system" / "agent.js",
    ]
    for c in candidates:
        if c.exists():
            agent_js_raw = _read(c)
            break

    # Strip comments for code analysis (comments shouldn't count as implementation)
    agent_js = _strip_js_comments(agent_js_raw) if agent_js_raw else ""

    # Look for main.py
    main_py_raw = ""
    main_candidates = [
        ws / "fixtures" / "refund-system" / "main.py",
        ws / "refund-system" / "main.py",
    ]
    for c in main_candidates:
        if c.exists():
            main_py_raw = _read(c)
            break
    # Strip Python comments for analysis
    main_py = re.sub(r'#[^\n]*', '', main_py_raw) if main_py_raw else ""

    components = {k: 0.0 for k in [
        "form_fill_implemented",
        "popup_mode_overlay",
        "overlay_auto_remove",
        "no_extra_alert_dialog",
        "operation_log_call",
        "result_field_int_type",
        "form_fill_completeness",
        "overlay_z_index_correctness",
        "log_error_handling",
        "form_fill_event_dispatch",
        "overlay_full_viewport",
        "popup_mode_click_conditional",
    ]}

    # --- Dimension 1: Form fill logic implemented (basic) ---
    # The fillForm function must actually fill form inputs, not just log
    if agent_js:
        # Check for DOM manipulation in fillForm (querySelector, value assignment, etc.)
        has_query_selector = bool(re.search(
            r'(querySelector|getElementById|getElementsBy|querySelectorAll)', agent_js
        ))
        has_value_assign = bool(re.search(
            r'\.\s*value\s*=', agent_js
        ))
        has_records_iteration = bool(re.search(
            r'(records\s*\.\s*(forEach|map|for)|for\s*\(.*records)', agent_js
        ))
        # Must have actual field mapping logic (not just console.log)
        fill_func_match = re.search(
            r'function\s+fillForm\s*\([^)]*\)\s*\{([\s\S]*?)(?:\n\s*function\s|\n\s*//\s*(?:TODO|显示|弹窗)|\Z)',
            agent_js
        )
        # Also match arrow function or method style
        if not fill_func_match:
            fill_func_match = re.search(
                r'(?:const|let|var)\s+fillForm\s*=\s*(?:async\s*)?\(?[^)]*\)?\s*=>\s*\{([\s\S]*?)(?:\n\s*(?:const|let|var|function)\s|\Z)',
                agent_js
            )
        fill_body = fill_func_match.group(1) if fill_func_match else ""
        has_field_mapping = bool(re.search(
            r'(field_name|field-customer|field-refund|客户姓名|退款金额)', fill_body
        )) if fill_body else False

        score = 0.0
        if has_query_selector and has_value_assign:
            score += 0.4
        if has_records_iteration or has_field_mapping:
            score += 0.3
        # Penalize if fillForm still only has console.log and no DOM ops
        if fill_body and 'console.log' in fill_body and not has_value_assign:
            score = max(0.0, score - 0.2)
        if has_field_mapping and has_value_assign:
            score += 0.3
        components["form_fill_implemented"] = min(1.0, score)

    # --- Dimension 2: Popup mode overlay (grey page) ---
    if agent_js:
        # Must create a grey/dark overlay element that covers the page
        has_overlay_create = bool(re.search(
            r'(createElement|innerHTML).*?(overlay|mask|backdrop)', agent_js, re.IGNORECASE
        )) or bool(re.search(
            r'(overlay|mask|backdrop).*?(createElement|innerHTML)', agent_js, re.IGNORECASE
        ))
        # Grey/dark semi-transparent background specifically for overlay
        # Must have rgba(0,0,0,0.3+) or similar dark overlay, not just box-shadow
        has_grey_style = bool(re.search(
            r'rgba\s*\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\.[3-9]', agent_js
        )) or bool(re.search(
            r'(overlay|mask|backdrop)[\s\S]{0,200}(background|backgroundColor)', agent_js, re.IGNORECASE
        ))
        # pointer-events:none on page content OR overlay blocking interactions
        has_pointer_events = bool(re.search(
            r'pointer-events\s*:\s*none', agent_js, re.IGNORECASE
        )) or bool(re.search(
            r'pointerEvents\s*=\s*["\']none', agent_js
        ))
        # Must fetch /api/models to check popup mode state
        has_model_fetch = bool(re.search(
            r'fetch\s*\(\s*[`"\'][^`"\']*api/models', agent_js
        ))
        # Must check state field
        has_state_check = bool(re.search(
            r'state\s*===?\s*1|state\s*==\s*1|\.state\s*===?\s*1', agent_js
        ))
        # Must reference 弹窗模式 in code (not comments)
        has_popup_name_check = bool(re.search(
            r'["\']弹窗模式["\']', agent_js
        )) or bool(re.search(
            r'name\s*===?\s*["\']弹窗模式', agent_js
        ))

        score = 0.0
        if has_overlay_create:
            score += 0.2
        if has_grey_style:
            score += 0.15
        if has_pointer_events:
            score += 0.15
        if has_model_fetch:
            score += 0.2
        if has_state_check and has_popup_name_check:
            score += 0.3
        elif has_state_check or has_popup_name_check:
            score += 0.15
        components["popup_mode_overlay"] = min(1.0, score)

    # --- Dimension 3: Overlay auto-removes after fill ---
    if agent_js:
        # After form fill completes, overlay must be removed/hidden
        has_remove_overlay = bool(re.search(
            r'(remove\s*\(\s*\)|display\s*=\s*["\']none|classList\.\s*remove|removeChild|style\.display)',
            agent_js
        ))
        # Removal should happen in or after fillForm / recognition success
        has_remove_after_fill = bool(re.search(
            r'(fillForm|fill.*complete|识别.*完成|填充.*完成)[\s\S]{0,500}(remove|display\s*=\s*["\']none|removeChild)',
            agent_js, re.IGNORECASE
        )) or bool(re.search(
            r'(remove|display\s*=\s*["\']none|removeChild)[\s\S]{0,200}(fillForm|fill.*complete)',
            agent_js, re.IGNORECASE
        ))

        score = 0.0
        if has_remove_overlay:
            score += 0.5
        if has_remove_after_fill:
            score += 0.5
        components["overlay_auto_remove"] = min(1.0, score)

    # --- Dimension 4: No extra alert/dialog box ---
    # Should NOT show "弹窗模式已激活" alert/confirm/modal dialog
    if agent_js:
        has_alert_activated = bool(re.search(
            r'(alert|confirm|window\.alert)\s*\([^)]*弹窗模式已激活', agent_js
        ))
        has_modal_activated_text = bool(re.search(
            r'(innerHTML|textContent|innerText)\s*=\s*[^;]*弹窗模式已激活', agent_js
        ))
        # Also check for creating a separate notification div with that text
        has_notification_div = bool(re.search(
            r'createElement.*?弹窗模式已激活|弹窗模式已激活.*?createElement', agent_js
        ))

        score = 1.0
        if has_alert_activated:
            score -= 0.6
        if has_modal_activated_text:
            score -= 0.3
        if has_notification_div:
            score -= 0.3
        components["no_extra_alert_dialog"] = max(0.0, score)

    # --- Dimension 5: Operation log API call ---
    if agent_js:
        # Must have an actual fetch call to /api/logs with POST
        # Support both template literals and string concatenation
        has_log_fetch = bool(re.search(
            r'fetch\s*\(\s*[`"\'][^`"\']*api/logs', agent_js
        )) or bool(re.search(
            r'fetch\s*\([^,)]*["\']/api/logs', agent_js
        ))
        has_post_method = bool(re.search(
            r'method\s*:\s*["\']POST["\']', agent_js, re.IGNORECASE
        ))
        # Must include result field in the body (as actual code, not comment)
        has_log_body_fields = bool(re.search(
            r'(file_name|business_name)\s*[,:=]', agent_js
        )) and has_log_fetch
        has_result_in_body = bool(re.search(
            r'result\s*:', agent_js
        )) and has_log_fetch

        score = 0.0
        if has_log_fetch:
            score += 0.4
        if has_post_method and has_log_fetch:
            score += 0.2
        if has_log_body_fields:
            score += 0.2
        if has_result_in_body:
            score += 0.2
        components["operation_log_call"] = min(1.0, score)

    # --- Dimension 6: result field is int type in backend ---
    if main_py:
        # Check that LogEntry.result is declared as int (not str)
        has_result_int = bool(re.search(
            r'result\s*:\s*int', main_py
        ))
        has_result_str = bool(re.search(
            r'result\s*:\s*str', main_py
        ))
        # Also check if there's validation logic
        has_validation = bool(re.search(
            r'(result\s*(not\s*in|in)\s*\[0,\s*1\]|result\s*[<>!=]|isinstance.*result.*int)',
            main_py
        ))

        if has_result_int and not has_result_str:
            score = 1.0
        elif has_result_int and has_result_str:
            score = 0.5
        elif has_validation:
            score = 0.6
        else:
            score = 0.0
        components["result_field_int_type"] = score

    # --- HIDDEN Dimension 7: Form fill completeness ---
    # Strong models should map ALL 6 fields from the HTML form, not just 1-2.
    # The form has: field-customer-name, field-refund-amount, field-refund-reason,
    # field-order-id, field-checkin-date, field-checkout-date
    if agent_js:
        all_field_ids = [
            "field-customer-name",
            "field-refund-amount",
            "field-refund-reason",
            "field-order-id",
            "field-checkin-date",
            "field-checkout-date",
        ]
        # Count how many field IDs are referenced in code (not comments)
        fields_found = sum(1 for fid in all_field_ids if fid in agent_js)

        # Also check for a complete mapping dict/object that maps Chinese names to IDs
        all_chinese_names = ["客户姓名", "退款金额", "退款原因", "订单编号", "入住日期", "退房日期"]
        chinese_found = sum(1 for cn in all_chinese_names if cn in agent_js)

        # Strong model maps all fields; weak model hardcodes 1-2 or uses generic approach
        # that may miss some fields
        mapped_count = max(fields_found, chinese_found)
        if mapped_count >= 6:
            score = 1.0
        elif mapped_count >= 4:
            score = 0.6
        elif mapped_count >= 2:
            score = 0.3
        else:
            # Generic approach without explicit mapping — give partial credit only
            # if there's a dynamic lookup that could handle all fields
            has_dynamic_lookup = bool(re.search(
                r'(field_name|fieldName)\s*[\]\)]\s*\|\|\s*|switch\s*\(\s*(record|item)\.(field_name|fieldName)',
                agent_js
            ))
            score = 0.2 if has_dynamic_lookup else 0.0
        components["form_fill_completeness"] = score

    # --- HIDDEN Dimension 8: Overlay z-index correctness ---
    # The overlay must have a z-index that is BELOW the AI panel (999998) but ABOVE
    # the page content. The AI panel must remain interactive above the overlay.
    # Weak models often set overlay z-index too high (blocking AI panel) or forget it.
    if agent_js:
        # Look for z-index on overlay element
        overlay_zindex_matches = re.findall(
            r'(?:overlay|mask|backdrop)[\s\S]{0,300}z-?[Ii]ndex\s*[:=]\s*["\']?(\d+)',
            agent_js, re.IGNORECASE
        )
        # Also look for zIndex assignment pattern
        overlay_zindex_matches += re.findall(
            r'z-?[Ii]ndex\s*[:=]\s*["\']?(\d+)[\s\S]{0,100}(?:overlay|mask|backdrop)',
            agent_js, re.IGNORECASE
        )

        # Check if the AI panel z-index is explicitly elevated in NEW code
        # (not just the pre-existing CSS template, which already has z-index: 999998)
        # We look for dynamic z-index assignment via JS (style.zIndex = ...) near panel/overlay context
        # Must be actual JS assignment (style.zIndex), NOT CSS in template strings
        panel_zindex_dynamic = bool(re.search(
            r'(panel|ai-agent-panel|agent-panel)[\s\S]{0,200}style\.zIndex\s*=',
            agent_js, re.IGNORECASE
        )) or bool(re.search(
            r'style\.zIndex\s*=[\s\S]{0,200}(panel|ai-agent-panel|agent-panel)',
            agent_js, re.IGNORECASE
        ))
        # Must also have overlay present in code
        panel_zindex_dynamic = panel_zindex_dynamic and bool(re.search(
            r'(overlay|mask|backdrop)', agent_js, re.IGNORECASE
        ))

        score = 0.0
        if overlay_zindex_matches:
            # Parse z-index values — overlay should be between page (0) and panel (999998)
            zvals = [int(z) for z in overlay_zindex_matches if z.isdigit()]
            if zvals:
                # Good: overlay z-index is less than 999998 (panel) and reasonably high
                good_zindex = any(100 <= z < 999998 for z in zvals)
                if good_zindex:
                    score += 0.5
                # Bad: overlay z-index >= 999998 (blocks panel)
                blocks_panel = any(z >= 999998 for z in zvals)
                if blocks_panel:
                    score = 0.0
        # Bonus if panel z-index is explicitly managed in overlay context
        if panel_zindex_dynamic and overlay_zindex_matches:
            score += 0.5
        components["overlay_z_index_correctness"] = min(1.0, score)

    # --- HIDDEN Dimension 9: Log call error handling & placement ---
    # The log POST should: (a) use await/then (async), (b) have try/catch or .catch,
    # (c) be placed AFTER successful recognition (not unconditionally),
    # (d) pass result as integer (1), not string ("1") or variable without type coercion
    if agent_js:
        score = 0.0
        # Support both template literal and concatenation patterns for detecting log fetch
        has_log_fetch_hidden = bool(re.search(
            r'fetch\s*\(\s*[`"\'][^`"\']*api/logs', agent_js
        )) or bool(re.search(
            r'fetch\s*\([^,)]*["\']/api/logs', agent_js
        ))

        if has_log_fetch_hidden:
            # (a) Async handling — must use await or .then() on the LOG fetch specifically
            # The await must be directly on the log fetch, not on some other fetch in same file
            has_await_log = bool(re.search(
                r'await\s+fetch\s*\(\s*[`"\'][^`"\']*api/logs', agent_js
            )) or bool(re.search(
                r'await\s+fetch\s*\([^,)]*["\']/api/logs', agent_js
            ))
            has_then_log = bool(re.search(
                r'fetch\s*\([^)]*api/logs[\s\S]{0,300}\.then\s*\(', agent_js
            )) or bool(re.search(
                r'/api/logs[\s\S]{0,300}\.then\s*\(', agent_js
            ))
            if has_await_log or has_then_log:
                score += 0.25

            # (b) Error handling on the log call specifically (SEPARATE try/catch around log)
            # Look for .catch() on the log fetch
            has_catch_log = bool(re.search(
                r'/api/logs[\s\S]{0,400}\.catch\s*\(', agent_js
            ))
            # Or a DEDICATED try block around the log fetch (not the outer recognize try)
            # The try must be within ~250 chars before /api/logs (indicating a nested try)
            has_dedicated_try_log = bool(re.search(
                r'try\s*\{[\s\S]{0,250}/api/logs[\s\S]{0,500}catch', agent_js
            ))
            if has_catch_log or has_dedicated_try_log:
                score += 0.25

            # (c) Log placed conditionally after success (inside data.success block)
            has_log_after_success = bool(re.search(
                r'(data\.success|success\s*===?\s*true)[\s\S]{0,800}/api/logs',
                agent_js
            ))
            if has_log_after_success:
                score += 0.25

            # (d) result value is numeric literal 1, not string "1"
            has_result_int_literal = bool(re.search(
                r'result\s*:\s*1\b', agent_js
            ))
            has_result_string_literal = bool(re.search(
                r'result\s*:\s*["\']1["\']', agent_js
            ))
            if has_result_int_literal and not has_result_string_literal:
                score += 0.25
            elif has_result_int_literal:
                score += 0.1  # partial if both exist somewhere

        components["log_error_handling"] = min(1.0, score)

    # --- HIDDEN Dimension 10: Form fill triggers input/change event ---
    # After setting element.value programmatically, the code MUST dispatch an
    # 'input' or 'change' event so that any framework bindings (Vue, React, etc.)
    # pick up the new value. Weak models just do el.value = x and stop.
    if agent_js:
        # Look for dispatchEvent with Event/InputEvent/CustomEvent near value assignment
        has_dispatch_event = bool(re.search(
            r'dispatchEvent\s*\(\s*new\s+(Event|InputEvent|CustomEvent)\s*\(\s*["\'](?:input|change)["\']',
            agent_js
        ))
        # Alternative: using trigger() if jQuery-style, or element.dispatchEvent(new Event(...))
        has_dispatch_generic = bool(re.search(
            r'dispatchEvent\s*\(\s*new\s+Event\s*\(\s*["\'](?:input|change)',
            agent_js
        ))
        # Must be near or after .value = assignment (within same function scope)
        has_dispatch_near_value = bool(re.search(
            r'\.value\s*=[\s\S]{0,200}dispatchEvent',
            agent_js
        )) or bool(re.search(
            r'dispatchEvent[\s\S]{0,200}\.value\s*=',
            agent_js
        ))

        score = 0.0
        if has_dispatch_event or has_dispatch_generic:
            score += 0.5
        if has_dispatch_near_value:
            score += 0.5
        components["form_fill_event_dispatch"] = min(1.0, score)
    else:
        components["form_fill_event_dispatch"] = 0.0

    # --- HIDDEN Dimension 11: Overlay is full-viewport fixed positioning ---
    # The grey overlay must use position:fixed with full coverage (top:0, left:0,
    # width:100%/100vw, height:100%/100vh or inset:0). Weak models often use
    # position:absolute (only covers scrolled area) or forget dimensions.
    if agent_js:
        # Must have position: fixed for the overlay
        has_position_fixed = bool(re.search(
            r'(overlay|mask|backdrop)[\s\S]{0,400}position\s*[:=]\s*["\']?fixed',
            agent_js, re.IGNORECASE
        )) or bool(re.search(
            r'position\s*[:=]\s*["\']?fixed[\s\S]{0,400}(overlay|mask|backdrop)',
            agent_js, re.IGNORECASE
        ))

        # Must cover full viewport: (top:0 + left:0) or inset:0
        has_full_coverage = bool(re.search(
            r'(top\s*[:=]\s*["\']?0|inset\s*[:=]\s*["\']?0)', agent_js
        )) and bool(re.search(
            r'(left\s*[:=]\s*["\']?0|inset\s*[:=]\s*["\']?0)', agent_js
        ))
        # Also accept width:100%/100vw + height:100%/100vh
        has_full_dims = bool(re.search(
            r'(width\s*[:=]\s*["\']?100\s*(%|vw)|inset\s*[:=]\s*["\']?0)', agent_js
        )) and bool(re.search(
            r'(height\s*[:=]\s*["\']?100\s*(%|vh)|inset\s*[:=]\s*["\']?0)', agent_js
        ))

        score = 0.0
        if has_position_fixed:
            score += 0.4
        if has_full_coverage or has_full_dims:
            score += 0.6
        # Penalize if position:absolute is used for overlay instead
        has_position_absolute = bool(re.search(
            r'(overlay|mask|backdrop)[\s\S]{0,300}position\s*[:=]\s*["\']?absolute',
            agent_js, re.IGNORECASE
        ))
        if has_position_absolute and not has_position_fixed:
            score = max(0.0, score - 0.4)
        components["overlay_full_viewport"] = min(1.0, score)
    else:
        components["overlay_full_viewport"] = 0.0

    # --- HIDDEN Dimension 12: Popup mode conditional fetch on ball click ---
    # The popup mode logic must: (a) be triggered inside/after the ball click handler,
    # (b) fetch /api/models THEN check 弹窗模式 state, (c) only apply overlay
    # if state===1. Weak models often put it outside click handler, or apply overlay
    # unconditionally, or fetch models at page load instead of on click.
    if agent_js:
        # The ball click handler must contain or call the popup mode fetch
        # Pattern: ball.addEventListener('click', ...) containing fetch /api/models
        ball_click_section = re.search(
            r'ball[\s\S]{0,80}addEventListener\s*\(\s*["\']click["\'][\s\S]{0,2000}',
            agent_js
        )
        ball_click_text = ball_click_section.group(0) if ball_click_section else ""

        # Alternative: ball.onclick = ... containing fetch
        ball_onclick_section = re.search(
            r'ball\s*\.\s*onclick\s*=[\s\S]{0,2000}',
            agent_js
        )
        if not ball_click_text and ball_onclick_section:
            ball_click_text = ball_onclick_section.group(0)

        has_fetch_in_click = bool(re.search(
            r'fetch\s*\([^)]*api/models', ball_click_text
        )) if ball_click_text else False

        # Also accept: ball click calls a function that then fetches models
        # Look for a named function call in ball click that fetches models elsewhere
        func_call_in_click = re.findall(r'(\w+)\s*\(\s*\)', ball_click_text) if ball_click_text else []
        has_indirect_fetch = False
        for fn in func_call_in_click:
            # Check if that function fetches /api/models
            fn_body = re.search(
                rf'(?:async\s+)?function\s+{fn}\s*\([^)]*\)\s*\{{([\s\S]*?)(?:\n\s*(?:async\s+)?function\s|\Z)',
                agent_js
            )
            if not fn_body:
                fn_body = re.search(
                    rf'(?:const|let|var)\s+{fn}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{{([\s\S]*?)(?:\n\s*(?:const|let|var|function)\s|\Z)',
                    agent_js
                )
            if fn_body and 'api/models' in fn_body.group(1):
                has_indirect_fetch = True
                break

        # Check: overlay creation is CONDITIONAL on state===1 (not unconditional)
        has_conditional_overlay = bool(re.search(
            r'(state\s*===?\s*1|state\s*==\s*1)[\s\S]{0,500}(overlay|mask|backdrop|grey|gray)',
            agent_js, re.IGNORECASE
        )) or bool(re.search(
            r'(弹窗模式)[\s\S]{0,500}(state)[\s\S]{0,300}(overlay|mask|backdrop)',
            agent_js, re.IGNORECASE
        ))

        score = 0.0
        if has_fetch_in_click or has_indirect_fetch:
            score += 0.5
        if has_conditional_overlay:
            score += 0.5
        components["popup_mode_click_conditional"] = min(1.0, score)
    else:
        components["popup_mode_click_conditional"] = 0.0

    # --- Weight distribution ---
    # Heavy weight on hidden discriminating checks; reduced weight on easy checks
    weights = {
        "form_fill_implemented": 0.10,       # basic pattern match — easy
        "popup_mode_overlay": 0.10,          # basic pattern match — easy
        "overlay_auto_remove": 0.07,         # relatively straightforward
        "no_extra_alert_dialog": 0.03,       # almost everyone gets this
        "operation_log_call": 0.07,          # moderate difficulty
        "result_field_int_type": 0.03,       # trivial one-line change
        "form_fill_completeness": 0.15,      # hidden — must map all 6 fields
        "overlay_z_index_correctness": 0.10, # hidden — z-index layering
        "log_error_handling": 0.10,          # hidden — async + error handling + int type
        "form_fill_event_dispatch": 0.10,    # hidden — dispatch input/change event
        "overlay_full_viewport": 0.08,       # hidden — position:fixed full coverage
        "popup_mode_click_conditional": 0.07, # hidden — fetch in click + conditional
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    # Try fixtures/ first (sandbox_files land there)
    if (ws / "fixtures" / "refund-system" / "agent.js").exists():
        print(json.dumps(grade_workspace(ws), ensure_ascii=False))
    elif (ws / "refund-system" / "agent.js").exists():
        print(json.dumps(grade_workspace(ws), ensure_ascii=False))
    else:
        # Fallback: search for agent.js anywhere
        found = list(ws.rglob("agent.js"))
        if found:
            parent = found[0].parent
            # reconstruct workspace root
            print(json.dumps(grade_workspace(parent.parent), ensure_ascii=False))
        else:
            print(json.dumps({"overall_score": 0.0, "components": {}, "error": "agent.js not found"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
