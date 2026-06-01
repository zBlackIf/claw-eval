# Hub v2.2 Migration Checklist

## Background
We've been running the POC routing rules in a separate JSON file (`routing_rules_poc.json`).
Now that the rules are stable, we need to consolidate them into `hub_config.yaml` and
add two new capabilities that the team requested this sprint.

## Requirements

### 1. Migrate routing rules into hub_config.yaml
- Move all rules from `routing_rules_poc.json` into the `routing.rules` section of `hub_config.yaml`
- Each rule should be a YAML object with: name, condition (nested map), target_agent, priority
- Keep `conflict_resolution` and `unmatched_behavior` settings
- After migration, delete `routing_rules_poc.json`

### 2. Add new source: gitlab-events
- Type: webhook
- Endpoint: /hooks/gitlab
- Port: 7892
- Events: merge_request.open, merge_request.merge, pipeline.failed
- Auth: bearer token from env var GITLAB_HOOK_TOKEN

### 3. Add routing rules for the new source
- merge_request.open -> rd agent (priority 35)
- merge_request.merge -> devops agent (priority 36)
- pipeline.failed -> devops agent (priority 15, highest prio for incidents)

### 4. Add new agent: "poc-frontend"
- Role: frontend-specialist
- Model: deepseek-v4-flash
- Config path: .pi/agents/poc-frontend/AGENT.md
- Capabilities: react-dev, css-review, a11y-audit
- Routing priority: 5
- Create its AGENT.md with appropriate content

### 5. Update lark agent AGENT.md
- Add the new SOP rule: "For frontend-related code tasks (React/CSS/a11y), delegate to poc-frontend agent"
- Add "skill-check" to its tools list

### 6. Add compaction recovery config
Under hub config, add a new top-level section `session_management`:
- compaction_threshold_tokens: 80000
- on_compaction: list of actions each agent must take
  - reload_skills: true
  - re_fetch_context_window: 5
  - notify_user: false
