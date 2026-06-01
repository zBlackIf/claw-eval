"""Hidden verifier for CP178 — MySQL SOP Runbook Update.

Tiered hidden checks:
- Easy hidden (any competent agent passes): structural integrity, no orphan references, basic formatting
- Hard hidden (only strong agents pass): cross-section consistency, operational rationale, semantic updates
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
    # Try primary path first, fallback to alternative
    sop_path = ws / "fixtures" / "ops-sop" / "slave1-hardware-maintenance.md"
    if not sop_path.exists():
        sop_path = ws / "ops-sop" / "slave1-hardware-maintenance.md"
    if not sop_path.exists():
        # Try finding it anywhere under workspace
        candidates = list(ws.rglob("slave1-hardware-maintenance.md"))
        sop_path = candidates[0] if candidates else ws / "fixtures" / "ops-sop" / "slave1-hardware-maintenance.md"

    content = _read(sop_path)

    components = {k: 0.0 for k in [
        # Explicit checks (from prompt)
        "time_window_updated",
        "stop_command_loop",
        "start_command_loop",
        "keepalived_no_enable",
        "processlist_check_added",
        "slave_status_loop",
        # Hidden EASY checks (structural/formatting — most agents pass)
        "h_easy_code_block_formatting",
        "h_easy_no_orphan_single_port",
        "h_easy_section_structure_preserved",
        "h_easy_flow_condition_syntax",
        # Hidden HARD checks (deep operational understanding — only strong pass)
        "h_hard_prep01_time_consistency",
        "h_hard_exec02_flow_condition_updated",
        "h_hard_exec05_netstat_multiport",
        "h_hard_keepalived_rationale",
        "h_hard_exec03_disable_symmetry",
    ]}

    if not content:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
            "error": "SOP file not found or empty",
        }

    # === EXPLICIT CHECKS (from prompt, 55% total) ===

    # 1. Time window updated (21:00 in announcement-defaults + non-working day mention)
    ann_block = _extract_block(content, "announcement-defaults")
    has_2100 = "21:00" in ann_block
    has_nonworkday = ("非工作日" in content[:3000]) or ("non-working" in content[:3000].lower())
    components["time_window_updated"] = (0.6 if has_2100 else 0.0) + (0.4 if has_nonworkday else 0.0)

    # 2. Stop command uses reportMysql.sh loop (exec-05 section)
    exec05_section = _extract_section(content, "exec-05")
    has_report_stop = "reportMysql.sh" in exec05_section and "stopMysql.sh" in exec05_section
    has_grep_runing = "grep" in exec05_section and "runing" in exec05_section
    has_for_loop_stop = "for PORT" in exec05_section or "for port" in exec05_section.lower()
    components["stop_command_loop"] = min(1.0, (0.4 if has_report_stop else 0.0) +
                                          (0.3 if has_grep_runing else 0.0) +
                                          (0.3 if has_for_loop_stop else 0.0))

    # 3. Start command uses stopped-port loop with touch/chown (exec-08 section)
    exec08_section = _extract_section(content, "exec-08")
    has_report_start = "reportMysql.sh" in exec08_section and "startMysql.sh" in exec08_section
    has_grep_stopped = "grep" in exec08_section and "stopped" in exec08_section
    has_touch_chown = "touch" in exec08_section and "chown" in exec08_section
    has_localhost_err = "localhost.err" in exec08_section
    components["start_command_loop"] = min(1.0, (0.3 if has_report_start else 0.0) +
                                           (0.2 if has_grep_stopped else 0.0) +
                                           (0.3 if has_touch_chown else 0.0) +
                                           (0.2 if has_localhost_err else 0.0))

    # 4. Keepalived no enable (exec-11 section)
    exec11_section = _extract_section(content, "exec-11")
    has_start = "systemctl start keepalived" in exec11_section
    # The enable command must be REMOVED (not just commented or noted)
    has_enable_cmd = "systemctl enable keepalived" in exec11_section
    if has_start and not has_enable_cmd:
        components["keepalived_no_enable"] = 1.0
    elif not has_start and not has_enable_cmd:
        components["keepalived_no_enable"] = 0.2
    else:
        components["keepalived_no_enable"] = 0.0

    # 5. Processlist check added (exec-02 section)
    exec02_section = _extract_section(content, "exec-02")
    has_processlist = "SHOW processlist" in exec02_section or "show processlist" in exec02_section.lower()
    has_config_conf = "config.conf" in exec02_section
    has_process_loop = "for PORT" in exec02_section or "for port" in exec02_section.lower()
    components["processlist_check_added"] = min(1.0, (0.4 if has_processlist else 0.0) +
                                                (0.3 if has_config_conf else 0.0) +
                                                (0.3 if has_process_loop else 0.0))

    # 6. Slave status loop command (exec-09 and acc-02)
    exec09_section = _extract_section(content, "exec-09")
    acc02_section = _extract_section(content, "acc-02")
    exec09_has_loop = ("for PORT" in exec09_section or "for port" in exec09_section.lower()) and "SHOW slave status" in exec09_section
    exec09_has_config = "config.conf" in exec09_section
    acc02_has_loop = ("for PORT" in acc02_section or "for port" in acc02_section.lower()) and ("SHOW slave status" in acc02_section or "show slave status" in acc02_section.lower())
    acc02_has_config = "config.conf" in acc02_section

    score_09 = (0.5 if exec09_has_loop else 0.0) + (0.25 if exec09_has_config else 0.0)
    score_02 = (0.5 if acc02_has_loop else 0.0) + (0.25 if acc02_has_config else 0.0)
    components["slave_status_loop"] = min(1.0, (score_09 + score_02) / 1.5)

    # === HIDDEN EASY CHECKS (15% total) ===
    # These check basic quality any competent agent should achieve.

    # E1. Code block formatting: multi-line loop commands should use fenced code blocks
    # (```) rather than inline backticks because the commands are multi-line.
    fenced_score = 0.0
    for section_id in ["exec-05", "exec-08", "exec-02"]:
        section = _extract_section(content, section_id)
        has_fenced = bool(re.search(r"```(?:bash|sh|shell)?\s*\n.*?for PORT", section, re.DOTALL))
        has_indented_block = bool(re.search(r"\n    for PORT", section))
        if has_fenced or has_indented_block:
            fenced_score += 1.0
    components["h_easy_code_block_formatting"] = min(1.0, fenced_score / 3.0)

    # E2. No orphan single-port references in sections that now use loops.
    # If agent added a loop to exec-05 but left the old single-port `/usr/local/mysql/stopMysql.sh {port}`
    # line intact (not inside the loop), that's a leftover. Check exec-05 and exec-08.
    orphan_penalty = 0.0
    # exec-05: if loop exists, old standalone stopMysql.sh {port} should be gone
    if has_for_loop_stop:
        # Check for old single-port command outside the loop context
        old_stop_line = re.search(r"stopMysql\.sh\s+\{port\}", exec05_section)
        if not old_stop_line:
            orphan_penalty += 0.5
    else:
        orphan_penalty += 0.0  # no loop means explicit check already penalizes
    # exec-08: if loop exists, old standalone startMysql.sh {port} should be gone
    if "for PORT" in exec08_section.upper() or "for port" in exec08_section.lower():
        old_start_line = re.search(r"startMysql\.sh\s+\{port\}", exec08_section)
        if not old_start_line:
            orphan_penalty += 0.5
    else:
        orphan_penalty += 0.0
    components["h_easy_no_orphan_single_port"] = min(1.0, orphan_penalty)

    # E3. Section structure preserved: the document should still have all major sections
    # (preparation, execution, acceptance, 异常与回滚). A sloppy edit might delete sections.
    required_sections = ["prep-01", "exec-01", "exec-05", "exec-08", "exec-11", "acc-01", "acc-02", "异常与回滚"]
    found_sections = sum(1 for s in required_sections if s in content)
    components["h_easy_section_structure_preserved"] = min(1.0, found_sections / len(required_sections))

    # E4. Flow condition syntax: flow conditions in modified sections should follow the
    # established pattern (`如果 →` or `否则 →`). Check that new/modified sections
    # still have properly formatted flow conditions.
    flow_score = 0.0
    for sec_id in ["exec-02", "exec-05", "exec-08", "exec-11"]:
        sec = _extract_section(content, sec_id)
        if "流转条件" in sec:
            # Has flow condition header — check it follows format
            if "如果 →" in sec or "如果→" in sec or "如果 ->" in sec:
                flow_score += 0.25
    components["h_easy_flow_condition_syntax"] = min(1.0, flow_score)

    # === HIDDEN HARD CHECKS (20% total) ===
    # These require deep operational understanding and cross-section reasoning.

    # H1. prep-01 time consistency: changing announcement-defaults to 21:00 means
    # prep-01 step 4 ("确认计划操作时间在晚上 22:00 后") is now stale. A strong model
    # recognizes this cross-reference and updates it.
    prep01_section = _extract_section(content, "prep-01")
    prep01_has_2100 = "21:00" in prep01_section
    prep01_has_nonworkday_note = "非工作日" in prep01_section or "non-working" in prep01_section.lower()
    prep01_still_only_2200 = ("22:00" in prep01_section and "21:00" not in prep01_section)
    if prep01_has_2100 or prep01_has_nonworkday_note:
        components["h_hard_prep01_time_consistency"] = 1.0
    elif not prep01_still_only_2200:
        components["h_hard_prep01_time_consistency"] = 0.3
    else:
        components["h_hard_prep01_time_consistency"] = 0.0

    # H2. exec-02 flow condition updated: after adding processlist check, the flow
    # condition should reflect that "确认从库无业务连接" is now part of the gate.
    exec02_flow_match = re.search(r"流转条件.*?(?=\n####|\n---|\Z)", exec02_section, re.DOTALL)
    exec02_flow = exec02_flow_match.group(0) if exec02_flow_match else ""
    has_flow_processlist_ref = any(w in exec02_flow for w in [
        "processlist", "无业务连接", "连接确认", "无连接", "无残留连接", "确认从库无"
    ])
    components["h_hard_exec02_flow_condition_updated"] = 1.0 if has_flow_processlist_ref else 0.0

    # H3. exec-05 netstat verification for multi-port: old exec-05 checks single {port}
    # with netstat. Now that we stop ALL ports via loop, the verification should be updated
    # to not reference a single {port} — it should check all ports or use a general approach.
    exec05_still_single_port_check = "{port}" in exec05_section and "reportMysql.sh" in exec05_section
    exec05_netstat_updated = (
        ("netstat" in exec05_section and "{port}" not in exec05_section) or
        ("for PORT" in exec05_section and ("netstat" in exec05_section or "ss " in exec05_section)) or
        ("reportMysql.sh" in exec05_section and "netstat" not in exec05_section and
         ("确认" in exec05_section or "检查" in exec05_section))
    )
    if exec05_still_single_port_check:
        components["h_hard_exec05_netstat_multiport"] = 0.0
    elif exec05_netstat_updated:
        components["h_hard_exec05_netstat_multiport"] = 1.0
    else:
        components["h_hard_exec05_netstat_multiport"] = 0.3

    # H4. keepalived rationale: when removing "enable", a strong model adds a note
    # explaining WHY (avoiding auto-start on reboot could cause split-brain).
    has_rationale = any(w in exec11_section for w in [
        "不要开机启动", "避免自动启动", "不要自启", "防止脑裂",
        "不加 enable", "不执行 enable", "不需要开机自启",
        "禁止 enable", "无需 enable", "不设置开机启动",
        "not enable", "no enable", "avoid auto-start",
        "split-brain", "脑裂",
    ])
    has_asymmetry_note = ("exec-03" in exec11_section or "disable" in exec11_section) and (
        "不" in exec11_section or "仅" in exec11_section or "只" in exec11_section
    )
    components["h_hard_keepalived_rationale"] = min(1.0, (0.7 if has_rationale else 0.0) +
                                                    (0.3 if has_asymmetry_note else 0.0))

    # H5. exec-03 disable symmetry: exec-03 does "systemctl disable keepalived" and
    # exec-11 now only does "start" without "enable". A strong model recognizes the
    # intentional asymmetry and either (a) adds a comment in exec-11 referencing exec-03,
    # or (b) updates exec-03's flow condition / description to note that re-enable is
    # intentionally omitted at recovery, or (c) updates 基本信息 / notes to explain.
    exec03_section = _extract_section(content, "exec-03")
    # Check if exec-03 mentions the intentional design of not re-enabling later
    exec03_has_note = any(w in exec03_section for w in [
        "不恢复", "不再 enable", "exec-11", "恢复时不",
        "仅 start", "只 start", "不会重新 enable",
    ])
    # Or exec-11 references exec-03's disable
    exec11_refs_exec03 = "exec-03" in exec11_section
    # Or anywhere in the doc there's an explicit note about this design
    design_note = bool(re.search(
        r"(keepalived|exec-11).*?(不.*?enable|仅.*?start|只.*?start)",
        content[content.find("exec-11"):] if "exec-11" in content else "",
        re.DOTALL
    ))
    components["h_hard_exec03_disable_symmetry"] = min(1.0,
        (0.5 if exec03_has_note else 0.0) +
        (0.3 if exec11_refs_exec03 else 0.0) +
        (0.2 if design_note else 0.0)
    )

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        # Explicit checks (55% total)
        "time_window_updated": 0.09,
        "stop_command_loop": 0.10,
        "start_command_loop": 0.10,
        "keepalived_no_enable": 0.09,
        "processlist_check_added": 0.10,
        "slave_status_loop": 0.07,
        # Hidden EASY checks (15% total) — most agents should pass these
        "h_easy_code_block_formatting": 0.04,
        "h_easy_no_orphan_single_port": 0.04,
        "h_easy_section_structure_preserved": 0.04,
        "h_easy_flow_condition_syntax": 0.03,
        # Hidden HARD checks (30% total) — only strong agents pass
        "h_hard_prep01_time_consistency": 0.07,
        "h_hard_exec02_flow_condition_updated": 0.07,
        "h_hard_exec05_netstat_multiport": 0.06,
        "h_hard_keepalived_rationale": 0.05,
        "h_hard_exec03_disable_symmetry": 0.05,
    }


def _extract_block(content: str, block_name: str) -> str:
    """Extract content between ```block_name and ``` markers."""
    pattern = rf"```{re.escape(block_name)}\s*\n(.*?)```"
    m = re.search(pattern, content, re.DOTALL)
    return m.group(1) if m else ""


def _extract_section(content: str, section_id: str) -> str:
    """Extract section content from a heading containing section_id to the next same-level heading."""
    lines = content.split("\n")
    in_section = False
    section_lines = []
    section_level = 0

    for line in lines:
        if section_id in line and line.strip().startswith("#"):
            in_section = True
            section_level = len(line) - len(line.lstrip("#"))
            section_lines.append(line)
            continue

        if in_section:
            # Check if we hit next section at same or higher level
            if line.strip().startswith("#"):
                current_level = len(line.strip()) - len(line.strip().lstrip("#"))
                if current_level <= section_level and section_lines:
                    break
            section_lines.append(line)

    return "\n".join(section_lines)


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
