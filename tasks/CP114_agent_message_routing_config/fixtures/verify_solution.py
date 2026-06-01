"""Hidden verifier for CP114 — Agent Message Routing Config Migration."""
from __future__ import annotations

import json
import os
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def _safe_load_yaml(path: Path) -> dict | None:
    """Load YAML file, trying PyYAML first then fallback to basic parsing."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    if yaml:
        try:
            return yaml.safe_load(text)
        except Exception:
            return None
    # Minimal fallback: just return text for keyword checks
    return {"_raw": text}


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    hub_dir = ws / "agent-hub"
    # Fallback: check if files are directly in ws
    if not hub_dir.exists():
        hub_dir = ws

    components = {k: 0.0 for k in [
        "routing_rules_migrated",
        "poc_json_removed",
        "gitlab_source_added",
        "gitlab_routing_rules",
        "poc_frontend_agent_added",
        "poc_frontend_agent_md",
        "lark_agent_updated",
        "session_management_added",
        # Hidden checks — only strong agents satisfy these
        "existing_config_preserved",
        "rule_condition_fidelity",
        "priority_ordering_coherent",
        "gitlab_rule_source_binding",
        "rule_description_preserved",
    ]}

    hub_config_path = hub_dir / "hub_config.yaml"
    hub_text = _read(hub_config_path)
    hub_data = _safe_load_yaml(hub_config_path)

    # --- 1. Routing rules migrated ---
    if hub_data and not isinstance(hub_data, type(None)):
        if isinstance(hub_data, dict) and "_raw" not in hub_data:
            routing = hub_data.get("routing", {})
            rules = routing.get("rules", [])
            if isinstance(rules, list) and len(rules) >= 5:
                # Check original 5 rules are present
                rule_names = {r.get("name", "") for r in rules if isinstance(r, dict)}
                expected_original = {
                    "private-chat-to-lark",
                    "group-mention-to-lark",
                    "doc-comment-to-obsidian",
                    "meego-issue-to-rd",
                    "daily-sync-to-lark",
                }
                matched = expected_original & rule_names
                components["routing_rules_migrated"] = min(1.0, len(matched) / 5.0)

                # Check conflict_resolution and unmatched_behavior
                if routing.get("conflict_resolution") and routing.get("unmatched_behavior"):
                    components["routing_rules_migrated"] = min(1.0, components["routing_rules_migrated"] + 0.1)
            elif len(rules) >= 3:
                components["routing_rules_migrated"] = 0.4
        else:
            # Fallback to text-based check
            raw = hub_data.get("_raw", "") if isinstance(hub_data, dict) else hub_text
            original_names = ["private-chat-to-lark", "group-mention-to-lark",
                             "doc-comment-to-obsidian", "meego-issue-to-rd", "daily-sync-to-lark"]
            found = sum(1 for name in original_names if name in raw)
            components["routing_rules_migrated"] = min(1.0, found / 5.0)
            if "conflict_resolution" in raw and "unmatched_behavior" in raw:
                components["routing_rules_migrated"] = min(1.0, components["routing_rules_migrated"] + 0.1)

    # --- 2. POC JSON removed ---
    poc_json_path = hub_dir / "routing_rules_poc.json"
    if not poc_json_path.exists():
        components["poc_json_removed"] = 1.0
    else:
        components["poc_json_removed"] = 0.0

    # --- 3. GitLab source added ---
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        sources = hub_data.get("sources", [])
        gitlab_source = None
        for s in (sources if isinstance(sources, list) else []):
            if isinstance(s, dict) and ("gitlab" in s.get("id", "").lower() or "gitlab" in str(s.get("events", "")).lower()):
                gitlab_source = s
                break
        if gitlab_source:
            score = 0.0
            if gitlab_source.get("type") == "webhook":
                score += 0.25
            events = gitlab_source.get("events", [])
            expected_events = ["merge_request.open", "merge_request.merge", "pipeline.failed"]
            if isinstance(events, list):
                found_events = sum(1 for e in expected_events if e in events)
                score += 0.25 * (found_events / 3.0)
            endpoint = str(gitlab_source.get("endpoint", ""))
            if "/hooks/gitlab" in endpoint:
                score += 0.2
            elif "gitlab" in endpoint:
                score += 0.1
            port = gitlab_source.get("port")
            if port == 7892 or str(port) == "7892":
                score += 0.15
            auth = gitlab_source.get("auth", {})
            if isinstance(auth, dict) and ("bearer" in str(auth.get("type", "")).lower() or "GITLAB_HOOK_TOKEN" in str(auth)):
                score += 0.15
            components["gitlab_source_added"] = min(1.0, score)
        else:
            components["gitlab_source_added"] = 0.0
    else:
        # text-based fallback — lower ceiling without structured parsing
        gitlab_indicators = ["gitlab-events", "/hooks/gitlab", "7892"]
        found = sum(1 for ind in gitlab_indicators if ind in hub_text)
        if "merge_request" in hub_text and "pipeline.failed" in hub_text:
            found += 1
        components["gitlab_source_added"] = min(0.6, found / 5.0)

    # --- 4. GitLab routing rules ---
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        routing = hub_data.get("routing", {})
        rules = routing.get("rules", [])
        gitlab_rules_score = 0.0
        if isinstance(rules, list):
            for r in rules:
                if not isinstance(r, dict):
                    continue
                cond = r.get("condition", {})
                if not isinstance(cond, dict):
                    continue
                event = cond.get("event_type", "")
                target = r.get("target_agent", "")
                if "merge_request.open" in event and target == "rd":
                    prio = r.get("priority", 999)
                    if prio == 35:
                        gitlab_rules_score += 0.33
                    else:
                        gitlab_rules_score += 0.2
                elif "merge_request.merge" in event and target == "devops":
                    prio = r.get("priority", 999)
                    if prio == 36:
                        gitlab_rules_score += 0.33
                    else:
                        gitlab_rules_score += 0.2
                elif "pipeline.failed" in event and target == "devops":
                    prio = r.get("priority", 999)
                    if isinstance(prio, int) and prio == 15:
                        gitlab_rules_score += 0.34
                    elif isinstance(prio, int) and prio <= 20:
                        gitlab_rules_score += 0.25
                    else:
                        gitlab_rules_score += 0.1
        components["gitlab_routing_rules"] = min(1.0, gitlab_rules_score)
    else:
        # text fallback — lower ceiling
        mr_open_rd = "merge_request.open" in hub_text and "rd" in hub_text
        mr_merge_devops = "merge_request.merge" in hub_text and "devops" in hub_text
        pipeline_devops = "pipeline.failed" in hub_text and "devops" in hub_text
        components["gitlab_routing_rules"] = min(0.6, sum([mr_open_rd, mr_merge_devops, pipeline_devops]) / 3.0 * 0.6)

    # --- 5. poc-frontend agent added to hub_config ---
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        agents = hub_data.get("agents", [])
        poc_fe = None
        for a in (agents if isinstance(agents, list) else []):
            if isinstance(a, dict) and "poc-frontend" in a.get("id", ""):
                poc_fe = a
                break
        if poc_fe:
            score = 0.2  # agent exists
            caps = poc_fe.get("capabilities", [])
            expected_caps = {"react-dev", "css-review", "a11y-audit"}
            if isinstance(caps, list):
                matched_caps = sum(1 for c in expected_caps if c in caps)
                score += 0.25 * (matched_caps / 3.0)
            if poc_fe.get("role") == "frontend-specialist":
                score += 0.2
            elif poc_fe.get("role") and "frontend" in str(poc_fe.get("role", "")).lower():
                score += 0.1
            if poc_fe.get("config_path") == ".pi/agents/poc-frontend/AGENT.md":
                score += 0.2
            elif poc_fe.get("config_path") and "poc-frontend" in str(poc_fe.get("config_path", "")):
                score += 0.1
            # model specified correctly
            if poc_fe.get("model") == "deepseek-v4-flash":
                score += 0.1
            # routing priority
            if poc_fe.get("routing_priority") == 5:
                score += 0.05
            components["poc_frontend_agent_added"] = min(1.0, score)
        else:
            components["poc_frontend_agent_added"] = 0.0
    else:
        has_pocfe = "poc-frontend" in hub_text
        has_react = "react" in hub_text.lower()
        components["poc_frontend_agent_added"] = 0.4 if (has_pocfe and has_react) else (0.2 if has_pocfe else 0.0)

    # --- 6. poc-frontend AGENT.md created ---
    poc_fe_md = hub_dir / ".pi" / "agents" / "poc-frontend" / "AGENT.md"
    if not poc_fe_md.exists():
        # Try alternate paths
        for candidate in [
            hub_dir / ".pi/agents/poc-frontend/AGENT.md",
            hub_dir / "agents" / "poc-frontend" / "AGENT.md",
        ]:
            if candidate.exists():
                poc_fe_md = candidate
                break
    if poc_fe_md.exists():
        content = _read(poc_fe_md)
        score = 0.2  # file exists
        if "poc-frontend" in content.lower() or "frontend" in content.lower():
            score += 0.15
        if "react" in content.lower():
            score += 0.2
        if "css" in content.lower():
            score += 0.15
        if "a11y" in content.lower() or "accessibility" in content.lower():
            score += 0.15
        # Structural quality: agent md should have role/tools/constraints sections
        section_count = sum(1 for kw in ["##", "role", "tools", "capabilities", "constraints", "responsibilities"]
                           if kw.lower() in content.lower())
        if section_count >= 4:
            score += 0.15
        elif section_count >= 2:
            score += 0.05
        components["poc_frontend_agent_md"] = min(1.0, score)
    else:
        components["poc_frontend_agent_md"] = 0.0

    # --- 7. Lark AGENT.md updated ---
    lark_md = hub_dir / ".pi" / "agents" / "lark" / "AGENT.md"
    if lark_md.exists():
        content = _read(lark_md)
        score = 0.0
        has_frontend_delegation = "poc-frontend" in content or ("frontend" in content.lower() and "delegat" in content.lower())
        has_skill_check = "skill-check" in content or "skill_check" in content
        if has_frontend_delegation:
            score += 0.5
        if has_skill_check:
            score += 0.4
        # Original content preserved (stricter — must keep substantive sections)
        if score > 0 and ("message-center" in content or "lark-im" in content):
            score += 0.1
        components["lark_agent_updated"] = min(1.0, score)
    else:
        components["lark_agent_updated"] = 0.0

    # --- 8. Session management config added ---
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        session_mgmt = hub_data.get("session_management", None)
        if isinstance(session_mgmt, dict):
            score = 0.2  # section exists
            threshold = session_mgmt.get("compaction_threshold_tokens")
            if threshold == 80000:
                score += 0.25
            elif str(threshold) == "80000":
                score += 0.15
            on_compact = session_mgmt.get("on_compaction", {})
            if isinstance(on_compact, dict):
                if on_compact.get("reload_skills") is True:
                    score += 0.2
                if on_compact.get("re_fetch_context_window") == 5:
                    score += 0.2
                if on_compact.get("notify_user") is False:
                    score += 0.15
            elif isinstance(on_compact, list):
                on_compact_str = str(on_compact)
                if "reload_skills" in on_compact_str:
                    score += 0.15
                if "re_fetch_context" in on_compact_str or "context_window" in on_compact_str:
                    score += 0.1
                if "notify_user" in on_compact_str:
                    score += 0.1
            components["session_management_added"] = min(1.0, score)
        else:
            components["session_management_added"] = 0.0
    else:
        has_section = "session_management" in hub_text
        has_threshold = "80000" in hub_text
        has_reload = "reload_skills" in hub_text
        score = sum([has_section * 0.2, has_threshold * 0.2, has_reload * 0.15])
        components["session_management_added"] = min(0.55, score)

    # =====================================================================
    # HIDDEN CHECKS — discriminate strong vs weak agents
    # =====================================================================

    # --- H1. Existing config preserved (no regression) ---
    # Strong agents won't break existing sources, agents, or hub settings.
    # Tests detail-level preservation of fields that weak agents commonly drop.
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        preservation_score = 0.0
        # Hub top-level settings preserved (including commonly dropped fields)
        hub_section = hub_data.get("hub", {})
        if isinstance(hub_section, dict):
            if hub_section.get("name") == "workspace-hub":
                preservation_score += 0.05
            if hub_section.get("listen_port") == 7890:
                preservation_score += 0.05
            if hub_section.get("protocol") == "jsonrpc":
                preservation_score += 0.05
            # These are commonly dropped by weak models during rewrite
            if hub_section.get("heartbeat_interval_ms") == 30000:
                preservation_score += 0.05
            if hub_section.get("max_reconnect_attempts") == 5:
                preservation_score += 0.05

        # Original 3 sources preserved with full detail
        sources = hub_data.get("sources", [])
        source_map = {}
        if isinstance(sources, list):
            for s in sources:
                if isinstance(s, dict):
                    source_map[s.get("id", "")] = s
            original_sources = {"lark-message-watcher", "rame-sync-source", "meego-webhook"}
            preserved_sources = original_sources & set(source_map.keys())
            preservation_score += 0.1 * (len(preserved_sources) / 3.0)

        # Check detail preservation of lark-message-watcher (rate_limit, restart_policy)
        lark_src = source_map.get("lark-message-watcher", {})
        if isinstance(lark_src, dict):
            if lark_src.get("restart_policy") == "always":
                preservation_score += 0.05
            rate_limit = lark_src.get("rate_limit", {})
            if isinstance(rate_limit, dict) and rate_limit.get("max_per_minute") == 60:
                preservation_score += 0.05

        # Check meego-webhook auth preserved
        meego_src = source_map.get("meego-webhook", {})
        if isinstance(meego_src, dict):
            meego_auth = meego_src.get("auth", {})
            if isinstance(meego_auth, dict):
                if meego_auth.get("type") == "hmac" and meego_auth.get("secret_env") == "MEEGO_WEBHOOK_SECRET":
                    preservation_score += 0.1

        # Original 4 agents preserved
        agents = hub_data.get("agents", [])
        if isinstance(agents, list):
            agent_ids = {a.get("id", "") for a in agents if isinstance(a, dict)}
            original_agents = {"lark", "obsidian", "rd", "devops"}
            preserved_agents = original_agents & agent_ids
            preservation_score += 0.15 * (len(preserved_agents) / 4.0)

        # Routing section: default_agent and queue settings preserved
        routing = hub_data.get("routing", {})
        if isinstance(routing, dict):
            if routing.get("default_agent") == "lark":
                preservation_score += 0.05
            if routing.get("fallback_behavior") == "queue":
                preservation_score += 0.05
            if routing.get("max_queue_size") == 100:
                preservation_score += 0.05
            if routing.get("queue_ttl_seconds") == 3600:
                preservation_score += 0.05

        # Original agent capabilities and routing_priority not corrupted
        for a in (agents if isinstance(agents, list) else []):
            if not isinstance(a, dict):
                continue
            if a.get("id") == "rd":
                if "code-review" in (a.get("capabilities") or []):
                    preservation_score += 0.025
                if a.get("routing_priority") == 3:
                    preservation_score += 0.025
            if a.get("id") == "devops":
                if "incident-response" in (a.get("capabilities") or []):
                    preservation_score += 0.025
                if a.get("routing_priority") == 4:
                    preservation_score += 0.025

        components["existing_config_preserved"] = min(1.0, preservation_score)
    else:
        components["existing_config_preserved"] = 0.0

    # --- H2. Rule condition fidelity ---
    # Checks that migrated rules preserve ALL original condition fields faithfully
    # (chat_type, mentions_bot, source_id — not just event_type)
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        routing = hub_data.get("routing", {})
        rules = routing.get("rules", [])
        fidelity_score = 0.0
        if isinstance(rules, list):
            for r in rules:
                if not isinstance(r, dict):
                    continue
                cond = r.get("condition", {})
                if not isinstance(cond, dict):
                    continue
                name = r.get("name", "")
                # private-chat: must have chat_type=p2p
                if name == "private-chat-to-lark":
                    if cond.get("chat_type") == "p2p":
                        fidelity_score += 0.2
                # group-mention: must have chat_type=group AND mentions_bot=true
                elif name == "group-mention-to-lark":
                    if cond.get("chat_type") == "group":
                        fidelity_score += 0.1
                    if cond.get("mentions_bot") is True:
                        fidelity_score += 0.1
                # meego-issue: must have source_id=meego-webhook
                elif name == "meego-issue-to-rd":
                    if cond.get("source_id") == "meego-webhook":
                        fidelity_score += 0.2
                # daily-sync: must have source_id=rame-sync-source
                elif name == "daily-sync-to-lark":
                    if cond.get("source_id") == "rame-sync-source":
                        fidelity_score += 0.2
                # doc-comment: event_type correct
                elif name == "doc-comment-to-obsidian":
                    if cond.get("event_type") == "drive.notice.comment_add_v1":
                        fidelity_score += 0.2
        components["rule_condition_fidelity"] = min(1.0, fidelity_score)
    else:
        components["rule_condition_fidelity"] = 0.0

    # --- H3. Priority ordering coherent ---
    # All rules should have explicit numeric priorities; priorities of migrated rules
    # should match originals exactly (10, 20, 30, 40, 50, 35, 36, 15)
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        routing = hub_data.get("routing", {})
        rules = routing.get("rules", [])
        ordering_score = 0.0
        expected_priorities = {
            "private-chat-to-lark": 10,
            "group-mention-to-lark": 20,
            "doc-comment-to-obsidian": 30,
            "meego-issue-to-rd": 40,
            "daily-sync-to-lark": 50,
        }
        if isinstance(rules, list):
            all_have_priority = True
            matched_priorities = 0
            for r in rules:
                if not isinstance(r, dict):
                    continue
                prio = r.get("priority")
                if not isinstance(prio, int):
                    all_have_priority = False
                name = r.get("name", "")
                if name in expected_priorities and prio == expected_priorities[name]:
                    matched_priorities += 1

            if all_have_priority:
                ordering_score += 0.3
            # Check original 5 priority values preserved exactly
            ordering_score += 0.5 * (matched_priorities / 5.0)

            # Check no duplicate priorities
            prios = [r.get("priority") for r in rules if isinstance(r, dict) and isinstance(r.get("priority"), int)]
            if len(prios) == len(set(prios)):
                ordering_score += 0.2

        components["priority_ordering_coherent"] = min(1.0, ordering_score)
    else:
        components["priority_ordering_coherent"] = 0.0

    # --- H4. GitLab routing rules bind to source_id ---
    # Strong agents infer from the pattern of meego-issue-to-rd (which has
    # source_id: "meego-webhook") that gitlab routing rules should similarly
    # have source_id: "gitlab-events" in their conditions. This is never
    # explicitly stated in the migration doc but follows the established pattern.
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        routing = hub_data.get("routing", {})
        rules = routing.get("rules", [])
        binding_score = 0.0
        if isinstance(rules, list):
            gitlab_rule_count = 0
            gitlab_with_source = 0
            for r in rules:
                if not isinstance(r, dict):
                    continue
                cond = r.get("condition", {})
                if not isinstance(cond, dict):
                    continue
                event = cond.get("event_type", "")
                if any(kw in event for kw in ["merge_request", "pipeline"]):
                    gitlab_rule_count += 1
                    src_id = cond.get("source_id", "") or cond.get("source", "")
                    if "gitlab" in str(src_id).lower():
                        gitlab_with_source += 1
            if gitlab_rule_count > 0:
                binding_score = gitlab_with_source / gitlab_rule_count
        components["gitlab_rule_source_binding"] = min(1.0, binding_score)
    else:
        components["gitlab_rule_source_binding"] = 0.0

    # --- H5. Rule description fields preserved during migration ---
    # The POC JSON has a "description" field for each rule. A thorough agent
    # preserves these when migrating to YAML. Weak agents only copy the
    # explicitly listed fields (name, condition, target_agent, priority).
    if hub_data and isinstance(hub_data, dict) and "_raw" not in hub_data:
        routing = hub_data.get("routing", {})
        rules = routing.get("rules", [])
        desc_score = 0.0
        if isinstance(rules, list):
            original_rules_with_desc = 0
            original_rules_found = 0
            expected_original = {
                "private-chat-to-lark",
                "group-mention-to-lark",
                "doc-comment-to-obsidian",
                "meego-issue-to-rd",
                "daily-sync-to-lark",
            }
            for r in rules:
                if not isinstance(r, dict):
                    continue
                name = r.get("name", "")
                if name in expected_original:
                    original_rules_found += 1
                    desc = r.get("description", "")
                    if isinstance(desc, str) and len(desc) >= 10:
                        original_rules_with_desc += 1
            if original_rules_found > 0:
                desc_score = original_rules_with_desc / original_rules_found
        components["rule_description_preserved"] = min(1.0, desc_score)
    else:
        # text fallback
        poc_descriptions = [
            "Private messages go to lark",
            "Group messages mentioning bot",
            "Doc comments route to obsidian",
            "Meego issue changes go to rd",
            "Daily sync reports handled by lark",
        ]
        found = sum(1 for d in poc_descriptions if d.lower() in hub_text.lower())
        components["rule_description_preserved"] = min(1.0, found / 5.0)

    # Calculate overall score with rebalanced weights
    weights = {
        "routing_rules_migrated": 0.09,
        "poc_json_removed": 0.02,
        "gitlab_source_added": 0.09,
        "gitlab_routing_rules": 0.07,
        "poc_frontend_agent_added": 0.07,
        "poc_frontend_agent_md": 0.06,
        "lark_agent_updated": 0.06,
        "session_management_added": 0.05,
        # Hidden checks carry significant weight (49% total)
        "existing_config_preserved": 0.12,
        "rule_condition_fidelity": 0.09,
        "priority_ordering_coherent": 0.07,
        "gitlab_rule_source_binding": 0.12,
        "rule_description_preserved": 0.09,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Check both possible locations
    ws = Path("/workspace/fixtures/agent-hub")
    if not ws.exists():
        ws = Path("/workspace/agent-hub")
    if not ws.exists():
        ws = Path("/workspace/fixtures")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
