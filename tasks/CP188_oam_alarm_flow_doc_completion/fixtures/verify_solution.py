"""Hidden verifier for CP188 - OAM Alarm Flow Documentation Completion."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_doc_file(ws: Path) -> Path | None:
    """Find the alarm processing flow documentation file."""
    # In sandbox: /workspace/fixtures/fm-adaptor-oam/doc/alarm_processing_flow.md
    candidates = [
        ws / "fixtures" / "fm-adaptor-oam" / "doc" / "alarm_processing_flow.md",
        ws / "fm-adaptor-oam" / "doc" / "alarm_processing_flow.md",
    ]
    for p in candidates:
        if p.exists():
            return p
    # Fallback: search recursively
    for p in ws.rglob("alarm_processing_flow.md"):
        return p
    return None


def _extract_section(content: str, heading_pattern: str, next_heading_level: int = 2) -> str:
    """Extract content between a heading and the next same-or-higher-level heading."""
    m = re.search(heading_pattern, content, re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    # Find next heading of same or higher level
    pattern = r'^#{1,' + str(next_heading_level) + r'}\s'
    rest = content[start:]
    next_h = re.search(pattern, rest, re.MULTILINE)
    if next_h:
        return rest[:next_h.start()]
    return rest


def _count_substantial_lines(text: str) -> int:
    """Count non-empty, non-comment, non-TODO lines."""
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<!--") or stripped.startswith("-->"):
            continue
        if "TODO" in stripped:
            continue
        count += 1
    return count


def _has_ascii_diagram(text: str) -> bool:
    """Check if text contains an ASCII sequence diagram (code block with arrows)."""
    code_blocks = re.findall(r'```[^`]*```', text, re.DOTALL)
    for block in code_blocks:
        # Must have at least arrow-like patterns
        if re.search(r'[-─]{3,}|[>►→←<]|-->', block) and len(block) > 100:
            return True
    # Also check for non-fenced diagrams with box-drawing chars
    if re.search(r'[│|]\s*$', text, re.MULTILINE) and re.search(r'[-─]{3,}>', text):
        return True
    return False


def grade_workspace(ws: Path) -> dict:
    doc_file = _find_doc_file(ws)
    if not doc_file:
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "Documentation file not found",
        }

    content = _read(doc_file)

    components = {k: 0.0 for k in [
        "section_3_3_delegate_flow",
        "section_3_4_oam_ordering",
        "section_4_1_normal_scenario",
        "section_4_2_outoforder_scenario",
        "section_5_complete_structures",
        "section_5_2_decision_points",
        "format_consistency",
        "technical_precision",
        "cross_reference_accuracy",
        "implementation_detail_depth",
        "algorithmic_precision",
        "inter_section_coherence",
    ]}

    # --- Dimension 1: Section 3.3 AlarmDelegate Core Processing (0.15) ---
    s3_3_text = _extract_section(content, r'^###\s*3\.3', next_heading_level=3)
    s3_3_lower = s3_3_text.lower()
    s3_3_lines = _count_substantial_lines(s3_3_text)
    s3_3_score = 0.0

    if s3_3_lines >= 10:
        s3_3_score += 0.1  # Section has real content

        # Must document the 5-step processing pipeline
        steps_found = 0
        step_indicators = [
            any(kw in s3_3_lower for kw in ["validate", "completeness", "non-null", "nename", "alarmid"]),
            any(kw in s3_3_lower for kw in ["enrich", "metadata", "netype", "location", "rack"]),
            any(kw in s3_3_lower for kw in ["suppress", "maintenance", "dedup", "duplicate", "filter"]),
            any(kw in s3_3_lower for kw in ["severity", "transform", "mapping", "policy"]),
            any(kw in s3_3_lower for kw in ["parseandsendmsg", "kafka", "send2kafka", "mqmessage"]),
        ]
        steps_found = sum(step_indicators)
        s3_3_score += steps_found * 0.10  # Up to 0.50

        # Must have a sequence diagram or flow representation
        if _has_ascii_diagram(s3_3_text):
            s3_3_score += 0.25

    components["section_3_3_delegate_flow"] = min(1.0, s3_3_score)

    # --- Dimension 2: Section 3.4 OAM Trap Ordering (0.18) ---
    s3_4_text = _extract_section(content, r'^###\s*3\.4', next_heading_level=3)
    s3_4_lower = s3_4_text.lower()
    s3_4_lines = _count_substantial_lines(s3_4_text)
    s3_4_score = 0.0

    if s3_4_lines >= 15:
        s3_4_score += 0.08

        # Must explain the ordering algorithm with specific terms
        algo_terms = ["expectedid", "currenttrapid", "maxjumpid", "jumpcount", "oamtrapentity"]
        algo_found = sum(1 for t in algo_terms if t in s3_4_lower)
        s3_4_score += min(algo_found * 0.07, 0.28)

        # Must document the 3 cases
        cases_found = 0
        if re.search(r'==\s*expected|normal\s*order|currenttrapid\s*==', s3_4_lower):
            cases_found += 1
        if re.search(r'>\s*expected|gap\s*detect|out.of.order|currenttrapid\s*>', s3_4_lower):
            cases_found += 1
        if re.search(r'<\s*expected|late\s*arrival|currenttrapid\s*<|ne\s*restart', s3_4_lower):
            cases_found += 1
        s3_4_score += cases_found * 0.10

        # Must mention delay queue for clear alarms
        if "delay" in s3_4_lower and "clear" in s3_4_lower:
            s3_4_score += 0.08

        # Should have a diagram
        if _has_ascii_diagram(s3_4_text):
            s3_4_score += 0.12

    components["section_3_4_oam_ordering"] = min(1.0, s3_4_score)

    # --- Dimension 3: Section 4.1 Normal Scenario (0.12) ---
    s4_1_text = _extract_section(content, r'^###\s*4\.1', next_heading_level=3)
    s4_1_lower = s4_1_text.lower()
    s4_1_lines = _count_substantial_lines(s4_1_text)
    s4_1_score = 0.0

    if s4_1_lines >= 10:
        s4_1_score += 0.15

        if _has_ascii_diagram(s4_1_text):
            s4_1_score += 0.30
            actors = ["oam", "trap", "alarm", "delegate", "kafka", "service"]
            actors_in = sum(1 for a in actors if a in s4_1_lower)
            s4_1_score += min(actors_in * 0.07, 0.28)

        if "kafka" in s4_1_lower or "send2kafka" in s4_1_lower:
            s4_1_score += 0.12

    components["section_4_1_normal_scenario"] = min(1.0, s4_1_score)

    # --- Dimension 4: Section 4.2 Out-of-Order Scenario (0.15) ---
    s4_2_text = _extract_section(content, r'^###\s*4\.2', next_heading_level=3)
    s4_2_lower = s4_2_text.lower()
    s4_2_lines = _count_substantial_lines(s4_2_text)
    s4_2_score = 0.0

    if s4_2_lines >= 12:
        s4_2_score += 0.10

        if "expectedid" in s4_2_lower or "expected" in s4_2_lower:
            s4_2_score += 0.12

        if "delay" in s4_2_lower and "clear" in s4_2_lower:
            s4_2_score += 0.12

        has_ids = bool(re.search(r'(?:trap|id)\s*(?:=|:)?\s*\d+', s4_2_lower))
        if has_ids:
            s4_2_score += 0.12

        if _has_ascii_diagram(s4_2_text):
            s4_2_score += 0.20

        if "raise" in s4_2_lower or "raised" in s4_2_lower:
            s4_2_score += 0.12

    components["section_4_2_outoforder_scenario"] = min(1.0, s4_2_score)

    # --- Dimension 5: Section 5 Complete Data Structures (0.08) ---
    s5_text = _extract_section(content, r'^###\s*5\.1', next_heading_level=3)
    s5_lower = s5_text.lower()
    s5_score = 0.0

    s5_clean = re.sub(r'<!--.*?-->', '', s5_text, flags=re.DOTALL).lower()
    table_lines = [l for l in s5_clean.splitlines() if "|" in l]
    table_text = "\n".join(table_lines)

    if "delayclearalarm" in table_text or "delay_clear_alarm" in table_text or "delayclear" in table_text:
        s5_score += 0.30
        if any(kw in table_text for kw in ["expiretime", "alarmdata", "workid", "expire"]):
            s5_score += 0.15

    if "trapevent" in table_text or "trap event" in table_text:
        s5_score += 0.25

    data_rows = [l for l in table_lines if "|" in l and "---" not in l and "Key Fields" not in l and "Data Structure" not in l]
    if len(data_rows) >= 4:
        s5_score += 0.15

    components["section_5_complete_structures"] = min(1.0, s5_score)

    # --- Dimension 6: Section 5.2 Decision Points (0.05) ---
    s5_2_text = _extract_section(content, r'^###\s*5\.2', next_heading_level=3)
    s5_2_lower = s5_2_text.lower()
    s5_2_lines = _count_substantial_lines(s5_2_text)
    s5_2_score = 0.0

    if s5_2_lines >= 5:
        s5_2_score += 0.25
        if "notification" in s5_2_lower and "event" in s5_2_lower:
            s5_2_score += 0.25
        if "oam" in s5_2_lower and ("non-oam" in s5_2_lower or "regular" in s5_2_lower or "non" in s5_2_lower):
            s5_2_score += 0.25
        if "order" in s5_2_lower or "expected" in s5_2_lower:
            s5_2_score += 0.15

    components["section_5_2_decision_points"] = min(1.0, s5_2_score)

    # --- Dimension 7: Format Consistency (0.03) ---
    fmt_score = 0.0
    all_code_blocks = re.findall(r'```[^`]*```', content, re.DOTALL)
    diagram_blocks = sum(1 for b in all_code_blocks if re.search(r'[-─]{3,}|[>►→]|-->', b))
    non_fenced = len(re.findall(r'^\s*[│|].*[-─]{2,}', content, re.MULTILINE))
    total_diagrams = diagram_blocks + (1 if non_fenced > 5 else 0)

    if total_diagrams >= 7:
        fmt_score += 0.35
    elif total_diagrams >= 5:
        fmt_score += 0.15

    todo_remaining = content.count("TODO")
    if todo_remaining == 0:
        fmt_score += 0.35
    elif todo_remaining <= 2:
        fmt_score += 0.15

    total_lines = len(content.splitlines())
    if total_lines >= 350:
        fmt_score += 0.20
    elif total_lines >= 250:
        fmt_score += 0.10

    components["format_consistency"] = min(1.0, fmt_score)

    # --- Dimension 8: Technical Precision (HIDDEN, 0.13) ---
    # Requires exact constants, method signatures, and implementation details
    # that only come from careful reading of the source code
    tp_score = 0.0

    content_lower = content.lower()

    # 8a: Must mention exact constants from source code
    # MAX_JUMP_THRESHOLD = 100 (FmAlarmService.java line 31)
    if re.search(r'max.?jump.?threshold.*?100|100.*?max.?jump|threshold.*100', content_lower):
        tp_score += 0.10
    # CLEAR_DELAY_MS = 30000 or 30s (FmAlarmService.java line 34)
    if re.search(r'30000|30\s*s(?:ec|econds?)?|clear.?delay.?ms', content_lower):
        tp_score += 0.10
    # 60s/60000ms dedup window (AlarmDelegate.java isSuppressed)
    if re.search(r'60\s*s(?:ec|econds?)?|60000|dedup.*?window|duplicate.*?60', content_lower):
        tp_score += 0.10

    # 8b: Must document message type mapping with exact type names
    msg_types_found = 0
    for mt in ["new_alarm", "clear_alarm", "change_alarm"]:
        if mt in content_lower:
            msg_types_found += 1
    tp_score += min(msg_types_found * 0.06, 0.18)

    # 8c: Must mention exact Kafka topic naming convention
    # fm-notification and fm-event-{meId}
    if "fm-notification" in content_lower:
        tp_score += 0.08
    if re.search(r'fm-event-.*?meid|fm-event-\{|fm-event.*per.*ne', content_lower):
        tp_score += 0.08

    # 8d: Must document the isNotification routing logic for topic selection
    if re.search(r'isnotification|is_notification|isnotification.*topic|topic.*notification', content_lower):
        tp_score += 0.08

    # 8e: Must document workId composite key pattern: neName + "_" + neType
    if re.search(r'workid.*nename.*netype|nename.*_.*netype|workid.*composite|workid.*=.*\+', content_lower):
        tp_score += 0.08

    # 8f: Must document the suppression rules with specifics (3 rules)
    suppression_details = 0
    if re.search(r'maintenance.*window|maintenancewindowmanager', content_lower):
        suppression_details += 1
    if re.search(r'dedup|alarmdedupache|duplicate.*filter', content_lower):
        suppression_details += 1
    if re.search(r'suppress.*list|global.*suppress|alarmsuppresslist', content_lower):
        suppression_details += 1
    if suppression_details >= 3:
        tp_score += 0.10
    elif suppression_details >= 2:
        tp_score += 0.05

    # 8g: Must mention severity mapping table specifics
    if re.search(r'critical.*critical|major.*major|minor.*warning|warning.*info|severity.*policy.*xml|severitypolicymanager', content_lower):
        tp_score += 0.10

    components["technical_precision"] = min(1.0, tp_score)

    # --- Dimension 9: Cross-Reference Accuracy (HIDDEN, 0.10) ---
    # Checks that the documentation is internally consistent and references
    # specific implementation details correctly across sections
    cr_score = 0.0

    # 9a: Section 4.2 must reference the exact delay mechanism timing (30s timeout)
    s4_2_has_delay_timing = bool(re.search(
        r'30\s*s(?:ec|onds?)?|30000\s*ms|clear.?delay', s4_2_lower))
    if s4_2_has_delay_timing:
        cr_score += 0.15

    # 9b: Section 4.2 must explain what happens AFTER delay expires
    # (clear alarm processed regardless of whether raise arrived)
    if re.search(r'expir|timeout|process.*regardless|still.*process|after.*delay', s4_2_lower):
        cr_score += 0.15

    # 9c: Section 3.3 must mention FmException throwing on validation failure
    if re.search(r'fmexception|fm.?exception|throw.*exception|validation.*fail', s3_3_lower):
        cr_score += 0.12

    # 9d: Section 3.3 must document null-check early return (null data -> skip)
    if re.search(r'null.*skip|null.*return|data\s*==\s*null|null.*check.*early', s3_3_lower):
        cr_score += 0.12

    # 9e: Section 3.4 must mention the ConcurrentHashMap / per-NE state management
    if re.search(r'concurrenthashmap|per.?ne.*state|oamtrapmap|thread.?safe|concurrent', s3_4_lower):
        cr_score += 0.12

    # 9f: Section 3.4 must mention reset() behavior on NE restart detection
    if re.search(r'reset.*state|reset\(\)|restart.*reset|reset.*expected', s3_4_lower):
        cr_score += 0.12

    # 9g: Documentation must show TABLE_ALARMRAISED/CLEARED/CHANGED constants
    table_consts = 0
    for c in ["table_alarmraised", "alarmraised", "table_alarmcleared", "alarmcleared", "table_alarmchanged", "alarmchanged"]:
        if c in content_lower:
            table_consts += 1
    # Need at least 2 of the 3 alarm type constants mentioned
    if table_consts >= 4:
        cr_score += 0.12
    elif table_consts >= 2:
        cr_score += 0.06

    # 9h: Section 4.1 must show the 5-step pipeline in the scenario flow
    # (not just listing steps, but showing them as part of the scenario)
    s4_1_pipeline = 0
    for kw in ["validate", "enrich", "suppress", "severity", "send"]:
        if kw in s4_1_lower:
            s4_1_pipeline += 1
    if s4_1_pipeline >= 4:
        cr_score += 0.10
    elif s4_1_pipeline >= 3:
        cr_score += 0.05

    components["cross_reference_accuracy"] = min(1.0, cr_score)

    # --- Dimension 10: Implementation Detail Depth (HIDDEN, 0.10) ---
    # Requires documenting exact Java implementation patterns that only come
    # from very careful reading of the source — method signatures, patterns,
    # data structure usage, and Java-specific constructs.
    impl_score = 0.0

    # 10a: Must document computeIfAbsent pattern for per-NE state creation
    # (FmAlarmService.java line 88: oamTrapMap.computeIfAbsent(workId, ...))
    if re.search(r'computeifabsent|compute.?if.?absent', content_lower):
        impl_score += 0.12

    # 10b: Must mention DelayQueue<DelayClearAlarm> as the queue implementation
    # (not just "delay queue" generically but the java.util.concurrent.DelayQueue)
    if re.search(r'delayqueue|java\.util\.concurrent.*delay', content_lower):
        impl_score += 0.12

    # 10c: Must document that DelayClearAlarm implements Delayed interface
    if re.search(r'implements\s+delayed|delayed\s+interface|getdelay.*timeunit', content_lower):
        impl_score += 0.10

    # 10d: Must mention Integer.parseInt for sendNotificationId -> currentTrapId
    if re.search(r'integer\.parseint|parseint.*sendnotificationid|sendnotificationid.*parseint', content_lower):
        impl_score += 0.10

    # 10e: Must document the isOamTrapAlarm() detection logic:
    # sendNotificationId != null AND neType.startsWith("OAM-")
    if re.search(r'startswith.*oam|oam-.*prefix|netype.*oam-|oam-.*netype', content_lower):
        impl_score += 0.12

    # 10f: Must mention originalExpectedId field in DelayClearAlarm
    if re.search(r'originalexpectedid|original.?expected.?id', content_lower):
        impl_score += 0.10

    # 10g: Must document the exact update sequence in gap case:
    # setExpectedId -> setMaxJumpId -> incrementJumpCount (3-step state mutation)
    state_mutation_steps = 0
    if "setexpectedid" in content_lower or re.search(r'set.*expectedid|expectedid\s*=\s*current', content_lower):
        state_mutation_steps += 1
    if "setmaxjumpid" in content_lower or re.search(r'set.*maxjumpid|maxjumpid\s*=.*max', content_lower):
        state_mutation_steps += 1
    if "incrementjumpcount" in content_lower or re.search(r'increment.*jump|jumpcount\s*\+\+', content_lower):
        state_mutation_steps += 1
    if state_mutation_steps >= 3:
        impl_score += 0.15
    elif state_mutation_steps >= 2:
        impl_score += 0.08

    # 10h: Must document lastTrapTime field in OamTrapEntity
    if re.search(r'lasttraptime|last.?trap.?time|timestamp.*last.*trap', content_lower):
        impl_score += 0.09

    # 10i: Must mention MqMessageBuilder.build() for message construction
    if re.search(r'mqmessagebuilder|mqmessagebuilder\.build|mqmessage.*build', content_lower):
        impl_score += 0.10

    components["implementation_detail_depth"] = min(1.0, impl_score)

    # --- Dimension 11: Algorithmic Precision (HIDDEN, 0.08) ---
    # Checks that the ordering algorithm is described with correct conditional logic,
    # not just a vague description but the exact branching and edge cases.
    algo_score = 0.0

    # 11a: Must document that in gap case (currentTrapId > expectedId),
    # clear alarms go to delay queue ONLY IF currentTrapId <= maxJumpId
    if re.search(r'clear.*<=\s*maxjump|currenttrapid\s*<=\s*maxjump|maxjumpid.*condition.*clear', s3_4_lower):
        algo_score += 0.20

    # 11b: Must document that in late-arrival case (currentTrapId < expectedId),
    # alarm is ALWAYS processed regardless of gap size (delegateAlarm called either way)
    if re.search(r'process.*regardless|always.*process|delegate.*either|late.*still.*process', s3_4_lower):
        algo_score += 0.15

    # 11c: Must document the initial expectedId value = 1
    # (OamTrapEntity constructor: new OamTrapEntity(workId, 1))
    if re.search(r'initial.*expected.*1|expectedid.*start.*1|initial.*1|begin.*from.*1', s3_4_lower):
        algo_score += 0.12

    # 11d: Must mention that gap detection uses Math.max for maxJumpId update
    if re.search(r'math\.max|max\(.*maxjumpid.*currenttrapid|max.*between.*maxjump', s3_4_lower):
        algo_score += 0.12

    # 11e: Section 4.2 must show specific trap ID numbers in the scenario
    # (e.g., expected=5, got=8, showing the gap scenario with concrete values)
    s4_2_concrete_ids = re.findall(r'(?:trap|id|expected|current)\s*(?:=|:)?\s*\d+', s4_2_lower)
    if len(s4_2_concrete_ids) >= 4:
        algo_score += 0.18
    elif len(s4_2_concrete_ids) >= 2:
        algo_score += 0.08

    # 11f: Must document that after NE restart detection (gap >= 100),
    # reset() is called which zeroes maxJumpId and jumpCount
    if re.search(r'reset.*maxjumpid.*0|reset.*zero|reset.*clear.*jump|jumpcount.*0.*maxjumpid.*0', s3_4_lower):
        algo_score += 0.13

    # 11g: Must document expireTimeMs = currentTimeMillis + CLEAR_DELAY_MS calculation
    if re.search(r'currenttimemillis|system\.currenttime|expire.*=.*\+.*30|now\s*\+\s*30', content_lower):
        algo_score += 0.10

    components["algorithmic_precision"] = min(1.0, algo_score)

    # --- Dimension 12: Inter-Section Coherence (HIDDEN, 0.07) ---
    # Checks that scenario sections (4.x) use exact method/class names from
    # the detail sections (3.x), proving the documentation is internally coherent.
    coh_score = 0.0

    # 12a: Section 4.1 must use exact method name "delegateAlarmData" (not just "delegate")
    if "delegatealarmdata" in s4_1_lower:
        coh_score += 0.18

    # 12b: Section 4.1 must mention "enrichNeMetadata" by name (not just "enrich")
    if "enrichnemetadata" in s4_1_lower or "enrichne" in s4_1_lower:
        coh_score += 0.15

    # 12c: Section 4.2 must use "addToDelayQueue" or exact queue method name
    if "addtodelayqueue" in s4_2_lower or "addtodelayqueue" in s4_2_lower.replace(" ", ""):
        coh_score += 0.18

    # 12d: Section 4.2 must reference "processOamTrapAlarm" as the entry method
    if "processoamtrapalarm" in s4_2_lower:
        coh_score += 0.15

    # 12e: Section 4.1 must show "isSuppressed" check in the flow
    if "issuppressed" in s4_1_lower or "is_suppressed" in s4_1_lower:
        coh_score += 0.15

    # 12f: Section 4.1 must show "transformSeverity" step by name
    if "transformseverity" in s4_1_lower or "transform_severity" in s4_1_lower:
        coh_score += 0.12

    # 12g: Consistency: section 5.2 must reference the 3-way routing from alarmProcess()
    s5_2_routing = 0
    if "processnotification" in s5_2_lower:
        s5_2_routing += 1
    if "processoamtrapalarm" in s5_2_lower or "isoamtrapalarm" in s5_2_lower:
        s5_2_routing += 1
    if "processregularalarm" in s5_2_lower:
        s5_2_routing += 1
    if s5_2_routing >= 2:
        coh_score += 0.12
    elif s5_2_routing >= 1:
        coh_score += 0.05

    components["inter_section_coherence"] = min(1.0, coh_score)

    # Weighted overall score - rebalanced to make high scores harder
    # Hidden dimensions carry significant weight (0.14 + 0.10 + 0.10 + 0.08 + 0.07 = 0.49 hidden)
    weights = {
        "section_3_3_delegate_flow": 0.10,
        "section_3_4_oam_ordering": 0.12,
        "section_4_1_normal_scenario": 0.08,
        "section_4_2_outoforder_scenario": 0.10,
        "section_5_complete_structures": 0.05,
        "section_5_2_decision_points": 0.03,
        "format_consistency": 0.03,
        "technical_precision": 0.14,
        "cross_reference_accuracy": 0.10,
        "implementation_detail_depth": 0.10,
        "algorithmic_precision": 0.08,
        "inter_section_coherence": 0.07,
    }
    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
