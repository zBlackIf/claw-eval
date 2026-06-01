"""Hidden verifier for CP186 — Redmine Charts Plugin PDF Export Feature."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(base: Path, pattern: str) -> Path | None:
    """Find a file matching pattern recursively."""
    for p in base.rglob(pattern):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the PDF export implementation."""
    plugin_root = ws / "rd_charts"
    if not plugin_root.exists():
        plugin_root = ws
        if not (plugin_root / "init.rb").exists() and not (plugin_root / "app").exists():
            plugin_root = ws / "fixtures" / "rd_charts"

    components = {k: 0.0 for k in [
        "export_button_added",
        "modal_dialog_implemented",
        "tab_selection_checkboxes",
        "pdf_generation_library",
        "canvas_to_image_handling",
        "hidden_panel_visibility_fix",
    ]}

    # Gather all relevant file contents
    view_file = _find_file(plugin_root, "index.html.erb")
    view_content = _read(view_file) if view_file else ""

    js_file = _find_file(plugin_root, "rd_charts.js")
    js_content = _read(js_file) if js_file else ""

    # Also check for any additional JS files (e.g. export-specific module)
    extra_js_content = ""
    for extra_js in plugin_root.rglob("*.js"):
        if extra_js != js_file and "min.js" not in extra_js.name:
            extra_js_content += "\n" + _read(extra_js)

    all_js = js_content + extra_js_content
    all_content = view_content + all_js

    css_file = _find_file(plugin_root, "rd_charts.css")
    css_content = _read(css_file) if css_file else ""

    # 1. Check export button in HTML view
    # Must have an explicit export/download button element (not just the word in comments)
    has_export_btn = bool(re.search(
        r'<(button|a|input|span|div)[^>]*(export|download)[^>]*>',
        view_content, re.IGNORECASE
    )) or bool(re.search(
        r'(id|class)\s*=\s*["\'][^"\']*export[^"\']*["\']',
        view_content, re.IGNORECASE
    ))
    has_export_in_js = bool(re.search(
        r'(export|doExport|openExport|showExport|handleExport)',
        all_js, re.IGNORECASE
    )) and bool(re.search(
        r'(addEventListener|onclick|click|bind)',
        all_js, re.IGNORECASE
    ))
    components["export_button_added"] = min(1.0,
        (0.6 if has_export_btn else 0.0) +
        (0.4 if has_export_in_js else 0.0)
    )

    # 2. Check modal dialog implementation
    # Must have explicit modal/dialog DOM structure
    has_modal_html = bool(re.search(
        r'<[^>]*(modal|dialog|export-dialog|export-modal)[^>]*>',
        view_content, re.IGNORECASE
    )) or bool(re.search(
        r'(id|class)\s*=\s*["\'][^"\']*modal[^"\']*["\']',
        view_content + all_js, re.IGNORECASE
    ))
    has_modal_show_hide = bool(re.search(
        r'(\.style\.display\s*=|modal.*show|modal.*hide|modal.*open|modal.*close|classList.*(add|remove|toggle).*modal)',
        all_js, re.IGNORECASE
    ))
    has_cancel_close = bool(re.search(
        r'(cancel|close).*?(modal|dialog|export)',
        all_content, re.IGNORECASE
    )) or bool(re.search(
        r'(modal|dialog|export).*?(cancel|close)',
        all_content, re.IGNORECASE
    ))
    components["modal_dialog_implemented"] = min(1.0,
        (0.4 if has_modal_html else 0.0) +
        (0.3 if has_modal_show_hide else 0.0) +
        (0.3 if has_cancel_close else 0.0)
    )

    # 3. Check tab selection checkboxes in modal
    # Must have actual checkbox inputs (type="checkbox") associated with tab names
    has_checkboxes = bool(re.search(
        r'type\s*=\s*["\']checkbox["\']',
        all_content, re.IGNORECASE
    ))
    # Check that checkboxes reference tab/panel names for selection
    checkbox_context = re.findall(
        r'checkbox[^<]{0,200}', all_content, re.IGNORECASE | re.DOTALL
    )
    checkbox_text = " ".join(checkbox_context)
    tab_names = ["overview", "dimension", "trend", "overdue", "efficiency"]
    tabs_in_checkbox_context = sum(1 for t in tab_names if t.lower() in checkbox_text.lower())
    # Also check if checkboxes are generated dynamically with tab refs
    has_dynamic_checkboxes = bool(re.search(
        r'(forEach|map|for)\s*\([^)]*\).*?checkbox',
        all_js, re.IGNORECASE | re.DOTALL
    )) or bool(re.search(
        r'checkbox.*?(forEach|map|for)',
        all_js, re.IGNORECASE | re.DOTALL
    ))
    has_checked_attr = bool(re.search(
        r'checked\s*[=:]?\s*["\']?(true|checked)',
        all_content, re.IGNORECASE
    )) or bool(re.search(
        r'\bchecked\b', all_content
    ))

    checkbox_score = 0.0
    if has_checkboxes:
        checkbox_score += 0.4
    if tabs_in_checkbox_context >= 2 or has_dynamic_checkboxes:
        checkbox_score += 0.3
    if has_checked_attr:
        checkbox_score += 0.3
    components["tab_selection_checkboxes"] = min(1.0, checkbox_score)

    # 4. Check PDF generation library usage
    # Must explicitly reference a PDF library (not just generic words)
    has_pdf_lib_ref = bool(re.search(
        r'(html2pdf|jspdf|jsPDF|pdfmake|PDFDocument)',
        all_content, re.IGNORECASE
    ))
    has_pdf_generation_call = bool(re.search(
        r'(html2pdf\s*\(|new\s+jsPDF|\.from\(|\.toPdf\(|\.save\s*\(|\.output\s*\()',
        all_js, re.IGNORECASE
    ))
    has_pdf_config = bool(re.search(
        r'(margin|orientation|format|filename|pagebreak|jsPDF)',
        all_js, re.IGNORECASE
    )) and has_pdf_lib_ref
    has_lib_script_tag = bool(re.search(
        r'(html2pdf|jspdf|pdfmake)',
        view_content, re.IGNORECASE
    )) or bool(re.search(
        r'javascript_include_tag.*?(html2pdf|jspdf|pdf)',
        view_content, re.IGNORECASE
    ))
    # Check for a separate PDF lib file
    has_pdf_lib_file = any(
        "pdf" in p.name.lower()
        for p in plugin_root.rglob("*.js")
    )

    pdf_score = 0.0
    if has_pdf_lib_ref:
        pdf_score += 0.3
    if has_pdf_generation_call:
        pdf_score += 0.3
    if has_pdf_config:
        pdf_score += 0.15
    if has_lib_script_tag or has_pdf_lib_file:
        pdf_score += 0.25
    components["pdf_generation_library"] = min(1.0, pdf_score)

    # 5. Check canvas-to-image handling (critical for Chart.js charts in PDF)
    # Must convert canvas elements to images for PDF rendering
    has_to_data_url = bool(re.search(
        r'\.toDataURL\s*\(', all_js
    ))
    has_html2canvas = bool(re.search(
        r'html2canvas', all_js, re.IGNORECASE
    ))
    has_canvas_to_img = bool(re.search(
        r'(canvas.*?(toDataURL|drawImage|getContext)|toDataURL.*?img|createElement\s*\(\s*["\']img["\'])',
        all_js, re.IGNORECASE
    ))
    # Check for explicit canvas → image replacement pattern
    has_img_src_from_canvas = bool(re.search(
        r'(\.src\s*=.*?toDataURL|img.*?src.*?canvas|data:image)',
        all_js, re.IGNORECASE
    ))

    canvas_score = 0.0
    if has_to_data_url or has_html2canvas:
        canvas_score += 0.5
    if has_canvas_to_img:
        canvas_score += 0.25
    if has_img_src_from_canvas:
        canvas_score += 0.25
    components["canvas_to_image_handling"] = min(1.0, canvas_score)

    # 6. Check hidden panel visibility fix (key bug from session)
    # Must explicitly handle showing hidden panels for export
    # Look for export-context visibility manipulation (not just tab switching)
    has_show_for_export = bool(re.search(
        r'(export|pdf|capture|print).*?(display\s*[=:]\s*["\']?(block|flex|""|none)|style\.display|visibility)',
        all_js, re.IGNORECASE | re.DOTALL
    )) or bool(re.search(
        r'(display\s*[=:]\s*["\']?(block|flex)|style\.display).*?(export|pdf|capture|print)',
        all_js, re.IGNORECASE | re.DOTALL
    ))
    # Check for iterating panels to show them specifically in export context
    has_panel_iteration_for_export = bool(re.search(
        r'(querySelectorAll|getElementsByClassName)\s*\([^)]*panel[^)]*\).*?(style\.display|display\s*=)',
        all_js, re.IGNORECASE | re.DOTALL
    ))
    # Check for async/promise pattern in export context
    has_async_export = bool(re.search(
        r'(async\s+function\s+\w*[Ee]xport|async\s+function\s+\w*[Dd]ownload|async\s+\w*[Ee]xport)',
        all_js, re.IGNORECASE
    )) or bool(re.search(
        r'(await\s+html2pdf|await\s+.*capture|await\s+.*export|Promise.*pdf)',
        all_js, re.IGNORECASE | re.DOTALL
    ))
    # Check for restoring original state after export
    has_state_restore = bool(re.search(
        r'(restore|original.*display|savedDisplay|prevDisplay|display.*="")',
        all_js, re.IGNORECASE
    )) and has_show_for_export

    visibility_score = 0.0
    if has_show_for_export:
        visibility_score += 0.35
    if has_panel_iteration_for_export:
        visibility_score += 0.25
    if has_async_export:
        visibility_score += 0.20
    if has_state_restore:
        visibility_score += 0.20
    components["hidden_panel_visibility_fix"] = min(1.0, visibility_score)

    # Bonus: CSS for modal
    if css_content:
        has_modal_css = bool(re.search(
            r'\.(modal|export-modal|dialog|overlay)\s*\{',
            css_content, re.IGNORECASE
        ))
        if has_modal_css and components["modal_dialog_implemented"] > 0:
            components["modal_dialog_implemented"] = min(1.0, components["modal_dialog_implemented"] + 0.1)

    weights = {
        "export_button_added": 0.15,
        "modal_dialog_implemented": 0.15,
        "tab_selection_checkboxes": 0.20,
        "pdf_generation_library": 0.20,
        "canvas_to_image_handling": 0.15,
        "hidden_panel_visibility_fix": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)

    # If overall_score is 0, try fixtures subdirectory
    if result["overall_score"] == 0.0:
        fixtures_ws = ws / "fixtures"
        if fixtures_ws.exists():
            result = grade_workspace(fixtures_ws)

    # If still 0, try rd_charts directly under workspace
    if result["overall_score"] == 0.0:
        rd_ws = ws / "fixtures" / "rd_charts"
        if rd_ws.exists():
            result = grade_workspace(rd_ws)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
