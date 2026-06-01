# Persistent Rule Engine Requirements

Implement all TODO methods in `rule_engine.py`:

- `add_rule`: generate a unique `rule_id`, add the rule, and persist it to `app_config.json`
- `remove_rule`: remove a rule by id and persist the updated rule list
- `get_active_rules`: return active rules sorted by descending `priority`
- `build_system_prompt_prefix`: format active rules into a system prompt prefix
- `apply_rules_to_config`: infer config suggestions from rule content

Validation scenario:

1. Add three rules: reply in Chinese with priority 10, show model name with priority 5, use dark theme with priority 1
2. Verify active rules are sorted by priority 10, 5, 1
3. Generate a system prompt prefix
4. Verify config suggestions include `frontend.language = zh-CN` for the Chinese rule
5. Remove the dark-theme rule
6. Re-instantiate `RuleEngine` and verify the remaining two rules persist
7. Confirm fields outside `rules` in `app_config.json` are preserved

Red lines:

- Rules must persist to `app_config.json`, not memory only
- Re-instantiating `RuleEngine` must reload persisted rules
- `rule_id` values must be unique
- Do not modify `app_config.json` fields outside `rules`
