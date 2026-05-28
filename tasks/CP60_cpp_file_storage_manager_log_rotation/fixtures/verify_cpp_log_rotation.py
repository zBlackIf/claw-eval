"""Hidden verifier for CP60 — C++ FileStorageManager log rotation."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    cpp = ws / "src" / "file_storage_manager.cpp"
    content = _read(cpp)
    header = _read(ws / "include" / "file_storage_manager.h")

    components = {k: 0.0 for k in [
        "file_exists", "non_stub", "compression", "rotation",
        "retention", "filename_format", "startup_scan",
        "header_unchanged", "raii_exception_safety",
    ]}

    if not content.strip():
        return {"overall_score": 0.0, "components": components}

    components["file_exists"] = 1.0

    # Non-stub: file must be substantive (>2KB and >10 braces)
    if len(content) >= 2000 and content.count("{") >= 10:
        components["non_stub"] = 1.0
    elif len(content) >= 800:
        components["non_stub"] = 0.4

    # Compression: CompressFile + ValidateCompressedFile + zlib/gz APIs
    has_compress = "CompressFile" in content and "ValidateCompressedFile" in content
    has_compress_lib = any(kw in content for kw in [
        "zlib", "gzopen", "gzwrite", "gzclose", "deflate", "gz_",
    ])
    if has_compress and has_compress_lib:
        components["compression"] = 1.0
    elif has_compress:
        components["compression"] = 0.5

    # Rotation: size-based + RotateFile + current_file_size
    rotation = sum([
        "max_file_size" in content,
        "RotateFile" in content or "Rotate" in content,
        "current_file_size" in content or "m_current_file_size" in content,
    ])
    components["rotation"] = min(rotation / 2.0, 1.0)

    # Retention
    retention = sum([
        "RetentionPolicy" in content or "Retention" in content,
        any(kw in content for kw in ["remove", "delete", "unlink", "remove_all", "fs::remove"]),
        "max_total_files" in content,
    ])
    components["retention"] = min(retention / 2.0, 1.0)

    # Filename format
    filename = sum([
        "ussdata" in content,
        any(kw in content for kw in ["file_no", "file_number", "m_next_file_number"]),
        any(kw in content for kw in ["chrono", "strftime", "put_time", "timestamp"]),
    ])
    components["filename_format"] = min(filename / 2.0, 1.0)

    # Startup scan
    scan = sum([
        "StartupScan" in content or "ScanDirectory" in content or "Scan(" in content,
        any(kw in content for kw in ["directory_iterator", "is_regular_file", "exists"]),
        any(kw in content for kw in ["m_next_file_number", "max_number", "max_file_no"]),
    ])
    components["startup_scan"] = min(scan / 2.0, 1.0)

    # Header should remain unchanged: at minimum still contain key symbols
    if header:
        sig_hits = sum(1 for s in ["FileStorageManager", "Write", "Init", "Shutdown"] if s in header)
        components["header_unchanged"] = sig_hits / 4.0
    else:
        components["header_unchanged"] = 0.5

    # RAII / exception safety hints
    raii_hits = sum(1 for k in ["unique_ptr", "lock_guard", "scoped_lock", "RAII", "try", "catch", "noexcept", "shared_ptr"]
                    if k in content)
    components["raii_exception_safety"] = min(raii_hits / 3.0, 1.0)

    weights = {
        "file_exists": 0.05,
        "non_stub": 0.10,
        "compression": 0.20,
        "rotation": 0.15,
        "retention": 0.15,
        "filename_format": 0.10,
        "startup_scan": 0.10,
        "header_unchanged": 0.05,
        "raii_exception_safety": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "cpp_size": len(content),
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
