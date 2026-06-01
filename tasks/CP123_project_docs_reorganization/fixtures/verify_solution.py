"""Hidden verifier for CP123 — Project Documentation Reorganization.

Checks that the agent properly reorganized scattered documentation files
into a clean directory structure with appropriate categorization.

Discrimination strategy (tiered):
- EASY TIER (30%): Straightforward file moves explicitly requested in the prompt.
  All competent agents should pass these. These serve as baseline confirmation.
- MEDIUM TIER (30%): Partially explicit but requires correct execution details
  (renaming correctly, archive semantics, README path correctness).
- HARD TIER (hidden, 40%): Subtle understanding checks that require deeper reasoning —
  understanding what NOT to move, updating cross-references correctly, preserving
  content integrity, inferring correct relative paths, maintaining directory semantics,
  using move (not copy), and not touching code files. Only strong agents pass these.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def grade_workspace(ws: Path) -> dict:
    """Grade the documentation reorganization."""
    base = ws / "messy-project"
    if not base.exists():
        # fallback: maybe files are directly in ws
        base = ws

    components = {k: 0.0 for k in [
        # --- EASY TIER: explicit moves (all agents should pass) ---
        "business_docs_grouped",
        "data_files_grouped",
        "design_docs_grouped",
        "archive_created",
        # --- MEDIUM TIER: correct execution details ---
        "design_docs_renamed",
        "code_design_relocated",
        "readme_updated",
        "readme_paths_valid",
        # --- HARD TIER (hidden): deeper understanding required ---
        "ops_manual_preserved",
        "cross_references_updated",
        "implementation_dir_preserved",
        "active_doc_not_archived",
        "naming_consistency",
        "content_integrity",
        "code_app_untouched",
        "no_orphan_originals",
    ]}

    # ===================================================================
    # EASY TIER: Explicitly requested file moves
    # ===================================================================

    # --- 1. Business requirement docs grouped together ---
    business_files = [
        "vendor_invoice_field_mapping.md",
        "cloud_vendor_billing.md",
        "partner_commission.md",
        "profit_report.md",
        "approval_ui_elements.md",
    ]
    found_in_subdir = 0
    business_dir = None
    for candidate_dir in ["docs/business", "docs/requirements", "docs/business-requirements",
                          "business", "requirements"]:
        d = base / candidate_dir
        if d.exists() and d.is_dir():
            for bf in business_files:
                if (d / bf).exists() or any(d.rglob(f"*{Path(bf).stem}*")):
                    found_in_subdir += 1
            if found_in_subdir >= 3:
                business_dir = d
                break
            found_in_subdir = 0

    still_in_root = sum(1 for bf in business_files if (base / bf).exists())
    if found_in_subdir >= 4:
        components["business_docs_grouped"] = min(1.0, found_in_subdir / 5.0)
    elif still_in_root <= 1 and found_in_subdir >= 3:
        components["business_docs_grouped"] = 0.7
    elif still_in_root <= 2:
        components["business_docs_grouped"] = 0.3

    # --- 2. Data files (CSV) grouped together ---
    data_files = [
        "aws_billing_2024_03.csv",
        "gcp_billing_export.csv",
        "azure_costs_march.csv",
        "commission_calc_march.csv",
        "profit_loss_2024_q1.csv",
        "partner_uploads_march.csv",
    ]
    data_in_root = sum(1 for df in data_files if (base / df).exists())
    data_in_subdir = 0
    data_dir = None
    for candidate_dir in ["docs/business/data", "data", "docs/data", "raw-data",
                          "docs/business-requirements/data", "business/data"]:
        d = base / candidate_dir
        if d.exists() and d.is_dir():
            count = sum(1 for df in data_files if (d / df).exists() or
                       any(f.name in data_files for f in d.iterdir() if f.is_file()))
            if count > data_in_subdir:
                data_in_subdir = count
                data_dir = d

    if data_in_subdir >= 5:
        components["data_files_grouped"] = 1.0
    elif data_in_subdir >= 3:
        components["data_files_grouped"] = 0.7
    elif data_in_root <= 2:
        components["data_files_grouped"] = 0.4
    else:
        components["data_files_grouped"] = 0.0

    # --- 3. Design docs grouped in design directory ---
    design_files_orig = [
        "draft2_fact_table_precompute.md",
        "draft2_e2e_pipeline_diagram.md",
        "draft2_e2e_pipeline_detailed.md",
        "draft2_layer_architecture.md",
        "draft2_layer_architecture_detailed.md",
        "draft2_technical_detailed.md",
        "draft2_requirements_detailed.md",
    ]
    design_in_orig = sum(1 for df in design_files_orig if (base / "docs" / df).exists())
    design_in_design_dir = 0
    design_dir = None
    for candidate_dir in ["docs/design", "design", "docs/architecture"]:
        d = base / candidate_dir
        if d.exists() and d.is_dir():
            md_files_count = sum(1 for f in d.iterdir() if f.is_file() and f.suffix == ".md")
            if md_files_count >= 5:
                design_in_design_dir = md_files_count
                design_dir = d
                break

    if design_in_design_dir >= 6:
        components["design_docs_grouped"] = 1.0
    elif design_in_design_dir >= 4:
        components["design_docs_grouped"] = 0.7
    elif design_in_orig < 7:
        components["design_docs_grouped"] = 0.3

    # --- 4. Archive directory created for historical files ---
    archive_exists = False
    original_archived = False
    for candidate_dir in ["docs/archive", "archive", "docs/history"]:
        d = base / candidate_dir
        if d.exists() and d.is_dir():
            archive_exists = True
            for f in d.rglob("*"):
                if "original" in f.name.lower() or "background_original" in f.name.lower():
                    original_archived = True
                    break
            break

    if archive_exists and original_archived:
        components["archive_created"] = 1.0
    elif archive_exists:
        components["archive_created"] = 0.6
    elif not (base / "project_background_original.md").exists():
        components["archive_created"] = 0.3

    # ===================================================================
    # MEDIUM TIER: Correct execution details
    # ===================================================================

    # --- 5. Design docs renamed (removed draft2_ prefix) ---
    if design_dir and design_dir.exists():
        renamed_count = 0
        for f in design_dir.iterdir():
            if f.is_file() and f.suffix == ".md":
                if not f.name.startswith("draft2_"):
                    renamed_count += 1
        if renamed_count >= 5:
            components["design_docs_renamed"] = 1.0
        elif renamed_count >= 3:
            components["design_docs_renamed"] = 0.6
        elif renamed_count >= 1:
            components["design_docs_renamed"] = 0.3
    else:
        for candidate_dir in ["docs/design", "design", "docs/architecture", "docs"]:
            d = base / candidate_dir
            if d.exists():
                renamed = sum(1 for f in d.iterdir()
                             if f.is_file() and f.suffix == ".md"
                             and not f.name.startswith("draft2_"))
                if renamed >= 3:
                    components["design_docs_renamed"] = 0.5
                    break

    # --- 6. code/docs design file relocated to docs/design ---
    code_docs_dir = base / "code" / "docs"
    billing_sync_in_code = (code_docs_dir / "billing_sync_approval_dependency.md").exists()
    billing_sync_relocated = False
    for candidate_dir in ["docs/design", "design", "docs/architecture"]:
        d = base / candidate_dir
        if d.exists():
            for f in d.rglob("*"):
                if "billing_sync" in f.name.lower() or "approval_dependency" in f.name.lower():
                    billing_sync_relocated = True
                    break
        if billing_sync_relocated:
            break

    if billing_sync_relocated and not billing_sync_in_code:
        components["code_design_relocated"] = 1.0
    elif billing_sync_relocated:
        components["code_design_relocated"] = 0.7
    elif not billing_sync_in_code:
        components["code_design_relocated"] = 0.5

    # --- 7. README.md updated with new paths ---
    readme = base / "README.md"
    readme_content = ""
    if readme.exists():
        readme_content = readme.read_text(encoding="utf-8", errors="ignore")
        has_new_paths = any(p in readme_content for p in [
            "docs/business", "docs/design", "docs/archive",
            "business/", "design/", "archive/",
            "requirements/", "architecture/"
        ])
        has_old_paths = any(p in readme_content for p in [
            "./vendor_invoice_field_mapping.md",
            "./cloud_vendor_billing.md",
            "./partner_commission.md",
            "draft2_technical_detailed"
        ])
        if has_new_paths and not has_old_paths:
            components["readme_updated"] = 1.0
        elif has_new_paths:
            components["readme_updated"] = 0.6
        elif not has_old_paths:
            components["readme_updated"] = 0.4

    # --- 8. README paths actually resolve to existing files ---
    # A strong agent updates paths AND ensures they point to real files.
    # A weak agent might update paths but get them wrong (wrong subdirectory name).
    if readme.exists() and readme_content:
        # Extract markdown links from README
        link_pattern = re.compile(r'\[.*?\]\((\./[^)]+|[^)]+\.md[^)]*|[^)]+\.csv[^)]*)\)')
        links_found = link_pattern.findall(readme_content)
        if links_found:
            valid_links = 0
            for link in links_found:
                # Resolve relative to base
                link_clean = link.lstrip("./")
                target = base / link_clean
                if target.exists():
                    valid_links += 1
            link_validity = valid_links / len(links_found) if links_found else 0.0
            components["readme_paths_valid"] = round(link_validity, 4)
        else:
            # No links found — if README was rewritten without links, partial credit
            if has_new_paths:
                components["readme_paths_valid"] = 0.5
            else:
                components["readme_paths_valid"] = 0.0
    else:
        components["readme_paths_valid"] = 0.0

    # ===================================================================
    # HARD TIER (hidden): Deeper understanding required
    # Only strong agents pass these consistently.
    # ===================================================================

    # --- 9. Ops manual preserved in code/docs (NOT moved to design) ---
    # The data_ingestion_ops_manual.md is operational documentation that belongs
    # with the code. Only the design-related billing_sync file should be moved.
    # A weak agent might move ALL files from code/docs/ to the design directory.
    ops_manual_in_code = (code_docs_dir / "data_ingestion_ops_manual.md").exists()
    ops_manual_in_design = False
    if design_dir and design_dir.exists():
        ops_manual_in_design = any(
            "ops_manual" in f.name.lower() or "data_ingestion" in f.name.lower()
            for f in design_dir.rglob("*") if f.is_file()
        )
    # Also check other design-like directories
    for candidate_dir in ["docs/design", "design", "docs/architecture"]:
        d = base / candidate_dir
        if d.exists():
            if any("ops_manual" in f.name.lower() or "data_ingestion" in f.name.lower()
                   for f in d.rglob("*") if f.is_file()):
                ops_manual_in_design = True

    if ops_manual_in_code and not ops_manual_in_design:
        components["ops_manual_preserved"] = 1.0
    elif ops_manual_in_code:
        # It's still in code/docs but also copied to design (not ideal but acceptable)
        components["ops_manual_preserved"] = 0.5
    elif not ops_manual_in_design:
        # Moved somewhere else but not design — partial credit
        components["ops_manual_preserved"] = 0.3
    else:
        # Incorrectly moved to design directory
        components["ops_manual_preserved"] = 0.0

    # --- 10. Cross-references updated in project_background.md ---
    # project_background.md has relative links to business docs that would break
    # after reorganization. A strong agent updates these references too.
    bg_file = base / "project_background.md"
    if bg_file.exists():
        bg_content = bg_file.read_text(encoding="utf-8", errors="ignore")
        # Original has links like ./vendor_invoice_field_mapping.md
        has_old_refs = any(p in bg_content for p in [
            "./vendor_invoice_field_mapping.md",
            "./cloud_vendor_billing.md",
            "./partner_commission.md",
            "./profit_report.md",
            "./approval_ui_elements.md",
        ])
        # Check if references were updated to new paths
        has_new_refs = any(p in bg_content for p in [
            "docs/business/", "business/", "docs/requirements/",
        ])
        # Also check if links use the correct relative paths from root
        has_correct_relative = False
        if business_dir:
            rel_path = str(business_dir.relative_to(base))
            if rel_path in bg_content:
                has_correct_relative = True

        # Additionally: verify the updated links actually resolve
        bg_links = re.findall(r'\[.*?\]\((\./[^)]+|[^)]+\.md[^)]*)\)', bg_content)
        bg_links_valid = 0
        for link in bg_links:
            link_clean = link.lstrip("./")
            if (base / link_clean).exists():
                bg_links_valid += 1

        if has_new_refs and not has_old_refs and bg_links_valid >= 3:
            components["cross_references_updated"] = 1.0
        elif has_new_refs and not has_old_refs:
            components["cross_references_updated"] = 0.8
        elif has_correct_relative:
            components["cross_references_updated"] = 0.7
        elif not has_old_refs:
            # Links removed or updated in some way
            components["cross_references_updated"] = 0.4
        else:
            # Links still point to old (now broken) paths
            components["cross_references_updated"] = 0.0
    else:
        # If project_background.md was removed/moved — 0
        components["cross_references_updated"] = 0.0

    # --- 11. Implementation directory preserved ---
    # docs/implementation/README.md should stay in place. It's not a design doc
    # or a draft — it's an implementation-specific directory. Weak agents might
    # flatten it or move it incorrectly.
    impl_readme = base / "docs" / "implementation" / "README.md"
    if impl_readme.exists():
        components["implementation_dir_preserved"] = 1.0
    else:
        # Check if it was moved to some reasonable place
        alt_paths = [
            base / "docs" / "implementation.md",
            base / "implementation" / "README.md",
        ]
        if any(p.exists() for p in alt_paths):
            components["implementation_dir_preserved"] = 0.4
        else:
            components["implementation_dir_preserved"] = 0.0

    # --- 12. Active project_background.md NOT archived ---
    # The task says to archive project_background_ORIGINAL.md (historical).
    # project_background.md is the ACTIVE reference and should stay in root.
    # A weak agent might archive both, or move the active doc.
    active_bg_in_root = (base / "project_background.md").exists()
    active_bg_archived = False
    for candidate_dir in ["docs/archive", "archive", "docs/history"]:
        d = base / candidate_dir
        if d.exists():
            # Check if the active (non-original) background was incorrectly archived
            for f in d.rglob("*"):
                # Only flag if it's the non-original version
                if f.name == "project_background.md":
                    active_bg_archived = True
                    break
        if active_bg_archived:
            break

    if active_bg_in_root and not active_bg_archived:
        components["active_doc_not_archived"] = 1.0
    elif active_bg_in_root:
        # Still in root but also (incorrectly) copied to archive
        components["active_doc_not_archived"] = 0.5
    elif not active_bg_archived:
        # Moved somewhere else but at least not to archive
        components["active_doc_not_archived"] = 0.4
    else:
        # Active doc was archived — clear mistake
        components["active_doc_not_archived"] = 0.0

    # --- 13. Naming consistency in design files ---
    # After renaming draft2_* files, all design files should follow a consistent
    # naming convention (all underscores or all hyphens, no mixing).
    # Strong agents maintain consistency; weak ones just strip the prefix mechanically.
    if design_dir and design_dir.exists():
        design_file_names = [f.stem for f in design_dir.iterdir()
                            if f.is_file() and f.suffix == ".md"]
        if len(design_file_names) >= 4:
            has_underscores = any("_" in name for name in design_file_names)
            has_hyphens = any("-" in name for name in design_file_names)
            # Check if naming is consistent (all use same separator)
            if has_underscores and not has_hyphens:
                components["naming_consistency"] = 1.0
            elif has_hyphens and not has_underscores:
                components["naming_consistency"] = 1.0
            elif has_underscores and has_hyphens:
                # Mixed naming — weak consistency
                # Count which is dominant
                underscore_count = sum(1 for n in design_file_names if "_" in n)
                hyphen_count = sum(1 for n in design_file_names if "-" in n)
                dominant_ratio = max(underscore_count, hyphen_count) / len(design_file_names)
                if dominant_ratio >= 0.8:
                    # Mostly consistent with minor exceptions (e.g., billing_sync has _)
                    components["naming_consistency"] = 0.7
                else:
                    components["naming_consistency"] = 0.3
            else:
                # Single-word files — trivially consistent
                components["naming_consistency"] = 1.0
        else:
            # Not enough files to judge
            components["naming_consistency"] = 0.5

    # --- 14. Content integrity after moves ---
    # Verify that moved files still contain their expected content (not truncated,
    # not empty, not swapped). A weak agent might accidentally overwrite or create
    # empty placeholder files instead of actually moving them.
    content_checks_passed = 0
    content_checks_total = 0

    # Check business docs contain expected keywords
    biz_content_markers = {
        "vendor_invoice_field_mapping.md": ["invoice", "field", "mapping"],
        "cloud_vendor_billing.md": ["billing", "cloud", "vendor"],
        "partner_commission.md": ["commission", "partner"],
    }
    for filename, markers in biz_content_markers.items():
        content_checks_total += 1
        # Search in business_dir or anywhere under base
        found_file = None
        if business_dir and (business_dir / filename).exists():
            found_file = business_dir / filename
        else:
            hits = list(base.rglob(filename))
            if hits:
                found_file = hits[0]
        if found_file and found_file.exists():
            try:
                content = found_file.read_text(encoding="utf-8", errors="ignore").lower()
                if len(content) > 50 and all(m in content for m in markers):
                    content_checks_passed += 1
            except Exception:
                pass

    # Check design docs contain expected content (not empty stubs)
    design_content_markers = {
        "technical_detailed.md": ["technical", "design"],
        "layer_architecture.md": ["layer", "architecture"],
        "e2e_pipeline_diagram.md": ["pipeline", "e2e"],
    }
    for filename, markers in design_content_markers.items():
        content_checks_total += 1
        found_file = None
        if design_dir:
            # Could be renamed (without draft2_ prefix)
            candidates = list(design_dir.rglob(f"*{Path(filename).stem}*"))
            if candidates:
                found_file = candidates[0]
        if not found_file:
            hits = list(base.rglob(f"*{Path(filename).stem}*"))
            if hits:
                found_file = hits[0]
        if found_file and found_file.exists():
            try:
                content = found_file.read_text(encoding="utf-8", errors="ignore").lower()
                if len(content) > 50 and any(m in content for m in markers):
                    content_checks_passed += 1
            except Exception:
                pass

    if content_checks_total > 0:
        components["content_integrity"] = round(
            content_checks_passed / content_checks_total, 4
        )

    # --- 15. code/app/ directory untouched ---
    # The reorganization is about DOCUMENTATION only. The code directory structure
    # (code/app/__init__.py) must remain intact. A weak agent might accidentally
    # move or delete code files while reorganizing.
    code_app_init = base / "code" / "app" / "__init__.py"
    if code_app_init.exists():
        components["code_app_untouched"] = 1.0
    else:
        # Check if code/app/ still exists at all
        if (base / "code" / "app").exists():
            components["code_app_untouched"] = 0.5
        elif (base / "code").exists():
            components["code_app_untouched"] = 0.3
        else:
            # Entire code directory was removed or moved — serious error
            components["code_app_untouched"] = 0.0

    # --- 16. No orphan originals left behind ---
    # After moving files, there should be no duplicates left in original locations.
    # A weak agent might COPY instead of MOVE, leaving originals behind.
    # Check that business docs are NOT still in root if they were successfully grouped.
    orphan_score = 1.0
    if components["business_docs_grouped"] >= 0.7:
        # Business docs should have been moved, not copied
        orphans_in_root = sum(1 for bf in business_files if (base / bf).exists())
        if orphans_in_root >= 4:
            orphan_score = 0.0  # Clearly copied, not moved
        elif orphans_in_root >= 2:
            orphan_score = 0.3
        elif orphans_in_root == 1:
            orphan_score = 0.7

    if components["data_files_grouped"] >= 0.7:
        # CSV files should not remain in root
        csv_orphans = sum(1 for df in data_files if (base / df).exists())
        if csv_orphans >= 4:
            orphan_score = min(orphan_score, 0.0)
        elif csv_orphans >= 2:
            orphan_score = min(orphan_score, 0.3)

    if components["design_docs_grouped"] >= 0.7:
        # draft2_* files should not remain in docs/
        draft_orphans = sum(1 for df in design_files_orig if (base / "docs" / df).exists())
        if draft_orphans >= 5:
            orphan_score = min(orphan_score, 0.0)
        elif draft_orphans >= 3:
            orphan_score = min(orphan_score, 0.3)

    components["no_orphan_originals"] = orphan_score

    # ===================================================================
    # SCORING — Tiered weights
    #   Easy tier:   30% (all agents should score well here)
    #   Medium tier: 30% (requires correct execution)
    #   Hard tier:   40% (hidden, only strong agents pass)
    # Hidden checks (hard tier) = 40% >= 30% requirement met.
    # ===================================================================
    weights = {
        # EASY TIER (30%): explicit moves, high pass rate expected
        "business_docs_grouped": 0.09,
        "data_files_grouped": 0.08,
        "design_docs_grouped": 0.08,
        "archive_created": 0.05,
        # MEDIUM TIER (30%): correct execution details
        "design_docs_renamed": 0.08,
        "code_design_relocated": 0.06,
        "readme_updated": 0.05,
        "readme_paths_valid": 0.06,
        "naming_consistency": 0.05,
        # HARD TIER (40%): hidden discrimination checks — only strong agents pass
        "ops_manual_preserved": 0.07,
        "cross_references_updated": 0.08,
        "implementation_dir_preserved": 0.05,
        "active_doc_not_archived": 0.06,
        "content_integrity": 0.05,
        "code_app_untouched": 0.05,
        "no_orphan_originals": 0.04,
    }
    # Verify weights sum to ~1.0
    assert abs(sum(weights.values()) - 1.0) < 0.01, f"Weights sum to {sum(weights.values())}"

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "tier_scores": {
            "easy": round(sum(weights[k] * components[k] for k in [
                "business_docs_grouped", "data_files_grouped",
                "design_docs_grouped", "archive_created"
            ]) / sum(weights[k] for k in [
                "business_docs_grouped", "data_files_grouped",
                "design_docs_grouped", "archive_created"
            ]), 4),
            "medium": round(sum(weights[k] * components[k] for k in [
                "design_docs_renamed", "code_design_relocated",
                "readme_updated", "readme_paths_valid", "naming_consistency"
            ]) / sum(weights[k] for k in [
                "design_docs_renamed", "code_design_relocated",
                "readme_updated", "readme_paths_valid", "naming_consistency"
            ]), 4),
            "hard": round(sum(weights[k] * components[k] for k in [
                "ops_manual_preserved", "cross_references_updated",
                "implementation_dir_preserved", "active_doc_not_archived",
                "content_integrity", "code_app_untouched", "no_orphan_originals"
            ]) / sum(weights[k] for k in [
                "ops_manual_preserved", "cross_references_updated",
                "implementation_dir_preserved", "active_doc_not_archived",
                "content_integrity", "code_app_untouched", "no_orphan_originals"
            ]), 4),
        },
    }


def main():
    # Try /workspace/fixtures/messy-project first, then /workspace/messy-project, then /workspace
    ws = Path("/workspace/fixtures/messy-project")
    if not ws.exists():
        ws = Path("/workspace/messy-project")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
