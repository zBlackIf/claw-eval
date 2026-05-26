#!/usr/bin/env python3
"""In-container verifier for CP43_vue_agent_view_data_overwrite.

Ports the original automated_score() to a script that runs under
env_snapshot_commands. Emits one JSON line with per-component scores plus
overall_score = mean(components).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WORKSPACE = Path("/workspace")


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    def read_safe(p: Path) -> str:
        return p.read_text(errors="ignore") if p.exists() else ""

    agent_view = read_safe(workspace / "web" / "src" / "views" / "AgentView.vue")
    plan_panel = read_safe(workspace / "web" / "src" / "components" / "PlanChatPanel.vue")
    db_layer = read_safe(workspace / "web" / "src" / "utils" / "agentChatManagerDB.js")
    server_routes = read_safe(workspace / "server" / "src" / "routes" / "agentChats.js")

    all_code = agent_view + plan_panel + db_layer + server_routes
    for p in workspace.rglob("*"):
        if p.is_file() and p.suffix in (".js", ".ts", ".vue"):
            rp = str(p.relative_to(workspace))
            if rp not in [
                "web/src/views/AgentView.vue",
                "web/src/components/PlanChatPanel.vue",
                "web/src/utils/agentChatManagerDB.js",
                "server/src/routes/agentChats.js",
            ]:
                all_code += read_safe(p)

    # Race condition fix: pinned ID or removed debounce
    has_pinned_id = bool(re.search(
        r"(const|let|ref)\s*\(?\s*(savedId|chatIdSnapshot|pinnedId|targetId|capturedId)\s*=",
        plan_panel, re.IGNORECASE,
    ))
    removed_debounce = "debounce" not in plan_panel.lower()
    uses_ref_tracking = bool(re.search(r"(activeChatId|currentSavingId)\.value", plan_panel))
    scores["race_condition_fixed"] = 1.0 if (has_pinned_id or removed_debounce or uses_ref_tracking) else 0.0

    # Dirty check added
    has_dirty = bool(re.search(
        r"(const|let|ref|computed)\s*\(?\s*(isDirty|dirty|hasChanges|isModified)",
        agent_view + plan_panel, re.IGNORECASE,
    ))
    has_confirm = bool(re.search(r"(confirm\(|window\.confirm|showConfirm)", agent_view, re.IGNORECASE))
    has_save_before_switch = bool(re.search(r"handleSelectChat[^}]*await\s+.*save", agent_view, re.DOTALL))
    if has_dirty and (has_confirm or has_save_before_switch):
        scores["dirty_check_added"] = 1.0
    elif has_dirty:
        scores["dirty_check_added"] = 0.5
    else:
        scores["dirty_check_added"] = 0.0

    # Request dedup or cancel
    has_abort = bool(re.search(r"AbortController|abort.*signal", all_code, re.IGNORECASE))
    has_cancel = bool(re.search(r"\.cancel\(\)", all_code))
    has_save_lock = bool(re.search(r"(isSaving|saveLock|mutex)", all_code, re.IGNORECASE))
    count = sum([has_abort, has_cancel, has_save_lock])
    scores["request_dedup"] = min(count / 2.0, 1.0)

    # Server concurrency
    has_version = bool(re.search(r"(version|etag|if-match|optimistic)", server_routes, re.IGNORECASE))
    scores["server_concurrency"] = 1.0 if has_version else 0.0

    return scores


def main() -> dict:
    try:
        scores = automated_score(WORKSPACE)
    except Exception as exc:  # noqa: BLE001
        return {"scores": {}, "overall_score": 0.0, "error": f"{type(exc).__name__}: {exc}"}
    numeric = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    overall = sum(numeric) / len(numeric) if numeric else 0.0
    return {"scores": scores, "overall_score": round(overall, 4)}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(main(), ensure_ascii=False) + "\n")
