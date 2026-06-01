"""Hidden verifier for CP115 — Agent Command Dispatcher Config."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _try_yaml_parse(content: str) -> dict | None:
    """Try to parse YAML content."""
    try:
        import yaml
        return yaml.safe_load(content)
    except Exception:
        return None


def _try_yaml_parse_fallback(content: str) -> dict | None:
    """Fallback YAML parsing without PyYAML."""
    # Check basic structural validity
    if "dispatch_rules:" not in content:
        return None
    return {"_fallback": True}


def grade_workspace(ws: Path) -> dict:
    # Check both possible output locations
    dispatch_dir = ws / "agent-dispatch"
    if not dispatch_dir.exists():
        dispatch_dir = ws / "fixtures" / "agent-dispatch"
    if not dispatch_dir.exists():
        return {"overall_score": 0.0, "components": {}, "error": "agent-dispatch directory not found"}

    components = {k: 0.0 for k in [
        "yaml_syntax_fixed",
        "command_parsing_fixed",
        "cron_expressions_valid",
        "denied_status_handled",
        "daily_check_aggregation",
        "handler_importable",
    ]}

    # === 1. YAML syntax fixed ===
    config_file = dispatch_dir / "dispatch_config.yaml"
    config_content = _read(config_file)
    config = _try_yaml_parse(config_content)
    if config is None:
        config = _try_yaml_parse_fallback(config_content)

    if config and not isinstance(config, dict):
        config = None

    if config and config.get("_fallback") is None:
        # Successfully parsed as valid YAML
        components["yaml_syntax_fixed"] = 0.5
        # Check the evening report rule specifically - the unclosed quote was the main bug
        rules = config.get("dispatch_rules", [])
        evening_found = False
        for rule in rules:
            handler = rule.get("handler", "")
            if "evening" in handler:
                evening_found = True
                break
        if evening_found:
            components["yaml_syntax_fixed"] = 1.0
    elif config_content:
        # Check if the obvious syntax errors are fixed
        # Original bug: unclosed quote on evening handler line
        if 'handler: "handlers.evening_report"' in config_content or "handler: handlers.evening_report" in config_content:
            # Quote is properly closed now
            if '"0 20 * *"' not in config_content:
                # The bad cron is also fixed
                components["yaml_syntax_fixed"] = 0.7

    # === 2. Command parsing fixed ===
    dispatcher_file = dispatch_dir / "dispatcher.py"
    dispatcher_content = _read(dispatcher_file)

    if dispatcher_content:
        # The bug: regex was r"RUN\s+REPORT_TYPE(.+)" missing the '=' sign
        # Fixed should have r"RUN\s+REPORT_TYPE=(.+)" or similar with '='
        # Look for the '=' inside a regex pattern matching REPORT_TYPE
        has_equals_in_pattern = bool(re.search(r'REPORT_TYPE=\(', dispatcher_content)) or \
                                bool(re.search(r"REPORT_TYPE=\(", dispatcher_content)) or \
                                bool(re.search(r'REPORT_TYPE=\\s', dispatcher_content)) or \
                                bool(re.search(r"REPORT_TYPE=['\"]", dispatcher_content) is None and
                                     re.search(r'REPORT_TYPE=\(\.', dispatcher_content))
        # More direct: check if there's a regex with REPORT_TYPE= followed by capture group
        has_equals_capture = bool(re.search(r'REPORT_TYPE=\(\.\+\)', dispatcher_content)) or \
                             bool(re.search(r'REPORT_TYPE=\([^)]+\)', dispatcher_content))
        # Also check for split-based parsing: split on '='
        has_split_parse = bool(re.search(r"split\(['\"]=['\"]", dispatcher_content))
        has_proper_extraction = "group(1)" in dispatcher_content

        if (has_equals_capture or has_equals_in_pattern) and has_proper_extraction:
            components["command_parsing_fixed"] = 1.0
        elif has_equals_capture or has_equals_in_pattern or has_split_parse:
            components["command_parsing_fixed"] = 0.7
        elif "REPORT_TYPE" in dispatcher_content:
            # At least the pattern is there
            # Check if parse_command specifically handles '=' extraction
            parse_fn_match = re.search(r'def parse_command.*?(?=\n    def |\nclass |\Z)', dispatcher_content, re.DOTALL)
            if parse_fn_match:
                parse_fn = parse_fn_match.group(0)
                # Look for explicit '=' stripping/splitting near the match extraction
                if ("lstrip('=')" in parse_fn or 'lstrip("=")' in parse_fn
                        or "split('=')" in parse_fn or 'split("=")' in parse_fn
                        or "strip('=')" in parse_fn or 'strip("=")' in parse_fn
                        or "[1:]" in parse_fn):
                    components["command_parsing_fixed"] = 0.5

    # === 3. Cron expressions valid (all 5 fields) ===
    if config and config.get("_fallback") is None:
        rules = config.get("dispatch_rules", [])
        total_crons = 0
        valid_crons = 0
        for rule in rules:
            schedule = rule.get("schedule", "")
            if schedule:
                total_crons += 1
                parts = schedule.split()
                if len(parts) == 5:
                    valid_crons += 1
        if total_crons > 0:
            components["cron_expressions_valid"] = valid_crons / total_crons
    else:
        # Fallback: check raw content for the specific bug (4-field cron)
        if config_content:
            # Original bug: "0 20 * *" (4 fields)
            four_field_crons = re.findall(r'schedule:\s*"(\d+\s+\d+\s+\*\s+\*)"', config_content)
            if not four_field_crons:
                # No 4-field crons found = likely fixed
                five_field_crons = re.findall(r'schedule:\s*"([^"]+)"', config_content)
                all_valid = all(len(c.split()) == 5 for c in five_field_crons if c.strip())
                components["cron_expressions_valid"] = 1.0 if all_valid and five_field_crons else 0.3

    # === 4. Denied status handled ===
    if config and config.get("_fallback") is None:
        exec_policy = config.get("exec_policy", {})
        valid_statuses = exec_policy.get("valid_statuses", [])
        if "denied" in valid_statuses:
            components["denied_status_handled"] = 0.5
    elif config_content and "denied" in config_content:
        components["denied_status_handled"] = 0.3

    # Check dispatcher.py also handles denied status
    if dispatcher_content:
        has_denied_handling = (
            "denied" in dispatcher_content.lower()
            and ("status" in dispatcher_content.lower())
        )
        if has_denied_handling:
            components["denied_status_handled"] = min(1.0, components["denied_status_handled"] + 0.5)

    # === 5. Daily check aggregation ===
    if dispatcher_content:
        # The bug: generate_daily_check counted all as successful
        # Fixed version should count by actual status
        has_status_counting = False
        # Look for status-aware counting patterns
        status_patterns = [
            r'status.*==.*"success"',
            r'status.*==.*"failed"',
            r'status.*==.*"denied"',
            r"e\[.status.\]",
            r"entry\[.status.\]",
            r"\.get\(.status.\)",
        ]
        matches = sum(1 for p in status_patterns if re.search(p, dispatcher_content))
        if matches >= 2:
            has_status_counting = True

        # Check output includes denied count
        has_denied_count = "denied" in dispatcher_content and (
            "denied_count" in dispatcher_content
            or '"denied"' in dispatcher_content
            or "'denied'" in dispatcher_content
        )

        if has_status_counting and has_denied_count:
            components["daily_check_aggregation"] = 1.0
        elif has_status_counting:
            components["daily_check_aggregation"] = 0.7
        elif has_denied_count:
            components["daily_check_aggregation"] = 0.4

    # === 6. Handlers importable ===
    handlers_dir = dispatch_dir / "handlers"
    if handlers_dir.exists():
        required_handlers = ["flash_report.py", "morning_report.py", "evening_report.py", "daily_check.py"]
        found = 0
        has_handle_method = 0
        for h in required_handlers:
            hf = handlers_dir / h
            if hf.exists():
                found += 1
                hc = _read(hf)
                if "def handle(" in hc or "def generate_" in hc:
                    has_handle_method += 1

        if found == len(required_handlers) and has_handle_method >= 3:
            components["handler_importable"] = 1.0
        elif found >= 3:
            components["handler_importable"] = 0.7
        elif found >= 1:
            components["handler_importable"] = 0.3

    # Check if a noon/午报 handler was added (bonus for noticing the missing mapping)
    noon_handler = handlers_dir / "noon_report.py" if handlers_dir.exists() else None
    if noon_handler and noon_handler.exists():
        # Bonus: agent noticed that 午报 type has no handler
        components["handler_importable"] = min(1.0, components["handler_importable"] + 0.1)
    # Also check if config has a 午报 rule now
    if config_content and "午报" in config_content:
        components["handler_importable"] = min(1.0, components["handler_importable"] + 0.1)

    weights = {
        "yaml_syntax_fixed": 0.25,
        "command_parsing_fixed": 0.25,
        "cron_expressions_valid": 0.15,
        "denied_status_handled": 0.15,
        "daily_check_aggregation": 0.10,
        "handler_importable": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    # Try primary location first
    if (ws / "agent-dispatch").exists():
        result = grade_workspace(ws)
    elif (ws / "fixtures" / "agent-dispatch").exists():
        result = grade_workspace(ws)
    else:
        result = {"overall_score": 0.0, "components": {}, "error": "No agent-dispatch directory found"}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
