"""Hidden verifier for CP66 — C++ channel adapter return-value refactor."""
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
    components = {k: 0.0 for k in [
        "return_value_refactored", "call_sites_updated",
        "new_interface_added", "nvt_implemented", "mtk_implemented",
        "all_files_present", "compiles_no_old_pattern",
    ]}

    # Probe both /workspace/src and /workspace (some agents may flatten)
    candidates = [ws / "src", ws]
    installer_h = installer_cpp = adapter_h = nvt_h = nvt_cpp = mtk_h = mtk_cpp = None
    for base in candidates:
        if (base / "channel" / "channel_map_installer.h").exists():
            installer_h = base / "channel" / "channel_map_installer.h"
            installer_cpp = base / "channel" / "channel_map_installer.cpp"
            adapter_h = base / "vendor" / "vendor_channel_adapter.h"
            nvt_h = base / "vendor" / "nvt_channel_adapter.h"
            nvt_cpp = base / "vendor" / "nvt_channel_adapter.cpp"
            mtk_h = base / "vendor" / "mtk_channel_adapter.h"
            mtk_cpp = base / "vendor" / "mtk_channel_adapter.cpp"
            break

    files_found = sum(1 for p in [installer_h, installer_cpp, adapter_h, nvt_h, nvt_cpp, mtk_h, mtk_cpp] if p and p.exists())
    components["all_files_present"] = files_found / 7.0

    # 1. Return value refactored in installer.h
    content = _read(installer_h) if installer_h else ""
    has_unique_ptr = bool(re.search(r"(unique_ptr|std::unique_ptr)\s*<\s*VendorChannel\s*>\s+convertToVendorChannel", content))
    has_old = bool(re.search(r"ErrorCode\s+convertToVendorChannel.*VendorChannel\s*\*", content, re.DOTALL))
    if has_unique_ptr and not has_old:
        components["return_value_refactored"] = 1.0
    elif has_unique_ptr:
        components["return_value_refactored"] = 0.6
    elif not has_old and content:
        components["return_value_refactored"] = 0.3

    # 2. Call sites updated in installer.cpp
    content = _read(installer_cpp) if installer_cpp else ""
    old_calls = len(re.findall(r"convertToVendorChannel\(.*?&\w+\w*\)", content, re.DOTALL))
    new_calls = len(re.findall(r"(?:auto|unique_ptr|std::unique_ptr)\s+\w+\s*=\s*convertToVendorChannel\(", content))
    if old_calls == 0 and new_calls >= 2:
        components["call_sites_updated"] = 1.0
    elif old_calls == 0 and new_calls >= 1:
        components["call_sites_updated"] = 0.7
    elif new_calls > old_calls:
        components["call_sites_updated"] = 0.4
    elif new_calls > 0:
        components["call_sites_updated"] = 0.2

    # 3. New interface in adapter.h
    content = _read(adapter_h) if adapter_h else ""
    content_nc = re.sub(r"//.*", "", content)
    content_nc = re.sub(r"/\*.*?\*/", "", content_nc, flags=re.DOTALL)
    has_iface = "addDirectTuneChannel" in content_nc
    is_virtual = bool(re.search(r"virtual.*addDirectTuneChannel|addDirectTuneChannel.*=\s*0", content_nc))
    has_vendor_param = bool(re.search(r"addDirectTuneChannel\s*\([^)]*VendorChannel", content_nc))
    if has_iface and is_virtual and has_vendor_param:
        components["new_interface_added"] = 1.0
    elif has_iface and has_vendor_param:
        components["new_interface_added"] = 0.7
    elif has_iface:
        components["new_interface_added"] = 0.4

    # 4. NVT impl
    nvt_h_content = _read(nvt_h) if nvt_h else ""
    nvt_cpp_content = _read(nvt_cpp) if nvt_cpp else ""
    if "addDirectTuneChannel" in nvt_h_content and "addDirectTuneChannel" in nvt_cpp_content:
        components["nvt_implemented"] = 1.0
    elif "addDirectTuneChannel" in nvt_h_content or "addDirectTuneChannel" in nvt_cpp_content:
        components["nvt_implemented"] = 0.5

    # 5. MTK impl
    mtk_h_content = _read(mtk_h) if mtk_h else ""
    mtk_cpp_content = _read(mtk_cpp) if mtk_cpp else ""
    if "addDirectTuneChannel" in mtk_h_content and "addDirectTuneChannel" in mtk_cpp_content:
        components["mtk_implemented"] = 1.0
    elif "addDirectTuneChannel" in mtk_h_content or "addDirectTuneChannel" in mtk_cpp_content:
        components["mtk_implemented"] = 0.5

    # 6. No old pattern leftover anywhere
    combined = _read(installer_h) + _read(installer_cpp)
    components["compiles_no_old_pattern"] = 0.0 if re.search(r"ErrorCode\s+convertToVendorChannel.*VendorChannel\s*\*", combined, re.DOTALL) else 1.0

    weights = {
        "all_files_present": 0.05,
        "return_value_refactored": 0.25,
        "call_sites_updated": 0.20,
        "new_interface_added": 0.20,
        "nvt_implemented": 0.10,
        "mtk_implemented": 0.10,
        "compiles_no_old_pattern": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "files_found": files_found,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
