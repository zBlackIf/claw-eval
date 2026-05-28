#!/usr/bin/env python3
"""In-container verifier for CP21 TCG card rule schema task.

Runs after agent loop completes. Inspects /workspace artifacts and emits a single
JSON line on stdout with the dimension subscores plus overall_score.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")

REQUIRED_CARD_TYPES = {"hero", "equipment", "strategy", "skill", "monster"}
ALLOWED_CARD_TYPES = REQUIRED_CARD_TYPES
PHASE_ALIASES = {
    "draw": ["draw", "抽牌"],
    "revive": ["revive", "复归", "revive_phase"],
    "swift": ["swift", "迅捷"],
    "active": ["active", "主动"],
    "strategy": ["strategy", "谋略"],
    "equip": ["equip", "装备"],
    "upgrade": ["upgrade", "升级"],
    "replace": ["replace", "替换"],
    "retreat": ["retreat", "撤退"],
    "end_turn": ["end_turn", "end", "结束"],
}
HERO_FIELDS = {
    "name", "card_art", "hp", "retreat_cost", "defeat_cost",
    "revive_cost", "effects", "tags", "tier",
}


def evaluate() -> dict:
    scores: dict[str, float] = {}

    rule_file = WORKSPACE / "data" / "rules" / "arena_tcg" / "rule.json"
    scores["rule_json_present"] = 1.0 if rule_file.exists() else 0.0

    if rule_file.exists():
        try:
            rules = json.loads(rule_file.read_text(encoding="utf-8"))
            scores["rule_json_valid"] = 1.0
            rule_text = json.dumps(rules, ensure_ascii=False).lower()
            found_types = sum(1 for ct in REQUIRED_CARD_TYPES if ct in rule_text)
            scores["card_types_complete"] = found_types / len(REQUIRED_CARD_TYPES)
            found_phases = sum(
                1
                for aliases in PHASE_ALIASES.values()
                if any(a in rule_text for a in aliases)
            )
            scores["turn_actions_complete"] = found_phases / len(PHASE_ALIASES)
        except (json.JSONDecodeError, UnicodeDecodeError):
            scores["rule_json_valid"] = 0.0
            scores["card_types_complete"] = 0.0
            scores["turn_actions_complete"] = 0.0
    else:
        scores["rule_json_valid"] = 0.0
        scores["card_types_complete"] = 0.0
        scores["turn_actions_complete"] = 0.0

    cards_dir = WORKSPACE / "data" / "rules" / "arena_tcg" / "cards"
    card_files = list(cards_dir.glob("*.json")) if cards_dir.exists() else []
    scores["card_files_count"] = min(len(card_files) / 6.0, 1.0)

    valid_cards = 0
    typed_cards = 0
    card_types_seen: set[str] = set()
    invalid_extra_fields = 0
    for cf in card_files:
        try:
            card = json.loads(cf.read_text(encoding="utf-8"))
            if isinstance(card, dict):
                card_keys = {str(k).lower() for k in card.keys()}
                card_type = str(card.get("type", card.get("card_type", ""))).lower()
                if card_type in ALLOWED_CARD_TYPES:
                    typed_cards += 1
                    card_types_seen.add(card_type)
                if card_type == "hero" and HERO_FIELDS.issubset(card_keys):
                    valid_cards += 1
                elif card_type in {"equipment", "strategy", "skill", "monster"} and {"name", "type"}.issubset(card_keys):
                    valid_cards += 1
                elif "name" in card_keys:
                    valid_cards += 0.25
                if any(k in card_keys for k in ["mana", "land", "planeswalker", "pokemon_type", "energy"]):
                    invalid_extra_fields += 1
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    scores["card_schema_valid"] = (
        min(valid_cards / 6.0, 1.0) if card_files else 0.0
    )
    scores["card_types_in_cards"] = len(card_types_seen.intersection(REQUIRED_CARD_TYPES)) / len(REQUIRED_CARD_TYPES)
    scores["typed_card_ratio"] = min(typed_cards / 6.0, 1.0) if card_files else 0.0
    scores["no_foreign_tcg_fields"] = 0.0 if invalid_extra_fields else 1.0

    sop_file = WORKSPACE / "skills" / "arena_tcg_card_import.md"
    scores["sop_document_present"] = 1.0 if sop_file.exists() else 0.0

    overall = sum(scores.values()) / len(scores) if scores else 0.0
    return {"scores": scores, "overall_score": round(overall, 4)}


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception as exc:  # noqa: BLE001
        result = {"scores": {}, "overall_score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
