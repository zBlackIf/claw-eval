"""Hidden verifier for CP153 — Vue Dead Code Removal by Routes."""
from __future__ import annotations

import json
import os
from pathlib import Path


def _exists(p: Path) -> bool:
    return p.exists()


def _dir_exists(p: Path) -> bool:
    return p.exists() and p.is_dir()


def _file_contains(p: Path, text: str) -> bool:
    try:
        return text in p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


def grade_workspace(ws: Path) -> dict:
    """Grade the dead code removal task.

    Active modules (from asyncRoutes.ts): order, product, settings
    Dead modules (old project): inventory, logistics, report, crm
    """
    # Try multiple possible base paths
    app_dir = ws / "fixtures" / "frontend-app"
    if not app_dir.exists():
        app_dir = ws / "frontend-app"
    if not app_dir.exists():
        # fallback: maybe they moved things around
        app_dir = ws

    src = app_dir / "src"

    components = {k: 0.0 for k in [
        "dead_views_removed",
        "dead_api_removed",
        "dead_models_removed",
        "dead_stores_removed",
        "dead_enums_removed",
        "dead_mocks_removed",
        "barrel_files_updated",
        "active_pages_preserved",
        "dead_components_removed",
    ]}

    # --- Dimension 1: Dead views removed ---
    dead_view_dirs = ["inventory", "logistics", "report", "crm"]
    dead_views_removed_count = 0
    for d in dead_view_dirs:
        view_path = src / "views" / d
        if not _dir_exists(view_path):
            dead_views_removed_count += 1
    components["dead_views_removed"] = dead_views_removed_count / len(dead_view_dirs)

    # --- Dimension 2: Dead API modules removed ---
    dead_api_dirs = ["inventory", "logistics", "report", "crm"]
    dead_api_removed_count = 0
    for d in dead_api_dirs:
        api_path = src / "api" / d
        if not _dir_exists(api_path):
            dead_api_removed_count += 1
    components["dead_api_removed"] = dead_api_removed_count / len(dead_api_dirs)

    # --- Dimension 3: Dead models removed ---
    dead_model_dirs = ["inventory", "logistics", "report", "crm"]
    dead_models_removed_count = 0
    for d in dead_model_dirs:
        model_path = src / "models" / d
        if not _dir_exists(model_path):
            dead_models_removed_count += 1
    components["dead_models_removed"] = dead_models_removed_count / len(dead_model_dirs)

    # --- Dimension 4: Dead store modules removed ---
    dead_store_files = ["inventory.ts", "logistics.ts", "report.ts", "crm.ts"]
    dead_stores_removed_count = 0
    for f in dead_store_files:
        store_path = src / "store" / "modules" / f
        if not _exists(store_path):
            dead_stores_removed_count += 1
    components["dead_stores_removed"] = dead_stores_removed_count / len(dead_store_files)

    # --- Dimension 5: Dead enums removed ---
    dead_enum_files = ["inventory.ts", "logistics.ts", "crm.ts"]
    dead_enums_removed_count = 0
    for f in dead_enum_files:
        enum_path = src / "enums" / f
        if not _exists(enum_path):
            dead_enums_removed_count += 1
    components["dead_enums_removed"] = dead_enums_removed_count / len(dead_enum_files)

    # --- Dimension 6: Dead mock files removed ---
    dead_mock_files = ["inventory.ts", "logistics.ts", "crm.ts", "report.ts"]
    mock_dir = app_dir / "mock"
    dead_mocks_removed_count = 0
    for f in dead_mock_files:
        mock_path = mock_dir / f
        if not _exists(mock_path):
            dead_mocks_removed_count += 1
    components["dead_mocks_removed"] = dead_mocks_removed_count / len(dead_mock_files)

    # --- Dimension 7: Barrel (index.ts) files updated ---
    # Check that barrel files no longer re-export dead modules
    barrel_score = 0.0
    barrel_checks = 0
    barrel_total = 0

    # api/index.ts
    api_index = src / "api" / "index.ts"
    if _exists(api_index):
        barrel_total += 4
        for dead in ["inventory", "logistics", "report", "crm"]:
            if not _file_contains(api_index, f'"{dead}"') and not _file_contains(api_index, f"'{dead}'") and not _file_contains(api_index, f"./{dead}"):
                barrel_checks += 1
    else:
        # If file was removed entirely, partial credit (it should still exist for active modules)
        barrel_total += 4

    # models/index.ts
    models_index = src / "models" / "index.ts"
    if _exists(models_index):
        barrel_total += 4
        for dead in ["inventory", "logistics", "report", "crm"]:
            if not _file_contains(models_index, f'"{dead}"') and not _file_contains(models_index, f"'{dead}'") and not _file_contains(models_index, f"./{dead}"):
                barrel_checks += 1
    else:
        barrel_total += 4

    # store/modules/index.ts
    store_index = src / "store" / "modules" / "index.ts"
    if _exists(store_index):
        barrel_total += 4
        for dead in ["Inventory", "Logistics", "Report", "Crm"]:
            content = ""
            try:
                content = store_index.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
            dead_lower = dead.lower()
            if dead_lower not in content.lower() or (f"use{dead}Store" not in content and f"./{dead_lower}" not in content):
                barrel_checks += 1
    else:
        barrel_total += 4

    # enums/index.ts
    enums_index = src / "enums" / "index.ts"
    if _exists(enums_index):
        barrel_total += 3
        for dead in ["inventory", "logistics", "crm"]:
            if not _file_contains(enums_index, f'"{dead}"') and not _file_contains(enums_index, f"'{dead}'") and not _file_contains(enums_index, f"./{dead}"):
                barrel_checks += 1
    else:
        barrel_total += 3

    components["barrel_files_updated"] = barrel_checks / barrel_total if barrel_total > 0 else 0.0

    # --- Dimension 8: Active pages preserved (critical - must NOT break active routes) ---
    active_views = [
        "order/order-list/index.vue",
        "order/order-detail/index.vue",
        "product/catalog/index.vue",
        "product/pricing/index.vue",
        "settings/user/index.vue",
        "settings/role/index.vue",
    ]
    active_apis = ["order/index.ts", "product/index.ts", "settings/index.ts"]
    active_models = ["order/index.ts", "product/index.ts", "settings/index.ts"]
    active_stores = ["order.ts", "product.ts", "settings.ts"]
    active_enums = ["order.ts", "product.ts"]

    preserved_count = 0
    total_active = 0

    for v in active_views:
        total_active += 1
        if _exists(src / "views" / v):
            preserved_count += 1

    for a in active_apis:
        total_active += 1
        if _exists(src / "api" / a):
            preserved_count += 1

    for m in active_models:
        total_active += 1
        if _exists(src / "models" / m):
            preserved_count += 1

    for s in active_stores:
        total_active += 1
        if _exists(src / "store" / "modules" / s):
            preserved_count += 1

    for e in active_enums:
        total_active += 1
        if _exists(src / "enums" / e):
            preserved_count += 1

    components["active_pages_preserved"] = preserved_count / total_active if total_active > 0 else 0.0

    # --- Dimension 9 (hidden/bonus): Dead-only components removed ---
    # warehouse-select and customer-card are only used by dead pages
    dead_components = ["warehouse-select", "customer-card", "chart-panel"]
    dead_comp_removed = 0
    for c in dead_components:
        comp_path = src / "components" / c
        if not _dir_exists(comp_path):
            dead_comp_removed += 1
    components["dead_components_removed"] = dead_comp_removed / len(dead_components)

    # --- Weights ---
    weights = {
        "dead_views_removed": 0.18,
        "dead_api_removed": 0.15,
        "dead_models_removed": 0.12,
        "dead_stores_removed": 0.10,
        "dead_enums_removed": 0.08,
        "dead_mocks_removed": 0.07,
        "barrel_files_updated": 0.12,
        "active_pages_preserved": 0.10,
        "dead_components_removed": 0.08,
    }

    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try workspace root first, then fixtures subdir
    ws = Path("/workspace")
    if not (ws / "fixtures" / "frontend-app" / "src").exists() and not (ws / "frontend-app" / "src").exists():
        # Maybe files are directly in /workspace
        pass
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
