"""Hidden verifier for CP108 - BLE Command Dispatch Service."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_comments(code: str) -> str:
    """Remove C single-line and multi-line comments to avoid matching TODOs."""
    # Remove single-line comments
    code = re.sub(r'//[^\n]*', '', code)
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    return code


def grade_workspace(ws: Path) -> dict:
    # Try both possible locations
    ble_dir = ws / "ble_peripheral" / "modules" / "ble"
    if not ble_dir.exists():
        ble_dir = ws / "fixtures" / "ble_peripheral" / "modules" / "ble"

    user_svc_file = ble_dir / "ble_user_service.c" if ble_dir.exists() else None
    user_svc_h = ble_dir / "ble_user_service.h" if ble_dir.exists() else None
    adv_file = ble_dir / "ble_adv.c" if ble_dir.exists() else None

    components = {k: 0.0 for k in [
        "dispatch_table_struct",
        "dispatch_table_entries",
        "write_callback_handle_check",
        "write_callback_hex_dump",
        "dispatch_call_in_write",
        "adv_mac_fill",
        "periodic_notify_func",
        "connection_guard",
    ]}

    # --- Check ble_user_service.c ---
    svc_raw = ""
    svc_content = ""  # comments stripped
    if user_svc_file and user_svc_file.exists():
        svc_raw = _read(user_svc_file)
    else:
        for candidate in [
            ws / "ble_peripheral" / "modules" / "ble" / "ble_user_service.c",
            ws / "fixtures" / "ble_peripheral" / "modules" / "ble" / "ble_user_service.c",
        ]:
            if candidate.exists():
                svc_raw = _read(candidate)
                break

    svc_content = _strip_comments(svc_raw)

    if svc_content:
        # 1. Dispatch table struct definition (actual typedef, not just a comment)
        # Must have typedef struct with function pointer and named type
        has_struct = bool(re.search(
            r'typedef\s+struct\s*\w*\s*\{[\s\S]*?\}\s*\w+',
            svc_content
        ))
        # Verify it has both data fields and function pointer
        if has_struct:
            struct_match = re.search(
                r'typedef\s+struct\s*\w*\s*\{([\s\S]*?)\}\s*\w+',
                svc_content
            )
            if struct_match:
                struct_body = struct_match.group(1)
                has_fields = bool(re.search(r'u8\s+\w+', struct_body))
                has_fptr = bool(re.search(r'\(\s*\*\s*\w+\s*\)', struct_body))
                has_struct = has_fields and has_fptr
        components["dispatch_table_struct"] = 1.0 if has_struct else 0.0

        # 2. Dispatch table array with >= 3 entries containing 0xEA
        # Must be actual array initialization, not comments
        # Look for array with at least 3 entries containing 0xEA hex
        table_match = re.search(
            r'(?:const\s+)?\w+\s+\w+\s*\[\s*\]\s*=\s*\{([^;]+)\};',
            svc_content, re.DOTALL
        )
        n_entries = 0
        if table_match:
            table_body = table_match.group(1)
            # Count entries with 0xEA
            n_entries = len(re.findall(r'\{[^}]*0x[Ee][Aa][^}]*\}', table_body))

        if n_entries >= 3:
            components["dispatch_table_entries"] = 1.0
        elif n_entries >= 2:
            components["dispatch_table_entries"] = 0.7
        elif n_entries >= 1:
            components["dispatch_table_entries"] = 0.4
        else:
            components["dispatch_table_entries"] = 0.0

        # 3. Write callback checks handle 0x0011 (actual code, not comment)
        # Look for if-statement checking handle in service_write_callback body
        write_cb_match = re.search(
            r'service_write_callback[^{]*\{(.+?)(?=\n\w|\nstatic|\nvoid|\Z)',
            svc_content, re.DOTALL
        )
        write_body = write_cb_match.group(1) if write_cb_match else ""
        has_handle_check = bool(re.search(
            r'if\s*\([^)]*(?:attribute_handle|handle)\s*==\s*(?:0x0011|ATT_CHARACTERISTIC_C7E6FAE2_VALUE_HANDLE)',
            write_body
        ))
        components["write_callback_handle_check"] = 1.0 if has_handle_check else 0.0

        # 4. Printf hex dump in write callback (actual printf call, not comment)
        has_hex_dump = bool(re.search(
            r'printf\s*\([^)]*%0?2[xX]',
            write_body
        ))
        if not has_hex_dump:
            # Accept for-loop printf pattern
            has_hex_dump = bool(re.search(
                r'for\s*\([^)]*\)[^{]*\{[^}]*printf',
                write_body, re.DOTALL
            ))
        if not has_hex_dump:
            has_hex_dump = bool(re.search(
                r'(?:TRACE|printf)\s*\([^)]*(?:buf|buffer|data)',
                write_body
            ))
        components["write_callback_hex_dump"] = 1.0 if has_hex_dump else 0.0

        # 5. Dispatch call within write callback
        has_dispatch = bool(re.search(
            r'(?:for|while)\s*\([^)]*\)\s*\{[^}]*(?:handler|func|callback)\s*\(',
            write_body, re.DOTALL
        )) or bool(re.search(
            r'\w+(?:dispatch|parse_cmd|cmd_process|package_process)\s*\(',
            write_body
        ))
        components["dispatch_call_in_write"] = 1.0 if has_dispatch else 0.0

        # 7. Periodic notify function (actual function definition, not TODO comment)
        has_1s_proc = bool(re.search(
            r'void\s+ble_user_1s_proc\s*\([^)]*\)\s*\{',
            svc_content
        )) or bool(re.search(
            r'void\s+ble_user_(?:heartbeat|timer|periodic|1s)\w*\s*\([^)]*\)\s*\{',
            svc_content
        ))
        components["periodic_notify_func"] = 0.0

        # Extract the 1s_proc function body (handle nested braces)
        proc_body = ""
        if has_1s_proc:
            proc_start = re.search(
                r'void\s+ble_user_(?:1s_proc|heartbeat|timer|periodic)\w*\s*\([^)]*\)\s*\{',
                svc_content
            )
            if proc_start:
                # Find matching closing brace by counting
                start_idx = proc_start.end()
                depth = 1
                idx = start_idx
                while idx < len(svc_content) and depth > 0:
                    if svc_content[idx] == '{':
                        depth += 1
                    elif svc_content[idx] == '}':
                        depth -= 1
                    idx += 1
                proc_body = svc_content[start_idx:idx-1]

            has_notify_call = bool(re.search(
                r'(?:ble_att_server_notify|att_server_notify)\s*\(',
                proc_body
            ))
            if has_notify_call:
                components["periodic_notify_func"] = 1.0
            else:
                components["periodic_notify_func"] = 0.5

        # 8. Connection guard in notify function
        if has_1s_proc and proc_body:
            has_conn_guard = bool(re.search(
                r'if\s*\(\s*(?:current_)?con_handle\s*(?:!=\s*(?:0|0x\w+|INVALID)|>\s*0)',
                proc_body
            )) or bool(re.search(
                r'if\s*\(\s*(?:!?\s*)?(?:is_connected|ble_connected|connected)',
                proc_body
            )) or bool(re.search(
                r'if\s*\(\s*(?:current_)?con_handle\s*\)',
                proc_body
            ))
            components["connection_guard"] = 1.0 if has_conn_guard else 0.0

    # --- Check ble_adv.c ---
    adv_content = ""
    if adv_file and adv_file.exists():
        adv_content = _read(adv_file)
    else:
        for candidate in [
            ws / "ble_peripheral" / "modules" / "ble" / "ble_adv.c",
            ws / "fixtures" / "ble_peripheral" / "modules" / "ble" / "ble_adv.c",
        ]:
            if candidate.exists():
                adv_content = _read(candidate)
                break

    adv_code = _strip_comments(adv_content)

    if adv_code:
        # 6. MAC address filled from xcfg_cb.le_addr (actual assignment, not comment)
        has_mac_fill = bool(re.search(
            r'(?:adv_buf|adv_data|buf)\s*\[\s*\d+\s*\]\s*=\s*xcfg_cb\s*\.\s*le_addr\s*\[',
            adv_code
        )) or bool(re.search(
            r'memcpy\s*\([^)]*xcfg_cb\s*\.\s*le_addr',
            adv_code
        ))
        # Verify it's inside ble_get_adv_data function
        adv_func_match = re.search(
            r'ble_get_adv_data[^{]*\{(.+?)(?=\n\w|\nstatic|\nvoid|\nconst|\Z)',
            adv_code, re.DOTALL
        )
        adv_func_body = adv_func_match.group(1) if adv_func_match else ""
        in_adv_func = bool(re.search(
            r'xcfg_cb\s*\.\s*le_addr',
            adv_func_body
        ))
        if has_mac_fill and in_adv_func:
            components["adv_mac_fill"] = 1.0
        elif has_mac_fill:
            components["adv_mac_fill"] = 0.7
        else:
            components["adv_mac_fill"] = 0.0

    # --- Compute overall score ---
    weights = {
        "dispatch_table_struct": 0.15,
        "dispatch_table_entries": 0.15,
        "write_callback_handle_check": 0.15,
        "write_callback_hex_dump": 0.10,
        "dispatch_call_in_write": 0.10,
        "adv_mac_fill": 0.15,
        "periodic_notify_func": 0.10,
        "connection_guard": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try /workspace first (where sandbox_files land),
    # then fallback to /workspace/fixtures/
    ws = Path("/workspace")
    result = grade_workspace(ws)
    if result["overall_score"] == 0.0:
        # Try fixtures subdirectory
        result = grade_workspace(ws / "fixtures")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
