"""Hidden verifier for CP175 — Feishu Channel Config Integration."""
from __future__ import annotations

import json
from pathlib import Path


def _load_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_raw(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return None


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "feishu_channel_exists",
        "credentials_correct",
        "channel_enabled",
        "features_configured",
        "existing_config_preserved",
        "workspace_path_updated",
        "valid_json_structure",
        # --- Hidden harder checks below ---
        "doc_driven_fields",
        "plugins_section_preserved",
        "config_structural_fidelity",
        "event_url_contextual",
        "telegram_untouched",
        "no_config_pollution",
    ]}

    # Try multiple possible locations for the config
    config_path = ws / "openclaw-project" / "openclaw.json"
    if not config_path.exists():
        config_path = ws / "fixtures" / "openclaw-project" / "openclaw.json"
    if not config_path.exists():
        # Search for any openclaw.json
        candidates = list(ws.rglob("openclaw.json"))
        config_path = candidates[0] if candidates else config_path

    config = _load_json(config_path)
    raw_text = _load_raw(config_path)
    if config is None:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": f"Cannot read config at {config_path}",
        }

    # Check 1: Valid JSON structure (parseable and has expected top-level keys)
    expected_keys = {"agents", "gateway", "channels"}
    if expected_keys.issubset(set(config.keys())):
        components["valid_json_structure"] = 1.0
    elif "channels" in config:
        components["valid_json_structure"] = 0.5
    else:
        components["valid_json_structure"] = 0.0

    # Check 2: Feishu channel section exists
    channels = config.get("channels", {})
    feishu = channels.get("feishu", {})
    if isinstance(feishu, dict) and feishu:
        components["feishu_channel_exists"] = 1.0
    else:
        return {
            "overall_score": round(components["valid_json_structure"] * 0.05, 4),
            "components": {k: round(v, 4) for k, v in components.items()},
            "weights": _weights(),
        }

    # Check 3: Credentials correct — no partial credit
    app_id = feishu.get("app_id", "")
    app_secret = feishu.get("app_secret", "")
    verification_token = feishu.get("verification_token", "")

    cred_score = 0.0
    if app_id == "cli_a93c333e8338dcc0":
        cred_score += 0.34
    if app_secret == "WWcDxFqmz3y44utjmBiNNgM0ZBn8yPOc":
        cred_score += 0.34
    if verification_token == "v-tk-9X8bQ2mLpR7nKz":
        cred_score += 0.32
    components["credentials_correct"] = min(cred_score, 1.0)

    # Check 4: Channel enabled
    enabled = feishu.get("enabled")
    if enabled is True:
        components["channel_enabled"] = 1.0
    elif enabled:
        components["channel_enabled"] = 0.3

    # Check 5: Features configured (must have all 5: doc, wiki, drive, bitable, chat)
    features = feishu.get("features", {})
    if isinstance(features, dict):
        expected_features = ["doc", "wiki", "drive", "bitable", "chat"]
        enabled_count = sum(1 for f in expected_features if features.get(f) is True)
        if enabled_count == 5:
            components["features_configured"] = 1.0
        elif enabled_count >= 3:
            components["features_configured"] = 0.5
        else:
            components["features_configured"] = round(enabled_count / 5.0 * 0.4, 4)
    else:
        components["features_configured"] = 0.0

    # Check 6: Existing config preserved (telegram, gateway, agents)
    preserve_score = 0.0
    telegram = channels.get("telegram", {})
    if isinstance(telegram, dict) and telegram.get("enabled") is True:
        preserve_score += 0.30
    if isinstance(telegram, dict) and telegram.get("bot_token") == "7012345678:AAHx1234567890abcdefghij":
        preserve_score += 0.20
    gw = config.get("gateway", {})
    if gw.get("port") == 7860 and gw.get("host") == "0.0.0.0":
        preserve_score += 0.15
    if isinstance(gw.get("auth"), dict) and gw["auth"].get("token") == "test-gateway-token-abc123":
        preserve_score += 0.10
    agents = config.get("agents", {})
    defaults = agents.get("defaults", {})
    if "volcengine-plan/ark-code-latest" in str(defaults.get("models", {})):
        preserve_score += 0.15
    if defaults.get("model", {}).get("primary") == "volcengine-plan/ark-code-latest":
        preserve_score += 0.10
    components["existing_config_preserved"] = min(preserve_score, 1.0)

    # Check 7: Workspace path updated to /data/openclaw-workspace
    workspace_path = defaults.get("workspace", "")
    if workspace_path == "/data/openclaw-workspace":
        components["workspace_path_updated"] = 1.0
    elif "/data" in str(workspace_path) and "openclaw" in str(workspace_path):
        components["workspace_path_updated"] = 0.4
    else:
        components["workspace_path_updated"] = 0.0

    # =========================================================================
    # HIDDEN HARDER CHECKS - differentiate strong from weak models
    # =========================================================================

    # Hidden Check 8: doc_driven_fields
    # Tests whether the model carefully read the feishu.md documentation and
    # included fields shown in the doc's config template beyond the bare minimum.
    # The doc template shows: encrypt_key (empty string), event_url (optional).
    # A strong model includes encrypt_key="" per the template.
    # Also: bot_name must be exactly "AI助手" (Chinese, from prompt).
    # Also: features should ONLY contain the 5 documented keys, not extras.
    # Also: no hallucinated/invented keys in the feishu config.
    doc_score = 0.0

    # encrypt_key present and empty string (per doc template) — major signal
    if "encrypt_key" in feishu and feishu["encrypt_key"] == "":
        doc_score += 0.40
    elif "encrypt_key" in feishu:
        doc_score += 0.15

    # bot_name exactly "AI助手"
    bot_name = feishu.get("bot_name", "")
    if bot_name == "AI助手":
        doc_score += 0.15
    elif bot_name:
        doc_score += 0.05

    # features object contains ONLY the 5 documented keys (no extras, no missing)
    if isinstance(features, dict):
        valid_feature_keys = {"doc", "wiki", "drive", "bitable", "chat"}
        actual_feature_keys = set(features.keys())
        if actual_feature_keys == valid_feature_keys:
            doc_score += 0.20
        elif len(actual_feature_keys - valid_feature_keys) > 0:
            # Has extra/hallucinated feature keys — penalize
            doc_score += 0.0
        elif len(actual_feature_keys) >= 4:
            doc_score += 0.10
        else:
            doc_score += 0.05

    # No hallucinated keys in feishu section — strong signal of careful work
    valid_feishu_keys = {
        "enabled", "app_id", "app_secret", "verification_token",
        "encrypt_key", "bot_name", "event_url", "features",
    }
    actual_feishu_keys = set(feishu.keys())
    hallucinated = actual_feishu_keys - valid_feishu_keys
    if len(hallucinated) == 0:
        doc_score += 0.25
    elif len(hallucinated) == 1:
        doc_score += 0.10
    # else: multiple hallucinated keys — 0

    components["doc_driven_fields"] = min(doc_score, 1.0)

    # Hidden Check 9: plugins section preserved
    # Original config has "plugins" with web_search (enabled, brave, api_key).
    # This is NOT mentioned in the task prompt at all — only a careful model
    # preserves what it didn't explicitly need to modify.
    plugins = config.get("plugins", {})
    plugins_score = 0.0
    if isinstance(plugins, dict) and "web_search" in plugins:
        web_search = plugins["web_search"]
        if isinstance(web_search, dict):
            if web_search.get("enabled") is True:
                plugins_score += 0.35
            if web_search.get("provider") == "brave":
                plugins_score += 0.30
            if web_search.get("api_key") == "BSAx1234567890":
                plugins_score += 0.35
    components["plugins_section_preserved"] = min(plugins_score, 1.0)

    # Hidden Check 10: config_structural_fidelity
    # Tests preservation of subtle structural details that careless editing breaks.
    structural_score = 0.0

    # gateway.mode == "local" preserved
    if gw.get("mode") == "local":
        structural_score += 0.20

    # gateway.auth.mode == "token" preserved
    if isinstance(gw.get("auth"), dict) and gw["auth"].get("mode") == "token":
        structural_score += 0.20

    # agents.defaults.model.primary preserved (nested structure)
    if defaults.get("model", {}).get("primary") == "volcengine-plan/ark-code-latest":
        structural_score += 0.20

    # Key ordering: feishu should be at same level as telegram (both in channels)
    # and channels should NOT be nested inside something else
    if "channels" in config and isinstance(config["channels"], dict):
        if "feishu" in config["channels"] and "telegram" in config["channels"]:
            structural_score += 0.15

    # JSON formatting quality: well-indented, not minified
    if raw_text:
        lines = raw_text.strip().splitlines()
        if len(lines) > 15:
            # Check consistent indentation
            indent_sizes = set()
            for line in lines:
                stripped = line.lstrip()
                if stripped and stripped not in ("{", "}", "[", "]", "},", "],"):
                    indent = len(line) - len(stripped)
                    if indent > 0:
                        indent_sizes.add(indent)
            if indent_sizes:
                base = min(indent_sizes)
                if base in (2, 4) and all(i % base == 0 for i in indent_sizes):
                    structural_score += 0.25
                else:
                    structural_score += 0.10
            else:
                structural_score += 0.15
        elif len(lines) > 5:
            structural_score += 0.10
        # else: likely minified, no credit

    components["config_structural_fidelity"] = min(structural_score, 1.0)

    # =========================================================================
    # HIDDEN CHECK 11: event_url_contextual
    # The doc says event_url is "auto-configured if using local gateway".
    # The existing config has gateway.mode == "local", so a strong model should
    # either omit event_url entirely OR leave it as empty string — NOT invent a URL.
    # A weak model often hallucinates "https://your-server.com/feishu/event" or similar.
    # =========================================================================
    event_url_score = 0.0
    event_url = feishu.get("event_url")
    if event_url is None:
        # Omitted entirely — best choice given local gateway mode
        event_url_score = 1.0
    elif event_url == "":
        # Empty string — acceptable, shows awareness it's optional
        event_url_score = 0.7
    elif "your-server" in str(event_url) or "example" in str(event_url):
        # Copied placeholder from doc template without adapting — weak signal
        event_url_score = 0.1
    elif isinstance(event_url, str) and event_url.startswith("http"):
        # Invented a concrete URL — hallucination penalty
        event_url_score = 0.15
    else:
        event_url_score = 0.2
    components["event_url_contextual"] = event_url_score

    # =========================================================================
    # HIDDEN CHECK 12: telegram_untouched
    # Original telegram config has EXACTLY {"enabled": true, "bot_token": "..."}
    # with only 2 keys. A strong model preserves it byte-for-byte.
    # Weak models sometimes add extra fields (e.g., "bot_name", "features"),
    # change the token, nest it differently, or remove fields.
    # =========================================================================
    telegram_score = 0.0
    if isinstance(telegram, dict):
        telegram_keys = set(telegram.keys())
        expected_telegram_keys = {"enabled", "bot_token"}
        if telegram_keys == expected_telegram_keys:
            # Exactly the original keys — perfect preservation
            telegram_score += 0.5
        elif expected_telegram_keys.issubset(telegram_keys):
            # Has the originals but added extras — partial credit
            extra_count = len(telegram_keys - expected_telegram_keys)
            telegram_score += max(0.3 - extra_count * 0.1, 0.05)
        else:
            # Missing original keys
            telegram_score += 0.0

        # Token value preserved exactly
        if telegram.get("bot_token") == "7012345678:AAHx1234567890abcdefghij":
            telegram_score += 0.3

        # enabled is boolean true (not string "true" or 1)
        if telegram.get("enabled") is True:
            telegram_score += 0.2
    components["telegram_untouched"] = min(telegram_score, 1.0)

    # =========================================================================
    # HIDDEN CHECK 13: no_config_pollution
    # Checks that the model didn't pollute the config with:
    # - Duplicate top-level keys (e.g., two "channels" sections merged wrong)
    # - New unexpected top-level keys beyond {agents, gateway, channels, plugins}
    # - Deeply nested errors like channels.feishu.channels or agents inside channels
    # - Comments or trailing content that breaks strict JSON
    # Strong models produce clean, minimal additions. Weak models add noise.
    # =========================================================================
    pollution_score = 0.0

    # Check 1: Only expected top-level keys
    valid_top_keys = {"agents", "gateway", "channels", "plugins"}
    actual_top_keys = set(config.keys())
    unexpected_top = actual_top_keys - valid_top_keys
    if len(unexpected_top) == 0:
        pollution_score += 0.35
    elif len(unexpected_top) == 1:
        pollution_score += 0.15
    # else: multiple unexpected keys — 0

    # Check 2: No accidental nesting (feishu shouldn't contain "channels" or "agents")
    feishu_vals_str = json.dumps(feishu)
    nesting_issues = 0
    if '"channels"' in feishu_vals_str and '"telegram"' in feishu_vals_str:
        nesting_issues += 1
    if '"agents"' in feishu_vals_str and '"workspace"' in feishu_vals_str:
        nesting_issues += 1
    if nesting_issues == 0:
        pollution_score += 0.30
    elif nesting_issues == 1:
        pollution_score += 0.10

    # Check 3: Raw text check — no JSON5 comments, no trailing commas before }
    if raw_text:
        import re
        # Trailing comma before } or ]
        trailing_comma_pattern = re.compile(r',\s*[}\]]')
        has_trailing = bool(trailing_comma_pattern.search(raw_text))
        # JS-style comments (exclude :// in URLs which is valid in JSON strings)
        raw_no_strings = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', raw_text)
        has_comments = '//' in raw_no_strings or '/*' in raw_no_strings
        if not has_trailing and not has_comments:
            pollution_score += 0.35
        elif has_trailing and not has_comments:
            pollution_score += 0.15
        elif not has_trailing:
            pollution_score += 0.10
    else:
        pollution_score += 0.0

    components["no_config_pollution"] = min(pollution_score, 1.0)

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        # Basic checks (easy — minimal weight)
        "feishu_channel_exists": 0.02,
        "credentials_correct": 0.07,
        "channel_enabled": 0.02,
        "features_configured": 0.05,
        "valid_json_structure": 0.02,
        # Medium checks
        "existing_config_preserved": 0.08,
        "workspace_path_updated": 0.06,
        # Hidden harder checks (high weight — differentiate strong models)
        "doc_driven_fields": 0.18,
        "plugins_section_preserved": 0.16,
        "config_structural_fidelity": 0.10,
        "event_url_contextual": 0.10,
        "telegram_untouched": 0.07,
        "no_config_pollution": 0.07,
    }


def main():
    # Try /workspace/fixtures/openclaw-project first, fallback to /workspace/openclaw-project
    ws = Path("/workspace/fixtures/openclaw-project")
    if not ws.exists():
        ws = Path("/workspace/openclaw-project")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws.parent), ensure_ascii=False))


if __name__ == "__main__":
    main()
