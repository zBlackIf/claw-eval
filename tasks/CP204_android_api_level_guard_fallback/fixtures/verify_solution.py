"""Hidden verifier for CP204 - Android API Level Guard & Fallback Patterns."""
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
    """Find a file by name recursively."""
    for p in base.rglob(name):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for Android 9 / Huawei compatibility fixes."""
    base = ws / "hyperisle-app"
    if not base.exists():
        # Fallback: check if files are directly in workspace
        base = ws

    components = {k: 0.0 for k in [
        "foreground_api_guard",
        "lateinit_fallback",
        "encrypted_prefs_fallback",
        "version_enforcer_timeout",
        "screen_capture_api_guard",
        "overlay_permission_huawei",
    ]}

    # 1. Check foreground service API level guard (weight: 0.25)
    fg_ctrl = _find_file(base, "OverlayForegroundController.kt")
    if fg_ctrl and fg_ctrl.exists():
        c = _read(fg_ctrl)
        has_version_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*>=?\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            c
        ))
        has_plain_startforeground = bool(re.search(
            r'startForeground\s*\(\s*\w+\s*,\s*\w+\s*\)',
            c
        ))
        has_typed_startforeground = bool(re.search(
            r'startForeground\s*\(.+FOREGROUND_SERVICE_TYPE_SPECIAL_USE',
            c, re.DOTALL
        )) or bool(re.search(
            r'startForeground\s*\(.+ServiceInfo\.',
            c, re.DOTALL
        ))
        # Must have the version check AND both code paths
        if has_version_check and has_plain_startforeground and has_typed_startforeground:
            components["foreground_api_guard"] = 1.0
        elif has_version_check and (has_plain_startforeground or has_typed_startforeground):
            components["foreground_api_guard"] = 0.6
        elif has_version_check:
            components["foreground_api_guard"] = 0.3

    # 2. Check lateinit -> fallback pattern (weight: 0.20)
    app_file = _find_file(base, "HyperIsleApp.kt")
    if app_file and app_file.exists():
        c = _read(app_file)
        # Check for fallback version enforcer (no more lateinit for versionEnforcer)
        no_lateinit_ve = "lateinit var versionEnforcer" not in c
        has_fallback_class = bool(re.search(
            r'(Fallback|NoOp|Default|Stub)\w*VersionEnforcer', c
        )) or bool(re.search(
            r'(Fallback|NoOp|Default|Stub)\w*VersionEnforcer',
            _read_all_kt(base)
        ))
        has_fallback_assignment_in_catch = bool(re.search(
            r'catch\s*\([^)]+\)\s*\{[^}]*(versionEnforcer|fallback)',
            c, re.DOTALL | re.IGNORECASE
        ))
        has_default_init = bool(re.search(
            r'var\s+versionEnforcer\s*[:\s].*=\s*\w+',
            c
        ))

        score = 0.0
        if no_lateinit_ve or has_default_init:
            score += 0.4
        if has_fallback_class:
            score += 0.4
        if has_fallback_assignment_in_catch:
            score += 0.2
        elif has_default_init:
            score += 0.2
        components["lateinit_fallback"] = min(score, 1.0)

    # 3. Check EncryptedSharedPreferences fallback (weight: 0.20)
    if app_file and app_file.exists():
        c = _read(app_file)
        has_try_catch_in_prefs = bool(re.search(
            r'(createEncryptedPrefs|EncryptedSharedPreferences)[^}]*try\s*\{',
            c, re.DOTALL
        )) or bool(re.search(
            r'try\s*\{[^}]*EncryptedSharedPreferences',
            c, re.DOTALL
        ))
        has_fallback_prefs = bool(re.search(
            r'getSharedPreferences\s*\(',
            c
        ))
        has_keystore_delete = bool(re.search(
            r'deleteEntry|deleteFeatureControlMasterKey|KeyStore',
            c
        ))
        has_retry = bool(re.search(
            r'(retry|second.*try|attempt|again)',
            c, re.IGNORECASE
        )) or c.count('EncryptedSharedPreferences.create') >= 2

        score = 0.0
        if has_try_catch_in_prefs:
            score += 0.3
        if has_keystore_delete and has_retry:
            score += 0.3
        elif has_keystore_delete:
            score += 0.15
        if has_fallback_prefs:
            score += 0.4
        components["encrypted_prefs_fallback"] = min(score, 1.0)

    # 4. Check VersionEnforcer timeout (weight: 0.15)
    ve_file = _find_file(base, "VersionEnforcer.kt")
    ve_impl_file = _find_file(base, "VersionEnforcerImpl.kt")
    ve_content = ""
    if ve_file:
        ve_content = _read(ve_file)
    if ve_impl_file:
        ve_content += "\n" + _read(ve_impl_file)
    # Also check HyperIsleApp for timeout wrapping
    app_content = _read(app_file) if app_file else ""
    all_content = ve_content + "\n" + app_content

    has_with_timeout = bool(re.search(r'withTimeout\s*\(', all_content))
    has_timeout_value = bool(re.search(r'withTimeout\s*\(\s*\d+', all_content))
    has_timeout_catch = bool(re.search(
        r'(TimeoutCancellationException|TimeoutException)',
        all_content
    ))
    has_cache_fallback_on_timeout = bool(re.search(
        r'(cache|cached|getMinimumVersion|Allowed)',
        all_content
    )) and has_timeout_catch

    score = 0.0
    if has_with_timeout or has_timeout_value:
        score += 0.5
    if has_timeout_catch:
        score += 0.25
    if has_cache_fallback_on_timeout:
        score += 0.25
    components["version_enforcer_timeout"] = min(score, 1.0)

    # 5. Check screen capture/recording API guard (weight: 0.10)
    sc_detector = _find_file(base, "ScreenCaptureDetectorActivity.kt")
    sc_recording = _find_file(base, "OverlayScreenRecordingController.kt")
    sc_score = 0.0

    if sc_detector and sc_detector.exists():
        c = _read(sc_detector)
        has_api_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*>=?\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            c
        ))
        has_early_return = bool(re.search(r'(finish\(\)|return)', c))
        if has_api_check and has_early_return:
            sc_score += 0.5
        elif has_api_check:
            sc_score += 0.3

    if sc_recording and sc_recording.exists():
        c = _read(sc_recording)
        has_api_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*>=?\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            c
        ))
        has_early_return = "return" in c and has_api_check
        if has_api_check and has_early_return:
            sc_score += 0.5
        elif has_api_check:
            sc_score += 0.3

    components["screen_capture_api_guard"] = min(sc_score, 1.0)

    # 6. Check Huawei overlay permission fallback (weight: 0.10)
    perm_file = _find_file(base, "OverlayPermissionChecker.kt")
    if perm_file and perm_file.exists():
        c = _read(perm_file)
        has_huawei_intent = bool(re.search(
            r'com\.huawei\.(systemmanager|permissionmanager)',
            c
        ))
        has_resolve_check = bool(re.search(
            r'resolveActivity|queryIntentActivities',
            c
        ))
        has_fallback_chain = bool(re.search(
            r'(ACTION_SETTINGS|ACTION_APPLICATION_DETAILS_SETTINGS)',
            c
        ))
        has_try_catch = bool(re.search(
            r'(try\s*\{|ActivityNotFoundException)',
            c
        ))

        score = 0.0
        if has_huawei_intent:
            score += 0.4
        if has_resolve_check or has_try_catch:
            score += 0.3
        if has_fallback_chain:
            score += 0.3
        components["overlay_permission_huawei"] = min(score, 1.0)

    # Calculate overall score
    weights = {
        "foreground_api_guard": 0.25,
        "lateinit_fallback": 0.20,
        "encrypted_prefs_fallback": 0.20,
        "version_enforcer_timeout": 0.15,
        "screen_capture_api_guard": 0.10,
        "overlay_permission_huawei": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _read_all_kt(base: Path) -> str:
    """Read all Kotlin files concatenated for cross-file search."""
    texts = []
    for p in base.rglob("*.kt"):
        try:
            texts.append(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            pass
    return "\n".join(texts)


def main():
    # Try /workspace/fixtures/hyperisle-app first, then /workspace/hyperisle-app, then /workspace
    ws = Path("/workspace/fixtures/hyperisle-app")
    if not ws.exists():
        ws = Path("/workspace/hyperisle-app")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
