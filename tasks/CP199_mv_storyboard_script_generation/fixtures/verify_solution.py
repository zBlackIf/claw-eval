"""Hidden verifier for CP199 — MV Storyboard Script Generation.

Tiered scoring:
  - EASY tier (basic checks): Any competent model passes these (~40% weight).
  - HARD tier (hidden discriminating checks): Only strong models pass (~35% weight).
    These require precise cross-referencing, temporal coherence, and creative depth.
  - MEDIUM tier (structure checks): ~25% weight.

Hidden checks account for >= 30% of the total score.
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


def _find_storyboard(ws: Path) -> str:
    """Find and read the storyboard file."""
    candidates = [
        ws / "fixtures" / "mv_project" / "STORYBOARD.md",
        ws / "mv_project" / "STORYBOARD.md",
        ws / "STORYBOARD.md",
    ]
    for c in candidates:
        if c.exists():
            return _read(c)
    for f in ws.rglob("STORYBOARD.md"):
        return _read(f)
    for f in ws.rglob("storyboard.md"):
        return _read(f)
    return ""


def _extract_scene_blocks(content: str) -> list[str]:
    """Extract individual scene blocks from the storyboard."""
    parts = re.split(r"(?i)###?\s*(?:scene|shot)\s*#?\s*\d+", content)
    if len(parts) <= 1:
        parts = re.split(r"(?m)^###?\s*\d+[\.\):\s]", content)
    return parts[1:] if len(parts) > 1 else []


def _extract_scene_durations(scene_blocks: list[str]) -> list[int]:
    """Extract duration value from each scene block."""
    durations = []
    for block in scene_blocks:
        match = re.search(r"(\d+)\s*(?:s|sec|seconds?|秒)\b", block)
        durations.append(int(match.group(1)) if match else 0)
    return durations


def grade_workspace(ws: Path) -> dict:
    content = _find_storyboard(ws)
    components = {k: 0.0 for k in [
        # --- EASY TIER (basic, all models pass) ---
        "has_metadata_section",
        "scene_count_sufficient",
        "has_technical_notes",
        "narrative_arc_present",
        "follows_song_structure",
        # --- MEDIUM TIER (structure checks) ---
        "scene_structure_complete",
        "duration_sums_correctly",
        # --- HARD TIER (hidden discriminating, only strong pass) ---
        "lyrics_precise_placement",
        "duration_per_section_balance",
        "camera_technique_variety",
        "emotional_arc_progression",
        "cross_section_continuity",
    ]}

    if not content:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "STORYBOARD.md not found or empty",
        }

    content_lower = content.lower()

    # =========================================================================
    # EASY TIER — Surface-level checks (any model passes)
    # =========================================================================

    # 1. METADATA section exists
    metadata_match = re.search(r"(?i)##?\s*METADATA(.*?)(?=##|\Z)", content, re.DOTALL)
    if metadata_match:
        meta_text = metadata_match.group(1).strip()
        has_title = any(k in meta_text.lower() for k in ["title", "song", "project", "listen to my baby"])
        has_duration = any(k in meta_text.lower() for k in ["duration", "length", "time", "60"])
        has_style = any(k in meta_text.lower() for k in ["style", "genre", "mood", "watercolor", "2d"])
        meta_score = sum([has_title, has_duration, has_style]) / 3.0
        components["has_metadata_section"] = round(min(1.0, meta_score + (0.3 if len(meta_text) > 50 else 0.0)), 4)

    # 2. Scene count
    scene_headers = re.findall(r"(?i)###?\s*(?:scene|shot)\s*#?\s*(\d+)", content)
    scene_count = len(scene_headers)
    if scene_count == 0:
        scene_headers = re.findall(r"(?m)^#{1,4}\s*\d+[\.\):]", content)
        scene_count = len(scene_headers)

    if scene_count >= 8:
        components["scene_count_sufficient"] = 1.0
    elif scene_count >= 6:
        components["scene_count_sufficient"] = 0.6
    elif scene_count >= 4:
        components["scene_count_sufficient"] = 0.3

    # 3. Technical notes section
    tech_match = re.search(r"(?i)##?\s*TECHNICAL\s*NOTES?(.*?)(?=##|\Z)", content, re.DOTALL)
    if tech_match:
        tech_text = tech_match.group(1).strip()
        has_resolution = any(k in tech_text.lower() for k in ["16:9", "resolution", "aspect", "1920", "1080"])
        has_color = any(k in tech_text.lower() for k in ["color", "palette", "tone", "warm", "golden"])
        has_style_ref = any(k in tech_text.lower() for k in ["watercolor", "2d", "illustrated", "animation", "style"])
        has_transition = any(k in tech_text.lower() for k in ["transition", "fade", "cut", "dissolve"])
        tech_score = sum([has_resolution, has_color, has_style_ref, has_transition]) / 3.0
        components["has_technical_notes"] = round(min(1.0, tech_score + (0.2 if len(tech_text) > 80 else 0.0)), 4)

    # 4. Narrative arc (basic keyword presence)
    narrative_keywords = {
        "baby_stage": ["baby", "infant", "sleeping", "newborn", "crib"],
        "toddler_stage": ["first step", "walk", "crawl", "toddler", "learn"],
        "childhood_stage": ["play", "park", "kite", "school", "teach"],
        "growing_stage": ["grow", "teen", "support", "behind"],
        "present_stage": ["together", "duet", "sing together", "grown", "adult"],
    }
    stages_found = sum(1 for keywords in narrative_keywords.values()
                       if any(kw in content_lower for kw in keywords))
    components["narrative_arc_present"] = round(min(1.0, stages_found / 4.0), 4)

    # 5. Follows song structure (basic keyword check)
    song_parts_found = sum(1 for kw in ["verse", "chorus", "bridge", "duet", "harmony"]
                          if kw in content_lower)
    lyric_refs = ["listen to my baby", "morning when you wake", "feeling scared",
                  "years will pass", "promise you"]
    lyrics_found = sum(1 for lr in lyric_refs if lr in content_lower)
    structure_score = min(1.0, (song_parts_found / 3.0) * 0.5 + (lyrics_found / 3.0) * 0.5)
    components["follows_song_structure"] = round(structure_score, 4)

    # =========================================================================
    # MEDIUM TIER — Structure checks (moderate difficulty)
    # =========================================================================

    # 6. Scene structure completeness
    scene_blocks = _extract_scene_blocks(content)
    complete_scenes = 0
    for block in scene_blocks:
        has_visual = False
        has_audio = False
        has_duration = bool(re.search(r"\d+\s*(?:s|sec|seconds?|秒)", block))
        has_camera = False
        for line in block.split("\n"):
            if re.search(r"(?i)(?:visual|image|画面|描述)", line):
                after = re.split(r"[:\-]\s*", line, maxsplit=1)
                if len(after) > 1 and len(after[1].strip()) >= 15:
                    has_visual = True
            if re.search(r"(?i)(?:audio|lyric|歌词|音频|lyrics?)", line):
                after = re.split(r"[:\-]\s*", line, maxsplit=1)
                if len(after) > 1 and len(after[1].strip()) >= 5:
                    has_audio = True
            if re.search(r"(?i)(?:camera|transition|movement|镜头)", line):
                after = re.split(r"[:\-]\s*", line, maxsplit=1)
                if len(after) > 1 and len(after[1].strip()) >= 5:
                    has_camera = True
        if sum([has_visual, has_audio, has_duration, has_camera]) >= 3:
            complete_scenes += 1
    if scene_count > 0:
        components["scene_structure_complete"] = round(min(1.0, complete_scenes / max(scene_count, 1)), 4)

    # 7. Duration sums to approximately 60 seconds
    scenes_section = content
    scenes_start = re.search(r"(?i)##?\s*SCENES?", content)
    tech_start = re.search(r"(?i)##?\s*TECHNICAL", content)
    if scenes_start:
        scenes_section = content[scenes_start.start():tech_start.start() if tech_start else len(content)]
    durations = re.findall(r"(\d+)\s*(?:s|sec|seconds?|秒)\b", scenes_section)
    total_duration = 0
    if durations:
        total_duration = sum(int(d) for d in durations)
        if 55 <= total_duration <= 65:
            components["duration_sums_correctly"] = 1.0
        elif 50 <= total_duration <= 70:
            components["duration_sums_correctly"] = 0.6
        elif 40 <= total_duration <= 80:
            components["duration_sums_correctly"] = 0.3
        else:
            components["duration_sums_correctly"] = 0.1

    # =========================================================================
    # HARD TIER — Hidden discriminating checks (only strong models pass)
    # These require precise cross-referencing of brief details, not just
    # keyword inclusion.
    # =========================================================================

    # 8. LYRICS PRECISE PLACEMENT (HARD)
    # Strong models place the EXACT lyrics from each section into the
    # CORRECT corresponding scene positions. Weak models either omit lyrics,
    # paraphrase them, or place them in wrong sections.
    # We check that specific lyrics appear WITHIN the correct scene block
    # (not just anywhere in the document).

    verse1_lyrics = ["morning when you wake", "world inside your eyes",
                     "little hand", "reach the skies"]
    chorus_lyrics = ["listen to my baby", "every word you say", "each and every day"]
    verse2_lyrics = ["feeling scared", "voice is like a lullaby", "night into the day"]
    bridge_lyrics = ["years will pass", "promise you", "road may lead",
                     "heart will always find"]

    lyrics_placement_score = 0.0
    if len(scene_blocks) >= 6:
        # Map: which scene block indices correspond to which song section?
        # Expected: scenes 1-2 = verse1, scenes 3-4 = chorus, scenes 5-6 = verse2,
        # scene 7 = bridge, scene 8 = final chorus
        # But we allow flexibility: just check relative ordering within blocks.

        def _lyrics_in_block_range(blocks: list[str], start: int, end: int,
                                   phrases: list[str]) -> int:
            """Count how many phrases appear in blocks[start:end]."""
            region = " ".join(blocks[start:end]).lower()
            return sum(1 for p in phrases if p in region)

        n = len(scene_blocks)
        # Divide into rough quarters
        q1_end = max(n // 4, 2)
        q2_end = max(n // 2, 4)
        q3_end = max(3 * n // 4, 6)

        v1_in_q1 = _lyrics_in_block_range(scene_blocks, 0, q1_end, verse1_lyrics)
        ch_in_q2 = _lyrics_in_block_range(scene_blocks, q1_end, q2_end, chorus_lyrics)
        v2_in_q3 = _lyrics_in_block_range(scene_blocks, q2_end, q3_end, verse2_lyrics)
        br_in_q4 = _lyrics_in_block_range(scene_blocks, q3_end, n, bridge_lyrics)

        # Also check that lyrics do NOT appear in wrong sections (penalty)
        v1_wrong = _lyrics_in_block_range(scene_blocks, q2_end, n, verse1_lyrics)
        v2_wrong = _lyrics_in_block_range(scene_blocks, 0, q2_end, verse2_lyrics)

        correct_placements = v1_in_q1 + ch_in_q2 + v2_in_q3 + br_in_q4
        wrong_placements = v1_wrong + v2_wrong
        max_possible = len(verse1_lyrics) + len(chorus_lyrics) + len(verse2_lyrics) + len(bridge_lyrics)

        placement_ratio = correct_placements / max_possible
        penalty = min(0.3, wrong_placements * 0.1)
        lyrics_placement_score = max(0.0, placement_ratio - penalty)

        # Bonus: if ALL four sections have at least one correct placement
        if v1_in_q1 >= 1 and ch_in_q2 >= 1 and v2_in_q3 >= 1 and br_in_q4 >= 1:
            lyrics_placement_score = min(1.0, lyrics_placement_score + 0.15)
    elif len(scene_blocks) >= 3:
        # Partial credit: check if any lyrics appear at all in correct halves
        all_text = " ".join(scene_blocks).lower()
        total_present = sum(1 for p in verse1_lyrics + chorus_lyrics + verse2_lyrics + bridge_lyrics
                           if p in all_text)
        lyrics_placement_score = min(0.3, total_present * 0.05)

    components["lyrics_precise_placement"] = round(min(1.0, lyrics_placement_score), 4)

    # 9. DURATION PER-SECTION BALANCE (HARD)
    # The brief implies ~60s total across 8+ scenes following the song structure.
    # Strong models will distribute time proportionally: chorus scenes get more
    # screen time than transitional scenes, and no single scene dominates.
    # Weak models either give equal time to all scenes or have wildly uneven
    # distributions (e.g., one scene at 20s and others at 3s).

    scene_durations = _extract_scene_durations(scene_blocks)
    duration_balance_score = 0.0

    valid_durations = [d for d in scene_durations if d > 0]
    if len(valid_durations) >= 6:
        # Check 1: No scene too long (> 12s) or too short (< 4s)
        reasonable_range = sum(1 for d in valid_durations if 4 <= d <= 12)
        range_ratio = reasonable_range / len(valid_durations)

        # Check 2: Standard deviation should be moderate (not all same, not wildly varied)
        mean_dur = sum(valid_durations) / len(valid_durations)
        variance = sum((d - mean_dur) ** 2 for d in valid_durations) / len(valid_durations)
        std_dev = variance ** 0.5
        # Ideal std_dev for 8 scenes of 6-9s each is ~1.5-3.0
        # Too low (<0.5) = all same length (lazy), too high (>4) = unbalanced
        std_score = 0.0
        if 1.0 <= std_dev <= 3.5:
            std_score = 1.0
        elif 0.5 <= std_dev <= 5.0:
            std_score = 0.5
        elif std_dev < 0.5:
            std_score = 0.2  # all same length = lazy
        else:
            std_score = 0.2  # too varied

        # Check 3: Chorus/climax scenes should be slightly longer than verse scenes
        # This requires the model to understand that emotional peaks need more time.
        pacing_bonus = 0.0
        if len(scene_blocks) >= 8:
            # Compare duration of middle scenes (chorus area) vs early scenes (verse)
            early_avg = sum(valid_durations[:3]) / 3 if len(valid_durations) >= 3 else 0
            mid_avg = sum(valid_durations[2:5]) / 3 if len(valid_durations) >= 5 else 0
            late_avg = sum(valid_durations[-2:]) / 2 if len(valid_durations) >= 2 else 0
            # Climax/chorus/finale should be >= verse duration
            if mid_avg >= early_avg and late_avg >= early_avg:
                pacing_bonus = 0.2
            elif mid_avg >= early_avg or late_avg >= early_avg:
                pacing_bonus = 0.1

        duration_balance_score = range_ratio * 0.4 + std_score * 0.4 + pacing_bonus
    elif len(valid_durations) >= 3:
        duration_balance_score = 0.2

    components["duration_per_section_balance"] = round(min(1.0, duration_balance_score), 4)

    # 10. CAMERA TECHNIQUE VARIETY (HARD)
    # A strong storyboard uses DIVERSE and SCENE-APPROPRIATE camera techniques.
    # Weak models repeat the same technique (e.g., "slow zoom" for every scene)
    # or use generic descriptions. Strong models vary between:
    # - Static/close-up for intimate moments
    # - Pan/tilt for environmental shots
    # - Zoom for emotional emphasis
    # - Tracking for movement scenes
    # - Wide/establishing for context
    # - Transition types between scenes (dissolve, cut, fade)

    camera_techniques = {
        "close_up": ["close-up", "close up", "closeup", "特写", "近景"],
        "pan": ["pan left", "pan right", "pan ", "panning", "横移", "摇"],
        "zoom": ["zoom in", "zoom out", "zooming", "推", "拉"],
        "tracking": ["tracking", "follow", "dolly", "跟拍", "移动"],
        "wide": ["wide shot", "wide angle", "establishing", "全景", "远景"],
        "tilt": ["tilt up", "tilt down", "tilting", "俯", "仰"],
        "static": ["static", "fixed", "still", "hold", "定格", "固定"],
        "dissolve": ["dissolve", "cross-dissolve", "溶解"],
        "fade": ["fade in", "fade out", "fade to", "淡入", "淡出"],
        "cut": ["hard cut", "jump cut", "match cut", "切"],
    }

    camera_variety_score = 0.0
    if len(scene_blocks) >= 4:
        techniques_used = set()
        scenes_with_specific_camera = 0
        per_scene_techniques: list[set] = []

        for block in scene_blocks:
            block_lower = block.lower()
            block_techs = set()
            for tech_name, keywords in camera_techniques.items():
                if any(kw in block_lower for kw in keywords):
                    techniques_used.add(tech_name)
                    block_techs.add(tech_name)
            if block_techs:
                scenes_with_specific_camera += 1
            per_scene_techniques.append(block_techs)

        # Variety: how many different techniques used across ALL scenes
        variety_ratio = min(1.0, len(techniques_used) / 5.0)  # Expect at least 5 different

        # Coverage: what fraction of scenes have specific camera directions
        coverage_ratio = scenes_with_specific_camera / max(len(scene_blocks), 1)

        # Non-repetition: penalize if the SAME technique is used in > 60% of scenes
        repetition_penalty = 0.0
        if len(scene_blocks) >= 4:
            for tech_name in techniques_used:
                count = sum(1 for st in per_scene_techniques if tech_name in st)
                if count / len(scene_blocks) > 0.6:
                    repetition_penalty = 0.2
                    break

        camera_variety_score = (variety_ratio * 0.45 + coverage_ratio * 0.35) - repetition_penalty
        camera_variety_score = max(0.0, camera_variety_score)

        # Bonus: scene-appropriate camera (intimate scenes use close-up, action uses tracking)
        appropriateness_bonus = 0.0
        for i, block in enumerate(scene_blocks):
            bl = block.lower()
            # Intimate/emotional scenes should have close-up or static
            if any(w in bl for w in ["sleeping", "holds", "embrace", "tears", "whisper", "comfort"]):
                if any(kw in bl for kw in camera_techniques["close_up"] + camera_techniques["static"]):
                    appropriateness_bonus += 0.05
            # Movement scenes should have tracking or pan
            if any(w in bl for w in ["running", "walking", "steps", "dancing", "playing"]):
                if any(kw in bl for kw in camera_techniques["tracking"] + camera_techniques["pan"]):
                    appropriateness_bonus += 0.05

        camera_variety_score = min(1.0, camera_variety_score + min(0.2, appropriateness_bonus))

    components["camera_technique_variety"] = round(camera_variety_score, 4)

    # 11. EMOTIONAL ARC PROGRESSION (HARD)
    # Strong models create an emotional trajectory that builds through scenes.
    # The brief implies: tender start -> playful middle -> bittersweet growth ->
    # triumphant reunion. A strong model uses different emotional tones per
    # scene block, showing escalation. Weak models stay flat (same emotional
    # register throughout).

    emotion_tiers = {
        "tender": ["gentle", "tender", "soft", "quiet", "peaceful", "calm",
                   "温柔", "安静", "宁静"],
        "playful": ["playful", "joyful", "laughter", "fun", "bright", "energetic",
                    "bounce", "skip", "cheerful", "欢快", "活泼"],
        "bittersweet": ["bittersweet", "nostalgia", "longing", "wistful",
                        "melancholy", "time passing", "growing apart", "miss",
                        "不舍", "成长", "离别"],
        "triumphant": ["triumphant", "powerful", "soaring", "crescendo", "climax",
                       "reunion", "full circle", "together again", "pride",
                       "高潮", "团聚", "骄傲"],
    }

    emotional_arc_score = 0.0
    if len(scene_blocks) >= 6:
        # Check that different emotional tiers appear in different positions
        n = len(scene_blocks)
        quarter_texts = [
            " ".join(scene_blocks[:n // 4]).lower(),
            " ".join(scene_blocks[n // 4:n // 2]).lower(),
            " ".join(scene_blocks[n // 2:3 * n // 4]).lower(),
            " ".join(scene_blocks[3 * n // 4:]).lower(),
        ]

        # Expected: tender in Q1, playful in Q2, bittersweet in Q3, triumphant in Q4
        expected_emotions = ["tender", "playful", "bittersweet", "triumphant"]
        matches = 0
        for i, expected_tier in enumerate(expected_emotions):
            keywords = emotion_tiers[expected_tier]
            if any(kw in quarter_texts[i] for kw in keywords):
                matches += 1

        # Also check for VARIETY: at least 3 different emotional tiers present overall
        all_scene_text = content_lower
        tiers_present = sum(1 for keywords in emotion_tiers.values()
                           if any(kw in all_scene_text for kw in keywords))

        positional_score = matches / 4.0
        variety_score = min(1.0, tiers_present / 3.0)

        # Check for escalation: visual descriptions get more intense/detailed later
        # (proxy: later scenes have more words in visual descriptions)
        escalation_bonus = 0.0
        if len(scene_blocks) >= 8:
            early_lengths = [len(b) for b in scene_blocks[:3]]
            late_lengths = [len(b) for b in scene_blocks[-3:]]
            if late_lengths and early_lengths:
                avg_early = sum(early_lengths) / len(early_lengths)
                avg_late = sum(late_lengths) / len(late_lengths)
                if avg_late >= avg_early * 1.1:  # Later scenes at least 10% more detailed
                    escalation_bonus = 0.15

        emotional_arc_score = positional_score * 0.5 + variety_score * 0.3 + escalation_bonus
    elif len(scene_blocks) >= 3:
        # Partial: just check variety
        all_text = " ".join(scene_blocks).lower()
        tiers_present = sum(1 for keywords in emotion_tiers.values()
                           if any(kw in all_text for kw in keywords))
        emotional_arc_score = min(0.3, tiers_present * 0.1)

    components["emotional_arc_progression"] = round(min(1.0, emotional_arc_score), 4)

    # 12. CROSS-SECTION CONTINUITY (HARD)
    # Strong models create CONNECTIONS between consecutive scenes — a visual
    # motif that carries through, a prop that reappears, or explicit transition
    # language linking scene N to scene N+1. Weak models treat each scene as
    # an isolated island with no narrative threading.

    continuity_score = 0.0
    if len(scene_blocks) >= 4:
        # Check 1: Explicit transition language between scenes
        transition_phrases = [
            "continues", "same location", "transitions to", "morphs into",
            "dissolves into", "we follow", "time lapse", "later",
            "same frame", "from the previous", "building on",
            "match cut", "following", "as we move", "carries over",
        ]
        scenes_with_transitions = 0
        for block in scene_blocks:
            bl = block.lower()
            if any(tp in bl for tp in transition_phrases):
                scenes_with_transitions += 1

        transition_ratio = scenes_with_transitions / max(len(scene_blocks) - 1, 1)

        # Check 2: Recurring visual motifs (elements that appear in 3+ scenes)
        motif_candidates = [
            "hand", "hands", "sunlight", "window", "music box", "photograph",
            "shadow", "silhouette", "tree", "stars", "moon", "sunrise",
            "piano", "guitar", "microphone", "mirror",
        ]
        recurring_motifs = 0
        for motif in motif_candidates:
            scenes_with_motif = sum(1 for b in scene_blocks if motif in b.lower())
            if scenes_with_motif >= 3:
                recurring_motifs += 1

        motif_score = min(1.0, recurring_motifs / 2.0)

        # Check 3: Color/lighting continuity language
        color_continuity_words = [
            "same warm", "golden light", "consistent", "matching",
            "warm glow", "continues the", "similar tone",
        ]
        has_color_continuity = any(w in content_lower for w in color_continuity_words)

        # Check 4: Bookend structure (first and last scene share visual elements)
        bookend_score = 0.0
        if len(scene_blocks) >= 2:
            first = scene_blocks[0].lower()
            last = scene_blocks[-1].lower()
            shared_elements = 0
            bookend_words = ["crib", "sleeping", "watching", "father",
                            "hand", "together", "close-up", "face"]
            for w in bookend_words:
                if w in first and w in last:
                    shared_elements += 1
            bookend_score = min(1.0, shared_elements / 2.0)

        continuity_score = (
            transition_ratio * 0.3 +
            motif_score * 0.3 +
            (0.15 if has_color_continuity else 0.0) +
            bookend_score * 0.25
        )

    components["cross_section_continuity"] = round(min(1.0, continuity_score), 4)

    # =========================================================================
    # WEIGHTED SCORING
    # Easy tier: ~35% | Medium tier: ~25% | Hard tier (hidden): ~40%
    # Hidden checks >= 30% as required.
    # =========================================================================
    weights = {
        # EASY TIER (35% total)
        "has_metadata_section": 0.05,
        "scene_count_sufficient": 0.08,
        "has_technical_notes": 0.05,
        "narrative_arc_present": 0.09,
        "follows_song_structure": 0.08,
        # MEDIUM TIER (25% total)
        "scene_structure_complete": 0.13,
        "duration_sums_correctly": 0.12,
        # HARD TIER — hidden discriminating (40% total)
        "lyrics_precise_placement": 0.10,
        "duration_per_section_balance": 0.08,
        "camera_technique_variety": 0.08,
        "emotional_arc_progression": 0.07,
        "cross_section_continuity": 0.07,
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
