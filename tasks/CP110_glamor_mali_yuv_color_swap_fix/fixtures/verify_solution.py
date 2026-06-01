"""Hidden verifier for CP110 — Glamor Mali YUV Color Swap Fix.

Checks that the agent correctly fixes the Mali GPU color-swap bug in
glamor_import_dmabuf_textures() by ensuring non-AFBC OES import is
skipped on Mali GPUs while preserving all other functionality.

Also checks for production-quality code patterns: null-safety, proper
diagnostics logging, efficient single-call detection, and const usage.
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


def grade_workspace(ws: Path) -> dict:
    # Try both possible locations
    glamor_dir = ws / "fixtures" / "glamor"
    if not glamor_dir.exists():
        glamor_dir = ws / "glamor"

    egl_file = glamor_dir / "glamor_egl.c"

    components = {k: 0.0 for k in [
        "mali_detection_added",
        "oes_skip_on_mali",
        "afbc_path_preserved",
        "zc_r8_fallback_intact",
        "no_regressions",
        "null_safety_glgetstring",
        "diagnostic_logging",
        "detection_efficiency",
        "gl_context_ordering",
        "static_detection_cache",
        "afbc_block_integrity",
    ]}

    if not egl_file.exists():
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "glamor_egl.c not found",
        }

    src = _read(egl_file)

    # === Dimension 1: Mali GPU detection (0.20) ===
    # Check that there's actual CODE (not just comments) that detects Mali GPU.
    # Strip C comments to avoid false positives from descriptive comments.
    src_no_comments = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
    src_no_comments = re.sub(r'//[^\n]*', '', src_no_comments)

    mali_detect_score = 0.0
    # Must have strstr call with "Mali" string literal in code (not comments)
    has_strstr_mali = bool(re.search(r'strstr\s*\([^)]*"[Mm]ali"', src_no_comments))
    # Or glGetString(GL_RENDERER) combined with "Mali" string literal in code
    has_renderer_check = bool(
        re.search(r'glGetString\s*\(\s*GL_RENDERER\s*\)', src_no_comments) and
        re.search(r'"[Mm]ali"', src_no_comments)
    )
    # Variable assignment pattern: is_mali = ... or mali_gpu = ...
    has_mali_var = bool(re.search(r'\b\w*[Mm]ali\w*\s*=', src_no_comments))

    if has_strstr_mali or (has_renderer_check and has_mali_var):
        mali_detect_score = 1.0
    elif has_renderer_check or has_mali_var:
        mali_detect_score = 0.6
    else:
        mali_detect_score = 0.0

    components["mali_detection_added"] = mali_detect_score

    # === Dimension 2: OES skip on Mali (0.20) ===
    # The non-AFBC OES import block should be conditionally skipped on Mali
    # Key: the block starting with "if (epoxy_has_gl_extension..." for non-AFBC OES
    # should now be gated by a Mali check. Use comment-stripped source.

    oes_skip_score = 0.0

    # Find the non-AFBC OES block region (after the AFBC handling) in stripped source
    afbc_drop_pos = src_no_comments.find("GLAMOR_DMABUF_IMPORT_AFBC_DROP")
    non_afbc_oes_region = src_no_comments[afbc_drop_pos:] if afbc_drop_pos >= 0 else ""

    if non_afbc_oes_region:
        # Check if there's a Mali-conditional skip/guard before OES import
        # Could be: if (!is_mali) { OES block } or if (is_mali) { skip } before OES

        # Pattern 1: The OES block is wrapped in a !mali condition
        has_mali_gate_before_oes = bool(
            re.search(r'(!|not)\s*\w*[Mm]ali\w*.*epoxy_has_gl_extension', non_afbc_oes_region, re.DOTALL) or
            re.search(r'[Mm]ali\w*\s*[!=]=\s*(FALSE|0|false)', non_afbc_oes_region) or
            re.search(r'if\s*\(\s*!\s*\w*[Mm]ali', non_afbc_oes_region)
        )

        # Pattern 2: A Mali check that skips/goto/returns before OES
        has_mali_skip = bool(
            re.search(r'[Mm]ali.*goto|[Mm]ali.*skip|[Mm]ali.*fall', non_afbc_oes_region, re.DOTALL) or
            re.search(r'if\s*\(\s*\w*[Mm]ali[^)]*\)\s*\{?\s*(goto|;)', non_afbc_oes_region)
        )

        # Pattern 3: A variable/flag set from Mali detection that guards OES
        has_skip_var = bool(
            re.search(r'(skip_oes|mali_skip|skip_non_afbc)', non_afbc_oes_region)
        )

        if has_mali_gate_before_oes:
            oes_skip_score = 1.0
        elif has_mali_skip or has_skip_var:
            oes_skip_score = 0.8
        elif has_mali_var and 'epoxy_has_gl_extension' in non_afbc_oes_region:
            # Has a mali variable and OES check in same region, likely attempted fix
            oes_skip_score = 0.4

    components["oes_skip_on_mali"] = oes_skip_score

    # === Dimension 3: AFBC path preserved (0.10) ===
    # The AFBC OES import path must remain intact - it works correctly on Mali
    afbc_score = 0.0
    has_afbc_block = "SUNXI_YUV_AFBC_MOD_16x16" in src and "SUNXI_YUV_AFBC_MOD_32x8" in src
    has_afbc_return = "GLAMOR_DMABUF_IMPORT_OES" in src  # Still returns OES for AFBC
    has_afbc_drop = "GLAMOR_DMABUF_IMPORT_AFBC_DROP" in src

    if has_afbc_block and has_afbc_return and has_afbc_drop:
        afbc_score = 1.0
    elif has_afbc_block and has_afbc_return:
        afbc_score = 0.7
    elif has_afbc_block:
        afbc_score = 0.4

    components["afbc_path_preserved"] = afbc_score

    # === Dimension 4: ZC_R8 fallback intact (0.10) ===
    # The R8/GR88 2-plane and 3-plane paths must remain working
    zc_score = 0.0
    has_nv12 = "DRM_FORMAT_NV12" in src
    has_2plane = "glamor_dmabuf_import_2plane" in src
    has_3plane = "glamor_dmabuf_import_3plane_r8" in src
    has_zc_return = "GLAMOR_DMABUF_IMPORT_ZC_R8" in src

    zc_count = sum([has_nv12, has_2plane, has_3plane, has_zc_return])
    zc_score = min(zc_count / 4.0, 1.0)

    components["zc_r8_fallback_intact"] = zc_score

    # === Dimension 5: No regressions (0.10) ===
    # Check that critical code was not accidentally removed or broken
    regression_score = 1.0

    # Must still have the function signature
    if "glamor_import_dmabuf_textures" not in src:
        regression_score -= 0.5

    # Must still have buf_size check
    if "buf_size <= 0" not in src and "buf_size < 1" not in src:
        regression_score -= 0.2

    # Must still call compute_yuv_plane_layout
    if "compute_yuv_plane_layout" not in src:
        regression_score -= 0.3

    # Must still have P010 handling
    if "DRM_FORMAT_P010" not in src:
        regression_score -= 0.2

    # Must still have stride alignment check
    if "PANFROST_STRIDE_ALIGN" not in src:
        regression_score -= 0.2

    components["no_regressions"] = max(0.0, regression_score)

    # === Dimension 6: NULL safety on glGetString (0.15) ===
    # glGetString(GL_RENDERER) can return NULL on error or before context is current.
    # A production-quality fix MUST check for NULL before passing to strstr.
    # This is a critical defensive programming check.
    null_safety_score = 0.0

    # Look for NULL/null check patterns around glGetString or the renderer variable
    # Pattern: renderer && strstr(renderer, ...) or if (renderer != NULL)
    # or if (renderer) before strstr usage
    has_null_guard_inline = bool(
        re.search(r'\w*[Rr]ender\w*\s*&&\s*strstr', src_no_comments) or
        re.search(r'\w*[Rr]ender\w*\s*!=\s*NULL.*strstr', src_no_comments, re.DOTALL)
    )
    # Ternary or conditional assignment with NULL check
    has_null_guard_assign = bool(
        re.search(r'\w*[Mm]ali\w*\s*=\s*\w*[Rr]ender\w*\s*(&&|\?)', src_no_comments) or
        re.search(r'\w*[Mm]ali\w*\s*=.*\w*[Rr]ender\w*\s*!=\s*NULL', src_no_comments)
    )
    # Early return or guard: if (!renderer) return/goto
    has_null_early_return = bool(
        re.search(r'if\s*\(\s*!\s*\w*[Rr]ender\w*\s*\)', src_no_comments)
    )
    # Also accept: glGetString result directly tested in condition
    has_inline_null_test = bool(
        re.search(r'glGetString\s*\(\s*GL_RENDERER\s*\)\s*!=\s*NULL', src_no_comments) or
        re.search(r'glGetString\s*\(\s*GL_RENDERER\s*\)\s*\)', src_no_comments)
    )

    if has_null_guard_inline or has_null_guard_assign:
        null_safety_score = 1.0
    elif has_null_early_return or has_inline_null_test:
        null_safety_score = 0.8
    else:
        # No NULL safety at all — dangerous in production
        null_safety_score = 0.0

    components["null_safety_glgetstring"] = null_safety_score

    # === Dimension 7: Diagnostic logging on Mali skip (0.15) ===
    # The existing code follows a pattern of logging important path decisions
    # (see the AFBC log messages, the OES failure log). A proper fix should
    # log when Mali is detected and OES is being skipped, following the
    # existing one-shot logging pattern (static Bool logged = FALSE).
    diag_score = 0.0

    # Check for a log message related to Mali OES skip
    # The log should mention Mali and skipping/bypassing OES
    has_mali_log_errorf = bool(
        re.search(r'ErrorF\s*\([^)]*[Mm]ali', src_no_comments)
    )
    # Or using a different log function with Mali context
    has_mali_log_other = bool(
        re.search(r'(LogMessageVerb|xf86DrvMsg|LogMessage)\s*\([^)]*[Mm]ali', src_no_comments)
    )
    # Check for one-shot pattern (static Bool logged/printed = FALSE)
    has_oneshot_pattern = bool(
        re.search(r'static\s+Bool\s+\w*(log|print|mali)\w*\s*=\s*(FALSE|0)', src_no_comments)
    )
    # Simple log without one-shot (acceptable but not ideal)
    has_any_skip_log = bool(
        re.search(r'(ErrorF|LogMessage|xf86DrvMsg)\s*\([^)]*([Ss]kip|[Bb]ypass|[Ff]all)', src_no_comments)
    )

    if has_mali_log_errorf and has_oneshot_pattern:
        diag_score = 1.0
    elif has_mali_log_errorf or has_mali_log_other:
        diag_score = 0.7
    elif has_any_skip_log:
        diag_score = 0.4
    else:
        diag_score = 0.0

    components["diagnostic_logging"] = diag_score

    # === Dimension 8: Detection efficiency — single glGetString call (0.10) ===
    # glGetString is an OpenGL call that may have driver overhead. In a hot path
    # like texture import, it should be called at most once and cached. Multiple
    # calls to glGetString(GL_RENDERER) indicate an inefficient fix.
    # Also checks that detection uses const char* (read-only semantics).
    efficiency_score = 0.0

    # Count how many times glGetString(GL_RENDERER) appears in code
    renderer_calls = len(re.findall(r'glGetString\s*\(\s*GL_RENDERER\s*\)', src_no_comments))

    if renderer_calls == 1:
        efficiency_score += 0.5
    elif renderer_calls == 0:
        # May have cached it elsewhere or uses a different approach
        efficiency_score += 0.3
    else:
        # Multiple calls — inefficient
        efficiency_score += 0.0

    # Check for const qualifier on the renderer string variable
    has_const_renderer = bool(
        re.search(r'const\s+char\s*\*\s*\w*[Rr]ender', src_no_comments)
    )
    if has_const_renderer:
        efficiency_score += 0.5
    else:
        # Acceptable but not production-quality — non-const pointer to string literal
        efficiency_score += 0.1

    components["detection_efficiency"] = min(efficiency_score, 1.0)

    # === Dimension 9: GL context ordering — detection after glamor_make_current (0.12) ===
    # glGetString(GL_RENDERER) requires a current OpenGL context. The existing code
    # calls glamor_make_current() to ensure the context is active. Any Mali detection
    # using glGetString MUST appear AFTER glamor_make_current() in the source, otherwise
    # it's undefined behavior (returns NULL or garbage on some drivers).
    # Only models that understand OpenGL context lifecycle will get this right.
    context_order_score = 0.0

    # Find the function body of glamor_import_dmabuf_textures
    func_match = re.search(
        r'glamor_import_dmabuf_textures\s*\([^)]*\)\s*\{',
        src_no_comments, re.DOTALL
    )
    if func_match:
        func_body = src_no_comments[func_match.end():]
        # Find positions within the function body only
        make_current_pos = func_body.find("glamor_make_current")
        # Find glGetString call (with GL_RENDERER arg, not just declaration)
        glgetstring_match = re.search(r'glGetString\s*\(\s*GL_RENDERER\s*\)', func_body)
        glgetstring_pos = glgetstring_match.start() if glgetstring_match else -1

        if make_current_pos >= 0 and glgetstring_pos >= 0:
            if glgetstring_pos > make_current_pos:
                # Correct: glGetString is called after context is made current
                context_order_score = 1.0
            else:
                # Bug: calling glGetString before context is current
                context_order_score = 0.0
        elif glgetstring_pos >= 0:
            # glGetString present but glamor_make_current is missing/moved — risky
            context_order_score = 0.2
        else:
            # No glGetString(GL_RENDERER) call in function — alternate approach
            context_order_score = 0.3
    else:
        # Function not found at all
        context_order_score = 0.0

    components["gl_context_ordering"] = context_order_score

    # === Dimension 10: Static caching of detection result (0.12) ===
    # glamor_import_dmabuf_textures is called once per video frame (30-60fps).
    # The GPU renderer string never changes at runtime, so a production-quality
    # fix should cache the Mali detection result in a static variable to avoid
    # repeated string comparisons on every frame. The existing code already uses
    # the "static Bool" pattern for one-shot logging (see logged = FALSE),
    # so a strong model should recognize and apply the same pattern for detection.
    static_cache_score = 0.0

    # Extract the function body for analysis
    func_body_for_cache = ""
    func_match_cache = re.search(
        r'glamor_import_dmabuf_textures\s*\([^)]*\)\s*\{',
        src_no_comments, re.DOTALL
    )
    if func_match_cache:
        func_body_for_cache = src_no_comments[func_match_cache.end():]

    if func_body_for_cache:
        # Pattern: static Bool/int for the mali detection variable
        has_static_mali = bool(
            re.search(r'static\s+(Bool|int|_Bool)\s+\w*[Mm]ali\w*', func_body_for_cache)
        )
        # Pattern: static const char* for renderer caching
        has_static_renderer = bool(
            re.search(r'static\s+(const\s+)?char\s*\*\s*\w*[Rr]ender', func_body_for_cache)
        )
        # Pattern: static int/Bool initialized to -1 or similar sentinel (tri-state)
        has_tristate_cache = bool(
            re.search(r'static\s+(int|Bool)\s+\w*(mali|detect|checked)\w*\s*=\s*(-1|2|0xFF)', func_body_for_cache)
        )

        if has_static_mali or has_static_renderer:
            static_cache_score = 1.0
        elif has_tristate_cache:
            static_cache_score = 0.8
        else:
            # No caching — works but inefficient for a per-frame hot path
            static_cache_score = 0.0

    components["static_detection_cache"] = static_cache_score

    # === Dimension 11: AFBC block internal integrity (0.08) ===
    # The fix must NOT modify the internal logic of the AFBC OES block.
    # The AFBC block works correctly on Mali — only the non-AFBC OES path is broken.
    # A careful engineer adds the gate *outside* the AFBC block; a sloppy fix might
    # accidentally add mali checks inside the AFBC block or restructure it.
    afbc_integrity_score = 0.0

    # Extract the AFBC block (from "if (afbc)" to "return GLAMOR_DMABUF_IMPORT_AFBC_DROP")
    afbc_block_match = re.search(
        r'if\s*\(\s*afbc\s*\)\s*\{(.*?)return\s+GLAMOR_DMABUF_IMPORT_AFBC_DROP\s*;',
        src_no_comments, re.DOTALL
    )
    if afbc_block_match:
        afbc_block = afbc_block_match.group(1)
        # The AFBC block should NOT contain any Mali-related checks
        has_mali_in_afbc = bool(re.search(r'[Mm]ali', afbc_block))
        # Should still have the two OES import attempts (16x16 and 32x8)
        has_both_afbc_mods = (
            "SUNXI_YUV_AFBC_MOD_16x16" in afbc_block and
            "SUNXI_YUV_AFBC_MOD_32x8" in afbc_block
        )
        # Should still have the logged pattern
        has_logged_pattern = "logged" in afbc_block

        if not has_mali_in_afbc and has_both_afbc_mods and has_logged_pattern:
            afbc_integrity_score = 1.0
        elif not has_mali_in_afbc and has_both_afbc_mods:
            afbc_integrity_score = 0.7
        elif not has_mali_in_afbc:
            afbc_integrity_score = 0.4
        else:
            # Mali check incorrectly placed inside AFBC block
            afbc_integrity_score = 0.0
    else:
        # AFBC block structure was broken/removed
        afbc_integrity_score = 0.0

    components["afbc_block_integrity"] = afbc_integrity_score

    # Weighted overall score — rebalanced with hidden checks carrying significant weight
    # Core functional checks (0.35 total): baseline correctness
    # Quality/production checks (0.65 total): separates strong from weak
    weights = {
        "mali_detection_added": 0.10,
        "oes_skip_on_mali": 0.12,
        "afbc_path_preserved": 0.06,
        "zc_r8_fallback_intact": 0.06,
        "no_regressions": 0.05,
        "null_safety_glgetstring": 0.15,
        "diagnostic_logging": 0.12,
        "detection_efficiency": 0.08,
        "gl_context_ordering": 0.10,
        "static_detection_cache": 0.10,
        "afbc_block_integrity": 0.06,
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
