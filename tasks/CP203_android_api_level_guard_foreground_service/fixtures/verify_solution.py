"""Hidden verifier for CP203 — Android API Level Guard for Foreground Service.

Checks that the agent properly:
1. Added Build.VERSION.SDK_INT >= 34 guard around FOREGROUND_SERVICE_TYPE_SPECIAL_USE
2. Replaced lateinit with safe defaults (fallback pattern) for versionEnforcer
3. Added API 34+ guard on ScreenCaptureDetectorActivity
4. Added API 34+ guard on OverlayScreenRecordingController
5. Added EncryptedSharedPreferences fallback (try/catch with plain SharedPreferences)
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


def _find_file(base: Path, name: str) -> Path | None:
    """Find a file recursively in the directory tree."""
    if not base.exists():
        return None
    for p in base.rglob(name):
        return p
    return None


def _find_file_pattern(base: Path, pattern: str) -> Path | None:
    """Find a file matching a glob pattern."""
    if not base.exists():
        return None
    for p in base.rglob(pattern):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for Android API level guard fixes."""

    # Try multiple paths for the project
    project_dir = ws / "fixtures" / "hyperisle-app"
    if not project_dir.exists():
        project_dir = ws / "hyperisle-app"
    if not project_dir.exists():
        # Try to find it anywhere
        for candidate in ws.rglob("OverlayForegroundController.kt"):
            project_dir = candidate.parent.parent.parent.parent.parent.parent.parent.parent
            break

    components = {k: 0.0 for k in [
        "foreground_service_api_guard",
        "lateinit_safe_default",
        "screen_capture_api_guard",
        "screen_recording_api_guard",
        "encrypted_prefs_fallback",
    ]}

    # --- Dimension 1: Foreground Service API Guard ---
    fc_file = _find_file(project_dir, "OverlayForegroundController.kt")
    if fc_file:
        content = _read(fc_file)
        # Check for Build.VERSION.SDK_INT check (both >= 34 and < 34 patterns are valid)
        has_version_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*[<>=!]+\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            content
        ))
        # Check that startForeground without type is used for lower APIs
        has_plain_start_foreground = bool(re.search(
            r'startForeground\s*\(\s*\w+\s*,\s*\w+\s*\)',
            content
        ))
        # Check the typed version is guarded
        has_typed_guarded = has_version_check and "FOREGROUND_SERVICE_TYPE_SPECIAL_USE" in content

        score = 0.0
        if has_version_check:
            score += 0.4
        if has_plain_start_foreground:
            score += 0.3
        if has_typed_guarded:
            score += 0.3
        components["foreground_service_api_guard"] = min(score, 1.0)

    # --- Dimension 2: lateinit safe default ---
    app_file = _find_file(project_dir, "HyperIsleApp.kt")
    if app_file:
        content = _read(app_file)
        # Check that lateinit is removed or replaced with safe default
        has_no_lateinit_version_enforcer = "lateinit" not in content or \
            "lateinit var versionEnforcer" not in content
        # Check for fallback/default initialization pattern
        has_fallback_pattern = bool(re.search(
            r'(FallbackVersionEnforcer|NoOpVersionEnforcer|object\s*:\s*VersionEnforcer|'
            r'VersionEnforcer\s*=\s*\w+|var\s+versionEnforcer.*=)',
            content
        ))
        # Check premiumGate and featureFlagRepository also fixed
        has_no_lateinit_premium = "lateinit var premiumGate" not in content
        has_no_lateinit_flags = "lateinit var featureFlagRepository" not in content

        score = 0.0
        if has_no_lateinit_version_enforcer:
            score += 0.35
        if has_fallback_pattern:
            score += 0.35
        if has_no_lateinit_premium and has_no_lateinit_flags:
            score += 0.3
        components["lateinit_safe_default"] = min(score, 1.0)

    # --- Dimension 3: Screen Capture API Guard ---
    sc_file = _find_file(project_dir, "ScreenCaptureDetectorActivity.kt")
    if sc_file:
        content = _read(sc_file)
        has_version_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*[<>=!]+\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            content
        ))
        # Check for early return/finish on lower API
        has_early_exit = bool(re.search(
            r'(finish\(\)|return)', content
        )) and has_version_check

        score = 0.0
        if has_version_check:
            score += 0.6
        if has_early_exit:
            score += 0.4
        components["screen_capture_api_guard"] = min(score, 1.0)

    # --- Dimension 4: Screen Recording API Guard ---
    sr_file = _find_file(project_dir, "OverlayScreenRecordingController.kt")
    if sr_file:
        content = _read(sr_file)
        has_version_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*[<>=!]+\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            content
        ))
        # Check for early return on lower API
        has_early_return = "return" in content and has_version_check

        score = 0.0
        if has_version_check:
            score += 0.6
        if has_early_return:
            score += 0.4
        components["screen_recording_api_guard"] = min(score, 1.0)

    # --- Dimension 5: EncryptedSharedPreferences Fallback ---
    if app_file:
        content = _read(app_file)
        # Check for try-catch specifically inside createEncryptedPrefs (not just the outer init)
        # The fix should wrap EncryptedSharedPreferences.create in try-catch with fallback
        has_try_catch_in_create_prefs = bool(re.search(
            r'(fun\s+createEncryptedPrefs|createEncryptedPrefs)[^{]*\{[^}]*try\s*\{',
            content, re.DOTALL
        )) or bool(re.search(
            r'try\s*\{[^}]*EncryptedSharedPreferences\.create',
            content, re.DOTALL
        ))
        # Check for fallback to regular SharedPreferences
        has_plain_prefs_fallback = bool(re.search(
            r'getSharedPreferences\s*\(',
            content
        ))
        # Check for KeyStore deletion/retry logic
        has_keystore_recovery = bool(re.search(
            r'(deleteEntry|KeyStore\.getInstance|deleteFeatureControlMasterKey|keyStore\s*\.\s*delete)',
            content, re.IGNORECASE
        ))

        score = 0.0
        if has_try_catch_in_create_prefs:
            score += 0.4
        if has_plain_prefs_fallback:
            score += 0.4
        if has_keystore_recovery:
            score += 0.2
        components["encrypted_prefs_fallback"] = min(score, 1.0)

    # Calculate overall weighted score
    weights = {
        "foreground_service_api_guard": 0.30,
        "lateinit_safe_default": 0.25,
        "screen_capture_api_guard": 0.15,
        "screen_recording_api_guard": 0.15,
        "encrypted_prefs_fallback": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try /workspace/fixtures first, then /workspace
    ws = Path("/workspace/fixtures")
    if not ws.exists() or not any(ws.rglob("OverlayForegroundController.kt")):
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
