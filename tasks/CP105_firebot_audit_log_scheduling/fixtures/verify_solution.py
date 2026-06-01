"""Hidden verifier for CP105 — FireBot Audit Log Scheduling."""
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


def _find_files(base: Path, pattern: str) -> list[Path]:
    """Recursively find files matching a glob pattern."""
    return list(base.rglob(pattern))


def grade_workspace(ws: Path) -> dict:
    firebot = ws / "fixtures" / "firebot"
    if not firebot.exists():
        firebot = ws / "firebot"
    src = firebot / "src"
    services = src / "services"

    components = {k: 0.0 for k in [
        "audit_service_exists",
        "hash_chain_integrity",
        "daily_rotation",
        "event_coverage",
        "tamper_detection",
        "cron_scheduling",
        "integration_wiring",
    ]}

    # ====== 1. AuditService exists and has proper structure (0.20) ======
    audit_files = _find_files(src, "*[Aa]udit*[Ss]ervice*")
    if not audit_files:
        audit_files = _find_files(src, "*audit*service*")
    if not audit_files:
        audit_files = _find_files(src, "*Audit*")

    audit_content = ""
    if audit_files:
        audit_content = _read(audit_files[0])
        has_class = bool(re.search(r'class\s+\w*[Aa]udit\w*', audit_content))
        has_log_method = bool(re.search(r'(log|record|write|append)\s*\(', audit_content))
        has_exports = "module.exports" in audit_content or "export" in audit_content
        score = 0.0
        if has_class:
            score += 0.4
        if has_log_method:
            score += 0.3
        if has_exports:
            score += 0.3
        components["audit_service_exists"] = min(score, 1.0)

    # ====== 2. Hash chain for tamper detection (0.20) ======
    # Look for crypto/hash usage in audit service
    all_audit_files = audit_files + _find_files(src, "*audit*") + _find_files(src, "*hash*")
    hash_found = False
    prev_hash_found = False
    chain_logic = False

    for f in set(all_audit_files):
        c = _read(f)
        if re.search(r'(crypto|createHash|sha256|sha512|md5|hash)', c, re.IGNORECASE):
            hash_found = True
        if re.search(r'(prevHash|previousHash|prev_hash|lastHash|chainHash)', c):
            prev_hash_found = True
        if re.search(r'(chain|link|previous.*hash|hash.*previous)', c, re.IGNORECASE):
            chain_logic = True

    score = 0.0
    if hash_found:
        score += 0.4
    if prev_hash_found:
        score += 0.4
    if chain_logic:
        score += 0.2
    components["hash_chain_integrity"] = min(score, 1.0)

    # ====== 3. Daily rotation / date-based file naming (0.15) ======
    rotation_found = False
    date_naming = False
    files_dir_used = False

    for f in set(all_audit_files):
        c = _read(f)
        # Date-based naming pattern: YYYY-MM-DD in filename
        if re.search(r'(toISOString|getFullYear|getMonth|getDate|new Date|\.slice\(0,\s*10\))', c):
            date_naming = True
        # Files directory / audit directory
        if re.search(r'(files.*audit|audit.*dir|auditDir|audit_dir)', c, re.IGNORECASE):
            files_dir_used = True
        # Rotation logic
        if re.search(r'(rotat|daily|day|\.audit|\.log)', c, re.IGNORECASE):
            rotation_found = True

    score = 0.0
    if date_naming:
        score += 0.5
    if files_dir_used:
        score += 0.3
    if rotation_found:
        score += 0.2
    components["daily_rotation"] = min(score, 1.0)

    # ====== 4. Event type coverage - alarm, device, task (0.15) ======
    alarm_logged = False
    device_logged = False
    task_logged = False

    all_src_files = _find_files(src, "*.js")
    combined_src = ""
    for f in all_src_files:
        combined_src += _read(f) + "\n"

    # Check if audit service logs different event types
    if re.search(r'(alarm|fire|smoke|sensor)', combined_src, re.IGNORECASE):
        if re.search(r'audit.*\.(log|record|write)|log.*audit', combined_src, re.IGNORECASE):
            alarm_logged = True
        elif re.search(r'(alarm.*audit|audit.*alarm)', combined_src, re.IGNORECASE):
            alarm_logged = True

    if re.search(r'(device.*control|control.*device)', combined_src, re.IGNORECASE):
        if re.search(r'audit', combined_src, re.IGNORECASE):
            device_logged = True

    if re.search(r'(task.*dispatch|dispatch.*task)', combined_src, re.IGNORECASE):
        if re.search(r'audit', combined_src, re.IGNORECASE):
            task_logged = True

    # Also check audit service itself for event type differentiation
    if audit_content:
        if re.search(r'(alarm|ALARM|fire|FIRE)', audit_content):
            alarm_logged = True
        if re.search(r'(device|DEVICE|control|CONTROL)', audit_content):
            device_logged = True
        if re.search(r'(task|TASK|dispatch|DISPATCH)', audit_content):
            task_logged = True

    score = sum([alarm_logged, device_logged, task_logged]) / 3.0
    components["event_coverage"] = round(score, 4)

    # ====== 5. HIDDEN: Tamper detection verification method (0.10) ======
    # A strong implementation provides a verify/validate method that
    # can check if logs were modified after writing
    verify_method = False
    readonly_mechanism = False

    for f in set(all_audit_files):
        c = _read(f)
        if re.search(r'(verify|validate|check[Ii]ntegrity|isIntact|isTampered|detectTamper)', c):
            verify_method = True
        # Read-only enforcement: chmod, fs flags, or explicit check
        if re.search(r'(chmod|readOnly|readonly|READONLY|r--r--|0o444|0444|immutable|appendOnly)', c):
            readonly_mechanism = True
        # Alternative: file permission setting
        if re.search(r'(fs\.chmod|chmodSync|writeFileSync.*{.*flag|O_APPEND)', c):
            readonly_mechanism = True

    score = 0.0
    if verify_method:
        score += 0.6
    if readonly_mechanism:
        score += 0.4
    components["tamper_detection"] = min(score, 1.0)

    # ====== 6. HIDDEN: Cron/scheduled daily generation (0.10) ======
    # The prompt mentions "daily" but doesn't explicitly require cron scheduling
    # A strong model will implement actual scheduling, not just on-demand logging
    cron_used = False
    schedule_setup = False

    for f in all_src_files:
        c = _read(f)
        if re.search(r'(cron|node-schedule|setInterval|schedule\.|CronJob|scheduleJob)', c):
            cron_used = True
        if re.search(r'(daily|0\s+0\s+\*\s+\*\s+\*|midnight|endOfDay|startOfDay)', c, re.IGNORECASE):
            schedule_setup = True

    score = 0.0
    if cron_used:
        score += 0.6
    if schedule_setup:
        score += 0.4
    components["cron_scheduling"] = min(score, 1.0)

    # ====== 7. HIDDEN: Integration wiring with existing services (0.10) ======
    # A strong implementation will wire into AlarmService, DeviceService, TaskDispatcher
    # via event listeners or direct integration (not just standalone)
    # Key: the AUDIT service must be explicitly referenced alongside other services
    integrated_alarm = False
    integrated_device = False
    integrated_task = False

    # First confirm AuditService exists somewhere
    audit_service_referenced = False
    for f in all_src_files:
        c = _read(f)
        if re.search(r'(AuditService|auditService|audit_service)', c):
            audit_service_referenced = True
            break

    if audit_service_referenced:
        for f in all_src_files:
            c = _read(f)
            # Must have BOTH audit reference AND service event wiring in same file
            has_audit_ref = bool(re.search(r'(AuditService|auditService|audit)', c))
            if not has_audit_ref:
                continue
            # Check for event listener patterns hooking audit into existing services
            if re.search(r"(alarmService|AlarmService).*on\(|on\(.*alarm", c):
                integrated_alarm = True
            if re.search(r"(deviceService|DeviceService).*on\(|on\(.*device", c):
                integrated_device = True
            if re.search(r"(taskDispatcher|TaskDispatcher).*on\(|on\(.*task|dispatch", c):
                integrated_task = True

        # Also check app.js for wiring (must have AuditService import/require)
        app_content = _read(src / "app.js")
        if re.search(r'(AuditService|auditService|require.*[Aa]udit)', app_content):
            if re.search(r"(alarmService|AlarmService).*audit|audit.*alarm", app_content, re.IGNORECASE):
                integrated_alarm = True
            if re.search(r"(deviceService|DeviceService).*audit|audit.*device", app_content, re.IGNORECASE):
                integrated_device = True
            if re.search(r"(taskDispatcher|TaskDispatcher).*audit|audit.*task|audit.*dispatch", app_content, re.IGNORECASE):
                integrated_task = True

    score = sum([integrated_alarm, integrated_device, integrated_task]) / 3.0
    components["integration_wiring"] = round(score, 4)

    # ====== Compute overall ======
    weights = {
        "audit_service_exists": 0.20,
        "hash_chain_integrity": 0.20,
        "daily_rotation": 0.15,
        "event_coverage": 0.15,
        "tamper_detection": 0.10,
        "cron_scheduling": 0.10,
        "integration_wiring": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
