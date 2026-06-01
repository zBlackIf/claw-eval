"""Hidden verifier for CP165 — Gateway Config Repair and Model Switch."""
from __future__ import annotations

import json
import os
from pathlib import Path


def _load_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def grade_workspace(ws: Path) -> dict:
    config_dir = ws / "fixtures" / "gateway-config"
    if not config_dir.exists():
        config_dir = ws / "gateway-config"

    config_path = config_dir / "gateway.json"
    schema_path = config_dir / "schema.json"

    components = {k: 0.0 for k in [
        "valid_json",
        "no_schema_violations",
        "model_switched",
        "channel_added",
        "plugin_disabled",
        "channel_exact_id",
        "credential_exact_values",
        "model_registry_consistency",
        "existing_channels_preserved",
        "fallback_model_intact",
        "gateway_structural_integrity",
        "no_residual_artifacts",
    ]}

    config = _load_json(config_path)
    schema = _load_json(schema_path)

    if config is None:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "gateway.json is not valid JSON or missing",
        }

    # 1. Valid JSON structure
    components["valid_json"] = 1.0

    # 2. No schema violations (check additionalProperties)
    violations = []
    if schema:
        def check_additional(obj, schema_node, path="<root>"):
            if not isinstance(obj, dict) or not isinstance(schema_node, dict):
                return
            if schema_node.get("additionalProperties") is False:
                allowed = set(schema_node.get("properties", {}).keys())
                for key in obj:
                    if key not in allowed:
                        violations.append(f'{path}: "{key}"')
            props = schema_node.get("properties", {})
            for key, val in obj.items():
                if key in props and isinstance(val, dict):
                    prop_schema = props[key]
                    if prop_schema.get("type") == "object":
                        if "additionalProperties" in prop_schema and isinstance(prop_schema["additionalProperties"], dict):
                            for sub_key, sub_val in val.items():
                                if isinstance(sub_val, dict):
                                    check_additional(sub_val, prop_schema["additionalProperties"], f"{path}.{key}.{sub_key}")
                        else:
                            check_additional(val, prop_schema, f"{path}.{key}")

        check_additional(config, schema)

    if not violations:
        components["no_schema_violations"] = 1.0
    elif len(violations) == 1:
        components["no_schema_violations"] = 0.3
    else:
        components["no_schema_violations"] = 0.0

    # 3. Model switched to "volcengine/ark-coe-latest"
    try:
        primary = config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "")
        if primary == "volcengine/ark-coe-latest":
            components["model_switched"] = 1.0
        elif "ark-coe" in primary.lower():
            components["model_switched"] = 0.7
        elif primary != "volcengine/deepseek-v3-2-251201":
            # Changed from default but to wrong value
            components["model_switched"] = 0.2
    except Exception:
        pass

    # 4. Feishu channel added with correct structure
    try:
        channels = config.get("gateway", {}).get("channels", {})
        feishu_found = False
        for ch_id, ch_config in channels.items():
            if isinstance(ch_config, dict) and ch_config.get("type") == "feishu":
                feishu_found = True
                has_enabled = "enabled" in ch_config
                has_credentials = "credentials" in ch_config
                creds = ch_config.get("credentials", {})
                has_app_id = isinstance(creds, dict) and "app_id" in creds
                has_app_secret = isinstance(creds, dict) and "app_secret" in creds

                score = 0.3  # base: feishu channel exists
                if has_enabled and ch_config["enabled"] is True:
                    score += 0.2
                if has_credentials:
                    score += 0.2
                if has_app_id and has_app_secret:
                    score += 0.3
                components["channel_added"] = min(score, 1.0)
                break
        if not feishu_found:
            components["channel_added"] = 0.0
    except Exception:
        pass

    # 5. Plugin amazon-bedrock disabled (to fix the load error)
    try:
        plugins = config.get("plugins", {})
        bedrock = plugins.get("amazon-bedrock", {})
        if isinstance(bedrock, dict):
            if bedrock.get("enabled") is False:
                components["plugin_disabled"] = 1.0
            elif "amazon-bedrock" not in plugins:
                # Removed entirely — acceptable but not ideal
                components["plugin_disabled"] = 0.5
        elif "amazon-bedrock" not in plugins:
            components["plugin_disabled"] = 0.5
    except Exception:
        pass

    # --- HIDDEN CHECKS (discriminate strong vs weak models) ---

    # 6. Channel ID must be exactly "feishu-bot" as user specified
    try:
        channels = config.get("gateway", {}).get("channels", {})
        if "feishu-bot" in channels:
            ch = channels["feishu-bot"]
            if isinstance(ch, dict) and ch.get("type") == "feishu":
                components["channel_exact_id"] = 1.0
            else:
                components["channel_exact_id"] = 0.3
        else:
            # Check if there's a feishu channel but with wrong key name
            for ch_id, ch_config in channels.items():
                if isinstance(ch_config, dict) and ch_config.get("type") == "feishu":
                    # Channel exists but under wrong ID
                    components["channel_exact_id"] = 0.2
                    break
    except Exception:
        pass

    # 7. Credential values must exactly match what user provided
    try:
        channels = config.get("gateway", {}).get("channels", {})
        feishu_ch = None
        # Prefer feishu-bot key, fall back to any feishu channel
        if "feishu-bot" in channels:
            feishu_ch = channels["feishu-bot"]
        else:
            for ch_id, ch_config in channels.items():
                if isinstance(ch_config, dict) and ch_config.get("type") == "feishu":
                    feishu_ch = ch_config
                    break

        if feishu_ch and isinstance(feishu_ch, dict):
            creds = feishu_ch.get("credentials", {})
            if isinstance(creds, dict):
                score = 0.0
                if creds.get("app_id") == "cli_a5f3x8k":
                    score += 0.5
                elif creds.get("app_id"):
                    # Has app_id but wrong value (typo or hallucination)
                    score += 0.1
                if creds.get("app_secret") == "secret_9d7e2b":
                    score += 0.5
                elif creds.get("app_secret"):
                    score += 0.1
                components["credential_exact_values"] = score
    except Exception:
        pass

    # 8. Model registry consistency: if primary model changed, the new model
    #    should be registered in agents.defaults.models dict (best practice)
    try:
        defaults = config.get("agents", {}).get("defaults", {})
        models_dict = defaults.get("models", {})
        primary = defaults.get("model", {}).get("primary", "")
        fallback = defaults.get("model", {}).get("fallback", "")

        if primary == "volcengine/ark-coe-latest":
            if "volcengine/ark-coe-latest" in models_dict:
                # New model registered - excellent
                if "volcengine/deepseek-v3-2-251201" not in models_dict:
                    # Old model removed from registry too - perfect
                    components["model_registry_consistency"] = 1.0
                else:
                    # New model added but old one left (acceptable)
                    components["model_registry_consistency"] = 0.7
            else:
                # Model changed but not registered in models dict
                components["model_registry_consistency"] = 0.0
        else:
            # Model not properly switched; no registry credit
            components["model_registry_consistency"] = 0.0
    except Exception:
        pass

    # 9. HIDDEN: Existing channels must be preserved intact.
    #    Weak models often overwrite the channels dict entirely when adding
    #    the new feishu channel, losing the pre-existing weixin-personal channel.
    try:
        channels = config.get("gateway", {}).get("channels", {})
        score = 0.0
        if "weixin-personal" in channels:
            wx = channels["weixin-personal"]
            if isinstance(wx, dict):
                # Check the original channel is fully preserved
                if wx.get("type") == "wechat":
                    score += 0.4
                if wx.get("mode") == "whatmeow":
                    score += 0.3
                if wx.get("enabled") is True:
                    score += 0.3
        components["existing_channels_preserved"] = score
    except Exception:
        pass

    # 10. HIDDEN: Fallback model AND overall agent config structure must remain
    #     intact. When switching the primary model, careless edits may accidentally
    #     modify/remove the fallback, workspace path, or compaction settings.
    #     The user only asked to change the primary model — everything else should
    #     stay unchanged.
    try:
        defaults = config.get("agents", {}).get("defaults", {})
        model_cfg = defaults.get("model", {})
        score = 0.0
        if isinstance(model_cfg, dict):
            # Fallback must remain openai/gpt-4o
            if model_cfg.get("fallback") == "openai/gpt-4o":
                score += 0.4
            elif model_cfg.get("fallback"):
                score += 0.1
            # model object should still have exactly primary+fallback keys
            expected_model_keys = {"primary", "fallback"}
            if set(model_cfg.keys()) == expected_model_keys:
                score += 0.1

        # workspace path must be preserved
        if defaults.get("workspace") == "/home/user/.aigateway/workspace":
            score += 0.25

        # compaction settings must be preserved
        compaction = defaults.get("compaction", {})
        if isinstance(compaction, dict) and compaction.get("mode") == "safeguard":
            score += 0.25

        components["fallback_model_intact"] = min(score, 1.0)
    except Exception:
        pass

    # 11. HIDDEN: Gateway auth and structural integrity check.
    #     The gateway.auth section must remain completely unchanged (token value,
    #     auth mode). Also verifies that controlUi only has allowed fields after
    #     locale removal, and gateway.mode is still "local". Weak models often
    #     introduce accidental mutations to adjacent config when making repairs.
    try:
        gw = config.get("gateway", {})
        score = 0.0

        # gateway.mode must remain "local"
        if gw.get("mode") == "local":
            score += 0.2

        # auth section must be completely preserved
        auth = gw.get("auth", {})
        if isinstance(auth, dict):
            if auth.get("mode") == "token" and auth.get("token") == "abc123def456":
                score += 0.35
            elif auth.get("mode") == "token":
                score += 0.1

        # controlUi: locale must be gone, port must remain 18789,
        # no unexpected keys introduced
        ctrl = gw.get("controlUi", {})
        if isinstance(ctrl, dict):
            if "locale" not in ctrl:
                score += 0.2
            if ctrl.get("port") == 18789:
                score += 0.25
            # Only "port" and optionally "bind" are schema-valid
            allowed_ctrl_keys = {"port", "bind"}
            extra_keys = set(ctrl.keys()) - allowed_ctrl_keys
            if extra_keys:
                score -= 0.2
        elif "controlUi" not in gw:
            # controlUi removed entirely — over-zealous fix
            score += 0.0

        components["gateway_structural_integrity"] = max(min(score, 1.0), 0.0)
    except Exception:
        pass

    # 12. No residual artifacts: no .bak files, no commented-out blocks,
    #     no trailing whitespace lines in the JSON, proper formatting
    try:
        artifact_score = 1.0

        # Check for backup files in config dir
        for f in config_dir.iterdir():
            if f.suffix in (".bak", ".orig", ".tmp", ".old"):
                artifact_score -= 0.3
            if f.name.startswith("gateway.json.") or f.name.endswith("~"):
                artifact_score -= 0.3

        # Check JSON formatting: should be properly indented (not minified)
        raw_text = config_path.read_text(encoding="utf-8")
        lines = raw_text.splitlines()
        if len(lines) < 5:
            # Minified JSON - poor practice for config files
            artifact_score -= 0.4

        # Check for trailing whitespace on lines (sloppy edits)
        trailing_ws_count = sum(1 for line in lines if line != line.rstrip())
        if trailing_ws_count > 3:
            artifact_score -= 0.3
        elif trailing_ws_count > 0:
            artifact_score -= 0.1

        # Verify it re-serializes cleanly (no duplicate keys via raw parse)
        # Use object_pairs_hook to detect duplicates
        pairs_seen: list[tuple[str, int]] = []
        def _check_dupes(pairs):
            keys = [k for k, v in pairs]
            if len(keys) != len(set(keys)):
                pairs_seen.append(("duplicate", 1))
            return dict(pairs)
        json.loads(raw_text, object_pairs_hook=_check_dupes)
        if pairs_seen:
            artifact_score -= 0.4

        components["no_residual_artifacts"] = max(artifact_score, 0.0)
    except Exception:
        components["no_residual_artifacts"] = 0.0

    # --- SCORING ---
    # Weights: hidden checks dominate (0.66 total) to separate strong/weak.
    # Strong model (registry + preserves all + clean output): 0.70-0.85
    # Weak model (basic fixes only, no registry, some collateral damage): 0.40-0.60
    weights = {
        "valid_json": 0.02,
        "no_schema_violations": 0.06,
        "model_switched": 0.05,
        "channel_added": 0.05,
        "plugin_disabled": 0.03,
        "channel_exact_id": 0.06,
        "credential_exact_values": 0.07,
        "model_registry_consistency": 0.24,
        "existing_channels_preserved": 0.14,
        "fallback_model_intact": 0.10,
        "gateway_structural_integrity": 0.10,
        "no_residual_artifacts": 0.08,
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
