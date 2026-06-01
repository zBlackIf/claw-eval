"""Hidden verifier for CP156 — Obsidian Plugin Remove Auto Backup Feature."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    """Grade the removal of auto-backup feature from yh-inklight plugin.

    Checks 5 basic dimensions + 7 hidden quality dimensions:
    Basic:
    1. main.ts: lastBackupAt field removed
    2. main.ts: registerAutomaticBackups + runScheduledBackup methods removed
    3. annotationStore.ts: BACKUP_DIR constant + backupDocuments method + backupTimestamp function removed
    4. types.ts: backupFrequencyMinutes removed from interface AND default settings
    5. settingsTab.ts: backup frequency slider UI removed

    Hidden (quality/completeness):
    6. Dead import/reference cleanup: no leftover 'backup' string references in imports or comments
    7. Store module cleanup: ensureDir(BACKUP_DIR) call removed, no orphaned backup-related helpers
    8. File header consistency: file headers updated to no longer mention backup
    9. Formatting cleanliness: no triple blank lines or awkward gaps at removal sites
    10. No commented-out backup code: code is deleted not commented out
    11. Module-level function removal: standalone backupTimestamp() at module scope removed
    12. Settings count integrity: interface has exactly 8 fields, DEFAULT_SETTINGS has 8 keys
    """
    # Locate files - check both fixture dir and workspace root
    base = ws / "yh-inklight"
    if not base.exists():
        base = ws / "fixtures" / "yh-inklight"
    if not base.exists():
        return {"overall_score": 0.0, "components": {}, "error": "yh-inklight directory not found"}

    main_ts = base / "main.ts"
    annotation_store = base / "src" / "storage" / "annotationStore.ts"
    types_ts = base / "src" / "storage" / "types.ts"
    settings_tab = base / "src" / "settings" / "settingsTab.ts"

    components = {
        "main_backup_field_removed": 0.0,
        "main_backup_methods_removed": 0.0,
        "store_backup_code_removed": 0.0,
        "types_backup_setting_removed": 0.0,
        "settings_backup_ui_removed": 0.0,
        "dead_reference_cleanup": 0.0,
        "store_orphan_cleanup": 0.0,
        "header_consistency": 0.0,
        "formatting_cleanliness": 0.0,
        "no_commented_backup_code": 0.0,
        "module_fn_removal": 0.0,
        "settings_count_integrity": 0.0,
    }

    # --- Check main.ts ---
    main_content = _read(main_ts)
    if main_content:
        # Check lastBackupAt field removed
        has_last_backup_field = "lastBackupAt" in main_content
        components["main_backup_field_removed"] = 0.0 if has_last_backup_field else 1.0

        # Check registerAutomaticBackups and runScheduledBackup removed
        has_register_backups = "registerAutomaticBackups" in main_content
        has_run_backup = "runScheduledBackup" in main_content
        has_backup_call = "this.store.backupDocuments" in main_content or "backupDocuments()" in main_content

        if not has_register_backups and not has_run_backup and not has_backup_call:
            components["main_backup_methods_removed"] = 1.0
        elif not has_register_backups and not has_run_backup:
            components["main_backup_methods_removed"] = 0.8
        elif not has_register_backups or not has_run_backup:
            components["main_backup_methods_removed"] = 0.4
        else:
            components["main_backup_methods_removed"] = 0.0

        # Verify the rest of main.ts still works (not overly deleted)
        if "onload" not in main_content or "registerCommands" not in main_content:
            # Penalize if essential functionality was broken
            components["main_backup_methods_removed"] = max(0.0, components["main_backup_methods_removed"] - 0.3)

    # --- Check annotationStore.ts ---
    store_content = _read(annotation_store)
    if store_content:
        has_backup_dir = "BACKUP_DIR" in store_content
        has_backup_documents = "backupDocuments" in store_content
        has_backup_timestamp = "backupTimestamp" in store_content

        removed_count = sum([
            not has_backup_dir,
            not has_backup_documents,
            not has_backup_timestamp,
        ])
        components["store_backup_code_removed"] = removed_count / 3.0

        # Verify store still has essential methods (not broken)
        if "saveDocument" not in store_content or "loadDocument" not in store_content:
            components["store_backup_code_removed"] = max(0.0, components["store_backup_code_removed"] - 0.3)

    # --- Check types.ts ---
    types_content = _read(types_ts)
    if types_content:
        has_backup_freq_interface = bool(re.search(r"backupFrequencyMinutes\s*:", types_content))
        # Check in DEFAULT_SETTINGS
        has_backup_freq_default = bool(re.search(r"backupFrequencyMinutes\s*:\s*\d+", types_content))

        if not has_backup_freq_interface and not has_backup_freq_default:
            components["types_backup_setting_removed"] = 1.0
        elif not has_backup_freq_interface or not has_backup_freq_default:
            components["types_backup_setting_removed"] = 0.5
        else:
            components["types_backup_setting_removed"] = 0.0

        # Verify other settings still exist
        if "defaultHighlightColor" not in types_content or "migrateOnRename" not in types_content:
            components["types_backup_setting_removed"] = max(0.0, components["types_backup_setting_removed"] - 0.3)

    # --- Check settingsTab.ts ---
    settings_content = _read(settings_tab)
    if settings_content:
        has_backup_freq_ui = "backupFrequencyMinutes" in settings_content
        has_backup_name = "数据备份频率" in settings_content or "备份" in settings_content

        if not has_backup_freq_ui and not has_backup_name:
            components["settings_backup_ui_removed"] = 1.0
        elif not has_backup_freq_ui:
            components["settings_backup_ui_removed"] = 0.8
        else:
            components["settings_backup_ui_removed"] = 0.0

        # Verify other settings UI still present
        if "默认高亮颜色" not in settings_content or "重命名时迁移批注" not in settings_content:
            components["settings_backup_ui_removed"] = max(0.0, components["settings_backup_ui_removed"] - 0.3)

    # --- HIDDEN CHECKS (gated: only apply if basic removal is mostly done) ---
    # These checks only matter if the model actually attempted the removal.
    # A model that didn't touch the files gets 0 on these (not free points).
    basic_score = (
        components["main_backup_field_removed"] * 0.08
        + components["main_backup_methods_removed"] * 0.15
        + components["store_backup_code_removed"] * 0.15
        + components["types_backup_setting_removed"] * 0.12
        + components["settings_backup_ui_removed"] * 0.10
    )
    basic_threshold = 0.40  # At least ~67% of basic checks must pass

    if basic_score >= basic_threshold and main_content and store_content and settings_content:
        # --- HIDDEN CHECK 1: Dead reference cleanup ---
        # After removing backup feature, there should be no leftover "backup" references
        # in comments, console.log strings, or variable names across all files.
        # A strong model would do a thorough sweep removing ALL traces.
        dead_ref_penalties = 0
        total_dead_ref_checks = 6

        # Check if the word "backup" still appears ANYWHERE in main.ts (case-insensitive)
        # after proper removal, zero occurrences expected
        if re.search(r'[Bb]ackup', main_content):
            dead_ref_penalties += 1

        # Check annotationStore.ts for ANY leftover backup reference
        # (the entire backupDocuments method, BACKUP_DIR const, backupTimestamp func
        #  should all be gone — but also comments mentioning backup)
        if re.search(r'[Bb]ackup', store_content):
            dead_ref_penalties += 1

        # Check settingsTab.ts - no backup-related strings should remain (even in headers)
        if re.search(r'[Bb]ackup', settings_content):
            dead_ref_penalties += 1

        # Check types.ts - no backup-related strings should remain
        if re.search(r'[Bb]ackup', types_content):
            dead_ref_penalties += 1

        # Check main.ts for orphaned interval constant (60_000 was only for backup)
        # After removing registerAutomaticBackups, no 60_000 setInterval should remain
        if re.search(r'60[_,]?000', main_content) and "setInterval" in main_content:
            dead_ref_penalties += 1

        # Check annotationStore.ts: after removal, the file should not have
        # excessive consecutive blank lines (3+) suggesting incomplete cleanup
        if re.search(r'\n\n\n\n', store_content):
            dead_ref_penalties += 1

        components["dead_reference_cleanup"] = max(0.0, 1.0 - (dead_ref_penalties / total_dead_ref_checks))

        # --- HIDDEN CHECK 2: Store orphan cleanup ---
        # After removing backupDocuments + backupTimestamp + BACKUP_DIR:
        # - The 'backups' string literal should be gone
        # - No orphan ensureDir calls referencing backup paths
        # - The store should not export or expose backup-related symbols
        orphan_score = 1.0

        # Check if "backups" directory path string still exists anywhere
        if "backups" in store_content:
            orphan_score -= 0.4

        # Check for orphaned ensureDir calls that served backup
        ensure_dir_calls = re.findall(r'ensureDir\([^)]+\)', store_content)
        for call in ensure_dir_calls:
            if "backup" in call.lower() or "BACKUP" in call:
                orphan_score -= 0.3

        # The normalizePath import was used for BACKUP_DIR — check if
        # there are now-unused normalizePath calls for backup paths
        if re.search(r'normalizePath\([^)]*backup', store_content, re.IGNORECASE):
            orphan_score -= 0.3

        components["store_orphan_cleanup"] = max(0.0, orphan_score)

        # --- HIDDEN CHECK 3: File header consistency ---
        # The settingsTab.ts header [OUTPUT] line explicitly mentions "backup".
        # A strong model would update these headers to reflect the removed feature.
        # The PROTOCOL line says "Update this header on changes".
        header_score = 1.0

        # settingsTab.ts header mentions "backup" in the [OUTPUT] line
        settings_header_match = re.search(r'/\*\*.*?\*/', settings_content, re.DOTALL)
        if settings_header_match:
            header_text = settings_header_match.group(0)
            if "backup" in header_text.lower():
                header_score -= 0.5

        # main.ts header - if it mentions backup anywhere in header block
        main_header_match = re.search(r'/\*\*.*?\*/', main_content, re.DOTALL)
        if main_header_match:
            header_text = main_header_match.group(0)
            if "backup" in header_text.lower():
                header_score -= 0.5

        components["header_consistency"] = max(0.0, header_score)

        # --- HIDDEN CHECK 4: Formatting cleanliness ---
        # After removal, the code should not have excessive blank lines or
        # trailing whitespace at the removal sites. A strong model produces
        # clean diffs without leftover formatting artifacts.
        format_score = 1.0

        # main.ts: no triple+ blank lines (indicates sloppy removal)
        if re.search(r'\n\n\n', main_content):
            format_score -= 0.25

        # annotationStore.ts: no triple+ blank lines
        if re.search(r'\n\n\n', store_content):
            format_score -= 0.25

        # main.ts: after removing registerAutomaticBackups call from onload,
        # the surrounding code should flow naturally (store.initialize -> registerView)
        # Check there's no awkward double blank between them
        onload_section = re.search(r'await this\.store\.initialize\(\);(.*?)this\.registerView', main_content, re.DOTALL)
        if onload_section:
            between = onload_section.group(1)
            if between.count('\n') > 2:
                format_score -= 0.25

        # settingsTab.ts: no triple+ blank lines
        if re.search(r'\n\n\n', settings_content):
            format_score -= 0.25

        components["formatting_cleanliness"] = max(0.0, format_score)

        # --- HIDDEN CHECK 5: No commented-out backup code ---
        # A strong model DELETES backup code entirely. Weak models often comment
        # it out (// this.registerAutomaticBackups(), /* backup */, etc.) or leave
        # TODO/FIXME comments referencing backup. This check catches that pattern.
        commented_score = 1.0
        total_comment_penalties = 0

        # Check all files for commented-out backup references
        all_files_content = [
            ("main.ts", main_content),
            ("annotationStore.ts", store_content),
            ("settingsTab.ts", settings_content),
            ("types.ts", types_content),
        ]
        for fname, content in all_files_content:
            # Single-line comments containing backup keywords
            commented_backup = re.findall(
                r'//.*[Bb]ackup|//.*BACKUP_DIR|//.*backupFrequency|//.*backupDocuments|//.*backupTimestamp|//.*lastBackupAt',
                content
            )
            total_comment_penalties += len(commented_backup)

            # Multi-line comments containing backup keywords
            block_comments = re.findall(r'/\*(?!\*).*?[Bb]ackup.*?\*/', content, re.DOTALL)
            # Exclude the file header (first /** ... */) from this check
            if block_comments and fname in ("main.ts", "settingsTab.ts"):
                # The header is already checked separately; skip the first block comment
                block_comments = block_comments[1:]
            total_comment_penalties += len(block_comments)

        # Each commented-out reference costs points (max 4 penalties = 0 score)
        commented_score = max(0.0, 1.0 - (total_comment_penalties * 0.25))
        components["no_commented_backup_code"] = commented_score

        # --- HIDDEN CHECK 6: Module-level function removal ---
        # annotationStore.ts has a standalone module-level function `backupTimestamp()`
        # at the bottom (outside the class). Weak models often only delete class methods
        # and miss standalone helper functions defined at module scope.
        # Also checks that no other standalone function was accidentally removed
        # (the file should still end cleanly after the class closing brace).
        module_fn_score = 1.0

        # The backupTimestamp function should be completely gone
        if re.search(r'function\s+backupTimestamp', store_content):
            module_fn_score -= 0.6

        # The ISO date formatting logic (.toISOString().replace) that was ONLY
        # inside backupTimestamp should be gone from this file
        if re.search(r'toISOString\(\)\.replace\(\s*/\[:\.\]/g', store_content):
            module_fn_score -= 0.4

        components["module_fn_removal"] = max(0.0, module_fn_score)

        # --- HIDDEN CHECK 7: Settings count integrity ---
        # After removal, types.ts AnnotationPluginSettings interface should have
        # exactly 8 fields (was 9 with backupFrequencyMinutes). DEFAULT_SETTINGS
        # should have exactly 8 key-value pairs. This catches both under-deletion
        # (leaving backup) and over-deletion (removing non-backup settings).
        settings_integrity_score = 1.0

        # Count interface fields: look for lines with `fieldName:` pattern
        # inside the AnnotationPluginSettings interface block
        iface_match = re.search(
            r'interface\s+AnnotationPluginSettings\s*\{(.*?)\}',
            types_content, re.DOTALL
        )
        if iface_match:
            iface_body = iface_match.group(1)
            # Count property declarations (word followed by optional ? then colon)
            iface_fields = re.findall(r'^\s*\w+\??\s*:', iface_body, re.MULTILINE)
            if len(iface_fields) != 8:
                # Wrong number of fields: either over-deleted or under-deleted
                settings_integrity_score -= 0.5

        # Count DEFAULT_SETTINGS keys
        defaults_match = re.search(
            r'DEFAULT_SETTINGS\s*(?::\s*\w+)?\s*=\s*\{(.*?)\}',
            types_content, re.DOTALL
        )
        if defaults_match:
            defaults_body = defaults_match.group(1)
            default_keys = re.findall(r'^\s*\w+\s*:', defaults_body, re.MULTILINE)
            if len(default_keys) != 8:
                settings_integrity_score -= 0.5

        components["settings_count_integrity"] = max(0.0, settings_integrity_score)

    # --- Compute overall score ---
    # Weighted to differentiate strong (0.7-0.85) from weak (0.4-0.6) models.
    # Basic removal (easy) is low weight. Hidden quality checks separate models.
    # Strong models: nail basic + most hidden checks -> 0.7-0.85
    # Weak models: nail basic but miss header updates, cross-file refs, formatting -> 0.4-0.6
    weights = {
        "main_backup_field_removed": 0.02,
        "main_backup_methods_removed": 0.05,
        "store_backup_code_removed": 0.05,
        "types_backup_setting_removed": 0.03,
        "settings_backup_ui_removed": 0.03,
        "dead_reference_cleanup": 0.18,
        "store_orphan_cleanup": 0.08,
        "header_consistency": 0.18,
        "formatting_cleanliness": 0.10,
        "no_commented_backup_code": 0.10,
        "module_fn_removal": 0.08,
        "settings_count_integrity": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try /workspace/fixtures/yh-inklight first, then /workspace/yh-inklight
    ws = Path("/workspace/fixtures")
    if not (ws / "yh-inklight").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
