"""Hidden verifier for CP206 — Android 9 / Huawei Compatibility Fixes.

Tiered scoring with explicit hidden discrimination:
  - Visible checks: basic correctness that any competent solution hits (~55%)
  - Hidden-easy checks: structural integrity that all passing solutions should have (~15%)
  - Hidden-hard checks: deep quality patterns only strong agents produce (~30%)

Hidden checks combined >= 30% weight to ensure discrimination.
"""
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
    for p in base.rglob(pattern):
        return p
    return None


def _find_files(base: Path, pattern: str) -> list[Path]:
    return list(base.rglob(pattern))


# ---------------------------------------------------------------------------
# VISIBLE CHECKS — Basic correctness (any agent that attempts the fix should get these)
# ---------------------------------------------------------------------------

def check_lateinit_fallback(ws: Path) -> dict:
    """Check that lateinit vars are replaced with fallback-initialized vars."""
    score = 0.0
    details = []

    app_file = _find_file(ws, "HyperIsleApp.kt")
    if not app_file:
        return {"score": 0.0, "details": ["HyperIsleApp.kt not found"]}

    content = _read(app_file)

    # lateinit removal (0.30)
    has_any_lateinit = bool(re.search(r"\blateinit\b", content))
    if not has_any_lateinit:
        score += 0.30
        details.append("All lateinit vars removed")
    else:
        details.append("FAIL: lateinit still present in code")

    # proper initialized defaults (0.40)
    ve_initialized = bool(re.search(
        r"var\s+versionEnforcer\s*:\s*VersionEnforcer\s*=", content
    ))
    ffr_initialized = bool(re.search(
        r"var\s+featureFlagRepository\s*:\s*FeatureFlagRepository\s*=", content
    ))
    pg_initialized = bool(re.search(
        r"var\s+premiumGate\s*:\s*PremiumGate\s*=", content
    ))
    init_count = sum([ve_initialized, ffr_initialized, pg_initialized])
    if init_count == 3:
        score += 0.40
        details.append("All 3 fields properly typed and initialized")
    elif init_count >= 1:
        score += 0.15
        details.append(f"Only {init_count}/3 fields properly initialized with type")
    else:
        details.append("FAIL: Fields not initialized with proper typed defaults")

    # Fallback implementation exists (0.30)
    all_kt_files = _find_files(ws, "*.kt")
    all_kt_content = "\n".join(_read(f) for f in all_kt_files)

    has_fallback_ve = bool(re.search(
        r"(class|object)\s+\w*(Fallback|NoOp|Default|Stub)\w*\s*.*"
        r":\s*VersionEnforcer",
        all_kt_content,
    ))
    has_inline_ve = bool(re.search(
        r"versionEnforcer\s*=\s*object\s*:\s*VersionEnforcer",
        all_kt_content,
    ))
    if has_fallback_ve or has_inline_ve:
        score += 0.30
        details.append("Fallback VersionEnforcer exists")
    else:
        details.append("FAIL: No fallback VersionEnforcer")

    return {"score": min(score, 1.0), "details": details}


def check_encrypted_prefs_fallback(ws: Path) -> dict:
    """Check EncryptedSharedPreferences has try-catch and plain fallback."""
    score = 0.0
    details = []

    prefs_file = _find_file(ws, "SecurePrefsManager.kt")
    if not prefs_file:
        all_kt = _find_files(ws, "*.kt")
        for f in all_kt:
            c = _read(f)
            if "EncryptedSharedPreferences" in c and ("createEncryptedPrefs" in c or "create" in c):
                prefs_file = f
                break

    if not prefs_file:
        return {"score": 0.0, "details": ["SecurePrefsManager.kt or equivalent not found"]}

    content = _read(prefs_file)

    # Has try-catch (0.30)
    has_try_catch = "try" in content and "catch" in content
    if has_try_catch:
        score += 0.30
        details.append("try-catch present")
    else:
        details.append("FAIL: No try-catch")
        return {"score": 0.0, "details": details}

    # Plain SharedPreferences fallback (0.35)
    has_plain_fallback = bool(re.search(
        r"getSharedPreferences\s*\(", content
    ))
    if has_plain_fallback:
        score += 0.35
        details.append("Plain SharedPreferences fallback")
    else:
        details.append("FAIL: No plain SharedPreferences fallback")

    # KeyStore cleanup (0.35)
    has_delete_entry = "deleteEntry" in content
    has_keystore_instance = bool(re.search(
        r"KeyStore\s*\.\s*getInstance", content
    ))
    if has_delete_entry and has_keystore_instance:
        score += 0.35
        details.append("KeyStore cleanup present")
    elif has_delete_entry or "KeyStore" in content:
        score += 0.15
        details.append("Partial KeyStore handling")
    else:
        details.append("FAIL: No KeyStore cleanup logic")

    return {"score": min(score, 1.0), "details": details}


def check_foreground_service_api_guard(ws: Path) -> dict:
    """Check foreground service uses correct API version guard."""
    score = 0.0
    details = []

    overlay_file = _find_file(ws, "OverlayService.kt")
    if not overlay_file:
        all_kt = _find_files(ws, "*.kt")
        for f in all_kt:
            c = _read(f)
            if "startForeground" in c and ("OverlayService" in c or "Service" in c):
                overlay_file = f
                break

    if not overlay_file:
        return {"score": 0.0, "details": ["OverlayService.kt or equivalent not found"]}

    content = _read(overlay_file)

    # Has version check (0.25)
    has_correct_api = (
        "UPSIDE_DOWN_CAKE" in content or
        ">= 34" in content or
        ">= Build.VERSION_CODES.UPSIDE_DOWN_CAKE" in content
    )
    version_checks = re.findall(r"VERSION_CODES\.(\w+)", content)
    has_new_version_check = any(v not in ("O",) for v in version_checks)

    if has_correct_api:
        score += 0.25
        details.append("Correct API 34 / UPSIDE_DOWN_CAKE reference")
    elif has_new_version_check:
        score += 0.10
        details.append("Version check present but level unclear")
    else:
        details.append("FAIL: No SDK version check for startForeground")
        return {"score": 0.0, "details": details}

    # Two-arg vs three-arg branching (0.50)
    has_three_arg = bool(re.search(
        r"startForeground\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+",
        content
    ))
    has_two_arg = bool(re.search(
        r"startForeground\s*\(\s*\w+\s*,\s*\w+\s*\)",
        content
    ))
    has_else_branch = bool(re.search(
        r"}\s*else\s*\{", content
    ))

    if has_three_arg and has_two_arg and has_else_branch:
        score += 0.50
        details.append("Proper if/else with 3-arg and 2-arg startForeground")
    elif has_three_arg and has_two_arg:
        score += 0.35
        details.append("Both 3-arg and 2-arg present but branching unclear")
    elif has_two_arg:
        score += 0.15
        details.append("Only 2-arg present (removed 3-arg entirely)")
    else:
        details.append("FAIL: Missing proper startForeground branching")

    # Notification built before branch (0.25)
    notification_built = bool(re.search(
        r"(val|var)\s+notification\s*=.*Notification\.Builder",
        content, re.DOTALL
    )) or bool(re.search(
        r"(val|var)\s+\w+\s*=.*NotificationCompat\.Builder",
        content, re.DOTALL
    ))
    if notification_built and has_two_arg:
        score += 0.25
        details.append("Notification properly built before version branch")
    else:
        details.append("INFO: Notification construction pattern unclear")

    return {"score": min(score, 1.0), "details": details}


def check_screen_recording_api_guard(ws: Path) -> dict:
    """Check screen recording controller has proper API 34+ guard."""
    score = 0.0
    details = []

    ctrl_file = _find_file(ws, "OverlayScreenRecordingController.kt")
    if not ctrl_file:
        all_kt = _find_files(ws, "*.kt")
        for f in all_kt:
            c = _read(f)
            if "ScreenRecording" in c or "registerScreenCaptureCallback" in c:
                ctrl_file = f
                break

    if not ctrl_file:
        return {"score": 0.0, "details": ["ScreenRecordingController not found"]}

    content = _read(ctrl_file)

    # Has version check (0.25)
    has_version_check = (
        "SDK_INT" in content or
        "Build.VERSION" in content
    )
    if has_version_check:
        score += 0.25
        details.append("Version check present")
    else:
        details.append("FAIL: No version check")
        return {"score": 0.0, "details": details}

    # Correct API level (0.35)
    has_correct_level = (
        "UPSIDE_DOWN_CAKE" in content or
        ">= 34" in content
    )
    if has_correct_level:
        score += 0.35
        details.append("Correct API 34 / UPSIDE_DOWN_CAKE")
    else:
        score += 0.10
        details.append("Version check present but level may be wrong")

    # Guard pattern (0.40)
    has_early_return = bool(re.search(
        r"if\s*\(.*SDK_INT\s*<.*\)\s*(return|return@)",
        content
    ))
    has_wrap_pattern = bool(re.search(
        r"if\s*\(.*SDK_INT\s*>=.*\)\s*\{",
        content
    )) and "registerScreenCaptureCallback" in content

    if has_early_return or has_wrap_pattern:
        score += 0.40
        details.append("Proper guard pattern (early return or wrapping)")
    else:
        details.append("FAIL: No proper guard pattern around API call")

    return {"score": min(score, 1.0), "details": details}


def check_manifest_permission_guard(ws: Path) -> dict:
    """Check manifest has proper version guards on API 34+ permissions."""
    score = 0.0
    details = []

    manifest = _find_file(ws, "AndroidManifest.xml")
    if not manifest:
        return {"score": 0.0, "details": ["AndroidManifest.xml not found"]}

    content = _read(manifest)

    # FOREGROUND_SERVICE_SPECIAL_USE guarded (0.40)
    has_special_use_guard = (
        'tools:ignore' in content and "FOREGROUND_SERVICE_SPECIAL_USE" in content or
        'tools:targetApi' in content and "FOREGROUND_SERVICE_SPECIAL_USE" in content or
        'minSdkVersion="34"' in content
    )
    if has_special_use_guard:
        score += 0.40
        details.append("FOREGROUND_SERVICE_SPECIAL_USE guarded")
    elif "FOREGROUND_SERVICE_SPECIAL_USE" not in content:
        score += 0.30
        details.append("FOREGROUND_SERVICE_SPECIAL_USE removed (acceptable)")
    else:
        details.append("FAIL: FOREGROUND_SERVICE_SPECIAL_USE not guarded")

    # DETECT_SCREEN permissions guarded (0.40)
    detect_removed = "DETECT_SCREEN" not in content
    if detect_removed:
        score += 0.40
        details.append("DETECT_SCREEN permissions removed entirely (acceptable)")
    else:
        detect_guarded = (
            bool(re.search(r"DETECT_SCREEN[^>]*(tools:ignore|tools:targetApi|minSdkVersion)", content)) or
            bool(re.search(r"(tools:ignore|tools:targetApi|minSdkVersion)[^>]*DETECT_SCREEN", content))
        )
        if detect_guarded:
            score += 0.40
            details.append("DETECT_SCREEN permissions properly guarded")
        else:
            details.append("FAIL: DETECT_SCREEN permissions not guarded")

    # Has tools: namespace attribute on permissions (0.20)
    has_tools_on_perms = bool(re.search(
        r"<uses-permission[^>]*tools:(targetApi|ignore)", content
    ))
    if has_tools_on_perms:
        score += 0.20
        details.append("tools: attributes applied to permission elements")
    elif 'minSdkVersion="34"' in content:
        score += 0.15
        details.append("minSdkVersion approach used")
    else:
        details.append("FAIL: No version-aware attributes on permission elements")

    return {"score": min(score, 1.0), "details": details}


# ---------------------------------------------------------------------------
# HIDDEN-EASY CHECKS — Structural integrity, all passing solutions should get these
# ---------------------------------------------------------------------------

def check_hidden_easy(ws: Path) -> dict:
    """Hidden easy checks: basic structural integrity that any correct fix should satisfy.

    These verify the fix doesn't break basic compilation-like properties.
    Any agent that actually modifies the files correctly will pass these.
    """
    score = 0.0
    details = []

    all_kt_files = _find_files(ws, "*.kt")
    if not all_kt_files:
        return {"score": 0.0, "details": ["No Kotlin files found"]}

    all_content = {}
    for f in all_kt_files:
        all_content[f.name] = _read(f)

    # Easy-1: Brace matching in all files (0.25)
    brace_ok = True
    for name, content in all_content.items():
        opens = content.count("{")
        closes = content.count("}")
        if opens != closes:
            brace_ok = False
            details.append(f"FAIL: Mismatched braces in {name}")
            break
    if brace_ok:
        score += 0.25
        details.append("Brace matching OK in all files")

    # Easy-2: App class structure preserved (0.25)
    app_content = all_content.get("HyperIsleApp.kt", "")
    has_proper_structure = (
        "class HyperIsleApp" in app_content and
        "Application" in app_content and
        "onCreate" in app_content
    )
    if has_proper_structure:
        score += 0.25
        details.append("App class structure preserved correctly")
    else:
        details.append("FAIL: App class structure broken")

    # Easy-3: No duplicate class declarations across files (0.25)
    class_names = []
    for name, content in all_content.items():
        classes = re.findall(r"(?:class|object|interface)\s+(\w+)", content)
        for c in classes:
            class_names.append((c, name))

    seen = {}
    duplicates = []
    for cls, fname in class_names:
        if cls in seen and seen[cls] != fname:
            duplicates.append(cls)
        seen[cls] = fname

    if not duplicates:
        score += 0.25
        details.append("No duplicate class declarations")
    else:
        details.append(f"FAIL: Duplicate classes: {duplicates[:3]}")

    # Easy-4: Original interfaces still defined (0.25)
    # The fix should preserve FeatureFlagRepository and PremiumGate interfaces
    all_kt_text = "\n".join(all_content.values())
    has_ffr_interface = "interface FeatureFlagRepository" in all_kt_text
    has_pg_interface = "interface PremiumGate" in all_kt_text
    has_ve_interface = bool(re.search(
        r"(interface|abstract\s+class)\s+VersionEnforcer", all_kt_text
    ))
    if has_ffr_interface and has_pg_interface and has_ve_interface:
        score += 0.25
        details.append("All original interfaces preserved")
    elif has_ffr_interface and has_pg_interface:
        score += 0.15
        details.append("Most interfaces preserved")
    else:
        details.append("FAIL: Original interfaces removed or broken")

    return {"score": min(score, 1.0), "details": details}


# ---------------------------------------------------------------------------
# HIDDEN-HARD CHECKS — Deep quality patterns only strong agents produce
# ---------------------------------------------------------------------------

def check_hidden_hard(ws: Path) -> dict:
    """Hidden hard checks: advanced quality/correctness only strong agents achieve.

    These test deeper understanding of the problem domain:
    - Fallback behavior correctness (not just existence)
    - Retry patterns with proper cleanup
    - Catch-specificity
    - Cross-file consistency
    - stopMonitoring API guard symmetry
    """
    score = 0.0
    details = []
    max_score = 0.0

    all_kt_files = _find_files(ws, "*.kt")
    all_kt_content = "\n".join(_read(f) for f in all_kt_files)

    # Hard-1: VersionEnforcer fallback returns Allowed (not just exists) (0.12)
    max_score += 0.12
    has_fallback_ve = bool(re.search(
        r"(class|object)\s+\w*(Fallback|NoOp|Default|Stub)\w*\s*.*"
        r":\s*VersionEnforcer",
        all_kt_content,
    ))
    has_correct_fallback_behavior = has_fallback_ve and (
        "Allowed" in all_kt_content or
        "VersionStatus.Allowed" in all_kt_content or
        "VersionCheckResult.Allowed" in all_kt_content
    )
    if has_correct_fallback_behavior:
        score += 0.12
        details.append("Fallback VersionEnforcer returns Allowed status")
    elif has_fallback_ve:
        score += 0.04
        details.append("Fallback VersionEnforcer exists but behavior unclear")
    else:
        details.append("FAIL: No proper fallback VersionEnforcer with correct behavior")

    # Hard-2: FeatureFlagRepository fallback returns false (safe default) (0.10)
    max_score += 0.10
    has_ffr_fallback = bool(re.search(
        r"(class|object)\s+\w*(Fallback|NoOp|Default|Stub)\w*\s*.*"
        r":\s*FeatureFlagRepository",
        all_kt_content,
    ))
    if has_ffr_fallback:
        ffr_match = re.search(
            r"(class|object)\s+\w*(Fallback|NoOp|Default|Stub)\w*\s*.*"
            r":\s*FeatureFlagRepository\s*\{([^}]*)\}",
            all_kt_content, re.DOTALL
        )
        if ffr_match and "false" in ffr_match.group(3):
            score += 0.10
            details.append("FeatureFlagRepository fallback returns safe false default")
        else:
            score += 0.04
            details.append("FeatureFlagRepository fallback exists but safe default unclear")
    else:
        has_inline_ffr = bool(re.search(
            r"featureFlagRepository\s*=\s*object\s*:\s*FeatureFlagRepository",
            all_kt_content,
        ))
        if has_inline_ffr:
            score += 0.06
            details.append("FeatureFlagRepository inline fallback present")
        else:
            details.append("FAIL: No FeatureFlagRepository fallback")

    # Hard-3: PremiumGate fallback denies premium (safe default) (0.10)
    max_score += 0.10
    has_pg_fallback = bool(re.search(
        r"(class|object)\s+\w*(Fallback|NoOp|Default|Stub)\w*\s*.*"
        r":\s*PremiumGate",
        all_kt_content,
    ))
    if has_pg_fallback:
        pg_match = re.search(
            r"(class|object)\s+\w*(Fallback|NoOp|Default|Stub)\w*\s*.*"
            r":\s*PremiumGate\s*\{([^}]*)\}",
            all_kt_content, re.DOTALL
        )
        if pg_match and "false" in pg_match.group(3):
            score += 0.10
            details.append("PremiumGate fallback denies premium (safe)")
        else:
            score += 0.04
            details.append("PremiumGate fallback exists but safety unclear")
    else:
        has_inline_pg = bool(re.search(
            r"premiumGate\s*=\s*object\s*:\s*PremiumGate",
            all_kt_content,
        ))
        if has_inline_pg:
            score += 0.05
            details.append("PremiumGate inline fallback present")
        else:
            details.append("FAIL: No PremiumGate fallback")

    # Hard-4: EncryptedPrefs retry pattern (delete + retry create, not just fallback) (0.14)
    max_score += 0.14
    prefs_file = _find_file(ws, "SecurePrefsManager.kt")
    prefs_content = _read(prefs_file) if prefs_file else ""
    if not prefs_content:
        for f in all_kt_files:
            c = _read(f)
            if "EncryptedSharedPreferences" in c:
                prefs_content = c
                break

    esp_create_count = len(re.findall(r"EncryptedSharedPreferences\s*\.\s*create", prefs_content))
    has_retry = esp_create_count >= 2 or "retry" in prefs_content.lower() or bool(re.search(
        r"(for|while|repeat)\s*\(", prefs_content
    ))
    has_delete_entry = "deleteEntry" in prefs_content
    has_keystore_instance = bool(re.search(r"KeyStore\s*\.\s*getInstance", prefs_content))

    if has_delete_entry and has_keystore_instance and has_retry:
        score += 0.14
        details.append("Full KeyStore cleanup + retry pattern in encrypted prefs")
    elif has_delete_entry and has_keystore_instance:
        score += 0.08
        details.append("KeyStore cleanup present but no retry")
    elif has_delete_entry or "KeyStore" in prefs_content:
        score += 0.04
        details.append("Partial KeyStore handling")
    else:
        details.append("FAIL: No KeyStore cleanup/retry logic")

    # Hard-5: Catches specific crypto/security exceptions (not just generic Exception) (0.12)
    max_score += 0.12
    has_specific_catch = bool(re.search(
        r"catch\s*\(\s*\w+\s*:\s*(GeneralSecurityException|"
        r"InvalidKeyException|KeyStoreException|"
        r"InvalidProtocolBufferException|"
        r"SecurityException|IOException)",
        prefs_content,
    ))
    has_generic_catch = bool(re.search(r"catch\s*\(\s*\w+\s*:\s*(Exception|Throwable)\s*\)", prefs_content))
    if has_specific_catch:
        score += 0.12
        details.append("Catches specific security/crypto exceptions")
    elif has_generic_catch:
        score += 0.03
        details.append("Catches generic Exception (less robust)")
    else:
        details.append("FAIL: No proper exception catching in prefs")

    # Hard-6: MasterKey alias specifically deleted during cleanup (0.10)
    max_score += 0.10
    master_key_pattern = re.compile(
        r"(hyperisle_feature_control_key|master_key|MASTER_KEY|_androidx_security_master_key_)",
        re.IGNORECASE
    )
    has_master_key_cleanup = (
        master_key_pattern.search(prefs_content) is not None and
        "deleteEntry" in prefs_content
    )
    if has_master_key_cleanup:
        score += 0.10
        details.append("MasterKey alias specifically cleaned up")
    else:
        details.append("INFO: MasterKey alias not specifically targeted in cleanup")

    # Hard-7: stopMonitoring also guards unregisterScreenCaptureCallback (0.12)
    max_score += 0.12
    ctrl_file = _find_file(ws, "OverlayScreenRecordingController.kt")
    ctrl_content = _read(ctrl_file) if ctrl_file else ""

    stop_match = re.search(r"fun\s+stopMonitoring\s*\(\s*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}", ctrl_content, re.DOTALL)
    if stop_match:
        stop_body = stop_match.group(1)
        has_unregister = "unregisterScreenCaptureCallback" in stop_body or "unregister" in stop_body
        has_version_guard = "SDK_INT" in stop_body or "Build.VERSION" in stop_body
        if has_unregister and has_version_guard:
            score += 0.12
            details.append("stopMonitoring has API guard for unregister")
        elif has_unregister:
            score += 0.05
            details.append("stopMonitoring unregisters but no version guard")
        else:
            details.append("INFO: stopMonitoring does not unregister")
    else:
        details.append("INFO: stopMonitoring function not found")

    # Hard-8: @RequiresApi annotation on screen recording functions (0.08)
    max_score += 0.08
    has_requires_api = bool(re.search(
        r"@RequiresApi\s*\(\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)\s*\)",
        ctrl_content
    ))
    if has_requires_api:
        score += 0.08
        details.append("@RequiresApi annotation present on screen recording")
    else:
        details.append("INFO: No @RequiresApi annotation")

    # Hard-9: Manifest uses tools:targetApi (preferred over tools:ignore) (0.06)
    max_score += 0.06
    manifest = _find_file(ws, "AndroidManifest.xml")
    manifest_content = _read(manifest) if manifest else ""
    if 'tools:targetApi' in manifest_content:
        score += 0.06
        details.append("Manifest uses tools:targetApi (preferred)")
    elif 'tools:ignore' in manifest_content:
        score += 0.02
        details.append("Manifest uses tools:ignore (acceptable but less precise)")
    else:
        details.append("INFO: No tools:targetApi in manifest")

    # Hard-10: Logging in encrypted prefs fallback path (0.06)
    max_score += 0.06
    has_logging = bool(re.search(r"(Log\.\w|Timber\.\w|logger\.\w)", prefs_content))
    if has_logging:
        score += 0.06
        details.append("Logging present in prefs fallback path")
    else:
        details.append("FAIL: No logging in prefs fallback")

    # Normalize: max possible is 1.0
    normalized = score / max_score if max_score > 0 else 0.0
    return {"score": round(min(normalized, 1.0), 4), "details": details}


# ---------------------------------------------------------------------------
# GRADING AGGREGATION
# ---------------------------------------------------------------------------

def grade_workspace(ws: Path) -> dict:
    """Grade the full workspace with tiered scoring for discrimination.

    Weight distribution:
      Visible checks: ~55% (basic correctness any attempt should partially score)
      Hidden-easy:    ~15% (structural integrity, all passing solutions get full)
      Hidden-hard:    ~30% (deep quality, only strong agents score well)

    Hidden total = 15% + 30% = 45% >= 30% requirement.
    """
    components = {}

    # Visible checks
    components["lateinit_fallback"] = check_lateinit_fallback(ws)
    components["encrypted_prefs_fallback"] = check_encrypted_prefs_fallback(ws)
    components["foreground_service_guard"] = check_foreground_service_api_guard(ws)
    components["screen_recording_guard"] = check_screen_recording_api_guard(ws)
    components["manifest_permission_guard"] = check_manifest_permission_guard(ws)

    # Hidden checks (tiered)
    components["hidden_easy"] = check_hidden_easy(ws)
    components["hidden_hard"] = check_hidden_hard(ws)

    # Weights: hidden_easy (15%) + hidden_hard (30%) = 45% hidden
    weights = {
        "lateinit_fallback": 0.16,
        "encrypted_prefs_fallback": 0.14,
        "foreground_service_guard": 0.12,
        "screen_recording_guard": 0.07,
        "manifest_permission_guard": 0.06,
        "hidden_easy": 0.15,
        "hidden_hard": 0.30,
    }

    overall = sum(weights[k] * components[k]["score"] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v["score"], 4) for k, v in components.items()},
        "details": {k: v["details"] for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace/fixtures/hyperisle-app")
    if not ws.exists():
        ws = Path("/workspace/hyperisle-app")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
