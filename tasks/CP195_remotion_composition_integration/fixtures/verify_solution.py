"""Hidden verifier for CP195 — Remotion Composition Integration.

Tiered scoring:
  - EASY tier (~55%): basic correctness that any competent agent passes.
  - HARD/HIDDEN tier (~45%): deep Remotion/TypeScript expertise that only
    strong agents demonstrate — discriminates quality of implementation.
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


def _find_file(base: Path, pattern: str) -> Path | None:
    """Find a file matching glob pattern recursively."""
    matches = list(base.rglob(pattern))
    return matches[0] if matches else None


def _collect_all_tsx(src: Path) -> list[Path]:
    """Collect all .tsx/.ts files that might be part of the new composition."""
    existing_names = {"Root.tsx", "Composition.tsx", "index.ts", "index.tsx", "BreakingNewsRundown.tsx"}
    files = []
    if src.exists():
        for f in src.rglob("*.tsx"):
            if f.name not in existing_names:
                files.append(f)
        for f in src.rglob("*.ts"):
            if f.name not in existing_names and f.name != "remotion.config.ts":
                files.append(f)
    return files


def grade_workspace(ws: Path) -> dict:
    project = ws / "remotion-project"
    if not project.exists():
        project = ws
    src = project / "src"

    components = {k: 0.0 for k in [
        # --- EASY TIER: basic correctness (all agents should pass) ---
        "composition_file_created",
        "uses_remotion_apis",
        "has_multiple_sequences",
        "registered_in_root",
        "correct_composition_props",
        "content_from_summary",
        "existing_composition_preserved",
        # --- HARD/HIDDEN TIER: deep expertise (only strong pass) ---
        "h_zod_schema_integration",
        "h_temporal_gap_free",
        "h_spring_animation_correctness",
        "h_sequence_relative_frames",
        "h_composition_architecture",
        "h_remotion_v4_patterns",
    ]}

    # ======================================================================
    # EASY TIER: Basic correctness checks
    # ======================================================================

    # 1. Check if a new composition file exists (AiMoneySummary or similar)
    comp_file = None
    for pattern in ["*AiMoney*.*sx", "*ai*money*.*sx", "*ai_money*.*sx", "*AIMoney*.*sx"]:
        found = _find_file(src, pattern)
        if found:
            comp_file = found
            break
    # Also check for any new .tsx file that isn't the existing ones
    if not comp_file and src.exists():
        existing_names = {"Root.tsx", "Composition.tsx", "index.ts", "index.tsx", "BreakingNewsRundown.tsx"}
        for f in src.rglob("*.tsx"):
            if f.name not in existing_names:
                content = _read(f)
                if "remotion" in content.lower() and ("money" in content.lower() or "ai" in content.lower() or "summary" in content.lower()):
                    comp_file = f
                    break

    if comp_file and comp_file.exists():
        components["composition_file_created"] = 1.0
    else:
        return {
            "overall_score": 0.0,
            "components": {k: round(v, 4) for k, v in components.items()},
            "weights": _weights(),
        }

    comp_content = _read(comp_file)
    # Gather all related new files' content for architecture checks
    all_new_files = _collect_all_tsx(src)
    all_new_content = "\n".join(_read(f) for f in all_new_files)

    # 2. Check Remotion API usage (easy — just use any Remotion imports)
    remotion_apis = ["AbsoluteFill", "Sequence", "useCurrentFrame", "spring", "interpolate"]
    api_count = sum(1 for api in remotion_apis if api in comp_content)
    has_basic = "AbsoluteFill" in comp_content or "Sequence" in comp_content
    if has_basic and api_count >= 2:
        components["uses_remotion_apis"] = 1.0
    elif has_basic:
        components["uses_remotion_apis"] = 0.7
    elif api_count >= 1:
        components["uses_remotion_apis"] = 0.4
    else:
        components["uses_remotion_apis"] = 0.0

    # 3. Check for multiple sequences (easy — at least have some structure)
    sequence_count = comp_content.count("<Sequence")
    from_matches = re.findall(r'from=\{?(\d+)', comp_content)
    unique_froms = len(set(from_matches))
    if sequence_count >= 3 or unique_froms >= 3:
        components["has_multiple_sequences"] = 1.0
    elif sequence_count >= 2 or unique_froms >= 2:
        components["has_multiple_sequences"] = 0.7
    elif sequence_count >= 1:
        components["has_multiple_sequences"] = 0.4
    else:
        components["has_multiple_sequences"] = 0.0

    # 4. Check Root.tsx registration (easy — just import and add Composition)
    root_file = src / "Root.tsx"
    if root_file.exists():
        root_content = _read(root_file)
        has_import = bool(re.search(r'import.*(?:AiMoney|AIMoney|ai.?money)', root_content, re.IGNORECASE))
        has_composition = bool(re.search(r'<Composition[^>]*id=["\']AiMoneySummary["\']', root_content))
        if not has_composition:
            has_composition = bool(re.search(r'<Composition[^>]*id=["\'].*(?:money|Money|ai|AI).*["\']', root_content, re.IGNORECASE))
        if has_import and has_composition:
            components["registered_in_root"] = 1.0
        elif has_import or has_composition:
            components["registered_in_root"] = 0.5
        else:
            components["registered_in_root"] = 0.0
    else:
        components["registered_in_root"] = 0.0

    # 5. Check composition props (easy — standard Remotion Composition attrs)
    if root_file.exists() and components["registered_in_root"] > 0:
        root_content = _read(root_file)
        all_comps = re.findall(r'<Composition[^/]*?/>', root_content, re.DOTALL)
        all_comps += re.findall(r'<Composition[^>]*>', root_content, re.DOTALL)
        new_comp_blocks = [b for b in all_comps
                          if re.search(r'(?:money|Money|ai|AI|Summary)', b, re.IGNORECASE)
                          and "BreakingNews" not in b]
        if new_comp_blocks:
            block = new_comp_blocks[0]
            has_width = bool(re.search(r'width=\{?1920\}?', block))
            has_height = bool(re.search(r'height=\{?1080\}?', block))
            has_fps = bool(re.search(r'fps=\{?30\}?', block))
            has_duration = bool(re.search(r'durationInFrames=\{?\d+\}?', block))
            prop_score = sum([has_width, has_height, has_fps, has_duration]) / 4.0
            components["correct_composition_props"] = prop_score
        else:
            components["correct_composition_props"] = 0.0
    else:
        components["correct_composition_props"] = 0.0

    # 6. Content from summary (easy — reference any keywords from the markdown)
    summary_keywords = [
        "content creation", "automation", "saas", "consulting",
        "freelanc", "money", "2026", "sabrina",
    ]
    keyword_hits = sum(1 for kw in summary_keywords if kw.lower() in all_new_content.lower())
    components["content_from_summary"] = 1.0 if keyword_hits >= 3 else (0.6 if keyword_hits >= 2 else (0.3 if keyword_hits >= 1 else 0.0))

    # 7. Existing composition preserved (easy — don't break what exists)
    if root_file.exists():
        root_content = _read(root_file)
        has_old_import = "BreakingNewsRundown" in root_content
        has_old_composition = bool(re.search(r'<Composition[^>]*id=["\']BreakingNewsRundown["\']', root_content))
        if has_old_import and has_old_composition:
            components["existing_composition_preserved"] = 1.0
        elif has_old_import or has_old_composition:
            components["existing_composition_preserved"] = 0.5
        else:
            components["existing_composition_preserved"] = 0.0
    else:
        components["existing_composition_preserved"] = 0.0

    # ======================================================================
    # HARD/HIDDEN TIER: Deep Remotion expertise (discriminates strong agents)
    # ======================================================================

    # H1. Zod schema integration — Remotion v4 best practice for typed props
    # Strong agents know Remotion v4 uses zod schemas for Composition props,
    # enabling type-safe default props and studio editing.
    h_zod = 0.0
    has_zod_import = bool(re.search(r'(?:from\s+["\']zod["\']|require\s*\(["\']zod["\']\))', all_new_content))
    has_z_object = bool(re.search(r'z\.object\s*\(', all_new_content))
    has_z_infer = bool(re.search(r'z\.infer\s*<\s*typeof\s+\w+', all_new_content))
    # schema prop passed to <Composition> in Root.tsx
    has_schema_in_comp = False
    if root_file.exists():
        rc = _read(root_file)
        new_blocks = [b for b in re.findall(r'<Composition[^/]*?(?:/>|>)', rc, re.DOTALL)
                      if re.search(r'(?:money|Money|ai|AI|Summary)', b, re.IGNORECASE)
                      and "BreakingNews" not in b]
        if new_blocks:
            has_schema_in_comp = bool(re.search(r'schema=\{', new_blocks[0]))
    # Exported schema constant
    has_exported_schema = bool(re.search(r'export\s+const\s+\w*[Ss]chema\s*=\s*z\.', all_new_content))

    if has_zod_import and has_z_object:
        h_zod += 0.3
    if has_z_infer:
        h_zod += 0.2
    if has_schema_in_comp:
        h_zod += 0.3
    if has_exported_schema:
        h_zod += 0.2
    components["h_zod_schema_integration"] = min(1.0, h_zod)

    # H2. Temporal correctness — sequences are gap-free and sum to target duration
    # Weak agents often leave gaps between sequences or produce overlapping timelines.
    # Strong agents ensure from[i] == from[i-1] + duration[i-1] (gap-free) and
    # total matches the ~900 frame target.
    h_temporal = 0.0
    from_values = [int(x) for x in re.findall(r'from=\{?\s*(\d+)\s*\}?', comp_content)]
    dur_values = [int(x) for x in re.findall(r'durationInFrames=\{?\s*(\d+)\s*\}?', comp_content)]

    if len(from_values) >= 5 and len(dur_values) >= 5 and len(from_values) == len(dur_values):
        # Check gap-free: each from == prev_from + prev_duration (strict)
        gap_free = True
        for i in range(1, len(from_values)):
            expected = from_values[i - 1] + dur_values[i - 1]
            if from_values[i] != expected:
                gap_free = False
                break
        if gap_free:
            h_temporal += 0.4
        else:
            # Partial credit: ordered and no overlaps (but has gaps)
            ordered = from_values == sorted(from_values)
            no_overlap = all(from_values[i] >= from_values[i-1] + dur_values[i-1]
                           for i in range(1, len(from_values)))
            if ordered and no_overlap:
                h_temporal += 0.15

        # Check total duration is in tight range of 900 (800-1000)
        max_end = max(f + d for f, d in zip(from_values, dur_values))
        if 850 <= max_end <= 950:
            h_temporal += 0.35
        elif 800 <= max_end <= 1000:
            h_temporal += 0.2
        elif 700 <= max_end <= 1100:
            h_temporal += 0.1

        # First sequence starts at frame 0
        if from_values[0] == 0:
            h_temporal += 0.25
    elif len(from_values) >= 3 and len(dur_values) >= 3:
        # Has sequences but not enough — partial
        if from_values == sorted(from_values) and from_values[0] == 0:
            h_temporal += 0.15
        total_est = sum(dur_values)
        if 700 <= total_est <= 1100:
            h_temporal += 0.1

    components["h_temporal_gap_free"] = min(1.0, h_temporal)

    # H3. Spring animation correctness — proper spring() usage with config
    # Strong agents use spring({frame, fps, config: {damping, stiffness}}) which
    # is the Remotion-idiomatic way. Weak agents just use CSS transitions or
    # naive interpolate without spring physics.
    # NOTE: Check all_new_content since animations may be in sub-component files.
    h_spring = 0.0

    # spring() with fps parameter (required in Remotion — frame needs fps context)
    has_spring_fps = bool(re.search(r'spring\s*\(\s*\{[^}]*fps\s*[,:]', all_new_content))
    # spring() with frame parameter
    has_spring_frame = bool(re.search(r'spring\s*\(\s*\{[^}]*frame\s*[,:]', all_new_content))
    # spring() with config object (damping/stiffness/mass)
    has_spring_config = bool(re.search(r'spring\s*\(\s*\{[^}]*config\s*:', all_new_content))
    # Alternative: spring with explicit damping/stiffness at top level
    has_spring_params = bool(re.search(r'spring\s*\(\s*\{[^}]*(?:damping|stiffness|mass)\s*:', all_new_content))

    # interpolate() with extrapolateRight: 'clamp' (prevents values going beyond range)
    has_interpolate_clamp = bool(re.search(
        r'interpolate\s*\([^)]*\{[^}]*extrapolate(?:Right|Left)\s*:\s*["\']clamp["\']',
        all_new_content, re.DOTALL
    ))
    # interpolate() with at least 3 output values (smooth multi-step animation)
    has_multi_interpolate = bool(re.search(
        r'interpolate\s*\(\s*\w+\s*,\s*\[[^\]]*,\s*[^\]]*,\s*[^\]]+\]',
        all_new_content
    ))

    if has_spring_fps and has_spring_frame:
        h_spring += 0.35
    elif has_spring_fps or has_spring_frame:
        h_spring += 0.15
    if has_spring_config or has_spring_params:
        h_spring += 0.25
    if has_interpolate_clamp:
        h_spring += 0.25
    if has_multi_interpolate:
        h_spring += 0.15
    components["h_spring_animation_correctness"] = min(1.0, h_spring)

    # H4. Sequence-relative frame handling
    # CRITICAL Remotion knowledge: useCurrentFrame() returns the GLOBAL frame.
    # Inside a <Sequence from={X}>, you must subtract X to get the local frame.
    # Alternatively, Remotion provides useRelativeCurrentFrame() (v4.0.117+) or
    # you wrap in a sub-component where the Sequence resets the frame context.
    # Weak agents use raw useCurrentFrame() inside Sequences without adjustment.
    # NOTE: Check all_new_content since sub-components handle frames.
    h_relative = 0.0

    # Pattern 1: Explicit frame subtraction (frame - offset)
    has_frame_subtraction = bool(re.search(r'(?:frame|currentFrame|f)\s*-\s*(?:\d+|\w+(?:Offset|Start|From))', all_new_content))
    # Pattern 2: Each scene is its own component (Sequence resets frame context)
    # If scenes are separate components that each call useCurrentFrame, frame is local
    scene_components = re.findall(r'(?:const|function)\s+(\w+(?:Scene|Slide|Section|Intro|Outro|Part))\b', all_new_content)
    scene_uses_frame = 0
    for sc in scene_components:
        # Check if the scene component body uses useCurrentFrame
        pattern = rf'(?:const|function)\s+{re.escape(sc)}[^{{]*\{{(.*?)(?:\n\}}\s*;|\nreturn)'
        match = re.search(pattern, all_new_content, re.DOTALL)
        if match and "useCurrentFrame" in match.group(1):
            scene_uses_frame += 1
    # Also count: imported sub-components that are rendered inside <Sequence>
    # If comp_content imports scene components AND wraps them in Sequence, frame resets
    imported_scenes = re.findall(r'import\s*\{?\s*(\w+(?:Scene|Slide|Section|Intro|Outro))', comp_content)
    sequences_with_children = re.findall(r'<Sequence[^>]*>\s*<(\w+)', comp_content)
    scene_in_sequence = sum(1 for s in sequences_with_children if s in imported_scenes or s in [sc for sc in scene_components])

    # Pattern 3: using the Sequence's children prop pattern where each child is self-contained
    scenes_as_children = (len(scene_components) >= 5 and scene_uses_frame >= 3) or scene_in_sequence >= 5

    if has_frame_subtraction:
        h_relative += 0.5
    if scenes_as_children:
        h_relative += 0.5
    elif scene_in_sequence >= 3 or (len(scene_components) >= 5 and scene_uses_frame >= 2):
        # Sub-components exist and use frame — likely correct pattern
        h_relative += 0.35
    elif len(scene_components) >= 5:
        # Sub-components exist but may not handle frames correctly
        h_relative += 0.25
    elif len(scene_components) >= 3:
        h_relative += 0.15

    # Bonus: using useVideoConfig for fps-aware calculations
    has_video_config = "useVideoConfig" in all_new_content
    if has_video_config and (has_frame_subtraction or scenes_as_children):
        h_relative += 0.2

    components["h_sequence_relative_frames"] = min(1.0, h_relative)

    # H5. Composition architecture — professional-grade code organization
    # Strong agents split into multiple files, use barrel exports, separate
    # data from presentation, and follow Remotion project conventions.
    h_arch = 0.0

    # Multi-file organization: new composition in its own directory with multiple files
    comp_dir = comp_file.parent
    sibling_files = [f for f in comp_dir.iterdir() if f.is_file() and f.suffix in (".tsx", ".ts")] if comp_dir.exists() else []
    if len(sibling_files) >= 4:
        h_arch += 0.3
    elif len(sibling_files) >= 2:
        h_arch += 0.15

    # Separate data/constants file (not inlining all content in the component)
    has_separate_data = any(
        re.search(r'(?:data|constants?|content|config)', f.name, re.IGNORECASE)
        for f in sibling_files if f != comp_file
    )
    if has_separate_data:
        h_arch += 0.2

    # Import from local modules (shows proper code splitting)
    local_imports = re.findall(r'import\s+.*\s+from\s+["\']\./', comp_content)
    if len(local_imports) >= 2:
        h_arch += 0.2
    elif len(local_imports) >= 1:
        h_arch += 0.1

    # Proper named export (not default export — Remotion convention)
    has_named_export = bool(re.search(r'export\s+const\s+\w+', comp_content))
    has_no_default_export = "export default" not in comp_content
    if has_named_export and has_no_default_export:
        h_arch += 0.15

    # Color/style constants or theme object (production quality)
    has_theme = bool(re.search(r'(?:const|let)\s+(?:colors?|theme|palette|styles?)\s*[=:]', all_new_content))
    if has_theme:
        h_arch += 0.15

    components["h_composition_architecture"] = min(1.0, h_arch)

    # H6. Remotion v4 patterns — using modern Remotion features correctly
    # Tests knowledge of Remotion v4 specific APIs and patterns.
    h_v4 = 0.0

    # calculateMetadata — Remotion v4 way to compute props dynamically
    has_calc_metadata = bool(re.search(r'calculateMetadata', all_new_content))
    if has_calc_metadata:
        h_v4 += 0.25

    # Composition with lazyComponent or component + schema (v4 pattern)
    if root_file.exists():
        rc = _read(root_file)
        new_blocks = [b for b in re.findall(r'<Composition[^/]*?(?:/>|>)', rc, re.DOTALL)
                      if re.search(r'(?:money|Money|ai|AI|Summary)', b, re.IGNORECASE)
                      and "BreakingNews" not in b]
        if new_blocks:
            block = new_blocks[0]
            # component= prop (required for typed compositions in v4)
            has_component_prop = bool(re.search(r'component=\{', block))
            if has_component_prop:
                h_v4 += 0.15

    # useVideoConfig (fps-aware rendering)
    if "useVideoConfig" in all_new_content:
        h_v4 += 0.15

    # Proper Remotion easing functions (Easing.bezier, Easing.inOut, etc.)
    has_easing = bool(re.search(r'Easing\.(?:bezier|inOut|out|in|elastic|bounce)', all_new_content))
    if has_easing:
        h_v4 += 0.2

    # <AbsoluteFill> with style prop for centering/positioning
    has_styled_fill = bool(re.search(r'<AbsoluteFill[^>]*style=\{', all_new_content))
    if has_styled_fill:
        h_v4 += 0.1

    # Using Remotion's <Series> component (alternative to manual Sequence from/duration)
    has_series = "Series" in all_new_content and bool(re.search(r'<Series[.>]|<Series\.Sequence', all_new_content))
    if has_series:
        h_v4 += 0.15

    components["h_remotion_v4_patterns"] = min(1.0, h_v4)

    # ======================================================================
    # Compute overall score
    # ======================================================================
    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        # EASY TIER (55%) — all agents should score well here
        "composition_file_created": 0.07,
        "uses_remotion_apis": 0.08,
        "has_multiple_sequences": 0.08,
        "registered_in_root": 0.10,
        "correct_composition_props": 0.08,
        "content_from_summary": 0.07,
        "existing_composition_preserved": 0.07,
        # HARD/HIDDEN TIER (45%) — discriminates strong from weak
        "h_zod_schema_integration": 0.09,
        "h_temporal_gap_free": 0.08,
        "h_spring_animation_correctness": 0.08,
        "h_sequence_relative_frames": 0.08,
        "h_composition_architecture": 0.06,
        "h_remotion_v4_patterns": 0.06,
    }


def main():
    # Try primary location first, then fallback
    ws = Path("/workspace/fixtures/remotion-project")
    if not ws.exists():
        ws = Path("/workspace/remotion-project")
    if not ws.exists():
        ws = Path("/workspace")

    # If we found the project directly, grade it
    if (ws / "src").exists():
        result = grade_workspace(ws)
    else:
        # Try inside fixtures
        result = grade_workspace(Path("/workspace/fixtures"))
        if result["overall_score"] == 0.0:
            result = grade_workspace(Path("/workspace"))

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
