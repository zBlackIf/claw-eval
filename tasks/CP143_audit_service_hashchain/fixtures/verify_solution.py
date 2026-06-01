"""Hidden verifier for CP143 — Audit Service with Hash Chain Tamper Detection."""
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


def _find_file(base: Path, pattern: str) -> Path | None:
    """Find a file matching pattern (case-insensitive) under base."""
    for p in base.rglob("*"):
        if p.is_file() and re.search(pattern, p.name, re.IGNORECASE):
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    # Look in both possible locations
    firebot = ws / "fixtures" / "firebot"
    if not firebot.exists():
        firebot = ws / "firebot"
    if not firebot.exists():
        # Try finding src/services anywhere
        for candidate in [ws / "fixtures" / "firebot", ws / "firebot", ws]:
            if (candidate / "src" / "services").exists():
                firebot = candidate
                break

    services_dir = firebot / "src" / "services"

    components = {k: 0.0 for k in [
        "audit_service_exists",
        "hash_chain_impl",
        "daily_file_rotation",
        "event_categories",
        "tamper_detection",
        "integration_hooks",
        "file_permissions_readonly",
    ]}

    # 1. AuditService file exists with class/module structure
    audit_file = _find_file(services_dir, r"audit.*service|AuditService|audit_service")
    if not audit_file:
        # Also search broader
        audit_file = _find_file(firebot / "src", r"audit.*service|AuditService|audit_service")

    if audit_file and audit_file.exists():
        content = _read(audit_file)
        has_class = bool(re.search(r"class\s+\w*[Aa]udit\w*", content))
        has_exports = "module.exports" in content or "export" in content
        has_singleton = "instance" in content.lower() or "singleton" in content.lower() or "new " in content
        components["audit_service_exists"] = min(1.0,
            (0.4 if has_class else 0.0) +
            (0.3 if has_exports else 0.0) +
            (0.3 if has_singleton else 0.0)
        )

        # 2. Hash chain implementation
        has_hash = bool(re.search(r"(crypto|sha256|sha-256|createHash|hashlib|CryptoJS)", content, re.IGNORECASE))
        has_prev_hash = bool(re.search(r"prev.*hash|previous.*hash|lastHash|chainHash", content, re.IGNORECASE))
        has_chain_logic = bool(re.search(r"(hash.*prev|prev.*hash.*concat|chain)", content, re.IGNORECASE))
        components["hash_chain_impl"] = min(1.0,
            (0.4 if has_hash else 0.0) +
            (0.35 if has_prev_hash else 0.0) +
            (0.25 if has_chain_logic else 0.0)
        )

        # 3. Daily file rotation (date-based filenames)
        has_date_format = bool(re.search(
            r"(toISOString|YYYY-MM-DD|getFullYear|getMonth|getDate|new Date|"
            r"\.audit|\.jsonl|date.*file|file.*date|daily)",
            content, re.IGNORECASE
        ))
        has_path_join = bool(re.search(r"(path\.join|path\.resolve|\/audit\/)", content))
        has_date_in_filename = bool(re.search(
            r"(\$\{.*date.*\}|`.*date.*`|date.*\.audit|date.*\.log|date.*\.jsonl|"
            r"format.*date|toDateString|slice\(0,\s*10\))",
            content, re.IGNORECASE
        ))
        components["daily_file_rotation"] = min(1.0,
            (0.35 if has_date_format else 0.0) +
            (0.30 if has_path_join else 0.0) +
            (0.35 if has_date_in_filename else 0.0)
        )

        # 4. Event categories (ALARM, DEVICE_CONTROL, TASK, etc.)
        categories_found = 0
        for cat in ["ALARM", "DEVICE", "TASK", "CONTROL", "STATUS", "SYSTEM"]:
            if cat in content.upper():
                categories_found += 1
        components["event_categories"] = min(1.0, categories_found / 4.0)

        # 5. Tamper detection / verification method
        has_verify = bool(re.search(
            r"(verify|validate|check.*integrity|tamper|detect.*modif|audit.*check|"
            r"chain.*broken|hash.*mismatch|integrity)",
            content, re.IGNORECASE
        ))
        has_comparison = bool(re.search(
            r"(computed.*hash|recalculate|recompute|!==|!=.*hash|hash.*!==|mismatch)",
            content, re.IGNORECASE
        ))
        components["tamper_detection"] = min(1.0,
            (0.5 if has_verify else 0.0) +
            (0.5 if has_comparison else 0.0)
        )

        # 6. Integration hooks (subscribe to events from other services)
        has_event_listen = bool(re.search(
            r"(\.on\(|addEventListener|subscribe|EventEmitter|emit|"
            r"device.*service|alarm.*service|task.*service)",
            content, re.IGNORECASE
        ))
        # Also check if other services import/require audit
        integration_count = 0
        for svc_file in services_dir.glob("*.js"):
            if svc_file == audit_file:
                continue
            svc_content = _read(svc_file)
            if re.search(r"audit|AuditService", svc_content, re.IGNORECASE):
                integration_count += 1
        # Also check for integration in audit service itself (importing others)
        imports_others = bool(re.search(
            r"require.*['\"]\./(Device|Alarm|Task|Logger)", content
        ))
        components["integration_hooks"] = min(1.0,
            (0.4 if has_event_listen else 0.0) +
            (0.3 if integration_count > 0 else 0.0) +
            (0.3 if imports_others else 0.0)
        )

        # 7. File permissions / read-only enforcement
        has_readonly = bool(re.search(
            r"(chmod|0o444|0444|readOnly|read.only|READONLY|appendFile|"
            r"createWriteStream.*flags.*'a'|flags:\s*'a'|O_APPEND|"
            r"writeFile.*flag.*'a'|fs\.chmod|chmodSync|0o555)",
            content, re.IGNORECASE
        ))
        has_append_only = bool(re.search(
            r"(append|appendFile|flag.*['\"]a['\"]|'a\+'|\"a\+\")",
            content, re.IGNORECASE
        ))
        components["file_permissions_readonly"] = min(1.0,
            (0.5 if has_readonly else 0.0) +
            (0.5 if has_append_only else 0.0)
        )
    else:
        # No audit service found at all
        pass

    weights = {
        "audit_service_exists": 0.15,
        "hash_chain_impl": 0.25,
        "daily_file_rotation": 0.15,
        "event_categories": 0.10,
        "tamper_detection": 0.20,
        "integration_hooks": 0.08,
        "file_permissions_readonly": 0.07,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Check /workspace/fixtures/firebot first, then /workspace/firebot
    ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
