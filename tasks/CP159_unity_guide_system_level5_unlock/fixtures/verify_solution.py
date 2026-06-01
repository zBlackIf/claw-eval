"""Hidden verifier for CP159 — Unity Guide System Level 5 Unlock.

Tiered grading:
  EASY  checks — basic existence/presence (all agents should pass)
  HARD  checks — structural ordering, placement, guard patterns (strong only)

Hidden (hard) checks account for >= 30% of total weight.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    """Grade the implementation of GUIDE_108 - Level 5 stash unlock guide."""

    base = ws / "game-project"
    scripts = base / "Assets" / "Scripts"
    configs = base / "Assets" / "Configs"

    # ─────────────────────────────────────────────────────────────────────────
    # EASY TIER — basic presence/existence checks (all agents should pass)
    # ─────────────────────────────────────────────────────────────────────────

    easy = {k: 0.0 for k in [
        "easy_config_exists",
        "easy_level5_trigger_exists",
        "easy_register_target_exists",
        "easy_cost_override_exists",
        "easy_finish_guide_exists",
        "easy_locale_text_exists",
    ]}

    # E1. common_guide.json — GUIDE_108 entry exists with basic fields
    guide_json_path = configs / "common_guide.json"
    guide_108 = None
    if guide_json_path.exists():
        try:
            guide_data = json.loads(_read(guide_json_path))
            for entry in guide_data:
                if entry.get("guideId") == "GUIDE_108":
                    guide_108 = entry
                    break
            if guide_108:
                s = 0.0
                if guide_108.get("fingerEnable") == 1:
                    s += 0.25
                if guide_108.get("maskEnable") is True:
                    s += 0.25
                target_types = guide_108.get("targetTypes", [])
                if 12 in target_types:
                    s += 0.25
                if guide_108.get("clickToFinishType") == 1:
                    s += 0.25
                easy["easy_config_exists"] = s
        except (json.JSONDecodeError, TypeError):
            pass

    # E2. GuideComponent.cs — Level 5 trigger elements exist
    guide_comp_path = None
    for p in scripts.rglob("GuideComponent.cs"):
        guide_comp_path = p
        break
    gc_content = ""
    if guide_comp_path and guide_comp_path.exists():
        gc_content = _read(guide_comp_path)

        has_level5_check = bool(
            re.search(r'LevelIndex\s*\+\s*1\s*==\s*5', gc_content) or
            re.search(r'LevelIndex\s*==\s*4', gc_content)
        )
        has_finished_check = "IsFinished" in gc_content and "GUIDE_108" in gc_content
        has_guiding_id = "GuidingId" in gc_content and "GUIDE_108" in gc_content
        has_trigger = bool(
            re.search(r'Trigger\s*\(\s*GuideTrigger\.LevelStart\s*,\s*"5"\s*\)', gc_content)
        )

        trigger_score = 0.0
        if has_level5_check:
            trigger_score += 0.25
        if has_finished_check:
            trigger_score += 0.25
        if has_guiding_id:
            trigger_score += 0.25
        if has_trigger:
            trigger_score += 0.25
        easy["easy_level5_trigger_exists"] = trigger_score

    # E3. GuideComponent.cs — RegisterTarget with ClickUI and buy button ref
    if gc_content:
        has_register = bool(
            re.search(r'RegisterTarget\s*\(\s*GuideTargetType\.ClickUI', gc_content)
        )
        has_buy_btn_ref = bool(
            re.search(r'GetBuyStash', gc_content) or
            re.search(r'buyBtn|buyButton|stashBtn|BuyStash', gc_content, re.IGNORECASE)
        )
        register_score = 0.0
        if has_register:
            register_score += 0.6
        if has_buy_btn_ref:
            register_score += 0.4
        easy["easy_register_target_exists"] = register_score

    # E4. BoardController.cs — cost override presence
    board_ctrl_path = None
    for p in scripts.rglob("BoardController.cs"):
        board_ctrl_path = p
        break
    bc_content = ""
    if board_ctrl_path and board_ctrl_path.exists():
        bc_content = _read(board_ctrl_path)

        has_guide_check = "GUIDE_108" in bc_content
        has_cost_zero = bool(
            re.search(r'cost\s*=\s*0', bc_content) or
            re.search(r'return\s+0', bc_content)
        )
        has_get_cur_guide = "GetCurGuideId" in bc_content

        cost_score = 0.0
        if has_guide_check:
            cost_score += 0.4
        if has_cost_zero and has_guide_check:
            cost_score += 0.35
        if has_get_cur_guide:
            cost_score += 0.25
        easy["easy_cost_override_exists"] = min(cost_score, 1.0)

    # E5. BoardController.cs — FinishCurrent presence
    if bc_content:
        has_finish = "FinishCurrent" in bc_content
        has_finish_click_ui = bool(
            re.search(r'FinishCurrent\s*\(\s*GuideTargetType\.ClickUI', bc_content)
        )
        finish_basic = 0.0
        if has_finish:
            finish_basic += 0.4
        if has_finish_click_ui:
            finish_basic += 0.6
        easy["easy_finish_guide_exists"] = finish_basic

    # E6. locale_zh.json — Guide_108 text exists
    locale_path = configs / "locale_zh.json"
    if locale_path.exists():
        try:
            locale_data = json.loads(_read(locale_path))
            if "Guide_108" in locale_data:
                text = locale_data["Guide_108"]
                if len(text) > 2:
                    easy["easy_locale_text_exists"] = 1.0
                else:
                    easy["easy_locale_text_exists"] = 0.5
        except (json.JSONDecodeError, TypeError):
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # HARD TIER — structural ordering, placement, deep correctness (hidden)
    # Only strong agents pass these.
    # ─────────────────────────────────────────────────────────────────────────

    hard = {k: 0.0 for k in [
        "hard_code_placement_between_sections",
        "hard_return_after_trigger",
        "hard_register_before_trigger_order",
        "hard_combined_if_condition",
        "hard_cost_override_placement",
        "hard_finish_after_unlock",
        "hard_guarded_finish",
        "hard_config_deep_fields",
    ]}

    # H1. Code placement: Level 5 block between Level 3 (GUIDE_107) and Level 2 (GUIDE_105)
    if gc_content:
        level3_pos = gc_content.find("GUIDE_107")
        level2_legacy_pos = gc_content.find("GUIDE_105")
        level5_pos = gc_content.find("GUIDE_108")

        if level5_pos != -1:
            if level3_pos != -1 and level2_legacy_pos != -1:
                if level3_pos < level5_pos < level2_legacy_pos:
                    hard["hard_code_placement_between_sections"] = 1.0
                elif level3_pos < level5_pos:
                    hard["hard_code_placement_between_sections"] = 0.4
            elif level3_pos != -1 and level5_pos > level3_pos:
                hard["hard_code_placement_between_sections"] = 0.4

    # H2. Early return after Trigger call to prevent fallthrough
    # The return must be within ~3 lines (120 chars) of the Trigger call - same block
    if gc_content:
        level5_pos = gc_content.find("GUIDE_108")
        if level5_pos != -1:
            level5_context = gc_content[level5_pos:level5_pos + 400]
            trigger_m = re.search(r'Trigger\s*\([^)]*"5"[^)]*\)\s*;', level5_context)
            if trigger_m:
                # Check for return; within 120 chars after the Trigger statement
                after_trigger = level5_context[trigger_m.end():trigger_m.end() + 120]
                has_return_after_trigger = bool(re.search(r'return\s*;', after_trigger))
                if has_return_after_trigger:
                    hard["hard_return_after_trigger"] = 1.0

    # H3. RegisterTarget must come BEFORE Trigger and GuidingId before Trigger
    if gc_content:
        level5_pos = gc_content.find("GUIDE_108")
        if level5_pos != -1:
            level5_ctx = gc_content[level5_pos:level5_pos + 600]
            register_pos_in_ctx = level5_ctx.find("RegisterTarget")
            guiding_id_pos = level5_ctx.find("GuidingId")
            trigger_pos_in_ctx = -1
            m = re.search(r'Trigger\s*\([^)]*"5"[^)]*\)', level5_ctx)
            if m:
                trigger_pos_in_ctx = m.start()

            order_score = 0.0
            # RegisterTarget before Trigger
            if register_pos_in_ctx != -1 and trigger_pos_in_ctx != -1:
                if register_pos_in_ctx < trigger_pos_in_ctx:
                    order_score += 0.5
            # GuidingId before Trigger
            if guiding_id_pos != -1 and trigger_pos_in_ctx != -1:
                if guiding_id_pos < trigger_pos_in_ctx:
                    order_score += 0.5
            hard["hard_register_before_trigger_order"] = order_score

    # H4. IsFinished check in SAME if-condition as LevelIndex (not nested)
    if gc_content:
        level5_pos = gc_content.find("GUIDE_108")
        if level5_pos != -1:
            level5_if_ctx = gc_content[max(0, level5_pos - 150):level5_pos + 250]
            combined_if_check = bool(re.search(
                r'if\s*\(.*?LevelIndex.*?&&.*?IsFinished|'
                r'if\s*\(.*?IsFinished.*?&&.*?LevelIndex',
                level5_if_ctx
            ))
            if combined_if_check:
                hard["hard_combined_if_condition"] = 1.0

    # H5. Cost override placement: must be AFTER GetStashRowCost but BEFORE _playerCoins deduction
    if bc_content:
        cost_override_pos = -1
        for m in re.finditer(r'cost\s*=\s*0', bc_content):
            nearby = bc_content[max(0, m.start() - 200):m.end() + 200]
            if "GUIDE_108" in nearby or "GetCurGuideId" in nearby:
                cost_override_pos = m.start()
                break

        get_cost_pos = bc_content.find("GetStashRowCost")
        deduct_pos = bc_content.find("_playerCoins -=")
        if deduct_pos == -1:
            deduct_pos = bc_content.find("_playerCoins-=")

        if cost_override_pos != -1 and get_cost_pos != -1 and deduct_pos != -1:
            if get_cost_pos < cost_override_pos < deduct_pos:
                hard["hard_cost_override_placement"] = 1.0
            elif cost_override_pos < deduct_pos:
                hard["hard_cost_override_placement"] = 0.3

    # H6. FinishCurrent must be AFTER the row unlock (UnlockedStashRows++)
    if bc_content:
        finish_pos = -1
        for m in re.finditer(r'FinishCurrent', bc_content):
            finish_pos = m.start()
            break
        unlock_pos = bc_content.find("UnlockedStashRows++")
        if unlock_pos == -1:
            unlock_pos = bc_content.find("UnlockedStashRows +=")

        if finish_pos != -1 and unlock_pos != -1 and finish_pos > unlock_pos:
            hard["hard_finish_after_unlock"] = 1.0

    # H7. Guard check (GetCurGuideId == "GUIDE_108") immediately wrapping FinishCurrent
    if bc_content:
        has_guarded_finish = bool(re.search(
            r'if\s*\([^)]*GetCurGuideId\s*\(\s*\)\s*==\s*"GUIDE_108"[^)]*\)\s*\n?\s*'
            r'((\{[^}]*)?FinishCurrent|\s*guideMod\s*\.\s*FinishCurrent)',
            bc_content
        ))
        if has_guarded_finish:
            hard["hard_guarded_finish"] = 1.0

    # H8. Deep config fields: maskColor=0.5, maskShape=1 (not in prompt, must infer from pattern)
    if guide_108:
        deep_cfg = 0.0
        if guide_108.get("maskColor") == 0.5:
            deep_cfg += 0.5
        if guide_108.get("maskShape") == 1:
            deep_cfg += 0.5
        hard["hard_config_deep_fields"] = deep_cfg

    # ─────────────────────────────────────────────────────────────────────────
    # WEIGHTS — easy ~65%, hard ~35% (hidden >= 30%)
    # ─────────────────────────────────────────────────────────────────────────

    easy_weights = {
        "easy_config_exists": 0.09,
        "easy_level5_trigger_exists": 0.14,
        "easy_register_target_exists": 0.09,
        "easy_cost_override_exists": 0.11,
        "easy_finish_guide_exists": 0.09,
        "easy_locale_text_exists": 0.06,
    }
    # Easy total = 0.58

    hard_weights = {
        "hard_code_placement_between_sections": 0.06,
        "hard_return_after_trigger": 0.06,
        "hard_register_before_trigger_order": 0.06,
        "hard_combined_if_condition": 0.04,
        "hard_cost_override_placement": 0.07,
        "hard_finish_after_unlock": 0.05,
        "hard_guarded_finish": 0.05,
        "hard_config_deep_fields": 0.03,
    }
    # Hard total = 0.42 (hidden, >= 30%)

    # Compute overall
    overall = 0.0
    for k, w in easy_weights.items():
        overall += w * easy[k]
    for k, w in hard_weights.items():
        overall += w * hard[k]

    components = {}
    components.update(easy)
    components.update(hard)
    all_weights = {}
    all_weights.update(easy_weights)
    all_weights.update(hard_weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": all_weights,
        "tier_totals": {
            "easy_weight": sum(easy_weights.values()),
            "hard_weight": sum(hard_weights.values()),
        },
    }


def main():
    # grade_workspace expects ws such that ws / "game-project" / "Assets" / ... exists.
    # In sandbox: files land at /workspace/fixtures/game-project/...
    # Agent may also copy/move to /workspace/game-project/...
    for candidate in [
        Path("/workspace/fixtures"),
        Path("/workspace"),
    ]:
        if (candidate / "game-project" / "Assets").exists():
            print(json.dumps(grade_workspace(candidate), ensure_ascii=False))
            return
    # Fallback: grade anyway (will score 0)
    print(json.dumps(grade_workspace(Path("/workspace/fixtures")), ensure_ascii=False))


if __name__ == "__main__":
    main()
