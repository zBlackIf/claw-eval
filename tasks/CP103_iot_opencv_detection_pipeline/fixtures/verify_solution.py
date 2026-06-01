"""Hidden verifier for CP103 — IoT OpenCV Detection Pipeline coordinate fix."""
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
    pipeline_dir = ws / "fixtures" / "video_pipeline"
    if not pipeline_dir.exists():
        pipeline_dir = ws / "video_pipeline"
    components = {k: 0.0 for k in [
        "json_exporter_y_scaling_fixed",
        "json_exporter_h_scaling_fixed",
        "txt_exporter_y_scaling_fixed",
        "txt_exporter_h_scaling_fixed",
        "detect_image_buffer_init",
        "negative_coord_clamping",
        "consistent_with_visualizer",
    ]}

    # === Check 1 & 2: JSON exporter coordinate fix ===
    json_exp = pipeline_dir / "json_exporter.cpp"
    if json_exp.exists():
        c = _read(json_exp)

        # The fix: y-direction scaling should use SCALED_H (384) not MODEL_INPUT_W (640)
        # Scope to the JSON function (saveDetectionResultToJson) only
        json_func_match = re.search(
            r'saveDetectionResultToJson.*?\{(.*?)(?=\nbool\s+save|\Z)',
            c, re.DOTALL
        )
        json_section = json_func_match.group(1) if json_func_match else c

        # Check for VPSS_H/SCALED_H/384 usage in orig_y calculation
        has_384_y = bool(re.search(
            r'orig_y\s*=.*(?:384|VPSS_H|SCALED_H|YOLO_SCALED_HEIGHT)',
            json_section, re.IGNORECASE
        ))
        # Also check if the old bug (using 640/MODEL_INPUT_W for y) is removed
        old_bug_y = bool(re.search(
            r'orig_y\s*=.*(?:640\.0f|MODEL_INPUT_W)',
            json_section
        ))

        if has_384_y and not old_bug_y:
            components["json_exporter_y_scaling_fixed"] = 1.0
        elif has_384_y:
            components["json_exporter_y_scaling_fixed"] = 0.6

        # Check orig_h uses 384 not 640
        has_384_h = bool(re.search(
            r'orig_h\s*=.*(?:384|VPSS_H|SCALED_H|YOLO_SCALED_HEIGHT)',
            json_section, re.IGNORECASE
        ))
        old_bug_h = bool(re.search(
            r'orig_h\s*=.*(?:640\.0f|MODEL_INPUT_W)',
            json_section
        ))

        if has_384_h and not old_bug_h:
            components["json_exporter_h_scaling_fixed"] = 1.0
        elif has_384_h:
            components["json_exporter_h_scaling_fixed"] = 0.6

    # === Check 3 & 4: TXT exporter coordinate fix ===
    # TXT export is in the same file (json_exporter.cpp) in function saveDetectionResultToTxt
    if json_exp.exists():
        c = _read(json_exp)

        # Find the TXT function section
        txt_func_match = re.search(
            r'saveDetectionResultToTxt.*?\{(.*?)(?:^}|\Z)',
            c, re.DOTALL | re.MULTILINE
        )
        txt_section = txt_func_match.group(1) if txt_func_match else ""

        if txt_section:
            has_384_y_txt = bool(re.search(
                r'orig_y\s*=.*(?:384|VPSS_H|SCALED_H|YOLO_SCALED_HEIGHT)',
                txt_section, re.IGNORECASE
            ))
            old_bug_y_txt = bool(re.search(
                r'orig_y\s*=.*(?:640\.0f|MODEL_INPUT_W)',
                txt_section
            ))

            if has_384_y_txt and not old_bug_y_txt:
                components["txt_exporter_y_scaling_fixed"] = 1.0
            elif has_384_y_txt:
                components["txt_exporter_y_scaling_fixed"] = 0.6

            has_384_h_txt = bool(re.search(
                r'orig_h\s*=.*(?:384|VPSS_H|SCALED_H|YOLO_SCALED_HEIGHT)',
                txt_section, re.IGNORECASE
            ))
            old_bug_h_txt = bool(re.search(
                r'orig_h\s*=.*(?:640\.0f|MODEL_INPUT_W)',
                txt_section
            ))

            if has_384_h_txt and not old_bug_h_txt:
                components["txt_exporter_h_scaling_fixed"] = 1.0
            elif has_384_h_txt:
                components["txt_exporter_h_scaling_fixed"] = 0.6

    # === Check 5: detectImage buffer initialization (HIDDEN - not mentioned in prompt) ===
    detector_file = pipeline_dir / "yolo_detector_acl.cpp"
    if detector_file.exists():
        c = _read(detector_file)

        # Extract the detectImage function body (greedy up to next top-level function or end)
        detect_image_match = re.search(
            r'detectImage[^{]*\{(.*)',
            c, re.DOTALL
        )
        detect_section = ""
        if detect_image_match:
            # Take everything up to 2000 chars (covers the function body)
            detect_section = detect_image_match.group(1)[:2000]

        if detect_section:
            # Option A: Full buffer zero-init (memset) before or instead of partial copy
            has_memset = bool(re.search(r'memset\s*\(\s*input_buffer_', detect_section))
            # Option B: Full padded buffer copy (creates padded 640x640, copies whole thing)
            has_full_copy = bool(re.search(
                r'memcpy\s*\(\s*input_buffer_\s*,.*(?:yuv|padded|full).*YOLO_MODEL_INPUT_SIZE',
                detect_section, re.IGNORECASE
            ))
            # Option B alt: memcpy with MODEL_INPUT_SIZE
            has_full_copy_alt = bool(re.search(
                r'memcpy\s*\(\s*input_buffer_.*YOLO_MODEL_INPUT_SIZE',
                detect_section
            ))
            # Option C: Create padded mat (640x640) and convert+copy
            has_pad_mat = bool(re.search(
                r'(padded|pad).*Mat\s*\(|Mat\s*\(\s*(640|YOLO_INPUT_HEIGHT)',
                detect_section
            ))
            has_full_memcpy = bool(re.search(
                r'memcpy\s*\(\s*input_buffer_\s*,',
                detect_section
            )) and not bool(re.search(
                r'memcpy\s*\(\s*input_buffer_\s*\+\s*(?:y_plane_offset|YOLO_BORDER)',
                detect_section
            ))

            if has_memset or has_full_copy or has_full_copy_alt:
                components["detect_image_buffer_init"] = 1.0
            elif has_pad_mat and has_full_memcpy:
                components["detect_image_buffer_init"] = 1.0
            else:
                # Check for partial fix indicators (excluding comments)
                code_lines = [l for l in detect_section.split('\n')
                              if l.strip() and not l.strip().startswith('//')]
                code_only = '\n'.join(code_lines)
                if bool(re.search(r'(memset|std::fill|padded_mat|pad.*Mat)',
                                  code_only, re.IGNORECASE)):
                    components["detect_image_buffer_init"] = 0.5

    # === Check 6: Negative coordinate handling (HIDDEN) ===
    # When obj.rect.y < 128 (box in border region), y becomes negative after subtraction.
    # Good solution: clamp orig_y to >= 0, or filter out border-region detections
    # NOTE: The existing std::max(0.0f, ...) on normalized values does NOT count -
    # that's clamping the final 0-1 range. We need clamping on orig_y itself.
    if json_exp.exists():
        c = _read(json_exp)
        # Check for explicit clamping of orig_y (not the final normalized clamp)
        has_neg_clamp = bool(re.search(
            r'orig_y\s*=\s*(?:std::)?(?:max|fmax)\s*\(\s*0',
            c
        ))
        # Or: separate if-check with clamp assignment
        has_neg_clamp_alt = bool(re.search(
            r'if\s*\(\s*orig_y\s*<\s*0', c
        ))
        # Also check if there's filtering of objects whose rect.y < border threshold
        has_filter = bool(re.search(
            r'if\s*\(\s*obj\.rect\.y\s*<\s*(?:128|BLACK_BORDER_H|BORDER_H|YOLO_BORDER_HEIGHT)',
            c
        )) and bool(re.search(r'continue', c))
        # Or clamping orig_h when orig_y was negative
        has_h_adjust = bool(re.search(
            r'orig_h\s*[+-]=.*orig_y|orig_h\s*=.*max.*0.*orig_y',
            c
        ))

        if has_neg_clamp or has_neg_clamp_alt or has_filter or has_h_adjust:
            components["negative_coord_clamping"] = 1.0

    # === Check 7: Consistency verification (HIDDEN) ===
    # Strong models will ensure json_exporter uses the exact same formula as visualizer.
    # The KEY indicator is that 384 is used for y/h AND 640 is used for x/w.
    # In the buggy code, 640 is used for ALL four directions.
    # We need to verify the fix introduced asymmetric scaling (384 for y/h, 640 for x/w).
    if json_exp.exists():
        c = _read(json_exp)
        # The fixed code should have 384 for y/h direction
        uses_384_for_y = bool(re.search(
            r'orig_y\s*=.*(?:384|VPSS_H|SCALED_H|YOLO_SCALED_HEIGHT)',
            c, re.IGNORECASE
        ))
        uses_384_for_h = bool(re.search(
            r'orig_h\s*=.*(?:384|VPSS_H|SCALED_H|YOLO_SCALED_HEIGHT)',
            c, re.IGNORECASE
        ))
        # x/w should still use 640 (not accidentally changed to 384)
        x_still_640 = bool(re.search(
            r'orig_x\s*=.*(?:640|MODEL_INPUT_W|VPSS_W|YOLO_INPUT_WIDTH)',
            c, re.IGNORECASE
        ))
        w_still_640 = bool(re.search(
            r'orig_w\s*=.*(?:640|MODEL_INPUT_W|VPSS_W|YOLO_INPUT_WIDTH)',
            c, re.IGNORECASE
        ))

        consistency_score = 0.0
        if uses_384_for_y:
            consistency_score += 0.3
        if uses_384_for_h:
            consistency_score += 0.2
        if x_still_640 and uses_384_for_y:
            # Only credit x correctness if y was actually fixed (asymmetric scaling)
            consistency_score += 0.25
        if w_still_640 and uses_384_for_h:
            consistency_score += 0.25
        components["consistent_with_visualizer"] = min(1.0, consistency_score)

    # Weights
    weights = {
        "json_exporter_y_scaling_fixed": 0.20,
        "json_exporter_h_scaling_fixed": 0.15,
        "txt_exporter_y_scaling_fixed": 0.15,
        "txt_exporter_h_scaling_fixed": 0.10,
        "detect_image_buffer_init": 0.20,
        "negative_coord_clamping": 0.10,
        "consistent_with_visualizer": 0.10,
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
