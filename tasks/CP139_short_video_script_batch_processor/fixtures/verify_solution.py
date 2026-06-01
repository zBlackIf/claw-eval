"""Hidden verifier for CP139 — Short Video Script Batch Processor."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _find_output_dir() -> Path:
    """Find the output directory."""
    candidates = [
        Path("/workspace/output"),
        Path("/workspace/fixtures/output"),
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return Path("/workspace/output")


def _find_processor() -> Path | None:
    """Find the processor script."""
    candidates = [
        Path("/workspace/fixtures/content_pipeline/processor.py"),
        Path("/workspace/content_pipeline/processor.py"),
        Path("/workspace/processor.py"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _run_processor() -> tuple[int, str, str]:
    """Run the processor and capture output."""
    proc = _find_processor()
    if not proc:
        return -1, "", "processor.py not found"
    try:
        result = subprocess.run(
            [sys.executable, str(proc)],
            capture_output=True, text=True, timeout=30,
            cwd=str(proc.parent)
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def grade_workspace() -> dict:
    components = {
        "processor_runs": 0.0,
        "correct_file_count": 0.0,
        "correct_naming": 0.0,
        "sections_present": 0.0,
        "variable_substitution": 0.0,
        "duration_filtering": 0.0,
        "platform_compat_filtering": 0.0,
        "fallback_handling": 0.0,
        "tag_format_quality": 0.0,
        "summary_output": 0.0,
        "no_residual_placeholders": 0.0,
        "idempotent_rerun": 0.0,
        "hook_header_level": 0.0,
        "body_content_completeness": 0.0,
        "skip_reason_specificity": 0.0,
    }

    # --- Dimension 1: processor runs without error ---
    returncode, stdout, stderr = _run_processor()
    if returncode == 0:
        components["processor_runs"] = 1.0
    elif returncode > 0:
        components["processor_runs"] = 0.3  # runs but has issues
    else:
        # processor not found or crashes
        components["processor_runs"] = 0.0
        return _build_result(components)

    # --- Find output directory ---
    output_dir = _find_output_dir()
    if not output_dir.exists():
        return _build_result(components)

    md_files = list(output_dir.glob("*.md"))

    # --- Dimension 2: correct number of output files ---
    # Expected: 7 campaigns total
    # CAM-2024-003 uses T002 (95s) on douyin (limit 60s) -> SKIP (duration)
    # CAM-2024-006 uses T002 (95s) on kuaishou (limit 90s) -> SKIP (duration)
    #   ALSO: T002 platform_tags=["video_hao","douyin"], kuaishou not in list -> SKIP (platform)
    # Remaining 5 should generate
    expected_count = 5
    actual_count = len(md_files)
    if actual_count == expected_count:
        components["correct_file_count"] = 1.0
    elif abs(actual_count - expected_count) == 1:
        components["correct_file_count"] = 0.6
    elif actual_count > 0:
        components["correct_file_count"] = 0.3
    else:
        components["correct_file_count"] = 0.0

    # --- Dimension 3: correct file naming ---
    expected_names = {
        "CAM-2024-001_douyin.md",
        "CAM-2024-002_video_hao.md",
        "CAM-2024-004_kuaishou.md",
        "CAM-2024-005_douyin.md",
        "CAM-2024-007_video_hao.md",
    }
    actual_names = {f.name for f in md_files}
    name_matches = len(expected_names & actual_names)
    if name_matches == len(expected_names):
        components["correct_naming"] = 1.0
    elif name_matches >= 3:
        components["correct_naming"] = 0.6
    elif name_matches >= 1:
        components["correct_naming"] = 0.3

    # --- Dimension 4: sections present in generated files ---
    section_scores = []
    for f in md_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        has_hook = bool(re.search(r"^#\s+Hook", content, re.MULTILINE))
        has_body = bool(re.search(r"^##\s+Body", content, re.MULTILINE))
        has_cta = bool(re.search(r"^##\s+CTA", content, re.MULTILINE))
        has_tags = bool(re.search(r"^##\s+Tags", content, re.MULTILINE))
        section_scores.append(sum([has_hook, has_body, has_cta, has_tags]) / 4.0)
    if section_scores:
        components["sections_present"] = sum(section_scores) / len(section_scores)

    # --- Dimension 5: variable substitution worked ---
    sub_scores = []
    cam001 = output_dir / "CAM-2024-001_douyin.md"
    if cam001.exists():
        content = cam001.read_text(encoding="utf-8", errors="ignore")
        checks = [
            "皮肤干燥起皮" in content,       # pain_point
            "水光肌" in content,              # brand_name
            "玻尿酸精华液" in content,        # product_name
            "{{" not in content,              # no remaining placeholders
        ]
        sub_scores.append(sum(checks) / len(checks))

    cam004 = output_dir / "CAM-2024-004_kuaishou.md"
    if cam004.exists():
        content = cam004.read_text(encoding="utf-8", errors="ignore")
        checks = [
            "三顿半" in content,             # brand_name
            "618大促" in content,             # event_name
            "{{" not in content,
        ]
        sub_scores.append(sum(checks) / len(checks))

    if sub_scores:
        components["variable_substitution"] = sum(sub_scores) / len(sub_scores)

    # --- Dimension 6: duration filtering (hidden check) ---
    # CAM-2024-003: T002 (95s) on douyin (60s limit) -> should NOT exist
    cam003_exists = (output_dir / "CAM-2024-003_douyin.md").exists()
    cam006_exists = (output_dir / "CAM-2024-006_kuaishou.md").exists()
    if not cam003_exists and not cam006_exists:
        components["duration_filtering"] = 1.0
    elif not cam003_exists or not cam006_exists:
        components["duration_filtering"] = 0.5
    else:
        components["duration_filtering"] = 0.0

    # --- Dimension 7: platform compatibility filtering (HIDDEN - harder check) ---
    # CAM-2024-006 uses T002 on kuaishou, but T002.platform_tags = ["video_hao", "douyin"]
    # A correct implementation must check platform_tags AND duration separately.
    # We verify the processor SOURCE CODE implements platform_tags checking logic,
    # not just duration checking. This is a subtle distinction many weak models miss.
    proc = _find_processor()
    platform_compat_score = 0.0
    if proc and proc.exists():
        proc_src = proc.read_text(encoding="utf-8", errors="ignore")
        # Check that the code actually reads and validates platform_tags
        has_platform_tags_check = bool(
            re.search(r"platform_tags", proc_src) and
            (re.search(r"(not\s+in|in\s+.*platform_tags|\bif\b.*platform)", proc_src, re.IGNORECASE))
        )
        # Check that the stdout/stderr mentions platform incompatibility when skipping
        combined_output = stdout + stderr
        has_platform_skip_msg = bool(
            re.search(r"(平台.*不[兼支]|不支持|incompatib|platform.*not.*support|不在.*platform|skip.*platform|平台.*跳过)", combined_output, re.IGNORECASE)
        )
        if has_platform_tags_check and has_platform_skip_msg:
            platform_compat_score = 1.0
        elif has_platform_tags_check:
            platform_compat_score = 0.6
        elif has_platform_skip_msg:
            platform_compat_score = 0.4
        # Also: if CAM-2024-006 is absent, partial credit for correct behavior
        if not cam006_exists and platform_compat_score < 0.3:
            platform_compat_score = 0.3
    components["platform_compat_filtering"] = platform_compat_score

    # --- Dimension 8: fallback handling (HIDDEN - strict check) ---
    # The rules specify a 3-level variable resolution:
    #   1. variables_override -> 2. global_variables -> 3. default_fallback "[未填写]"
    # We check that the code implements ALL THREE levels correctly.
    fallback_score = 0.0
    if proc and proc.exists():
        proc_src = proc.read_text(encoding="utf-8", errors="ignore")
        # Level 1: uses variables_override (most models do this)
        has_override = bool(re.search(r"variables_override|override", proc_src))
        # Level 2: falls back to global_variables
        has_global = bool(re.search(r"global_variables|global_var", proc_src))
        # Level 3: uses default_fallback "[未填写]"
        has_default_fb = bool(re.search(r"default_fallback|未填写", proc_src))
        # Score: each level matters
        fallback_score = sum([has_override, has_global, has_default_fb]) / 3.0
    components["fallback_handling"] = fallback_score

    # --- Dimension 9: tag formatting quality (HIDDEN) ---
    # Tags section should be a proper markdown list with `- tag` items.
    # Many weak models just dump comma-separated or bracket-enclosed tags.
    tag_scores = []
    for f in md_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        tags_match = re.search(r"^##\s+Tags\s*\n(.*?)(?=\n#|\Z)", content, re.MULTILINE | re.DOTALL)
        if tags_match:
            tags_section = tags_match.group(1).strip()
            lines = [l.strip() for l in tags_section.splitlines() if l.strip()]
            if not lines:
                tag_scores.append(0.0)
                continue
            # Each tag line should start with "- "
            proper_list = sum(1 for l in lines if l.startswith("- ")) / len(lines)
            # Tags should NOT contain {{ }} (unresolved placeholders)
            no_placeholders = 0.0 if "{{" in tags_section else 1.0
            # Tags should have at least 2 items
            has_enough = 1.0 if len(lines) >= 2 else 0.5
            tag_scores.append((proper_list * 0.5 + no_placeholders * 0.3 + has_enough * 0.2))
    if tag_scores:
        components["tag_format_quality"] = sum(tag_scores) / len(tag_scores)

    # --- Dimension 10: summary output quality (HIDDEN) ---
    # rules.md requires: "处理完成后在控制台输出汇总：生成了多少条、跳过了多少条（含跳过原因）"
    combined_output = stdout + stderr
    summary_score = 0.0
    # Must mention number generated
    has_gen_count = bool(re.search(r"(生成.*[0-9]|[0-9].*[条个].*生成|generated\s*[:\s]*[0-9])", combined_output, re.IGNORECASE))
    # Must mention number skipped
    has_skip_count = bool(re.search(r"(跳过.*[0-9]|[0-9].*[条个].*跳过|skip.*[0-9])", combined_output, re.IGNORECASE))
    # Must mention skip reason (duration or platform)
    has_skip_reason = bool(re.search(r"(时长|超[过出]|duration|限制|platform|平台)", combined_output, re.IGNORECASE))
    summary_score = sum([has_gen_count, has_skip_count, has_skip_reason]) / 3.0
    components["summary_output"] = summary_score

    # --- Dimension 11: no residual placeholders across ALL files (HIDDEN - strict) ---
    # Check EVERY generated file for leftover {{ }} placeholders.
    # This is stricter than the spot check in dimension 5.
    placeholder_scores = []
    for f in md_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        remaining_placeholders = re.findall(r"\{\{[^}]+\}\}", content)
        if not remaining_placeholders:
            placeholder_scores.append(1.0)
        else:
            # Penalize proportionally to how many remain
            placeholder_scores.append(max(0.0, 1.0 - len(remaining_placeholders) * 0.25))
    if placeholder_scores:
        components["no_residual_placeholders"] = sum(placeholder_scores) / len(placeholder_scores)
    elif actual_count == 0:
        components["no_residual_placeholders"] = 0.0
    else:
        components["no_residual_placeholders"] = 0.0

    # --- Dimension 12: idempotent re-run (HIDDEN - advanced) ---
    # A well-written processor should produce the same output when run twice.
    # Run it again and verify file count hasn't changed (no duplicates, no appends).
    returncode2, _, _ = _run_processor()
    if returncode2 == 0:
        md_files_after = list(output_dir.glob("*.md"))
        if len(md_files_after) == len(md_files):
            # Check file sizes haven't doubled (no append-mode bug)
            sizes_before = {f.name: f.stat().st_size for f in md_files}
            sizes_after = {f.name: f.stat().st_size for f in md_files_after}
            size_stable = all(
                abs(sizes_after.get(name, 0) - size) < 10
                for name, size in sizes_before.items()
            )
            components["idempotent_rerun"] = 1.0 if size_stable else 0.4
        else:
            # File count changed on re-run (duplicate generation bug)
            components["idempotent_rerun"] = 0.0
    else:
        components["idempotent_rerun"] = 0.2  # at least it ran before

    # --- Dimension 13: hook header level (HIDDEN - attention to detail) ---
    # rules.md clearly shows "# Hook" as h1, while Body/CTA/Tags are h2.
    # Many weak models normalize everything to h2 (## Hook ## Body ## CTA ## Tags).
    # A careful implementation follows the exact spec: h1 for Hook, h2 for the rest.
    hook_level_scores = []
    for f in md_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        # Correct: "# Hook" (h1, exactly one #) NOT "## Hook" (h2)
        has_h1_hook = bool(re.search(r"^# Hook\s*$", content, re.MULTILINE))
        has_h2_hook = bool(re.search(r"^## Hook\s*$", content, re.MULTILINE))
        # Correct: "## Body", "## CTA", "## Tags" are h2
        has_h2_body = bool(re.search(r"^## Body\s*$", content, re.MULTILINE))
        has_h2_cta = bool(re.search(r"^## CTA\s*$", content, re.MULTILINE))
        has_h2_tags = bool(re.search(r"^## Tags\s*$", content, re.MULTILINE))
        if has_h1_hook and has_h2_body and has_h2_cta and has_h2_tags:
            hook_level_scores.append(1.0)
        elif has_h2_hook and has_h2_body and has_h2_cta and has_h2_tags:
            # Common weak-model mistake: all h2. Partial credit only.
            hook_level_scores.append(0.3)
        elif has_h1_hook:
            hook_level_scores.append(0.6)
        else:
            hook_level_scores.append(0.0)
    if hook_level_scores:
        components["hook_header_level"] = sum(hook_level_scores) / len(hook_level_scores)

    # --- Dimension 14: body content completeness (HIDDEN - quality check) ---
    # Verify generated body text is substantive and contains expected key phrases
    # from the fully-resolved template. Weak models often produce truncated or
    # structurally broken body content (e.g., missing second half of template text).
    body_completeness_scores = []
    # CAM-2024-001_douyin.md: T001 body should contain feature_1, feature_2, usage_period, demo_description
    cam001_file = output_dir / "CAM-2024-001_douyin.md"
    if cam001_file.exists():
        content = cam001_file.read_text(encoding="utf-8", errors="ignore")
        body_match = re.search(r"^## Body\s*\n(.*?)(?=\n##|\Z)", content, re.MULTILINE | re.DOTALL)
        if body_match:
            body_text = body_match.group(1).strip()
            # Check key phrases that must appear from full template expansion
            expected_phrases = [
                "小分子玻尿酸深层补水",        # feature_1
                "不油腻",                       # feature_2 partial
                "两个月",                       # usage_period
                "判若两人",                     # demo_description partial
                "护肤",                         # product_category (from "护肤神器")
            ]
            found = sum(1 for p in expected_phrases if p in body_text)
            body_completeness_scores.append(found / len(expected_phrases))
        else:
            body_completeness_scores.append(0.0)

    # CAM-2024-005_douyin.md: T004 body should contain step_1, tip_1, step_2, etc.
    cam005_file = output_dir / "CAM-2024-005_douyin.md"
    if cam005_file.exists():
        content = cam005_file.read_text(encoding="utf-8", errors="ignore")
        body_match = re.search(r"^## Body\s*\n(.*?)(?=\n##|\Z)", content, re.MULTILINE | re.DOTALL)
        if body_match:
            body_text = body_match.group(1).strip()
            expected_phrases = [
                "剪映",                         # step_1 partial
                "素材最好提前按顺序命名",       # tip_1
                "自动踩点",                     # step_2 partial
                "手动拖拽对齐",                 # common_mistake
                "微调转场",                     # step_3 partial
            ]
            found = sum(1 for p in expected_phrases if p in body_text)
            body_completeness_scores.append(found / len(expected_phrases))
        else:
            body_completeness_scores.append(0.0)

    # CAM-2024-004_kuaishou.md: T003 body should contain deal_1, deal_2, reason, personal_quantity
    cam004_file = output_dir / "CAM-2024-004_kuaishou.md"
    if cam004_file.exists():
        content = cam004_file.read_text(encoding="utf-8", errors="ignore")
        body_match = re.search(r"^## Body\s*\n(.*?)(?=\n##|\Z)", content, re.MULTILINE | re.DOTALL)
        if body_match:
            body_text = body_match.group(1).strip()
            expected_phrases = [
                "买三送一",                     # deal_1
                "满199再减30",                  # deal_2
                "清库存给新品让位",             # reason
                "5盒",                          # personal_quantity
            ]
            found = sum(1 for p in expected_phrases if p in body_text)
            body_completeness_scores.append(found / len(expected_phrases))
        else:
            body_completeness_scores.append(0.0)

    if body_completeness_scores:
        components["body_content_completeness"] = sum(body_completeness_scores) / len(body_completeness_scores)

    # --- Dimension 15: skip reason specificity (HIDDEN - communication quality) ---
    # A well-written processor outputs SPECIFIC skip reasons with actual numbers,
    # e.g., "CAM-2024-003 跳过：模板时长95s超过douyin限制60s"
    # Weak models just output generic "跳过" without campaign IDs or numbers.
    combined_out = stdout + stderr
    specificity_score = 0.0
    specificity_checks = 0
    specificity_hits = 0

    # Check 1: Skip message mentions specific campaign ID (CAM-2024-003 or CAM-2024-006)
    has_cam003_ref = bool(re.search(r"CAM-2024-003", combined_out))
    has_cam006_ref = bool(re.search(r"CAM-2024-006", combined_out))
    specificity_checks += 2
    specificity_hits += int(has_cam003_ref) + int(has_cam006_ref)

    # Check 2: Skip message includes actual duration numbers (95, 60, 90)
    has_duration_numbers = bool(
        re.search(r"95", combined_out) and
        re.search(r"(60|90)", combined_out)
    )
    specificity_checks += 1
    specificity_hits += int(has_duration_numbers)

    # Check 3: Skip message differentiates between duration and platform reasons
    # (i.e., mentions both types of skip reasons separately, not a single generic message)
    has_duration_keyword = bool(re.search(r"(时长|duration|超[过出]限)", combined_out, re.IGNORECASE))
    has_platform_keyword = bool(re.search(r"(平台[^限]|platform(?!.*limit)|兼容|适用)", combined_out, re.IGNORECASE))
    has_both_reasons = has_duration_keyword and has_platform_keyword
    specificity_checks += 1
    specificity_hits += int(has_both_reasons)

    if specificity_checks > 0:
        specificity_score = specificity_hits / specificity_checks
    components["skip_reason_specificity"] = specificity_score

    return _build_result(components)


def _build_result(components: dict) -> dict:
    # Weights designed so that:
    # - Basic functionality (runs, file count, naming, sections, basic substitution) = ~0.30
    # - Hidden harder checks = ~0.70
    # Strong model target: 0.7-0.85, weak model target: 0.4-0.6
    weights = {
        "processor_runs": 0.06,
        "correct_file_count": 0.06,
        "correct_naming": 0.06,
        "sections_present": 0.06,
        "variable_substitution": 0.06,
        "duration_filtering": 0.06,
        "platform_compat_filtering": 0.10,
        "fallback_handling": 0.10,
        "tag_format_quality": 0.06,
        "summary_output": 0.06,
        "no_residual_placeholders": 0.05,
        "idempotent_rerun": 0.05,
        "hook_header_level": 0.10,
        "body_content_completeness": 0.08,
        "skip_reason_specificity": 0.04,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    result = grade_workspace()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
