"""Hidden verifier for CP179 — GDScript Path-Follow + Timeline Trigger."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(ws: Path, filename: str) -> Path | None:
    """Search for file in expected locations."""
    # Primary: /workspace/fixtures/scripts/birthday/
    primary = ws / "fixtures" / "scripts" / "birthday" / filename
    if primary.exists():
        return primary
    # Fallback: /workspace/scripts/birthday/
    fallback = ws / "scripts" / "birthday" / filename
    if fallback.exists():
        return fallback
    # Deep search
    for p in ws.rglob(filename):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    level_file = _find_file(ws, "Level_BirthdaySurprise.gd")
    timeline_file = _find_file(ws, "TimelineController.gd")

    components = {k: 0.0 for k in [
        "dog_export_speed",
        "dog_node_reference",
        "dog_process_movement",
        "dog_step5_trigger",
        "dog_animation_continues",
        "timeline_step5_time_36",
        "timeline_subsequent_shifted",
    ]}

    level_content = _read(level_file) if level_file else ""
    timeline_content = _read(timeline_file) if timeline_file else ""

    # --- Level_BirthdaySurprise.gd checks ---

    # 1. Dog speed as @export variable with default ~80
    export_speed_pattern = re.compile(
        r'@export\s+var\s+\w*dog\w*speed\w*\s*[:=].*?(\d+(?:\.\d+)?)',
        re.IGNORECASE
    )
    match = export_speed_pattern.search(level_content)
    if match:
        try:
            speed_val = float(match.group(1))
            # Must be 80 or close to it
            if 75.0 <= speed_val <= 85.0:
                components["dog_export_speed"] = 1.0
            else:
                components["dog_export_speed"] = 0.5  # Has export but wrong default
        except ValueError:
            components["dog_export_speed"] = 0.3
    elif "@export" in level_content and "dog" in level_content.lower() and "speed" in level_content.lower():
        components["dog_export_speed"] = 0.4  # Has export and mentions dog speed but pattern didn't match

    # 2. Node reference for dog path (PathFollow2D or Path2D reference)
    dog_ref_patterns = [
        r'@onready\s+var\s+\w*dog\w*\s*[:=].*?\$.*(?:Dog|dog)',
        r'@onready\s+var\s+\w*dog\w*follow\w*\s*[:=].*?\$',
        r'@onready\s+var\s+\w*dog\w*path\w*\s*[:=].*?\$',
    ]
    for pattern in dog_ref_patterns:
        if re.search(pattern, level_content, re.IGNORECASE):
            components["dog_node_reference"] = 1.0
            break
    if components["dog_node_reference"] == 0.0:
        # Check for any dog-related @onready var
        if re.search(r'@onready\s+var\s+\w*dog\w*', level_content, re.IGNORECASE):
            components["dog_node_reference"] = 0.6

    # 3. Path movement logic in _process using progress_ratio for DOG specifically
    has_dog_moving_var = re.search(r'\w*dog\w*mov\w*', level_content, re.IGNORECASE) is not None
    has_dog_speed_usage = re.search(
        r'\w*dog\w*speed\w*\s*\*\s*delta', level_content, re.IGNORECASE
    ) is not None
    # Check for dog-specific progress_ratio usage (not just cat)
    has_dog_progress = re.search(
        r'dog\w*(?:follow|path)\w*\.progress_ratio', level_content, re.IGNORECASE
    ) is not None

    process_score = 0.0
    if has_dog_moving_var:
        process_score += 0.3
    if has_dog_speed_usage:
        process_score += 0.4
    if has_dog_progress:
        process_score += 0.3
    components["dog_process_movement"] = min(1.0, process_score)

    # 4. Dog triggered at step 5 in _on_performance_step
    step5_pattern = re.compile(
        r'(?:match\s+step|_on_performance_step).*?5\s*:.*?dog',
        re.DOTALL | re.IGNORECASE
    )
    # Also check simpler patterns
    has_step5_section = re.search(r'5\s*:', level_content) is not None
    has_dog_in_step_handler = False
    # Look for dog-related code near step 5
    lines = level_content.split('\n')
    in_step5 = False
    step5_dog_found = False
    for line in lines:
        stripped = line.strip()
        if stripped == '5:' or stripped.startswith('5:'):
            in_step5 = True
            continue
        if in_step5:
            if re.match(r'^\d+:', stripped) or (stripped and not stripped.startswith('#') and not stripped.startswith('\t') and not stripped.startswith(' ')):
                # New step or non-indented code
                if re.match(r'^\d+:', stripped):
                    in_step5 = False
            if 'dog' in stripped.lower():
                step5_dog_found = True
                break

    if step5_dog_found:
        components["dog_step5_trigger"] = 1.0
    elif has_step5_section and 'dog' in level_content.lower():
        # Has step 5 and mentions dog somewhere - partial credit
        components["dog_step5_trigger"] = 0.4

    # 5. Animation continues after path end (dog keeps playing after stopping)
    # The dog must: (a) have a movement stop condition and (b) NOT stop animation
    # Look for dog-specific stop logic that preserves animation
    has_stop_but_animate = False

    # Check that dog movement stops (dog_moving = false) while animation persists
    has_dog_stop = re.search(r'dog\w*mov\w*\s*=\s*false', level_content, re.IGNORECASE) is not None

    # Check for animation play in the dog spawn/trigger function
    # Look for dog-related play() call (not cat play calls)
    has_dog_play = re.search(
        r'(?:dog|Dog).*?\.play\(\)', level_content, re.DOTALL
    ) is not None
    if not has_dog_play:
        # Alternative: look for play() near dog-related variable usage
        has_dog_play = re.search(
            r'_(?:spawn|start|trigger)_dog.*?play\(\)', level_content, re.DOTALL | re.IGNORECASE
        ) is not None

    # The key insight: when dog reaches end, movement stops but no .stop() on sprite
    has_no_anim_stop = "dog" in level_content.lower() and not re.search(
        r'dog.*?(?:sprite|anim).*?\.stop\(\)', level_content, re.DOTALL | re.IGNORECASE
    )

    if has_dog_stop and has_dog_play and has_no_anim_stop:
        has_stop_but_animate = True
    elif has_dog_stop and has_no_anim_stop:
        has_stop_but_animate = True  # Implicit: animation not stopped = continues

    components["dog_animation_continues"] = 1.0 if has_stop_but_animate else 0.0

    # --- TimelineController.gd checks ---

    # 6. Step 5 time changed to 36.0 seconds
    step5_time_match = re.search(
        r'"time"\s*:\s*(\d+(?:\.\d+)?)\s*,\s*"step"\s*:\s*5',
        timeline_content
    )
    if step5_time_match:
        try:
            time_val = float(step5_time_match.group(1))
            if 35.0 <= time_val <= 37.0:  # Allow small rounding
                components["timeline_step5_time_36"] = 1.0
            elif time_val > 7.0:  # At least changed from original
                components["timeline_step5_time_36"] = 0.4
        except ValueError:
            pass

    # 7. Subsequent steps (6-10) shifted by approximately +36s from their original times
    # Original times: step6=9, step7=10, step8=11, step9=16, step10=20
    # Expected: step6=45, step7=46, step8=47, step9=52, step10=56
    original_times = {6: 9.0, 7: 10.0, 8: 11.0, 9: 16.0, 10: 20.0}
    shifted_count = 0
    total_checks = len(original_times)

    for step_num, orig_time in original_times.items():
        pattern = re.compile(
            rf'"time"\s*:\s*(\d+(?:\.\d+)?)\s*,\s*"step"\s*:\s*{step_num}'
        )
        match = pattern.search(timeline_content)
        if match:
            try:
                new_time = float(match.group(1))
                expected_shifted = orig_time + 29.0  # 36 - 7 = 29 offset from original step5 time
                # The shift should be: new_step5_time - old_step5_time = 36 - 7 = 29
                # So each subsequent step should be at: original_time + 29
                # Allow some tolerance
                if abs(new_time - expected_shifted) <= 2.0:
                    shifted_count += 1
                elif new_time > orig_time + 10.0:
                    # At least significantly increased
                    shifted_count += 0.5
            except ValueError:
                pass

    components["timeline_subsequent_shifted"] = round(shifted_count / total_checks, 4)

    weights = {
        "dog_export_speed": 0.15,
        "dog_node_reference": 0.15,
        "dog_process_movement": 0.20,
        "dog_step5_trigger": 0.20,
        "dog_animation_continues": 0.10,
        "timeline_step5_time_36": 0.10,
        "timeline_subsequent_shifted": 0.10,
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
