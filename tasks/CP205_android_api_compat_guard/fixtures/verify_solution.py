"""Hidden verifier for CP205 — Android API Compatibility Guards.

Tiered hidden-check design for discrimination:

VISIBLE checks (basic, from the prompt — any agent that reads instructions passes):
  V1. foreground_api34_guard — has version check + both startForeground variants
  V2. version_enforcer_fallback — FallbackVersionEnforcer exists + no lateinit crash
  V3. screen_recording_api_guard — has SDK_INT check + early return
  V4. screen_capture_api_guard — has SDK_INT check + finish()
  V5. encrypted_prefs_fallback — try-catch around EncryptedSharedPreferences

HIDDEN-EASY checks (any competent agent passes — test basic correctness):
  HE1. foreground_has_both_calls — both typed and plain startForeground present
  HE2. fallback_implements_interface — FallbackVersionEnforcer has 'override' keyword
  HE3. screen_capture_has_oncreate_guard — version check is inside onCreate
  HE4. encrypted_prefs_has_return — catch block returns a SharedPreferences (not null)

HIDDEN-HARD checks (only strong agents pass — test deep domain understanding):
  HH1. foreground_correct_branch_structure — proper if/else with typed in >= branch
  HH2. fallback_stateflow_allowed_default — StateFlow(VersionStatus.Allowed), not Checking
  HH3. screen_recording_guards_both_methods — guard in BOTH register() AND unregister()
  HH4. screen_capture_early_return_before_register — finish()+return BEFORE callback reg
  HH5. encrypted_prefs_specific_catch — catches specific exception, not bare Exception
  HH6. init_order_safety — field default set before initializeFeatureControl can throw

Weight budget:
  Visible: 40%  |  Hidden-Easy: 15%  |  Hidden-Hard: 45%
  (Hidden total = 60%, well above 30% floor)
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
    """Find a file matching glob pattern recursively."""
    for p in base.rglob(pattern):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    # Try both possible paths
    project_root = ws / "fixtures" / "HyperIsle2"
    if not project_root.exists():
        project_root = ws / "HyperIsle2"
    if not project_root.exists():
        # Try to find it anywhere under workspace
        for candidate in ws.rglob("HyperIsle2"):
            if candidate.is_dir():
                project_root = candidate
                break

    app_src = project_root / "app" / "src" / "main" / "java" / "com" / "coni" / "hyperisle"
    overlay_dir = app_src / "overlay"
    app_dir = app_src / "app"
    version_dir = project_root / "core-version-enforcement" / "src" / "main" / "java" / "com" / "coni" / "hyperisle" / "core" / "versionenforcement"

    components = {k: 0.0 for k in [
        # Visible (from prompt)
        "foreground_api34_guard",
        "version_enforcer_fallback",
        "screen_recording_api_guard",
        "screen_capture_api_guard",
        "encrypted_prefs_fallback",
        # Hidden-Easy (basic correctness, most agents pass)
        "he_foreground_has_both_calls",
        "he_fallback_implements_interface",
        "he_screen_capture_oncreate_guard",
        "he_encrypted_prefs_has_return",
        # Hidden-Hard (domain understanding, only strong agents pass)
        "hh_foreground_correct_branch",
        "hh_fallback_stateflow_allowed",
        "hh_screen_recording_both_methods",
        "hh_screen_capture_early_return",
        "hh_encrypted_prefs_specific_catch",
        "hh_init_order_safety",
    ]}

    # =========================================================================
    # 1. OverlayForegroundController
    # =========================================================================
    fg_ctrl = _find_file(overlay_dir, "OverlayForegroundController.kt") if overlay_dir.exists() else None
    if fg_ctrl and fg_ctrl.exists():
        c = _read(fg_ctrl)
        has_version_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*[<>=!]+\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            c
        ))
        has_plain_start_foreground = bool(re.search(
            r'startForeground\s*\(\s*\w+\s*,\s*\w+\s*\)',
            c
        ))
        has_typed_start_foreground = bool(re.search(
            r'startForeground\s*\([^)]*FOREGROUND_SERVICE_TYPE_SPECIAL_USE[^)]*\)',
            c
        )) or bool(re.search(
            r'startForeground\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+',
            c
        ))

        # --- V1: Visible basic check ---
        if has_version_check and has_plain_start_foreground and has_typed_start_foreground:
            components["foreground_api34_guard"] = 1.0
        elif has_version_check and (has_plain_start_foreground or has_typed_start_foreground):
            components["foreground_api34_guard"] = 0.7
        elif has_version_check:
            components["foreground_api34_guard"] = 0.4

        # --- HE1: Hidden-Easy — both call variants present ---
        if has_plain_start_foreground and has_typed_start_foreground:
            components["he_foreground_has_both_calls"] = 1.0
        elif has_plain_start_foreground or has_typed_start_foreground:
            components["he_foreground_has_both_calls"] = 0.5

        # --- HH1: Hidden-Hard — proper if/else branching with typed in >= branch ---
        has_proper_branching = bool(re.search(
            r'if\s*\(\s*Build\.VERSION\.SDK_INT\s*>=?\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)\s*\)'
            r'[\s\S]{0,200}?startForeground[\s\S]{0,200}?\}\s*else\s*\{[\s\S]{0,200}?startForeground',
            c
        )) or bool(re.search(
            r'if\s*\(\s*Build\.VERSION\.SDK_INT\s*<\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)\s*\)'
            r'[\s\S]{0,200}?startForeground[\s\S]{0,200}?\}\s*else\s*\{[\s\S]{0,200}?startForeground',
            c
        )) or bool(re.search(
            r'when\s*\{[\s\S]{0,400}?SDK_INT[\s\S]{0,400}?startForeground[\s\S]{0,400}?startForeground',
            c
        ))
        correct_typed_in_ge_branch = bool(re.search(
            r'if\s*\(\s*Build\.VERSION\.SDK_INT\s*>=?\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)\s*\)'
            r'[\s\S]{0,200}?(FOREGROUND_SERVICE_TYPE_SPECIAL_USE|ServiceInfo\.\w+)',
            c
        )) or bool(re.search(
            r'if\s*\(\s*Build\.VERSION\.SDK_INT\s*<\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)\s*\)'
            r'[\s\S]{0,200}?startForeground\s*\(\s*\w+\s*,\s*\w+\s*\)',
            c
        ))
        if has_proper_branching and correct_typed_in_ge_branch:
            components["hh_foreground_correct_branch"] = 1.0
        elif has_proper_branching:
            components["hh_foreground_correct_branch"] = 0.6

    # =========================================================================
    # 2. VersionEnforcer / FallbackVersionEnforcer
    # =========================================================================
    fallback_file = None
    if version_dir.exists():
        fallback_file = _find_file(version_dir, "Fallback*Enforcer*.kt")
    if not fallback_file and app_dir.exists():
        fallback_file = _find_file(app_dir, "Fallback*Enforcer*.kt")
    if not fallback_file and project_root.exists():
        fallback_file = _find_file(project_root, "Fallback*Enforcer*.kt")
    # Also try searching by content if file pattern doesn't match
    if not fallback_file:
        for kt_file in project_root.rglob("*.kt"):
            content = _read(kt_file)
            if "FallbackVersionEnforcer" in content and "class" in content:
                fallback_file = kt_file
                break

    app_file = _find_file(app_dir, "HyperIsleApp.kt") if app_dir.exists() else None

    # --- V2: Visible — fallback exists + no lateinit crash ---
    fallback_score = 0.0
    if fallback_file and fallback_file.exists():
        fc = _read(fallback_file)
        has_version_enforcer_impl = "VersionEnforcer" in fc
        has_allowed = "Allowed" in fc
        if has_version_enforcer_impl and has_allowed:
            fallback_score += 0.5
        elif has_version_enforcer_impl:
            fallback_score += 0.3

    if app_file and app_file.exists():
        ac = _read(app_file)
        has_no_lateinit_version = "lateinit" not in ac or "lateinit var versionEnforcer" not in ac
        has_fallback_default = bool(re.search(
            r'var\s+versionEnforcer\s*[:\s].*=\s*\w*[Ff]allback',
            ac
        )) or bool(re.search(
            r'versionEnforcer\s*=\s*\w*[Ff]allback',
            ac
        ))
        has_try_catch = "try" in ac and "catch" in ac

        if has_no_lateinit_version and has_fallback_default:
            fallback_score += 0.5
        elif has_no_lateinit_version and has_try_catch:
            fallback_score += 0.3
        elif has_try_catch:
            fallback_score += 0.2

    components["version_enforcer_fallback"] = min(1.0, fallback_score)

    # --- HE2: Hidden-Easy — FallbackVersionEnforcer implements interface ---
    if fallback_file and fallback_file.exists():
        fc = _read(fallback_file)
        has_override = "override" in fc
        has_allowed = "Allowed" in fc
        has_class_decl = bool(re.search(r'class\s+\w*Fallback\w*.*:', fc))
        if has_override and has_allowed and has_class_decl:
            components["he_fallback_implements_interface"] = 1.0
        elif has_override and has_allowed:
            components["he_fallback_implements_interface"] = 0.8
        elif has_override or has_class_decl:
            components["he_fallback_implements_interface"] = 0.4

    # --- HH2: Hidden-Hard — StateFlow(VersionStatus.Allowed) default ---
    deep_stateflow_score = 0.0
    if fallback_file and fallback_file.exists():
        fc = _read(fallback_file)
        has_stateflow_allowed = bool(re.search(
            r'MutableStateFlow\s*\(\s*VersionStatus\.Allowed\s*\)',
            fc
        )) or bool(re.search(
            r'stateFlowOf\s*\(\s*VersionStatus\.Allowed\s*\)',
            fc
        )) or bool(re.search(
            r'StateFlow.*Allowed',
            fc
        ))
        wrong_default = bool(re.search(
            r'MutableStateFlow\s*\(\s*VersionStatus\.Checking\s*\)',
            fc
        ))
        returns_allowed = bool(re.search(
            r'checkVersion[\s\S]{0,100}?(VersionCheckResult\.Allowed|return.*Allowed)',
            fc
        ))
        has_override = "override" in fc

        if has_stateflow_allowed and returns_allowed and has_override and not wrong_default:
            deep_stateflow_score = 1.0
        elif has_stateflow_allowed and has_override:
            deep_stateflow_score = 0.7
        elif has_override and returns_allowed:
            deep_stateflow_score = 0.5
        elif "Allowed" in fc and "override" in fc:
            deep_stateflow_score = 0.3
    components["hh_fallback_stateflow_allowed"] = deep_stateflow_score

    # =========================================================================
    # 3. ScreenRecordingController
    # =========================================================================
    sr_ctrl = _find_file(overlay_dir, "OverlayScreenRecordingController.kt") if overlay_dir.exists() else None
    if sr_ctrl and sr_ctrl.exists():
        c = _read(sr_ctrl)
        has_version_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*[<>=!]+\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            c
        ))
        has_early_return = "return" in c

        # --- V3: Visible — has version guard + early return ---
        if has_version_check and has_early_return:
            components["screen_recording_api_guard"] = 1.0
        elif has_version_check:
            components["screen_recording_api_guard"] = 0.6

        # --- HH3: Hidden-Hard — guard in BOTH register() AND unregister() ---
        register_match = re.search(
            r'fun\s+register\s*\(\s*\)[\s\S]*?(?=fun\s+\w|\Z)',
            c
        )
        unregister_match = re.search(
            r'fun\s+unregister\s*\(\s*\)[\s\S]*?(?=fun\s+\w|\Z)',
            c
        )
        register_guarded = False
        unregister_guarded = False

        if register_match:
            reg_body = register_match.group(0)
            register_guarded = bool(re.search(
                r'Build\.VERSION\.SDK_INT\s*[<>=!]+\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
                reg_body
            ))
        if unregister_match:
            unreg_body = unregister_match.group(0)
            unregister_guarded = bool(re.search(
                r'Build\.VERSION\.SDK_INT\s*[<>=!]+\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
                unreg_body
            ))

        if register_guarded and unregister_guarded:
            components["hh_screen_recording_both_methods"] = 1.0
        elif register_guarded:
            components["hh_screen_recording_both_methods"] = 0.4

    # =========================================================================
    # 4. ScreenCaptureDetectorActivity
    # =========================================================================
    sc_activity = _find_file(overlay_dir, "ScreenCaptureDetectorActivity.kt") if overlay_dir.exists() else None
    if sc_activity and sc_activity.exists():
        c = _read(sc_activity)
        has_version_check = bool(re.search(
            r'Build\.VERSION\.SDK_INT\s*[<>=!]+\s*(Build\.VERSION_CODES\.UPSIDE_DOWN_CAKE|34)',
            c
        ))
        has_finish = "finish()" in c

        # --- V4: Visible — version check + finish() ---
        if has_version_check and has_finish:
            components["screen_capture_api_guard"] = 1.0
        elif has_version_check:
            components["screen_capture_api_guard"] = 0.5

        # --- HE3: Hidden-Easy — version check is inside onCreate ---
        oncreate_match = re.search(
            r'override\s+fun\s+onCreate[\s\S]*?\{([\s\S]*)',
            c
        )
        if oncreate_match:
            oncreate_body = oncreate_match.group(1)
            has_version_in_oncreate = bool(re.search(
                r'Build\.VERSION\.SDK_INT',
                oncreate_body
            ))
            has_finish_in_oncreate = "finish()" in oncreate_body
            if has_version_in_oncreate and has_finish_in_oncreate:
                components["he_screen_capture_oncreate_guard"] = 1.0
            elif has_version_in_oncreate:
                components["he_screen_capture_oncreate_guard"] = 0.6

            # --- HH4: Hidden-Hard — finish()+return BEFORE registerScreenCaptureCallback ---
            version_pos = -1
            register_pos = -1
            vm = re.search(r'Build\.VERSION\.SDK_INT', oncreate_body)
            rm = re.search(r'registerScreenCaptureCallback|ScreenCaptureCallback', oncreate_body)
            if vm:
                version_pos = vm.start()
            if rm:
                register_pos = rm.start()

            guard_before_register = version_pos >= 0 and (register_pos < 0 or version_pos < register_pos)
            has_finish_return = bool(re.search(
                r'finish\s*\(\s*\)\s*[;\s]*\n?\s*return',
                oncreate_body
            ))

            if guard_before_register and has_finish_return:
                components["hh_screen_capture_early_return"] = 1.0
            elif guard_before_register and "finish()" in oncreate_body:
                components["hh_screen_capture_early_return"] = 0.6
            elif "finish()" in oncreate_body and version_pos >= 0:
                components["hh_screen_capture_early_return"] = 0.3

    # =========================================================================
    # 5. EncryptedSharedPreferences fallback
    # =========================================================================
    if app_file and app_file.exists():
        c = _read(app_file)
        has_try_encrypted = bool(re.search(
            r'try\s*\{[^}]*[Ee]ncrypted',
            c, re.DOTALL
        )) or ("EncryptedSharedPreferences" in c and "catch" in c)
        has_fallback_prefs = bool(re.search(
            r'getSharedPreferences|SharedPreferences',
            c
        )) and ("catch" in c or "fallback" in c.lower())
        has_keystore_recovery = "deleteEntry" in c or "deleteFeatureControlMasterKey" in c or "KeyStore" in c

        # --- V5: Visible — try-catch + fallback prefs ---
        score = 0.0
        if has_try_encrypted:
            score += 0.4
        if has_fallback_prefs:
            score += 0.4
        if has_keystore_recovery:
            score += 0.2
        components["encrypted_prefs_fallback"] = min(1.0, score)

        # --- HE4: Hidden-Easy — catch block returns a SharedPreferences ---
        has_return_in_catch = bool(re.search(
            r'catch[\s\S]{0,300}?(getSharedPreferences|SharedPreferences\.)',
            c, re.DOTALL
        ))
        if has_return_in_catch:
            components["he_encrypted_prefs_has_return"] = 1.0
        elif has_fallback_prefs:
            components["he_encrypted_prefs_has_return"] = 0.5

        # --- HH5: Hidden-Hard — specific exception catch ---
        prefs_fn = re.search(
            r'(fun\s+createEncryptedPrefs|fun\s+create\w*[Pp]refs|fun\s+getEncrypted\w*)\s*\([^)]*\)[\s\S]*?\{([\s\S]*?)(?=\n\s{4}(?:private\s+)?fun\s|\n\})',
            c
        )
        prefs_body = prefs_fn.group(0) if prefs_fn else c

        has_specific_catch = bool(re.search(
            r'catch\s*\(\s*\w+\s*:\s*(GeneralSecurityException|KeyStoreException|InvalidKeyException|IOException)',
            prefs_body
        ))
        has_logged_catch = bool(re.search(
            r'catch\s*\([^)]+\)\s*\{[^}]*(Log\.|UiLog\.|Timber\.|logger\.|println|e\.message|e\.stackTrace)',
            prefs_body, re.DOTALL
        ))
        has_retry = bool(re.search(
            r'(deleteEntry|deleteMasterKey|delete\w*Key)[\s\S]{0,200}?(EncryptedSharedPreferences|MasterKey)',
            prefs_body, re.DOTALL
        )) or bool(re.search(
            r'(EncryptedSharedPreferences|MasterKey)[\s\S]{0,200}?(deleteEntry|deleteMasterKey|delete\w*Key)',
            prefs_body, re.DOTALL
        ))

        deep_prefs_score = 0.0
        if has_specific_catch:
            deep_prefs_score += 0.4
        elif has_logged_catch:
            deep_prefs_score += 0.2
        if has_return_in_catch:
            deep_prefs_score += 0.3
        if has_retry:
            deep_prefs_score += 0.3
        components["hh_encrypted_prefs_specific_catch"] = min(1.0, deep_prefs_score)

    # =========================================================================
    # HH6: Init order safety in HyperIsleApp
    # =========================================================================
    if app_file and app_file.exists():
        c = _read(app_file)
        has_field_default = bool(re.search(
            r'var\s+versionEnforcer\s*:\s*VersionEnforcer\s*=\s*\w*[Ff]allback',
            c
        ))
        has_private_set_default = bool(re.search(
            r'var\s+versionEnforcer\s*:\s*VersionEnforcer\s*=\s*\w*[Ff]allback\w*\(\)',
            c
        ))
        has_try_around_init = bool(re.search(
            r'try\s*\{[\s\S]{0,200}?initializeFeatureControl[\s\S]{0,200}?\}\s*catch',
            c
        ))
        has_try_inside_init = bool(re.search(
            r'fun\s+initializeFeatureControl[\s\S]{0,50}?\{[\s\S]{0,100}?try',
            c
        ))
        remaining_lateinit_count = len(re.findall(r'lateinit\s+var\s+\w+', c))
        all_lateinit_removed = remaining_lateinit_count == 0

        init_score = 0.0
        if has_field_default or has_private_set_default:
            init_score += 0.5
        if has_try_around_init or has_try_inside_init:
            init_score += 0.3
        if all_lateinit_removed:
            init_score += 0.2
        elif remaining_lateinit_count <= 1:
            init_score += 0.1

        components["hh_init_order_safety"] = min(1.0, init_score)

    # =========================================================================
    # Scoring — tiered weights
    # =========================================================================
    # Visible: 40% total
    visible_weights = {
        "foreground_api34_guard": 0.10,
        "version_enforcer_fallback": 0.10,
        "screen_recording_api_guard": 0.08,
        "screen_capture_api_guard": 0.06,
        "encrypted_prefs_fallback": 0.06,
    }
    # Hidden-Easy: 15% total (easy — most agents get these)
    hidden_easy_weights = {
        "he_foreground_has_both_calls": 0.04,
        "he_fallback_implements_interface": 0.04,
        "he_screen_capture_oncreate_guard": 0.04,
        "he_encrypted_prefs_has_return": 0.03,
    }
    # Hidden-Hard: 45% total (discriminating — only strong agents)
    hidden_hard_weights = {
        "hh_foreground_correct_branch": 0.09,
        "hh_fallback_stateflow_allowed": 0.09,
        "hh_screen_recording_both_methods": 0.09,
        "hh_screen_capture_early_return": 0.07,
        "hh_encrypted_prefs_specific_catch": 0.06,
        "hh_init_order_safety": 0.05,
    }

    all_weights = {**visible_weights, **hidden_easy_weights, **hidden_hard_weights}
    overall = sum(all_weights[k] * components[k] for k in all_weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": all_weights,
    }


def main():
    # Try standard workspace path first
    ws = Path("/workspace")
    if not (ws / "fixtures" / "HyperIsle2").exists() and not (ws / "HyperIsle2").exists():
        # Fallback: look for project dir anywhere in workspace
        for candidate in ws.rglob("HyperIsle2"):
            if candidate.is_dir() and (candidate / "app").exists():
                ws = candidate.parent
                break
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
