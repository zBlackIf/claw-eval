"""Hidden verifier for CP141 — Content Creator Workflow Toolkit.

Three-tier grading with discrimination:
  - Tier 1 EASY (25%): basic structure + basic functionality — all agents should pass
  - Tier 2 MEDIUM (40%): functional correctness — most agents pass partially
  - Tier 3 HARD (35%): advanced hidden checks — only strong agents pass

Tier 3 (hidden, hard) tests edge cases, structural output quality, multi-rule
interactions, and robustness that weaker agents miss.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(ws: Path, name_pattern: str) -> Path | None:
    """Find a file matching pattern anywhere under ws."""
    for p in ws.rglob("*"):
        if re.search(name_pattern, p.name, re.IGNORECASE):
            return p
    return None


def _run_cli(workflow_file: Path, args: list[str], cwd: Path, timeout: int = 15) -> tuple[int, str, str]:
    """Run the workflow CLI with given args. Returns (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            [sys.executable, str(workflow_file.resolve())] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd.resolve()),
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)


def grade_workspace(ws: Path) -> dict:
    """Grade the content creator workflow toolkit implementation."""

    # Find workflow.py
    workflow_file = None
    for candidate in [
        ws / "content-workspace" / "workflow.py",
        ws / "workflow.py",
    ]:
        if candidate.exists():
            workflow_file = candidate
            break
    if not workflow_file:
        workflow_file = _find_file(ws, r"workflow\.py$")

    # ========== TIER 1 EASY: Basic checks all agents pass (25% total) ==========
    tier1 = {k: 0.0 for k in [
        "cli_structure",
        "forbidden_word_logic",
        "config_driven",
        "runs_without_crash",
    ]}

    if workflow_file and workflow_file.exists():
        content = _read(workflow_file)

        # 1a. CLI framework detection
        has_argparse = "argparse" in content or "click" in content or "typer" in content
        has_subcommands = bool(re.search(
            r"(add_subparsers|add_parser|@app\.command|@cli\.command|subparsers)", content
        ))
        if has_argparse and has_subcommands:
            tier1["cli_structure"] = 1.0
        elif has_argparse:
            tier1["cli_structure"] = 0.5

        # 1b. Forbidden word detection logic
        has_word_iter = bool(re.search(
            r"for\s+\w+\s+in\s+.*(?:forbidden|banned|word)", content, re.IGNORECASE
        ))
        has_match = bool(re.search(r"(in\s+\w+|\.find\(|re\.(search|findall))", content))
        if has_word_iter and has_match:
            tier1["forbidden_word_logic"] = 1.0
        elif has_word_iter or ("forbidden" in content.lower() and has_match):
            tier1["forbidden_word_logic"] = 0.5

        # 1c. Config-driven (must json.load a config file)
        has_json_load = bool(re.search(r"json\.loads?\(", content))
        has_config_ref = "config" in content.lower()
        if has_json_load and has_config_ref:
            tier1["config_driven"] = 1.0
        elif has_json_load or has_config_ref:
            tier1["config_driven"] = 0.3

        # 1d. Runs without crash
        cwd = workflow_file.parent
        rc_help, _, _ = _run_cli(workflow_file, ["--help"], cwd)
        rc_scan, out_scan, err_scan = _run_cli(workflow_file, ["scan"], cwd)
        rc_check, out_check, err_check = _run_cli(
            workflow_file, ["check", "drafts/weekly_plan.md"], cwd
        )
        if rc_check != 0:
            rc_check, out_check, err_check = _run_cli(
                workflow_file, ["check", "--file", "drafts/weekly_plan.md"], cwd
            )
        if rc_check != 0:
            rc_check, out_check, err_check = _run_cli(
                workflow_file, ["check", str(cwd / "drafts" / "weekly_plan.md")], cwd
            )

        any_ran = (rc_help == 0) or (rc_scan == 0) or (rc_check == 0)
        tier1["runs_without_crash"] = 1.0 if any_ran else 0.0

    tier1_weights = {
        "cli_structure": 0.07,
        "forbidden_word_logic": 0.06,
        "config_driven": 0.06,
        "runs_without_crash": 0.06,
    }
    tier1_score = sum(tier1_weights[k] * tier1[k] for k in tier1_weights)

    # ========== TIER 2 MEDIUM: Functional correctness (40% total) ==========
    tier2 = {k: 0.0 for k in [
        "detects_forbidden_weekly_plan",
        "detects_title_too_long",
        "clean_file_no_false_positive",
        "batch_scan_logic",
        "exit_code_semantics",
    ]}

    if workflow_file and workflow_file.exists():
        cwd = workflow_file.parent
        # Reuse scan/check output from tier1
        all_output = f"{out_scan}\n{out_check}\n{err_scan}\n{err_check}".lower()

        # 2a. Detects forbidden words in weekly_plan.md
        expected_forbidden = ["不看后悔", "免费领取", "限时秒杀"]
        found_forbidden = sum(1 for w in expected_forbidden if w in all_output)
        if found_forbidden == 0:
            if "forbidden" in all_output and "weekly_plan" in all_output:
                found_forbidden = 1
            elif "违禁" in all_output and "weekly" in all_output:
                found_forbidden = 1

        if found_forbidden >= 3:
            tier2["detects_forbidden_weekly_plan"] = 1.0
        elif found_forbidden >= 2:
            tier2["detects_forbidden_weekly_plan"] = 0.6
        elif found_forbidden >= 1:
            tier2["detects_forbidden_weekly_plan"] = 0.3

        # 2b. Detects title too long in weekly_plan.md
        title_violation_found = bool(re.search(
            r"(title.*(长|exceed|over|too.?long|chars)|标题.*(超|长)|title_too_long|max_title)",
            all_output, re.IGNORECASE
        ))
        tier2["detects_title_too_long"] = 1.0 if title_violation_found else 0.0

        # 2c. Clean file should NOT trigger false positives
        rc_clean, out_clean, err_clean = _run_cli(
            workflow_file, ["check", "drafts/article_skincare_guide.md"], cwd
        )
        if rc_clean != 0:
            rc_clean, out_clean, err_clean = _run_cli(
                workflow_file, ["check", "--file", "drafts/article_skincare_guide.md"], cwd
            )
        if rc_clean != 0:
            rc_clean, out_clean, err_clean = _run_cli(
                workflow_file, ["check", str(cwd / "drafts" / "article_skincare_guide.md")], cwd
            )

        clean_output = f"{out_clean}\n{err_clean}".lower()
        clean_stripped = re.sub(
            r"(no|0|zero|没有|无)\s*(violation|error|issue|problem|违禁|问题)s?\s*(found|detected|发现)?",
            "", clean_output
        )
        has_violation_in_clean = bool(re.search(
            r"(violation|违禁|forbidden|问题|超长|exceed)", clean_stripped
        ))
        if rc_clean == 0 and not has_violation_in_clean:
            tier2["clean_file_no_false_positive"] = 1.0
        elif rc_clean == 0 and has_violation_in_clean:
            tier2["clean_file_no_false_positive"] = 0.0
        else:
            if "skincare" in all_output or "article_skincare" in all_output:
                if not bool(re.search(r"(skincare|article_skincare).*?(violation|违禁|forbidden)", all_output)):
                    tier2["clean_file_no_false_positive"] = 0.5
                else:
                    tier2["clean_file_no_false_positive"] = 0.0
            else:
                tier2["clean_file_no_false_positive"] = 0.3

        # 2d. Batch scan logic (static check in code)
        content = _read(workflow_file)
        has_dir_scan = bool(re.search(r"(glob|listdir|scandir|iterdir|walk|rglob)", content))
        has_file_filter = bool(re.search(r"\.(md|txt|markdown)", content))
        if has_dir_scan and has_file_filter:
            tier2["batch_scan_logic"] = 1.0
        elif has_dir_scan:
            tier2["batch_scan_logic"] = 0.5

        # 2e. Exit code semantics
        if any_ran:
            dirty_nonzero = (rc_check != 0) or (rc_scan != 0)
            clean_zero = (rc_clean == 0)
            if dirty_nonzero and clean_zero:
                tier2["exit_code_semantics"] = 1.0
            elif clean_zero and not dirty_nonzero:
                tier2["exit_code_semantics"] = 0.3
            elif dirty_nonzero and not clean_zero:
                tier2["exit_code_semantics"] = 0.2

    tier2_weights = {
        "detects_forbidden_weekly_plan": 0.10,
        "detects_title_too_long": 0.08,
        "clean_file_no_false_positive": 0.08,
        "batch_scan_logic": 0.06,
        "exit_code_semantics": 0.08,
    }
    tier2_score = sum(tier2_weights[k] * tier2[k] for k in tier2_weights)

    # ========== TIER 3 HARD: Advanced hidden checks (35% total) ==========
    # Only strong agents pass these — tests edge cases, precision, config
    # interactions, and robustness under novel inputs.
    tier3 = {k: 0.0 for k in [
        "line_number_accuracy",
        "config_change_respected",
        "substring_false_match_avoidance",
        "multi_violation_per_line",
        "novel_file_detection",
        "title_length_boundary",
        "structured_output_format",
    ]}

    if workflow_file and workflow_file.exists():
        cwd = workflow_file.parent
        all_output = f"{out_scan}\n{out_check}\n{err_scan}\n{err_check}".lower()

        # 3a. Line number accuracy — must report CORRECT line numbers
        # In weekly_plan.md:
        #   Line 13: "不看后悔" (forbidden word in title)
        #   Line 25: "免费领取" (forbidden word in title)
        #   Line 33: "限时秒杀" (forbidden word in title)
        expected_lines = [13, 25, 33]
        line_accuracy_hits = 0
        for ln in expected_lines:
            if re.search(rf"(line\s*{ln}|行\s*{ln}|:{ln}[\s:]|L{ln}\b|第{ln}行|\[{ln}\])", all_output):
                line_accuracy_hits += 1

        if line_accuracy_hits >= 3:
            tier3["line_number_accuracy"] = 1.0
        elif line_accuracy_hits >= 2:
            tier3["line_number_accuracy"] = 0.7
        elif line_accuracy_hits >= 1:
            tier3["line_number_accuracy"] = 0.3

        # 3b. Config change respected — modify config and re-run
        # Add "面霜" to forbidden words, then check previously-clean article
        config_path = cwd / "config.json"
        original_config = _read(config_path)
        if original_config:
            try:
                cfg = json.loads(original_config)
                cfg["content_rules"]["forbidden_words"].append("面霜")
                config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

                rc_mod, out_mod, err_mod = _run_cli(
                    workflow_file, ["check", "drafts/article_skincare_guide.md"], cwd
                )
                if rc_mod != 0:
                    rc_mod, out_mod, err_mod = _run_cli(
                        workflow_file, ["check", "--file", "drafts/article_skincare_guide.md"], cwd
                    )
                if rc_mod != 0:
                    rc_mod, out_mod, err_mod = _run_cli(
                        workflow_file, ["check", str(cwd / "drafts" / "article_skincare_guide.md")], cwd
                    )

                mod_output = f"{out_mod}\n{err_mod}".lower()
                if "面霜" in mod_output:
                    tier3["config_change_respected"] = 1.0
                elif re.search(r"(violation|违禁|forbidden|问题)", mod_output):
                    tier3["config_change_respected"] = 0.7
            except Exception:
                pass
            finally:
                try:
                    config_path.write_text(original_config, encoding="utf-8")
                except Exception:
                    pass

        # 3c. Substring false match avoidance
        # Create a temp file with "免费" (substring of "免费领取") — tool should NOT flag it.
        # Also include "秒杀" (substring of "限时秒杀") — should NOT flag.
        # A strong tool only matches exact forbidden word phrases.
        try:
            tmp_content = "# 测试标题\n\n这是免费的资源。秒杀价格很划算。\n"
            tmp_file = cwd / "drafts" / "_test_substring.md"
            tmp_file.write_text(tmp_content, encoding="utf-8")

            rc_sub, out_sub, err_sub = _run_cli(
                workflow_file, ["check", "drafts/_test_substring.md"], cwd
            )
            if rc_sub != 0:
                rc_sub, out_sub, err_sub = _run_cli(
                    workflow_file, ["check", "--file", "drafts/_test_substring.md"], cwd
                )
            if rc_sub != 0:
                rc_sub, out_sub, err_sub = _run_cli(
                    workflow_file, ["check", str(tmp_file)], cwd
                )

            sub_output = f"{out_sub}\n{err_sub}".lower()
            sub_stripped = re.sub(
                r"(no|0|zero|没有|无)\s*(violation|error|issue|problem|违禁|问题)s?\s*(found|detected|发现)?",
                "", sub_output
            )
            # If the tool falsely detects violations (substring matches)
            has_false_match = bool(re.search(
                r"(violation|违禁|forbidden|问题)", sub_stripped
            ))
            if not has_false_match and rc_sub == 0:
                # Correct: no false positive on substrings
                tier3["substring_false_match_avoidance"] = 1.0
            elif not has_false_match:
                # Ran but maybe exited non-zero for other reasons
                tier3["substring_false_match_avoidance"] = 0.5
            else:
                # False positive — weak implementation
                tier3["substring_false_match_avoidance"] = 0.0
        except Exception:
            tier3["substring_false_match_avoidance"] = 0.0
        finally:
            try:
                tmp_file.unlink(missing_ok=True)
            except Exception:
                pass

        # 3d. Multi-violation per line detection
        # Line 33 of weekly_plan.md has BOTH a forbidden word ("限时秒杀") AND
        # title too long. Strong tools report both violations for the same line.
        # Check that both forbidden word AND title length issue mentioned for line 33
        has_forbidden_33 = bool(re.search(
            r"(33|三十三).{0,40}(限时秒杀|forbidden|违禁)", all_output
        )) or bool(re.search(
            r"(限时秒杀).{0,40}(33|三十三)", all_output
        ))
        has_title_33 = bool(re.search(
            r"(33|三十三).{0,40}(title|标题|长|exceed|too.?long)", all_output
        )) or bool(re.search(
            r"(title|标题|长|exceed).{0,40}(33|三十三)", all_output
        ))
        if has_forbidden_33 and has_title_33:
            tier3["multi_violation_per_line"] = 1.0
        elif has_forbidden_33 or has_title_33:
            tier3["multi_violation_per_line"] = 0.3

        # 3e. Novel file detection — tool handles new files dynamically
        # Create a new draft with known violations, run scan, verify it's found
        try:
            novel_content = (
                "# 超级限时秒杀活动不容错过的好产品推荐给大家一起来看\n\n"
                "这里有史上最低价格的面膜推荐。\n"
                "不看后悔哦。\n"
            )
            novel_file = cwd / "drafts" / "_test_novel_draft.md"
            novel_file.write_text(novel_content, encoding="utf-8")

            rc_novel, out_novel, err_novel = _run_cli(workflow_file, ["scan"], cwd)
            novel_output = f"{out_novel}\n{err_novel}".lower()

            # Check that the new file is picked up in scan results
            novel_detected = (
                "_test_novel" in novel_output or "novel_draft" in novel_output
            )
            # Check that violations in the novel file are reported
            novel_has_violations = (
                "限时秒杀" in novel_output or
                "史上最低" in novel_output or
                "不看后悔" in novel_output
            )
            if novel_detected and novel_has_violations:
                tier3["novel_file_detection"] = 1.0
            elif novel_has_violations:
                tier3["novel_file_detection"] = 0.7
            elif novel_detected:
                tier3["novel_file_detection"] = 0.4
        except Exception:
            pass
        finally:
            try:
                novel_file.unlink(missing_ok=True)
            except Exception:
                pass

        # 3f. Title length boundary — exactly at limit should NOT be flagged
        # Config says max_title_length: 20. A 20-char title is OK, 21 is not.
        try:
            # "测试标题正好二十个字符呀" = exactly 11 chars. Use ASCII for precision.
            # 20 chars: "12345678901234567890"
            boundary_content = (
                "# 12345678901234567890\n\n"  # exactly 20 chars - should pass
                "正文内容。\n\n"
                "# 123456789012345678901\n\n"  # 21 chars - should fail
                "另一段正文。\n"
            )
            boundary_file = cwd / "drafts" / "_test_boundary.md"
            boundary_file.write_text(boundary_content, encoding="utf-8")

            rc_bnd, out_bnd, err_bnd = _run_cli(
                workflow_file, ["check", "drafts/_test_boundary.md"], cwd
            )
            if rc_bnd != 0:
                rc_bnd, out_bnd, err_bnd = _run_cli(
                    workflow_file, ["check", "--file", "drafts/_test_boundary.md"], cwd
                )
            if rc_bnd != 0:
                rc_bnd, out_bnd, err_bnd = _run_cli(
                    workflow_file, ["check", str(boundary_file)], cwd
                )

            bnd_output = f"{out_bnd}\n{err_bnd}".lower()
            # Should detect ONE title violation (21 chars) but not the other (20 chars)
            # Check that 21-char title is flagged
            flags_21 = bool(re.search(
                r"(123456789012345678901|21|title.*exceed|标题.*超)", bnd_output
            ))
            # Check that 20-char title is NOT flagged as violation
            # Look for mentions of line 1 or the exact 20-char string in violation context
            flags_20_violation = bool(re.search(
                r"12345678901234567890[^1].{0,30}(violation|exceed|超|too.?long)", bnd_output
            ))
            if flags_21 and not flags_20_violation:
                tier3["title_length_boundary"] = 1.0
            elif flags_21:
                # Caught the 21-char but also false positive on 20
                tier3["title_length_boundary"] = 0.4
            elif not flags_21 and not flags_20_violation:
                # Didn't flag either — lenient partial credit if file ran clean
                tier3["title_length_boundary"] = 0.1
        except Exception:
            pass
        finally:
            try:
                boundary_file.unlink(missing_ok=True)
            except Exception:
                pass

        # 3g. Structured output format — output should be parseable / well-structured
        # Strong tools produce machine-readable output (JSON, or consistent tabular format)
        # Check if output has structured violation reports with file + line + type + detail
        scan_output = f"{out_scan}\n{err_scan}"
        check_output = f"{out_check}\n{err_check}"
        combined = scan_output + check_output

        # Check for JSON output
        is_json_output = False
        try:
            # Try to parse any JSON in the output
            for line in combined.splitlines():
                line = line.strip()
                if line.startswith(("{", "[")):
                    json.loads(line)
                    is_json_output = True
                    break
        except (json.JSONDecodeError, ValueError):
            pass

        # Check for consistent columnar/tabular structure
        # e.g., "file:line:type:detail" or "| file | line | ..."
        has_consistent_format = False
        output_lines = [l for l in combined.splitlines() if l.strip()]
        if len(output_lines) >= 2:
            # Check if multiple lines share the same delimiter pattern
            delim_patterns = [
                r"^.+:.+:.+:.+$",  # colon-separated
                r"^\|.+\|.+\|",     # pipe-separated table
                r"^\[.+\]\s+.+",    # bracketed prefix
            ]
            for pat in delim_patterns:
                matching = sum(1 for l in output_lines if re.match(pat, l.strip()))
                if matching >= 2:
                    has_consistent_format = True
                    break

        if is_json_output:
            tier3["structured_output_format"] = 1.0
        elif has_consistent_format:
            tier3["structured_output_format"] = 0.6
        else:
            # Check for at least filename + line number in output
            has_file_line = bool(re.search(
                r"(weekly_plan|article_skincare).*(line|行|:)\s*\d+", combined.lower()
            ))
            if has_file_line:
                tier3["structured_output_format"] = 0.3

    tier3_weights = {
        "line_number_accuracy": 0.06,
        "config_change_respected": 0.06,
        "substring_false_match_avoidance": 0.06,
        "multi_violation_per_line": 0.05,
        "novel_file_detection": 0.05,
        "title_length_boundary": 0.04,
        "structured_output_format": 0.03,
    }
    tier3_score = sum(tier3_weights[k] * tier3[k] for k in tier3_weights)

    # ========== Overall ==========
    overall = tier1_score + tier2_score + tier3_score
    components = {}
    components.update({f"t1_{k}": v for k, v in tier1.items()})
    components.update({f"t2_{k}": v for k, v in tier2.items()})
    components.update({f"t3_{k}": v for k, v in tier3.items()})

    return {
        "overall_score": round(overall, 4),
        "tier1_easy_score": round(tier1_score, 4),
        "tier2_medium_score": round(tier2_score, 4),
        "tier3_hard_score": round(tier3_score, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "tier1_weights": tier1_weights,
        "tier2_weights": tier2_weights,
        "tier3_weights": tier3_weights,
    }


def main():
    # Try /workspace/fixtures/content-workspace first, fallback to /workspace/content-workspace
    ws = Path("/workspace/fixtures/content-workspace")
    if not ws.exists():
        ws = Path("/workspace/content-workspace")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
