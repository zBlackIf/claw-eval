"""Hidden verifier for CP148 — Desktop Transfer Cabin Detail Page.

Checks that the agent created a proper secondary page for the desktop transfer cabin
device with the required data fields and proper integration into the existing app.

Tiered scoring architecture:
- EASY tier (visible, ~35%): Basic requirements any implementation should meet.
  All agents that attempt the task should score well here.
- HARD tier (hidden, ~35%): Structural/architectural checks that require careful
  study of the existing codebase patterns. Only strong agents pass these.
  Hidden weight >= 30% of total.
- MEDIUM tier (~30%): Moderate checks that differentiate reasonable from minimal.
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


def _find_tsx_files(base: Path) -> list[Path]:
    results = []
    if base.exists():
        for p in base.rglob("*.tsx"):
            results.append(p)
    return results


def _find_ts_files(base: Path) -> list[Path]:
    results = []
    if base.exists():
        for p in base.rglob("*.ts"):
            results.append(p)
    return results


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for the desktop transfer cabin detail page task."""

    # Try both possible locations
    project = ws / "blood-device-monitor"
    if not project.exists():
        project = ws / "fixtures" / "blood-device-monitor"
    if not project.exists():
        if (ws / "src").exists():
            project = ws
        else:
            return {
                "overall_score": 0.0,
                "components": {},
                "error": "Project directory not found",
            }

    src = project / "src"
    components_dir = src / "components"
    pages_dir = components_dir / "pages"
    types_dir = src / "types"

    scores: dict[str, float] = {}

    # Collect all source content
    all_tsx = _find_tsx_files(src)
    all_ts = _find_ts_files(src)

    # Find the cabin-specific file or section
    cabin_page_file = None
    cabin_content = ""

    # Priority 1: dedicated file for the cabin
    for f in all_tsx:
        fname_lower = f.name.lower()
        if any(kw in fname_lower for kw in ["desktop", "transfer", "cabin", "jiaojiechang"]):
            cabin_page_file = f
            cabin_content = _read(f)
            break

    # Priority 2: DeviceDetailPage extended with cabin functions
    if not cabin_page_file:
        detail_page = pages_dir / "DeviceDetailPage.tsx"
        if detail_page.exists():
            full_content = _read(detail_page)
            cabin_func_patterns = [
                r"function\s+\w*[Dd]esktop\w*[Tt]ransfer\w*\(",
                r"function\s+\w*[Cc]abin\w*[Pp]anel\(",
                r"function\s+\w*[Cc]abin\w*[Dd]etail\(",
                r"function\s+\w*[Tt]ransfer\w*[Cc]abin\w*\(",
            ]
            has_cabin_func = any(re.search(pat, full_content) for pat in cabin_func_patterns)
            if has_cabin_func:
                cabin_page_file = detail_page
                cabin_content = full_content

    # Gather all code for cross-file checks
    all_code = ""
    for f in all_tsx + all_ts:
        all_code += _read(f) + "\n"

    # If we have a dedicated file, use it as the primary search content
    search_content = cabin_content if cabin_content else ""
    if cabin_page_file and cabin_page_file.name.lower() != "devicedetailpage.tsx":
        search_content = _read(cabin_page_file)

    # ==================================================================
    # EASY TIER — Basic checks (any agent that attempts should pass these)
    # Total weight: ~35%
    # ==================================================================

    # E1. Page component exists (weight: 0.08) — EASY
    # Any attempt to create a cabin page should pass this.
    if cabin_page_file and len(search_content) > 200:
        scores["page_component_exists"] = 1.0
    elif cabin_page_file:
        scores["page_component_exists"] = 0.6
    else:
        scores["page_component_exists"] = 0.0

    # E2. Blood info keywords present (weight: 0.08) — EASY
    # Just checks that blood-related keywords appear in the output.
    if search_content:
        blood_keywords = [
            ("donationCode" in search_content or "献血码" in search_content or "donation" in search_content.lower()),
            ("bloodType" in search_content or "血型" in search_content),
            ("specification" in search_content or "规格" in search_content or "spec" in search_content.lower()),
            ("category" in search_content or "品类" in search_content or "类型" in search_content),
        ]
        found = sum(1 for c in blood_keywords if c)
        scores["blood_info_keywords"] = found / 4.0
    else:
        scores["blood_info_keywords"] = 0.0

    # E3. Device info keywords present (weight: 0.08) — EASY
    if search_content:
        device_keywords = [
            ("deviceCode" in search_content or "设备编号" in search_content or "device" in search_content.lower()),
            ("status" in search_content or "状态" in search_content),
            ("time" in search_content.lower() or "日期" in search_content or "时间" in search_content),
            ("operator" in search_content or "操作者" in search_content or "操作员" in search_content),
        ]
        found = sum(1 for c in device_keywords if c)
        scores["device_info_keywords"] = found / 4.0
    else:
        scores["device_info_keywords"] = 0.0

    # E4. Batch/heat seal keywords present (weight: 0.06) — EASY
    if search_content:
        batch_kw = 0.0
        if "批次" in search_content or "batch" in search_content.lower():
            batch_kw += 0.5
        if "热合" in search_content or "heatSeal" in search_content or "seal" in search_content.lower():
            batch_kw += 0.3
        if "接驳" in search_content or "docking" in search_content.lower():
            batch_kw += 0.2
        scores["batch_keywords"] = min(batch_kw, 1.0)
    else:
        scores["batch_keywords"] = 0.0

    # E5. Has TypeScript type definition (weight: 0.05) — EASY
    # Any new interface/type related to cabin counts.
    all_type_content = ""
    for f in all_ts + all_tsx:
        all_type_content += "\n" + _read(f)

    cabin_type_patterns = [
        r"(interface|type)\s+\w*[Dd]esktop\w*[Tt]ransfer\w*",
        r"(interface|type)\s+\w*[Cc]abin\w*",
        r"(interface|type)\s+\w*[Tt]ransfer\w*[Cc]abin",
        r"(interface|type)\s+\w*[Dd]ocking\w*[Bb]atch",
    ]
    has_any_cabin_type = any(re.search(pat, all_type_content) for pat in cabin_type_patterns)
    scores["type_exists"] = 1.0 if has_any_cabin_type else 0.0

    # ==================================================================
    # MEDIUM TIER — Moderate checks (reasonable implementations pass)
    # Total weight: ~30%
    # ==================================================================

    # M1. UI consistency with existing components (weight: 0.10) — MEDIUM
    if search_content and len(search_content) > 100:
        ui_score = 0.0
        if "GlassCard" in search_content:
            ui_score += 0.3
        elif "bg-slate-800" in search_content and "rounded" in search_content:
            ui_score += 0.15
        if "InfoRow" in search_content:
            ui_score += 0.3
        elif "label" in search_content and "value" in search_content:
            ui_score += 0.1
        if "<table" in search_content.lower() or "thead" in search_content or "<th" in search_content:
            ui_score += 0.2
        if "cyan" in search_content and "slate" in search_content:
            ui_score += 0.2
        scores["ui_consistency"] = min(ui_score, 1.0)
    else:
        scores["ui_consistency"] = 0.0

    # M2. Type definition quality (weight: 0.10) — MEDIUM
    # Checks that the type has proper field coverage (not just exists).
    type_quality = 0.0
    if has_any_cabin_type:
        type_quality += 0.3
        if re.search(r"(heatSeal\w*|sealTime|sealDuration|热合时间)\s*[?:]", all_type_content):
            type_quality += 0.25
        if re.search(r"(bloodItems|items|bloods|blood)\s*[?:]?\s*\w*\[\]", all_type_content):
            type_quality += 0.25
        if re.search(r"(batchId|batchNo|batch_id|batchNumber)\s*[?:]", all_type_content):
            type_quality += 0.2
    scores["type_quality"] = min(type_quality, 1.0)

    # M3. Basic routing — cabin is actively used in DeviceDetailPage (weight: 0.10) — MEDIUM
    # NOTE: The original DeviceDetailPage already has 'desktop_transfer_cabin' in the
    # getDeviceType map as a TODO hint. We need to detect ACTUAL component rendering,
    # not just the existing string in the map.
    detail_page = pages_dir / "DeviceDetailPage.tsx"
    detail_content = _read(detail_page) if detail_page.exists() else ""
    if cabin_page_file and cabin_page_file == detail_page:
        detail_content = search_content

    basic_routing = 0.0
    if detail_content:
        # Must have a JSX component rendered for cabin (not just string in map)
        # Pattern: <CabinXxx or <DesktopTransferXxx used as JSX
        cabin_jsx_patterns = [
            r"<\w*(Cabin|DesktopTransfer)\w+",  # JSX component usage
            r"desktop_transfer_cabin['\"]?\s*&&\s*<",  # conditional render
            r"desktop_transfer_cabin['\"]?\s*\?\s*<",  # ternary render
            r"case\s*['\"]desktop_transfer_cabin['\"].*?<\w+",  # switch case
        ]
        has_cabin_jsx = any(re.search(pat, detail_content, re.DOTALL) for pat in cabin_jsx_patterns)
        if has_cabin_jsx:
            basic_routing = 0.7
        # If cabin file is imported via import statement
        if cabin_page_file and cabin_page_file.name.lower() != "devicedetailpage.tsx":
            import_pat = r"import\s+.*?" + re.escape(cabin_page_file.stem)
            if re.search(import_pat, detail_content):
                basic_routing = max(basic_routing, 0.9)
            elif cabin_page_file.stem in detail_content:
                basic_routing = max(basic_routing, 0.6)
    # Also grant partial credit if the cabin page IS the detail page (extended inline)
    if cabin_page_file and cabin_page_file == detail_page and cabin_content:
        basic_routing = max(basic_routing, 0.7)
    scores["routing_basic"] = basic_routing

    # ==================================================================
    # HARD TIER — Hidden discriminating checks (only strong agents pass)
    # Total weight: ~35% (>= 30% requirement satisfied)
    # ==================================================================

    # H1. Dual-panel architecture (weight: 0.12) — HARD
    # Must implement BOTH LeftPanel AND RightPanel functions matching EXACT
    # naming pattern: <DeviceName>LeftPanel + <DeviceName>RightPanel.
    # This is the core architectural pattern in the codebase. Weak agents
    # miss this and just create a single component.
    dual_panel_score = 0.0
    check_code = all_code if not search_content else search_content

    left_panel_patterns = [
        r"function\s+\w*(Cabin|Desktop|Transfer)\w*Left\w*Panel\(",
        r"function\s+\w*Left\w*Panel\w*(Cabin|Desktop|Transfer)\(",
        r"function\s+Desktop\w*Transfer\w*Cabin\w*Left\(",
    ]
    right_panel_patterns = [
        r"function\s+\w*(Cabin|Desktop|Transfer)\w*Right\w*Panel\(",
        r"function\s+\w*Right\w*Panel\w*(Cabin|Desktop|Transfer)\(",
        r"function\s+Desktop\w*Transfer\w*Cabin\w*Right\(",
    ]

    has_left = any(re.search(pat, check_code) for pat in left_panel_patterns)
    has_right = any(re.search(pat, check_code) for pat in right_panel_patterns)

    if has_left and has_right:
        dual_panel_score = 1.0
    elif has_left or has_right:
        dual_panel_score = 0.3
    else:
        # Fallback: check for two substantial cabin-related functions
        cabin_funcs = re.findall(
            r"function\s+(\w*(Desktop|Transfer|Cabin)\w*)\s*\([^)]*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
            check_code,
            re.DOTALL,
        )
        substantial_funcs = [f for f in cabin_funcs if len(f[2]) > 200]
        if len(substantial_funcs) >= 2:
            dual_panel_score = 0.4
        elif len(substantial_funcs) == 1:
            dual_panel_score = 0.15

    scores["dual_panel_architecture"] = dual_panel_score

    # H2. Routing integration — BOTH panels (weight: 0.10) — HARD
    # The cabin must appear in BOTH the <aside> (left) and <section> (right)
    # blocks of DeviceDetailPage. This is the conditional rendering pattern:
    # deviceType === 'desktop_transfer_cabin' && <CabinLeftPanel />
    # in both aside and section. Weak agents only add one or none.
    integration_score = 0.0
    if detail_content:
        cabin_render_patterns = [
            r"desktop_transfer_cabin['\"]?\s*&&\s*<\w+",
            r"desktop_transfer_cabin['\"]?\s*\?\s*<\w+",
            r"'desktop_transfer_cabin'\s*:\s*<\w+",
            r"case\s*'desktop_transfer_cabin'",
        ]
        render_count = 0
        for pat in cabin_render_patterns:
            render_count += len(re.findall(pat, detail_content))

        if render_count >= 2:
            integration_score = 1.0
        elif render_count == 1:
            integration_score = 0.35
        else:
            if cabin_page_file and cabin_page_file.name.lower() != "devicedetailpage.tsx":
                cabin_name = cabin_page_file.stem
                if cabin_name in detail_content:
                    integration_score = 0.4

    scores["routing_dual_panel"] = integration_score

    # H3. Mock data with batch array structure (weight: 0.08) — HARD
    # Must create mock data following the established pattern:
    # - Exported from mock-data.ts
    # - Has properly typed batch array with multiple entries
    # - Each batch has heatSeal/sealTime field
    mock_data_file = src / "lib" / "mock-data.ts"
    mock_content = _read(mock_data_file) if mock_data_file.exists() else ""
    for f in all_ts:
        if "mock" in f.name.lower() or "data" in f.name.lower():
            mock_content += "\n" + _read(f)

    mock_score = 0.0
    has_cabin_mock = bool(
        re.search(
            r"(export\s+)?(const|let)\s+\w*(cabin|transferCabin|desktopTransfer|dockingBatch)\w*\s*[:=]",
            mock_content,
            re.IGNORECASE,
        )
    )

    if has_cabin_mock:
        mock_score += 0.35
        if re.search(r"\[\s*\{[^}]*(batch|docking|heatSeal|sealTime)", mock_content, re.IGNORECASE | re.DOTALL):
            mock_score += 0.35
        batch_objects = re.findall(r"\{\s*(?:batchId|batch_id|batchNo|batchNumber)", mock_content, re.IGNORECASE)
        if len(batch_objects) >= 2:
            mock_score += 0.3
    else:
        if search_content:
            inline_mock = bool(
                re.search(
                    r"(const|let)\s+\w*(cabin|transferCabin|dockingBatch)\w*\s*[:=]\s*\[",
                    search_content,
                    re.IGNORECASE,
                )
            )
            if inline_mock:
                mock_score += 0.2

    scores["mock_data_structure"] = min(mock_score, 1.0)

    # H4. Heat seal time rendered per-batch in JSX (weight: 0.05) — HARD
    # The task requires "物料的接驳热合时间" displayed PER BATCH — must appear
    # inside a .map() context or equivalent iteration, not just as a static label.
    heat_seal_score = 0.0
    if search_content:
        has_heat_in_map = bool(
            re.search(
                r"\.map\([^)]*\).*?(heatSeal|seal[Tt]ime|热合)|"
                r"(heatSeal|seal[Tt]ime|热合).*?\.map\(",
                search_content,
                re.DOTALL,
            )
        )
        has_heat_time_in_jsx = bool(
            re.search(
                r"\{[^}]*(heatSeal|seal[Tt]ime|seal[Dd]uration|热合)[^}]*\}",
                search_content,
            )
        )
        has_heat_time_value = bool(
            re.search(
                r"(heatSeal\w*Time|sealTime|sealDuration|热合时间|热合)\s*[}'\"]",
                search_content,
            )
        )

        if has_heat_in_map:
            heat_seal_score = 1.0
        elif has_heat_time_in_jsx:
            heat_seal_score = 0.5
        elif has_heat_time_value:
            heat_seal_score = 0.2

    scores["heat_seal_per_batch"] = heat_seal_score

    # ==================================================================
    # Weight calculation
    # EASY:   page_component_exists(0.08) + blood_info_keywords(0.08) +
    #         device_info_keywords(0.08) + batch_keywords(0.06) +
    #         type_exists(0.05) = 0.35
    # MEDIUM: ui_consistency(0.10) + type_quality(0.10) +
    #         routing_basic(0.10) = 0.30
    # HARD:   dual_panel_architecture(0.12) + routing_dual_panel(0.10) +
    #         mock_data_structure(0.08) + heat_seal_per_batch(0.05) = 0.35
    # ==================================================================
    weights = {
        # EASY tier (0.35 total)
        "page_component_exists": 0.08,
        "blood_info_keywords": 0.08,
        "device_info_keywords": 0.08,
        "batch_keywords": 0.06,
        "type_exists": 0.05,
        # MEDIUM tier (0.30 total)
        "ui_consistency": 0.10,
        "type_quality": 0.10,
        "routing_basic": 0.10,
        # HARD tier (0.35 total) — hidden discriminating checks
        "dual_panel_architecture": 0.12,
        "routing_dual_panel": 0.10,
        "mock_data_structure": 0.08,
        "heat_seal_per_batch": 0.05,
    }

    overall = sum(weights[k] * scores[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in scores.items()},
        "weights": weights,
        "tier_totals": {
            "easy_max": 0.35,
            "medium_max": 0.30,
            "hard_max": 0.35,
        },
    }


def main():
    ws = Path("/workspace/fixtures")
    if not ws.exists():
        ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
