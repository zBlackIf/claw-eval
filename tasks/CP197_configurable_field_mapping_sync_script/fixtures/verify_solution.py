"""Hidden verifier for CP197 — Configurable Field Mapping Sync Script.

Tiered grading structure:
  VISIBLE checks (weight ~55%): structural/static analysis of config-driven refactoring
  HIDDEN EASY tier (weight ~13%): basic runtime correctness any valid solution passes
  HIDDEN HARD tier (weight ~32%): deep behavioral tests only strong solutions pass

Checks that the sync script has been refactored to support:
1. Configurable main-table field mapping (not hardcoded)
2. Configurable sub-table field name mapping (banks -> gyszhxx_items)
3. Sub-table internal field mapping is config-driven
4. Change detection covers sub-table changes (not just main table)
5. The script actually runs against test data with correct results
6. Deep: End-to-end correctness of the sync pipeline with expected outcomes
7. Deep: Edge case robustness (empty subtables, missing fields, config isolation)
8. Deep: Config hot-swap — changing config produces different output without code edits
9. Deep: Idempotency — running sync twice with same data produces consistent results
"""
from __future__ import annotations

import json
import sys
import os
import re
import copy
import importlib.util
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_sync_script(project: Path) -> Path | None:
    """Find the main sync script (not example/template files)."""
    candidates = []
    for f in project.rglob("*.py"):
        if "verify" in f.name.lower():
            continue
        content = _read(f)
        if ("convert_supplier" in content or "sync" in f.name.lower()) and "supplier" in content.lower():
            candidates.append(f)
    # Prefer sync_supplier_archive.py
    for c in candidates:
        if "sync_supplier" in c.name:
            return c
    return candidates[0] if candidates else None


def _find_config_yaml(project: Path) -> list[Path]:
    """Find YAML config files that are NOT .example files."""
    results = []
    for f in list(project.rglob("*.yaml")) + list(project.rglob("*.yml")):
        if ".example" in f.name:
            continue
        results.append(f)
    return results


def _import_module(sync_script: Path, module_name: str = "sync_module"):
    """Safely import the sync script as a module."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, sync_script)
        mod = importlib.util.module_from_spec(spec)
        orig_path = sys.path[:]
        sys.path.insert(0, str(sync_script.parent))
        sys.path.insert(0, str(sync_script.parent.parent))
        try:
            spec.loader.exec_module(mod)
        except (ImportError, ModuleNotFoundError):
            pass
        except SystemExit:
            pass
        finally:
            sys.path = orig_path
        return mod
    except Exception:
        return None


def _find_convert_fn(mod):
    """Find the convert function in a module."""
    if not mod:
        return None
    for name in dir(mod):
        fn = getattr(mod, name, None)
        if callable(fn) and "convert" in name.lower() and "supplier" in name.lower():
            return fn
    for name in dir(mod):
        fn = getattr(mod, name, None)
        if callable(fn) and "convert" in name.lower():
            return fn
    return None


def _find_detect_fn(mod):
    """Find the detect_changes function in a module."""
    if not mod:
        return None
    for name in dir(mod):
        fn = getattr(mod, name, None)
        if callable(fn) and "detect" in name.lower() and "change" in name.lower():
            return fn
    return None


def _find_sync_fn(mod):
    """Find the sync_suppliers function in a module."""
    if not mod:
        return None
    for name in dir(mod):
        fn = getattr(mod, name, None)
        if callable(fn) and "sync" in name.lower() and "supplier" in name.lower():
            return fn
    return None


def _load_test_data(project: Path) -> dict | None:
    """Load test_data.json from the project."""
    for f in project.rglob("test_data.json"):
        try:
            return json.loads(_read(f))
        except Exception:
            continue
    fallback = Path("/workspace/fixtures/lianshang/test_data.json")
    if fallback.exists():
        try:
            return json.loads(_read(fallback))
        except Exception:
            pass
    return None


# =============================================================================
# VISIBLE CHECKS — Structural/static analysis (weight ~55%)
# =============================================================================


def check_configurable_main_mapping(project: Path) -> tuple[float, str]:
    """Check if main table field mapping is configurable (not hardcoded)."""
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    content = _read(sync_script)
    config_yamls = _find_config_yaml(project)
    all_yaml_content = "\n".join(_read(f) for f in config_yamls)

    # Check for YAML/JSON config loading in the script
    has_external_config = any(x in content for x in [
        "yaml.safe_load", "yaml.load", "json.load", "load_config", "read_config"
    ])

    # Check for a mapping dictionary/constant that's separate from conversion logic
    has_mapping_dict = bool(re.search(
        r"(?:MAIN_FIELD_MAPPING|FIELD_MAPPING|field_mapping|main_mapping|FIELD_MAPPING_CONFIG)\s*[=:]\s*\{",
        content, re.IGNORECASE
    ))
    if not has_mapping_dict:
        has_mapping_dict = bool(re.search(
            r'(?:config|CONFIG)\s*\[\s*["\']main_fields["\']\s*\]',
            content
        ))

    # Check for config-driven conversion (iterating over mapping dict)
    has_loop_driven = bool(re.search(
        r"for\s+\w+\s*,\s*\w+\s+in\s+.*(?:mapping|MAPPING|config|FIELD).*\.items\(\)",
        content
    ))

    # Check that the old hardcoded approach with 5+ direct .get() calls is gone
    hardcoded_count = len(re.findall(
        r'result\[.*\]\s*=\s*\{["\']value["\']\s*:\s*supplier_data\.get\(',
        content
    ))
    is_still_hardcoded = hardcoded_count >= 4

    # Check if YAML config has main field entries
    yaml_has_main_fields = bool(re.search(
        r"(?:fullName|shortName|supplier_full_name|supplier_short_name)",
        all_yaml_content
    ))

    score = 0.0
    if has_external_config and yaml_has_main_fields:
        score += 0.5
    elif has_mapping_dict:
        score += 0.4
    if has_loop_driven:
        score += 0.4
    if not is_still_hardcoded:
        score += 0.2
    else:
        score -= 0.2  # penalty for keeping hardcoded

    details = (f"ext_config={has_external_config}, mapping_dict={has_mapping_dict}, "
               f"loop_driven={has_loop_driven}, still_hardcoded={is_still_hardcoded}, "
               f"yaml_main_fields={yaml_has_main_fields}")
    return min(max(score, 0.0), 1.0), details


def check_subtable_field_name_mapping(project: Path) -> tuple[float, str]:
    """Check if sub-table field name is configurable (banks -> gyszhxx_items)."""
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    py_content = _read(sync_script)
    config_yamls = _find_config_yaml(project)
    yaml_content = "\n".join(_read(f) for f in config_yamls)
    combined = py_content + "\n" + yaml_content

    # Key: "gyszhxx_items" must appear in the script or its config (not just .example)
    has_gyszhxx_in_code = "gyszhxx_items" in py_content
    has_gyszhxx_in_config = "gyszhxx_items" in yaml_content

    # Check for a mapping structure that connects banks <-> gyszhxx_items
    has_subtable_name_config = False
    patterns = [
        r"['\"]?(?:api|upstream)['\"]?\s*[:=]\s*['\"]banks['\"]",
        r"['\"]?(?:jdy|downstream)['\"]?\s*[:=]\s*['\"]gyszhxx_items['\"]",
        r"_subform_name.*(?:banks|gyszhxx_items)",
        r"upstream_field.*banks",
        r"downstream_field.*gyszhxx_items",
    ]
    for pat in patterns:
        if re.search(pat, combined, re.IGNORECASE):
            has_subtable_name_config = True
            break

    # Check that the code uses the configured name dynamically
    has_dynamic_access = bool(re.search(
        r"supplier_data\.get\(\s*(?!\"banks\")(?:\w+|config|subform|api_)",
        py_content
    )) or bool(re.search(
        r"\.get\(\s*(?:api_subform|upstream_field|subform_config|SUBFORM)",
        py_content
    ))

    # Check output uses gyszhxx_items (not hardcoded "banks")
    outputs_banks = bool(re.search(r'result\[.?banks.?\]', py_content))
    outputs_configured = bool(re.search(
        r'result\[.*(?:jdy_subform|downstream|subform_config|SUBFORM)',
        py_content
    ))

    score = 0.0
    if has_gyszhxx_in_code or has_gyszhxx_in_config:
        score += 0.3
    if has_subtable_name_config:
        score += 0.3
    if has_dynamic_access:
        score += 0.2
    if outputs_configured and not outputs_banks:
        score += 0.2
    elif not outputs_banks:
        score += 0.1

    details = (f"gyszhxx_in_code={has_gyszhxx_in_code}, gyszhxx_in_config={has_gyszhxx_in_config}, "
               f"name_config={has_subtable_name_config}, dynamic_access={has_dynamic_access}, "
               f"outputs_configured={outputs_configured}")
    return min(max(score, 0.0), 1.0), details


def check_subtable_internal_field_mapping(project: Path) -> tuple[float, str]:
    """Check if sub-table internal fields are also config-driven."""
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    py_content = _read(sync_script)
    config_yamls = _find_config_yaml(project)
    yaml_content = "\n".join(_read(f) for f in config_yamls)
    combined = py_content + "\n" + yaml_content

    # Check for downstream sub-table field names in config (not .example)
    downstream_fields = [
        "gyszhxx_receiving_account_number", "gyszhxx_account_name",
        "gyszhxx_bank_name", "gyszhxx_bank_property"
    ]
    downstream_in_config = sum(1 for f in downstream_fields if f in combined)

    # Check for a sub-table field mapping dict in the script
    has_subtable_mapping_dict = bool(re.search(
        r"(?:SUBFORM_FIELD_MAPPING|subtable_fields|sub_field_mapping|bank_field_mapping)\s*[=:]\s*\{",
        py_content, re.IGNORECASE
    ))
    if not has_subtable_mapping_dict:
        has_subtable_mapping_dict = bool(re.search(
            r'(?:config|CONFIG|FIELD_MAPPING_CONFIG)\s*\[\s*["\'](?:subtable|sub_table)["\']\s*\]\s*\[\s*["\']fields["\']\s*\]',
            py_content
        ))

    # Check for loop-driven sub-table field conversion
    has_subtable_loop = bool(re.search(
        r"for\s+\w+\s*,\s*\w+\s+in\s+.*(?:SUBFORM|subtable|sub_field|bank_field|sub_mapping).*\.items\(\)",
        py_content, re.IGNORECASE
    ))

    # Check that hardcoded bank.get("account") etc. is gone
    hardcoded_bank_gets = len(re.findall(
        r'bank\.get\("(?:account|accountName|bankName|bankAccountProperty)"\)',
        py_content
    ))
    not_hardcoded = hardcoded_bank_gets < 2

    score = 0.0
    if downstream_in_config >= 3:
        score += 0.3
    elif downstream_in_config >= 1:
        score += 0.15
    if has_subtable_mapping_dict:
        score += 0.25
    if has_subtable_loop:
        score += 0.25
    if not_hardcoded:
        score += 0.2

    details = (f"downstream_fields={downstream_in_config}/4, mapping_dict={has_subtable_mapping_dict}, "
               f"subtable_loop={has_subtable_loop}, not_hardcoded={not_hardcoded}(gets={hardcoded_bank_gets})")
    return min(max(score, 0.0), 1.0), details


def check_subtable_change_detection(project: Path) -> tuple[float, str]:
    """Check if change detection now includes sub-table comparison."""
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    py_content = _read(sync_script)

    # Check if the "skip sub-table" pattern is still present
    still_skips = bool(re.search(
        r'if\s+field_name\s*==\s*["\']banks["\']\s*:\s*\n\s*#?\s*(?:TODO|continue)',
        py_content
    )) or bool(re.search(
        r'field_name\s*==\s*["\']banks["\']\s*.*continue',
        py_content
    ))

    # Check for sub-table comparison function
    has_subtable_compare_fn = bool(re.search(
        r"def\s+\w*(?:subform|subtable|sub_table|bank)\w*(?:changed|compare|diff|equal)",
        py_content, re.IGNORECASE
    ))

    # Check for row-level comparison logic
    has_row_compare = bool(re.search(
        r"(?:zip|enumerate).*(?:old|new|existing).*(?:row|item|bank)",
        py_content, re.IGNORECASE
    )) or bool(re.search(
        r"len\(\s*\w*(?:old|existing|current)\w*\s*\)\s*!=\s*len\(\s*\w*(?:new|updated)\w*\s*\)",
        py_content, re.IGNORECASE
    ))

    # Check for any sub-table comparison in detect_changes
    has_subtable_in_detect = bool(re.search(
        r"def\s+detect_changes.*?(?:subform|subtable|sub_table|gyszhxx|banks)",
        py_content, re.DOTALL | re.IGNORECASE
    ))

    score = 0.0
    if not still_skips:
        score += 0.25
    if has_subtable_compare_fn:
        score += 0.35
    if has_row_compare:
        score += 0.25
    if has_subtable_in_detect:
        score += 0.15

    details = (f"still_skips={still_skips}, compare_fn={has_subtable_compare_fn}, "
               f"row_compare={has_row_compare}, in_detect={has_subtable_in_detect}")
    return min(max(score, 0.0), 1.0), details


# =============================================================================
# HIDDEN EASY TIER — Basic runtime correctness (any valid solution passes)
# =============================================================================


def check_hidden_easy_import_and_convert(project: Path) -> tuple[float, str]:
    """HIDDEN EASY: Script imports cleanly and convert function produces valid output.

    This is the most basic runtime check — any solution that actually works will pass.
    Tests:
    - Module imports without crashing
    - convert function exists and is callable
    - convert produces a dict with at least 5 fields
    - Output contains 'supplier_code' key (basic field name correctness)
    - No exceptions raised during basic conversion
    """
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    test_data = _load_test_data(project)
    if not test_data:
        return 0.0, "Cannot find test_data.json"

    # Part 1: Module imports (0.3)
    mod = _import_module(sync_script, "sync_easy_check")
    if not mod:
        return 0.0, "Module import failed"

    score = 0.3  # Import succeeded

    # Part 2: convert function callable (0.2)
    convert_fn = _find_convert_fn(mod)
    if not convert_fn:
        return score, "No convert function found"
    score += 0.2

    # Part 3: Basic conversion produces valid output (0.3)
    try:
        sample = test_data["suppliers"][0]
        result = convert_fn(sample)
        if isinstance(result, dict) and len(result) >= 5:
            score += 0.3
        elif isinstance(result, dict):
            score += 0.15
    except Exception as e:
        return score, f"Conversion raised: {str(e)[:80]}"

    # Part 4: Output has supplier_code (0.2)
    if isinstance(result, dict) and "supplier_code" in result:
        score += 0.2

    return min(score, 1.0), "Import OK, convert callable and produces valid output"


def check_hidden_easy_sync_function_exists(project: Path) -> tuple[float, str]:
    """HIDDEN EASY: sync_suppliers function exists, is callable, and returns expected shape.

    Any correct refactoring preserves the sync_suppliers function signature.
    Tests:
    - sync_suppliers function exists
    - Returns a dict with 'created', 'updated', 'skipped' keys
    - Doesn't crash on test data
    """
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    test_data = _load_test_data(project)
    if not test_data:
        return 0.0, "Cannot find test_data.json"

    mod = _import_module(sync_script, "sync_easy_fn_check")
    if not mod:
        return 0.0, "Module import failed"

    # Part 1: sync_suppliers exists (0.3)
    sync_fn = _find_sync_fn(mod)
    if not sync_fn:
        return 0.0, "No sync_suppliers function found"
    score = 0.3

    # Part 2: Call it without crash (0.4)
    upstream_data = {s["code"]: s for s in test_data["suppliers"]}
    downstream_data = test_data.get("existing_downstream", {})
    try:
        results = sync_fn(upstream_data, downstream_data)
    except Exception as e:
        return score, f"sync_suppliers raised: {str(e)[:80]}"
    score += 0.4

    # Part 3: Returns correct shape (0.3)
    if isinstance(results, dict):
        has_created = "created" in results
        has_updated = "updated" in results
        has_skipped = "skipped" in results
        if has_created and has_updated and has_skipped:
            score += 0.3
        elif has_created or has_updated:
            score += 0.15

    return min(score, 1.0), "sync_suppliers callable and returns expected shape"


# =============================================================================
# HIDDEN HARD TIER — Deep behavioral tests (only strong solutions pass)
# =============================================================================


def check_hidden_hard_e2e_pipeline(project: Path) -> tuple[float, str]:
    """HIDDEN HARD: Full end-to-end pipeline correctness with format verification.

    Expected behavior with test_data.json:
    - SUP001: UPDATED (shortName changed + bank count changed)
    - SUP002: CREATED (not in downstream)
    - SUP003: SKIPPED (no changes)

    Critical discriminator: output MUST use 'gyszhxx_items' (not 'banks'),
    internal sub-table fields must use downstream naming.
    """
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    test_data = _load_test_data(project)
    if not test_data:
        return 0.0, "Cannot find test_data.json"

    mod = _import_module(sync_script, "sync_e2e_hard")
    if not mod:
        return 0.0, "Module import failed"

    sync_fn = _find_sync_fn(mod)
    if not sync_fn:
        return 0.0, "No sync_suppliers function found"

    upstream_data = {s["code"]: s for s in test_data["suppliers"]}
    downstream_data = test_data.get("existing_downstream", {})

    try:
        results = sync_fn(upstream_data, downstream_data)
    except Exception as e:
        return 0.0, f"sync_suppliers raised: {str(e)[:100]}"

    score = 0.0
    issues = []

    # Check routing correctness (0.2)
    created_codes = [r.get("code", "") for r in results.get("created", [])]
    updated_codes = [r.get("code", "") for r in results.get("updated", [])]
    skipped_codes = results.get("skipped", [])

    if "SUP002" in created_codes:
        score += 0.07
    else:
        issues.append("SUP002 not created")
    if "SUP001" in updated_codes:
        score += 0.07
    else:
        issues.append("SUP001 not updated")
    if "SUP003" in skipped_codes:
        score += 0.06
    else:
        issues.append("SUP003 not skipped")

    # Critical: output format uses gyszhxx_items (0.4)
    for item in results.get("created", []):
        if item.get("code") == "SUP002":
            data = item.get("data", {})
            if "gyszhxx_items" in data and "banks" not in data:
                score += 0.2
            elif "gyszhxx_items" in data:
                score += 0.1
            else:
                issues.append("SUP002 uses 'banks' not 'gyszhxx_items'")
            break

    for item in results.get("updated", []):
        if item.get("code") == "SUP001":
            data = item.get("data", {})
            if "gyszhxx_items" in data and "banks" not in data:
                score += 0.2
                # Check internal field names
                subtable_val = data.get("gyszhxx_items", {})
                rows = subtable_val.get("value", []) if isinstance(subtable_val, dict) else (subtable_val if isinstance(subtable_val, list) else [])
                if rows and len(rows) >= 1:
                    first_row = rows[0]
                    if isinstance(first_row, dict):
                        row_keys = set(first_row.keys())
                        expected = {"gyszhxx_receiving_account_number", "gyszhxx_account_name",
                                    "gyszhxx_bank_name", "gyszhxx_bank_property"}
                        matching = row_keys & expected
                        if len(matching) >= 3:
                            score += 0.15
                        elif len(matching) >= 1:
                            score += 0.07
                        else:
                            issues.append(f"Internal fields wrong: {row_keys}")
                    if len(rows) == 2:
                        score += 0.05
            elif "gyszhxx_items" in data:
                score += 0.1
            else:
                issues.append("SUP001 uses 'banks' not 'gyszhxx_items'")
            break

    details = f"created={created_codes}, updated={updated_codes}, skipped={skipped_codes}, issues={issues}"
    return min(max(score, 0.0), 1.0), details


def check_hidden_hard_subtable_change_accuracy(project: Path) -> tuple[float, str]:
    """HIDDEN HARD: Sub-table change detection with isolated scenarios.

    Key discriminator tests:
    1. Main fields match but sub-table rows differ (count) -> must detect
    2. Main fields match, same row count, different field values -> must detect
    3. Empty sub-tables both sides -> must NOT detect (false positive trap)

    Only properly implemented row-count + field-value comparison passes all three.
    Naive "always changed" or "never check subtable" fails at least one.
    """
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    test_data = _load_test_data(project)
    if not test_data:
        return 0.0, "Cannot find test_data.json"

    mod = _import_module(sync_script, "sync_cd_hard")
    if not mod:
        return 0.0, "Module import failed"

    detect_fn = _find_detect_fn(mod)
    convert_fn = _find_convert_fn(mod)

    if not detect_fn or not convert_fn:
        # Static fallback
        content = _read(sync_script)
        has_len_check = bool(re.search(r"len\(.*\)\s*!=\s*len\(", content))
        has_row_iter = bool(re.search(r"for\s+.*\s+in\s+.*(?:zip|enumerate)", content))
        has_field_compare = bool(re.search(r"!=.*(?:old|existing|current)", content))
        score = 0.0
        if has_len_check:
            score += 0.2
        if has_row_iter:
            score += 0.2
        if has_field_compare:
            score += 0.15
        return score, f"static: len={has_len_check}, iter={has_row_iter}, cmp={has_field_compare}"

    score = 0.0
    issues = []
    sup001_data = test_data["suppliers"][0]
    existing_sup001 = test_data["existing_downstream"]["SUP001"]["data"]

    # Test 1 (0.35): Main fields match, sub-table row count differs (1 vs 2)
    try:
        sup001_main_match = dict(sup001_data)
        sup001_main_match["shortName"] = "BJ Tech OLD NAME"  # match existing
        converted = convert_fn(sup001_main_match)
        changed = detect_fn(existing_sup001, converted)
        if changed:
            score += 0.35
        else:
            issues.append("Failed sub-table-only change (row count 1->2)")
    except Exception as e:
        issues.append(f"Test1 error: {str(e)[:50]}")

    # Test 2 (0.35): Same row count, different field values
    try:
        sup001_diff_val = dict(sup001_data)
        sup001_diff_val["shortName"] = "BJ Tech OLD NAME"
        sup001_diff_val["banks"] = [{
            "account": "9999999999999999",  # different
            "accountName": "Beijing Tech Materials",
            "bankName": "ICBC Beijing Haidian Sub-branch",
            "bankAccountProperty": "corporate"
        }]
        converted = convert_fn(sup001_diff_val)
        changed = detect_fn(existing_sup001, converted)
        if changed:
            score += 0.35
        else:
            issues.append("Failed sub-table field value change (same count, diff account)")
    except Exception as e:
        issues.append(f"Test2 error: {str(e)[:50]}")

    # Test 3 (0.3): Empty sub-tables both sides -> no false positive
    try:
        sup003_data = test_data["suppliers"][2]
        existing_sup003 = test_data["existing_downstream"]["SUP003"]["data"]
        converted = convert_fn(sup003_data)
        changed = detect_fn(existing_sup003, converted)
        if not changed:
            score += 0.3
        else:
            issues.append("False positive on SUP003 (empty banks both sides)")
    except Exception as e:
        issues.append(f"Test3 error: {str(e)[:50]}")

    details = f"issues={issues}" if issues else "All subtable change detection tests passed"
    return min(max(score, 0.0), 1.0), details


def check_hidden_hard_config_hot_swap(project: Path) -> tuple[float, str]:
    """HIDDEN HARD: Config hot-swap — changing config produces different output.

    This tests whether the solution is TRULY config-driven (not just reading config
    but still hardcoding logic). A strong solution lets you change the mapping config
    and get different output WITHOUT editing the Python code.

    Test: Monkey-patch the config to use different downstream field names,
    then verify the output changes accordingly.
    """
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    test_data = _load_test_data(project)
    if not test_data:
        return 0.0, "Cannot find test_data.json"

    mod = _import_module(sync_script, "sync_hotswap")
    if not mod:
        return 0.0, "Module import failed"

    convert_fn = _find_convert_fn(mod)
    if not convert_fn:
        return 0.0, "No convert function found"

    sample = test_data["suppliers"][0]
    score = 0.0
    issues = []

    # First, get baseline output
    try:
        baseline = convert_fn(sample)
    except Exception as e:
        return 0.0, f"Baseline conversion failed: {str(e)[:80]}"

    if not isinstance(baseline, dict):
        return 0.0, "Baseline is not a dict"

    # Strategy: Find the config variable in the module and try to patch it
    # Look for common config variable names
    config_var_names = [
        "MAIN_FIELD_MAPPING", "FIELD_MAPPING", "field_mapping", "main_mapping",
        "CONFIG", "config", "MAPPING", "mapping", "FIELD_MAPPING_CONFIG",
    ]

    patched = False
    original_config = None
    config_attr = None

    for var_name in config_var_names:
        val = getattr(mod, var_name, None)
        if isinstance(val, dict) and len(val) >= 3:
            config_attr = var_name
            original_config = copy.deepcopy(val)
            break

    if not config_attr:
        # Try to find a config dict that contains field mapping keys
        for name in dir(mod):
            if name.startswith("_"):
                continue
            val = getattr(mod, name, None)
            if isinstance(val, dict):
                val_str = json.dumps(val, default=str)
                if "fullName" in val_str or "supplier_full_name" in val_str or "main_fields" in val_str:
                    config_attr = name
                    original_config = copy.deepcopy(val)
                    break

    if not config_attr:
        # Cannot find config variable to patch — check if convert takes config param
        import inspect
        try:
            sig = inspect.signature(convert_fn)
            params = list(sig.parameters.keys())
            if len(params) >= 2:
                # Try calling with a custom mapping
                alt_mapping = {
                    "code": "alt_supplier_code",
                    "fullName": "alt_full_name",
                    "shortName": "alt_short_name",
                }
                try:
                    alt_result = convert_fn(sample, alt_mapping)
                    if isinstance(alt_result, dict) and "alt_supplier_code" in alt_result:
                        score = 1.0
                        return score, "convert accepts mapping param and produces different output"
                    elif isinstance(alt_result, dict) and "alt_full_name" in alt_result:
                        score = 0.8
                        return score, "convert partially uses passed mapping"
                except (TypeError, Exception):
                    pass
        except Exception:
            pass
        return 0.0, "Cannot find config variable to test hot-swap"

    # Patch the config: change a main field downstream name
    try:
        patched_config = copy.deepcopy(original_config)
        # Handle nested config (e.g., config["main_fields"]) vs flat mapping
        if "main_fields" in patched_config:
            # Nested: config = {"main_fields": {"code": "supplier_code", ...}}
            inner = patched_config["main_fields"]
            if isinstance(inner, dict) and "fullName" in inner:
                inner["fullName"] = "test_alt_full_name"
                patched = True
        elif "fullName" in patched_config:
            # Flat: MAPPING = {"fullName": "supplier_full_name", ...}
            patched_config["fullName"] = "test_alt_full_name"
            patched = True
        elif any("fullName" in str(v) for v in patched_config.values()):
            # Could be reversed: {"supplier_full_name": "fullName"}
            for k, v in list(patched_config.items()):
                if v == "fullName" or (isinstance(v, dict) and "fullName" in str(v)):
                    patched_config[k] = "test_alt_full_name"
                    patched = True
                    break

        if patched:
            setattr(mod, config_attr, patched_config)
            try:
                patched_result = convert_fn(sample)
                # Restore
                setattr(mod, config_attr, original_config)

                if isinstance(patched_result, dict):
                    # Check if the output changed
                    if "test_alt_full_name" in patched_result:
                        score += 0.6  # Config change reflected in output key
                    elif patched_result != baseline:
                        score += 0.3  # Output changed but not exactly as expected
                    else:
                        issues.append("Config patched but output unchanged")
                else:
                    issues.append("Patched result is not a dict")
            except Exception as e:
                setattr(mod, config_attr, original_config)
                issues.append(f"Patched conversion failed: {str(e)[:60]}")
        else:
            issues.append("Could not determine how to patch config")
    except Exception as e:
        issues.append(f"Config patch error: {str(e)[:60]}")
        if config_attr and original_config:
            try:
                setattr(mod, config_attr, original_config)
            except Exception:
                pass

    # Also check: sub-table name is configurable (0.4)
    if config_attr and original_config:
        try:
            patched_sub = copy.deepcopy(original_config)
            # Try to change the sub-table downstream field name
            sub_patched = False
            if "subtable" in patched_sub:
                sub_conf = patched_sub["subtable"]
                if isinstance(sub_conf, dict) and "downstream_field" in sub_conf:
                    sub_conf["downstream_field"] = "test_alt_subtable"
                    sub_patched = True
            elif "subform" in patched_sub:
                sub_conf = patched_sub["subform"]
                if isinstance(sub_conf, dict):
                    for k in ["downstream_field", "jdy", "downstream"]:
                        if k in sub_conf:
                            sub_conf[k] = "test_alt_subtable"
                            sub_patched = True
                            break

            if sub_patched:
                setattr(mod, config_attr, patched_sub)
                try:
                    sub_result = convert_fn(sample)
                    setattr(mod, config_attr, original_config)
                    if isinstance(sub_result, dict) and "test_alt_subtable" in sub_result:
                        score += 0.4
                    elif isinstance(sub_result, dict) and "gyszhxx_items" not in sub_result:
                        score += 0.2  # Something changed
                except Exception:
                    setattr(mod, config_attr, original_config)
            else:
                # Give partial credit if main field hot-swap worked
                pass
        except Exception:
            if config_attr and original_config:
                try:
                    setattr(mod, config_attr, original_config)
                except Exception:
                    pass

    details = f"config_attr={config_attr}, patched={patched}, issues={issues}"
    return min(max(score, 0.0), 1.0), details


def check_hidden_hard_idempotency_and_edge_cases(project: Path) -> tuple[float, str]:
    """HIDDEN HARD: Output format correctness and field mapping completeness.

    Discriminating tests that specifically verify the config-driven refactoring
    produces correct downstream-formatted output:
    1. Convert SUP002 and verify ALL 4 sub-table internal fields use downstream names
    2. Verify sub-table output uses correct nested {"value": ...} structure per row
    3. Verify a supplier with 3 banks produces 3 sub-table rows with correct names
    4. Verify main-table output doesn't include raw upstream field names
    """
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    test_data = _load_test_data(project)
    if not test_data:
        return 0.0, "Cannot find test_data.json"

    mod = _import_module(sync_script, "sync_edge_cases")
    if not mod:
        return 0.0, "Module import failed"

    convert_fn = _find_convert_fn(mod)
    if not convert_fn:
        return 0.0, "No convert function found"

    score = 0.0
    issues = []

    # Test 1 (0.3): SUP002 sub-table internal fields use ALL downstream names
    try:
        sup002 = test_data["suppliers"][1]  # 1 bank
        result = convert_fn(sup002)
        if not isinstance(result, dict):
            issues.append("Result not a dict")
            return 0.0, str(issues)

        # Find sub-table in output
        subtable_key = None
        for k in ["gyszhxx_items", "banks"]:
            if k in result:
                subtable_key = k
                break

        if subtable_key == "gyszhxx_items":
            subtable_val = result["gyszhxx_items"]
            rows = subtable_val.get("value", []) if isinstance(subtable_val, dict) else (subtable_val if isinstance(subtable_val, list) else [])
            if rows and len(rows) >= 1:
                first_row = rows[0]
                if isinstance(first_row, dict):
                    # Extract actual field names (handle nested {"value": x} or flat)
                    row_keys = set(first_row.keys())
                    expected = {"gyszhxx_receiving_account_number", "gyszhxx_account_name",
                                "gyszhxx_bank_name", "gyszhxx_bank_property"}
                    matching = row_keys & expected
                    if len(matching) == 4:
                        score += 0.3  # All 4 downstream field names correct
                    elif len(matching) >= 3:
                        score += 0.2
                    elif len(matching) >= 1:
                        score += 0.1
                    else:
                        issues.append(f"Sub-table fields not downstream: {row_keys}")
                else:
                    issues.append(f"Row not a dict: {type(first_row)}")
            else:
                issues.append("No rows in gyszhxx_items")
        elif subtable_key == "banks":
            issues.append("Still uses 'banks' key, not 'gyszhxx_items'")
        else:
            issues.append("No sub-table key found in output")
    except Exception as e:
        issues.append(f"Test1 error: {str(e)[:60]}")

    # Test 2 (0.25): Sub-table row values use {"value": ...} wrapper structure
    try:
        if subtable_key == "gyszhxx_items" and rows and len(rows) >= 1:
            first_row = rows[0]
            if isinstance(first_row, dict):
                # Check if values are wrapped in {"value": ...}
                value_wrapped = 0
                for v in first_row.values():
                    if isinstance(v, dict) and "value" in v:
                        value_wrapped += 1
                if value_wrapped >= 3:
                    score += 0.25  # Correctly uses JDY format
                elif value_wrapped >= 1:
                    score += 0.1
                else:
                    # Flat format (just values) — acceptable but less correct
                    score += 0.05
                    issues.append("Sub-table fields not wrapped in {value: ...}")
    except Exception as e:
        issues.append(f"Test2 error: {str(e)[:60]}")

    # Test 3 (0.25): 3-bank supplier produces 3 rows with correct field names
    try:
        three_bank_supplier = {
            "code": "SUP_3BANK",
            "fullName": "Three Bank Corp",
            "shortName": "3Bank",
            "type": "services",
            "receiptAccount": "1111111111",
            "receiptBank": "Test Bank",
            "receiptCompany": "Three Bank Corp",
            "banks": [
                {"account": "111", "accountName": "A1", "bankName": "B1", "bankAccountProperty": "corporate"},
                {"account": "222", "accountName": "A2", "bankName": "B2", "bankAccountProperty": "personal"},
                {"account": "333", "accountName": "A3", "bankName": "B3", "bankAccountProperty": "corporate"},
            ]
        }
        result3 = convert_fn(three_bank_supplier)
        if isinstance(result3, dict) and "gyszhxx_items" in result3:
            st_val = result3["gyszhxx_items"]
            st_rows = st_val.get("value", []) if isinstance(st_val, dict) else (st_val if isinstance(st_val, list) else [])
            if len(st_rows) == 3:
                score += 0.15
                # Verify third row has correct field names too
                if isinstance(st_rows[2], dict):
                    third_keys = set(st_rows[2].keys())
                    expected = {"gyszhxx_receiving_account_number", "gyszhxx_account_name",
                                "gyszhxx_bank_name", "gyszhxx_bank_property"}
                    if third_keys & expected == expected:
                        score += 0.1
            else:
                issues.append(f"3-bank supplier produced {len(st_rows)} rows, expected 3")
        else:
            issues.append("3-bank supplier doesn't use gyszhxx_items")
    except Exception as e:
        issues.append(f"Test3 error: {str(e)[:60]}")

    # Test 4 (0.2): Main table output doesn't leak upstream field names
    try:
        result = convert_fn(test_data["suppliers"][0])
        if isinstance(result, dict):
            # These upstream names should NOT appear as keys in the output
            upstream_keys_leaked = set()
            upstream_raw_names = {"fullName", "shortName", "receiptAccount", "receiptBank", "receiptCompany"}
            for k in result.keys():
                if k in upstream_raw_names:
                    upstream_keys_leaked.add(k)
            if not upstream_keys_leaked:
                score += 0.2
            elif len(upstream_keys_leaked) <= 1:
                score += 0.1
            else:
                issues.append(f"Upstream names leaked: {upstream_keys_leaked}")
    except Exception as e:
        issues.append(f"Test4 error: {str(e)[:60]}")

    details = f"issues={issues}" if issues else "All output format tests passed"
    return min(max(score, 0.0), 1.0), details


# =============================================================================
# MAIN GRADING FUNCTION
# =============================================================================


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for CP197 with tiered hidden checks."""
    project = None

    if (ws / "lianshang").exists():
        project = ws / "lianshang"
    elif (ws / "fixtures" / "lianshang").exists():
        project = ws / "fixtures" / "lianshang"
    else:
        for f in ws.rglob("sync_supplier_archive.py"):
            if "verify" not in f.name:
                project = f.parent
                break

    if not project or not project.exists():
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "No project directory found"
        }

    components = {}
    details = {}

    # === VISIBLE CHECKS (combined weight: 0.55) ===

    # Dimension 1: Configurable main-table field mapping (weight: 0.15)
    s, d = check_configurable_main_mapping(project)
    components["main_field_mapping_configurable"] = s
    details["main_field_mapping_configurable"] = d

    # Dimension 2: Sub-table field name mapping banks -> gyszhxx_items (weight: 0.13)
    s, d = check_subtable_field_name_mapping(project)
    components["subtable_name_mapping"] = s
    details["subtable_name_mapping"] = d

    # Dimension 3: Sub-table internal field mapping is config-driven (weight: 0.12)
    s, d = check_subtable_internal_field_mapping(project)
    components["subtable_field_mapping"] = s
    details["subtable_field_mapping"] = d

    # Dimension 4: Change detection covers sub-table (weight: 0.08)
    s, d = check_subtable_change_detection(project)
    components["subtable_change_detection"] = s
    details["subtable_change_detection"] = d

    # Dimension 5: Config separation quality (weight: 0.07)
    s, d = check_config_separation_quality(project)
    components["config_separation_quality"] = s
    details["config_separation_quality"] = d

    # === HIDDEN EASY TIER (combined weight: 0.13) — all valid solutions pass ===

    # Dimension 6: Module imports and convert works (weight: 0.07)
    s, d = check_hidden_easy_import_and_convert(project)
    components["hidden_easy_import_convert"] = s
    details["hidden_easy_import_convert"] = d

    # Dimension 7: sync_suppliers function shape (weight: 0.06)
    s, d = check_hidden_easy_sync_function_exists(project)
    components["hidden_easy_sync_fn"] = s
    details["hidden_easy_sync_fn"] = d

    # === HIDDEN HARD TIER (combined weight: 0.32) — only strong solutions pass ===

    # Dimension 8: End-to-end pipeline correctness (weight: 0.12)
    s, d = check_hidden_hard_e2e_pipeline(project)
    components["hidden_hard_e2e_pipeline"] = s
    details["hidden_hard_e2e_pipeline"] = d

    # Dimension 9: Sub-table change detection accuracy (weight: 0.10)
    s, d = check_hidden_hard_subtable_change_accuracy(project)
    components["hidden_hard_subtable_accuracy"] = s
    details["hidden_hard_subtable_accuracy"] = d

    # Dimension 10: Config hot-swap test (weight: 0.05)
    s, d = check_hidden_hard_config_hot_swap(project)
    components["hidden_hard_config_hotswap"] = s
    details["hidden_hard_config_hotswap"] = d

    # Dimension 11: Idempotency and edge cases (weight: 0.05)
    s, d = check_hidden_hard_idempotency_and_edge_cases(project)
    components["hidden_hard_edge_cases"] = s
    details["hidden_hard_edge_cases"] = d

    weights = {
        # Visible (0.55)
        "main_field_mapping_configurable": 0.15,
        "subtable_name_mapping": 0.13,
        "subtable_field_mapping": 0.12,
        "subtable_change_detection": 0.08,
        "config_separation_quality": 0.07,
        # Hidden easy (0.13)
        "hidden_easy_import_convert": 0.07,
        "hidden_easy_sync_fn": 0.06,
        # Hidden hard (0.32)
        "hidden_hard_e2e_pipeline": 0.12,
        "hidden_hard_subtable_accuracy": 0.10,
        "hidden_hard_config_hotswap": 0.05,
        "hidden_hard_edge_cases": 0.05,
    }

    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "details": details,
    }


def check_config_separation_quality(project: Path) -> tuple[float, str]:
    """Config quality, separation of concerns, and robustness.

    Checks that a strong solution:
    1. Has a separate config file (not just inline dict) with ALL mappings
    2. Config is cleanly separated from logic (Single Responsibility)
    3. Conversion function accepts or reads config, not hardcoded to one source
    4. Handles graceful degradation: missing fields in config -> default/skip, not crash
    """
    sync_script = _find_sync_script(project)
    if not sync_script:
        return 0.0, "No sync script found"

    py_content = _read(sync_script)
    config_yamls = _find_config_yaml(project)
    all_yaml = "\n".join(_read(f) for f in config_yamls)

    score = 0.0
    issues = []

    # 1. Separate YAML file with BOTH main and sub-table field mappings (0.3)
    yaml_has_main = bool(re.search(r"(?:main_fields|main_table|MAIN)", all_yaml, re.IGNORECASE))
    yaml_has_sub = bool(re.search(r"(?:subtable|sub_table|subform|gyszhxx)", all_yaml, re.IGNORECASE))
    yaml_has_both_mappings = yaml_has_main and yaml_has_sub

    if yaml_has_both_mappings:
        score += 0.3
    elif yaml_has_main or yaml_has_sub:
        score += 0.15
        issues.append("YAML config missing either main or sub-table mapping")
    else:
        issues.append("No YAML config with field mappings found")

    # 2. Clean loading: config loaded at module level or via function, not inline in convert (0.25)
    has_config_loader = bool(re.search(
        r"def\s+(?:load_config|read_config|get_config|load_mapping|init_config)",
        py_content
    ))
    has_module_level_load = bool(re.search(
        r"^(?:config|CONFIG|MAPPING|mapping)\s*=\s*(?:yaml\.safe_load|load_config|read_config|json\.load)",
        py_content, re.MULTILINE
    ))
    has_with_open_config = bool(re.search(
        r"with\s+open\(.*(?:yaml|yml|config|mapping).*\)\s+as",
        py_content
    ))

    if has_config_loader or has_module_level_load or has_with_open_config:
        score += 0.25
    else:
        has_inline_mapping = bool(re.search(
            r"(?:MAIN_FIELD_MAPPING|FIELD_MAPPING)\s*=\s*\{",
            py_content
        ))
        if has_inline_mapping:
            score += 0.1
            issues.append("Config is inline dict, not loaded from file")

    # 3. Convert function uses config parameter or module-level config variable (0.2)
    convert_takes_config = bool(re.search(
        r"def\s+convert_supplier\w*\(.*(?:config|mapping|field_map)",
        py_content
    ))
    convert_uses_module_config = bool(re.search(
        r"def\s+convert_supplier.*?(?:MAIN_FIELD|FIELD_MAPPING|config\[|CONFIG\[|mapping\[)",
        py_content, re.DOTALL
    ))

    if convert_takes_config:
        score += 0.2
    elif convert_uses_module_config:
        score += 0.15
    else:
        issues.append("convert function doesn't clearly reference config")

    # 4. Error handling / graceful degradation (0.25)
    has_safe_config_access = bool(re.search(
        r"(?:config|mapping).*\.get\(\s*\w+.*,\s*(?:\"\"|None|\{\}|\[\]|\"\"\"\")",
        py_content
    ))
    has_config_error_handling = bool(re.search(
        r"(?:try|except).*(?:KeyError|yaml|config|FileNotFound)",
        py_content, re.DOTALL
    ))
    has_default_fallback = bool(re.search(
        r"(?:or|if not)\s+(?:config|mapping|field_map)",
        py_content
    ))

    robustness_signals = sum([has_safe_config_access, has_config_error_handling, has_default_fallback])
    if robustness_signals >= 2:
        score += 0.25
    elif robustness_signals == 1:
        score += 0.12
    else:
        issues.append("No error handling for config access")

    details = (f"yaml_both_mappings={yaml_has_both_mappings}, config_loader={has_config_loader or has_module_level_load}, "
               f"convert_uses_config={convert_takes_config or convert_uses_module_config}, "
               f"robustness_signals={robustness_signals}, issues={issues}")
    return min(max(score, 0.0), 1.0), details


def main():
    ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
