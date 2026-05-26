"""Rule Engine - manages persistent operational rules for the AI assistant.

Rules are user-defined behavioral constraints that persist across sessions.
Examples: "always reply in Chinese", "show current model name in every response",
"use dark theme by default".
"""
import json
from datetime import datetime
from typing import List, Optional


class Rule:
    """A persistent operational rule."""

    def __init__(self, rule_id: str, content: str, priority: int = 0,
                 active: bool = True, created_at: Optional[str] = None):
        self.rule_id = rule_id
        self.content = content
        self.priority = priority
        self.active = active
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "content": self.content,
            "priority": self.priority,
            "active": self.active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rule":
        return cls(**data)


class RuleEngine:
    """Manages persistent rules that survive restarts and new sessions."""

    def __init__(self, config_path: str = "app_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.rules: List[Rule] = self._load_rules()

    def _load_config(self) -> dict:
        """Load config from file."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"rules": []}

    def _load_rules(self) -> List[Rule]:
        """Load rules from config."""
        raw_rules = self.config.get("rules", [])
        return [Rule.from_dict(r) for r in raw_rules if isinstance(r, dict)]

    def _save(self):
        """Persist rules back to config file."""
        self.config["rules"] = [r.to_dict() for r in self.rules]
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    # TODO: Implement the following methods

    def add_rule(self, content: str, priority: int = 0) -> Rule:
        """Add a new rule and persist it.

        Args:
            content: The rule text (e.g., "Always reply in Chinese")
            priority: Higher priority rules are applied first

        Returns:
            The created Rule object
        """
        raise NotImplementedError("TODO: implement add_rule")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID and persist.

        Returns:
            True if rule was found and removed, False otherwise
        """
        raise NotImplementedError("TODO: implement remove_rule")

    def get_active_rules(self) -> List[Rule]:
        """Get all active rules sorted by priority (highest first).

        Returns:
            List of active Rule objects
        """
        raise NotImplementedError("TODO: implement get_active_rules")

    def build_system_prompt_prefix(self) -> str:
        """Build a system prompt prefix from all active rules.

        The prefix should be prepended to the AI's system prompt so that
        rules are enforced in every interaction, even after restart.

        Format:
            ## Operational Rules
            1. [Rule content 1]
            2. [Rule content 2]
            ...

        Returns:
            Formatted string to prepend to system prompt
        """
        raise NotImplementedError("TODO: implement build_system_prompt_prefix")

    def apply_rules_to_config(self) -> dict:
        """Check if any rules affect app configuration and return
        suggested config changes.

        For example, a rule "use Chinese language" should suggest
        changing frontend.language to "zh-CN".

        Returns:
            Dict of config path -> suggested value
        """
        raise NotImplementedError("TODO: implement apply_rules_to_config")
