#!/usr/bin/env python3
"""In-container verifier for CP46_file_processor_design.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")

REQUIRED_FILES = [
        "file_processor/__init__.py",
        "file_processor/config.py",
        "file_processor/base.py",
        "file_processor/txt_processor.py",
        "file_processor/markdown_processor.py",
        "file_processor/docx_processor.py",
    ]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    # Check package structure completeness
    present_count = sum(
        1 for f in REQUIRED_FILES if (workspace / f).exists()
    )
    scores["package_structure"] = present_count / len(REQUIRED_FILES)

    # Check config.py has required parameters
    config_file = workspace / "file_processor" / "config.py"
    if config_file.exists():
        content = config_file.read_text()
        has_chunk_size = bool(re.search(r'CHUNK_SIZE\s*=\s*\d+', content))
        has_overlap = bool(re.search(r'OVERLAP', content, re.IGNORECASE))
        scores["config_params"] = (
            0.5 * (1.0 if has_chunk_size else 0.0)
            + 0.5 * (1.0 if has_overlap else 0.0)
        )
    else:
        scores["config_params"] = 0.0

    # Check base.py has abstract class pattern
    base_file = workspace / "file_processor" / "base.py"
    if base_file.exists():
        content = base_file.read_text()
        has_abc = "ABC" in content or "abstractmethod" in content or "NotImplementedError" in content
        has_process = "process" in content or "chunk" in content
        scores["base_class_design"] = (
            0.5 * (1.0 if has_abc else 0.0)
            + 0.5 * (1.0 if has_process else 0.0)
        )
    else:
        scores["base_class_design"] = 0.0

    # Check txt_processor has character chunking
    txt_file = workspace / "file_processor" / "txt_processor.py"
    if txt_file.exists():
        content = txt_file.read_text()
        has_chunk_logic = bool(re.search(
            r'(CHUNK_SIZE|chunk_size|len\()', content
        ))
        has_overlap_logic = bool(re.search(
            r'(overlap|OVERLAP)', content, re.IGNORECASE
        ))
        scores["txt_chunking"] = (
            0.6 * (1.0 if has_chunk_logic else 0.0)
            + 0.4 * (1.0 if has_overlap_logic else 0.0)
        )
    else:
        scores["txt_chunking"] = 0.0

    # Check markdown_processor has heading-based splitting
    md_file = workspace / "file_processor" / "markdown_processor.py"
    if md_file.exists():
        content = md_file.read_text()
        has_heading_split = bool(re.search(
            r'(^#+\s|re\.split|split.*#|heading|标题)', content, re.IGNORECASE
        ))
        has_secondary_chunk = bool(re.search(
            r'(chunk|CHUNK_SIZE|chunk_size)', content, re.IGNORECASE
        ))
        scores["md_heading_split"] = (
            0.6 * (1.0 if has_heading_split else 0.0)
            + 0.4 * (1.0 if has_secondary_chunk else 0.0)
        )
    else:
        scores["md_heading_split"] = 0.0

    # Check code reuse from existing_code.py
    all_content = ""
    for f in REQUIRED_FILES:
        fp = workspace / f
        if fp.exists():
            all_content += fp.read_text()
    reuse_indicators = [
        "call_mineru_api" in all_content or "mineru" in all_content.lower(),
        "extract_images_from_markdown" in all_content or "extract_image" in all_content.lower(),
        "get_image_context" in all_content or "image_context" in all_content.lower(),
    ]
    scores["code_reuse"] = sum(reuse_indicators) / len(reuse_indicators)

    return scores


def main() -> dict:
    try:
        scores = automated_score(WORKSPACE)
    except Exception as exc:  # noqa: BLE001
        return {"scores": {}, "overall_score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    overall = sum(numeric) / len(numeric) if numeric else 0.0
    return {"scores": scores, "overall_score": round(overall, 4)}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(main(), ensure_ascii=False) + "\n")
