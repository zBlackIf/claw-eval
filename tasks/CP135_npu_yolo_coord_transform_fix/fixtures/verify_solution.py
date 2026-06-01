"""Hidden verifier for CP135 — NPU YOLO Coordinate Transform Fix.

Checks that the agent correctly fixes the detectImage memory copy bug
and optionally improves the TXT export clamping inconsistency.
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
    """Find a file by name recursively."""
    for p in base.rglob(name):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for correct NPU YOLO coordinate fix."""

    # Try multiple possible locations
    pipeline_dir = None
    for candidate in [
        ws / "fixtures" / "video_pipeline",
        ws / "video_pipeline",
    ]:
        if candidate.exists():
            pipeline_dir = candidate
            break

    if pipeline_dir is None:
        return {"overall_score": 0.0, "error": "video_pipeline directory not found",
                "components": {}, "weights": {}}

    components = {
        "detectimage_full_copy": 0.0,      # Main bug: detectImage should copy full 640x640
        "source_offset_correct": 0.0,      # Source data offset handled correctly
        "border_init_or_fullcopy": 0.0,    # Either pre-init borders OR full copy strategy
        "txt_clamp_consistent": 0.0,       # TXT clamping applied to all dims or none
        "no_regression_preprocess": 0.0,   # preprocess() still works correctly for video
    }

    # Read the detector implementation
    detector_file = _find_file(pipeline_dir, "yolo_detector_acl.cpp")
    detector_src = _read(detector_file) if detector_file else ""

    # Read the exporter
    exporter_file = _find_file(pipeline_dir, "json_exporter.cpp")
    exporter_src = _read(exporter_file) if exporter_file else ""

    # ===== Dimension 1: detectImage full buffer copy (0.35 weight) =====
    # The fix should copy the FULL 640x640 NV12 buffer, not just middle 384 rows
    if detector_src:
        # Check if detectImage now copies the full model input size
        # Look for: memcpy(input_buffer_, ..., YOLO_MODEL_INPUT_SIZE) or equivalent full copy
        # Without the BORDER_HEIGHT offset in the destination

        # Find the detectImage function body
        detect_image_match = re.search(
            r'(?:YoloDetectorAcl::)?detectImage\s*\([^)]*\)\s*\{(.*?)(?:\n\}|\nDetectionResult)',
            detector_src, re.DOTALL
        )
        detect_image_body = detect_image_match.group(1) if detect_image_match else detector_src

        # Strategy A: Full copy (no offset in destination for Y-plane)
        has_full_copy = False
        # Check for memcpy to input_buffer_ directly (no offset) with full size
        if re.search(r'memcpy\s*\(\s*input_buffer_\s*,\s*nv12', detect_image_body):
            has_full_copy = True
        if re.search(r'memcpy\s*\(\s*input_buffer_\s*,\s*model_input_size_', detect_image_body):
            has_full_copy = True
        # aclrtMemcpy variant
        if re.search(r'aclrtMemcpy\s*\(\s*input_buffer_\s*,\s*model_input_size_', detect_image_body):
            has_full_copy = True
        if re.search(r'YOLO_MODEL_INPUT_SIZE', detect_image_body) and not re.search(
            r'YOLO_BORDER_HEIGHT\s*\*\s*YOLO_INPUT_WIDTH', detect_image_body
        ):
            has_full_copy = True

        # Strategy B: Proper partial copy with correct source offset
        has_correct_partial = False
        # Source must also be offset: nv12_640x640 + BORDER_HEIGHT * WIDTH
        if re.search(r'nv12.*\+.*BORDER', detect_image_body) or \
           re.search(r'nv12.*\+.*128\s*\*\s*640', detect_image_body):
            has_correct_partial = True

        # The old bug: dest has offset but source starts from 0
        still_has_bug = re.search(
            r'memcpy\s*\(\s*input_buffer_\s*\+\s*YOLO_BORDER_HEIGHT.*nv12_640x640\s*,',
            detect_image_body
        ) or re.search(
            r'memcpy\s*\(\s*input_buffer_\s*\+\s*YOLO_BORDER_HEIGHT.*nv12_640x640\s*\)',
            detect_image_body
        )

        if has_full_copy:
            components["detectimage_full_copy"] = 1.0
        elif has_correct_partial and not still_has_bug:
            components["detectimage_full_copy"] = 0.7  # Partial credit for correct partial copy
        elif still_has_bug:
            components["detectimage_full_copy"] = 0.0
        else:
            # Check if the function was significantly rewritten
            if "YOLO_MODEL_INPUT_SIZE" in detect_image_body or "model_input_size" in detect_image_body:
                components["detectimage_full_copy"] = 0.8

    # ===== Dimension 2: Source offset correctness (0.25 weight) =====
    if detector_src:
        detect_image_match = re.search(
            r'(?:YoloDetectorAcl::)?detectImage\s*\([^)]*\)\s*\{(.*?)(?:\n\}|\nDetectionResult)',
            detector_src, re.DOTALL
        )
        detect_image_body = detect_image_match.group(1) if detect_image_match else ""

        # If full copy strategy: source should start from beginning (nv12_640x640), no offset needed
        if components["detectimage_full_copy"] >= 0.8:
            # Full copy from start is correct
            if re.search(r'nv12_640x640\s*,', detect_image_body) or \
               re.search(r'nv12_640x640\s*\)', detect_image_body):
                components["source_offset_correct"] = 1.0
            else:
                components["source_offset_correct"] = 0.7  # Probably renamed param
        elif components["detectimage_full_copy"] >= 0.5:
            # Partial copy: source needs offset to match destination
            if re.search(r'nv12.*\+.*BORDER', detect_image_body) or \
               re.search(r'nv12.*\+.*128', detect_image_body):
                components["source_offset_correct"] = 1.0
            else:
                components["source_offset_correct"] = 0.3

    # ===== Dimension 3: Border initialization or full copy (0.20 weight) =====
    if detector_src:
        # Either: (a) full copy of 640x640 makes borders correct automatically
        # Or: (b) explicit buffer initialization before partial copy
        if components["detectimage_full_copy"] >= 0.8:
            # Full copy inherently solves the border problem
            components["border_init_or_fullcopy"] = 1.0
        else:
            # Check for explicit initialization: memset, initBuffer call, etc.
            detect_image_match = re.search(
                r'(?:YoloDetectorAcl::)?detectImage\s*\([^)]*\)\s*\{(.*?)(?:\n\}|\nDetectionResult)',
                detector_src, re.DOTALL
            )
            body = detect_image_match.group(1) if detect_image_match else ""
            if "initBuffer" in body or "memset" in body or "initialized_" in body:
                components["border_init_or_fullcopy"] = 0.8
            elif "init" in body.lower():
                components["border_init_or_fullcopy"] = 0.5

    # ===== Dimension 4: TXT clamp consistency (0.10 weight) =====
    if exporter_src:
        # Find the TXT export function
        txt_func_match = re.search(
            r'saveDetectionResultToTxt\s*\([^)]*\)\s*\{(.*?)(?:\n\})',
            exporter_src, re.DOTALL
        )
        txt_body = txt_func_match.group(1) if txt_func_match else exporter_src

        # Count which variables are clamped
        center_clamped = bool(re.search(r'center_[xy]\s*=\s*std::(max|min|clamp)', txt_body))
        wh_clamped = bool(re.search(r'norm_[wh]\s*=\s*std::(max|min|clamp)', txt_body))

        if not center_clamped and not wh_clamped:
            # No clamping at all - acceptable (rely on upstream filtering)
            components["txt_clamp_consistent"] = 0.8
        elif center_clamped and wh_clamped:
            # All values clamped - consistent
            components["txt_clamp_consistent"] = 1.0
        elif center_clamped and not wh_clamped:
            # Only center clamped (original bug) - inconsistent
            components["txt_clamp_consistent"] = 0.2
        else:
            components["txt_clamp_consistent"] = 0.5

    # ===== Dimension 5: No regression in preprocess (0.10 weight) =====
    if detector_src:
        # preprocess function should still only copy middle 384 rows (correct for VPSS)
        preprocess_match = re.search(
            r'(?:YoloDetectorAcl::)?preprocess\s*\([^)]*\)\s*\{(.*?)(?:\n\})',
            detector_src, re.DOTALL
        )
        preprocess_body = preprocess_match.group(1) if preprocess_match else ""

        if preprocess_body:
            # Should still have the BORDER_HEIGHT offset for destination
            has_offset = "YOLO_BORDER_HEIGHT" in preprocess_body or "BORDER_HEIGHT" in preprocess_body or "128" in preprocess_body
            # Should still have initialization check
            has_init = "init" in preprocess_body.lower() or "initialized" in preprocess_body

            if has_offset and has_init:
                components["no_regression_preprocess"] = 1.0
            elif has_offset:
                components["no_regression_preprocess"] = 0.8
            else:
                # preprocess was incorrectly modified
                components["no_regression_preprocess"] = 0.2
        else:
            # Function still exists but couldn't parse - give benefit of doubt
            if "preprocess" in detector_src:
                components["no_regression_preprocess"] = 0.6

    weights = {
        "detectimage_full_copy": 0.35,
        "source_offset_correct": 0.25,
        "border_init_or_fullcopy": 0.20,
        "txt_clamp_consistent": 0.10,
        "no_regression_preprocess": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try /workspace/fixtures/video_pipeline first, fallback to /workspace/video_pipeline
    ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
