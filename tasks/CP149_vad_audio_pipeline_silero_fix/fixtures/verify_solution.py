"""Hidden verifier for CP149 — VAD Audio Pipeline Silero Fix.

Checks that the agent correctly diagnosed and fixed the VAD audio pipeline issues.

Three-tier scoring for discrimination:

Visible tier (45%) — surface-level fixes any agent can attempt:
  1. REQUIRED_SAMPLES changed from 480 to 512 (0.15)
  2. READ_INTERVAL_MS reduced (0.15)
  3. Probability threshold lowered (0.15)

Hidden-easy tier (20%) — basic correctness all competent agents pass:
  4. Pipeline integrity preserved (resampling, RMS, loop intact) (0.10)
  5. Files actually modified (not just discussed) (0.05)
  6. No obvious regressions (source->analyser still connected) (0.05)

Hidden-hard tier (35%) — deep understanding only strong agents demonstrate:
  7. AnalyserNode -> silent GainNode -> destination topology (0.12)
  8. Frame size consistency via shared constant (not dual hardcode) (0.08)
  9. GainNode cleanup in stopMicrophone (resource mgmt) (0.05)
  10. AudioContext state handling (resume suspended context) (0.05)
  11. Proper disconnect ordering in cleanup (0.05)
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


# ---------------------------------------------------------------------------
# VISIBLE TIER — surface-level fixes (45%)
# ---------------------------------------------------------------------------

def check_required_samples(service_src: str) -> float:
    """Check if REQUIRED_SAMPLES is updated to 512 for v4 model."""
    has_512 = bool(re.search(r'\b512\b', service_src))
    still_480 = bool(re.search(r'REQUIRED_SAMPLES\s*=\s*480', service_src))

    if has_512 and not still_480:
        return 1.0

    # Dynamic detection approach (checking state shape to determine frame size)
    has_dynamic = bool(re.search(
        r'(stateSize|state.*128|lstm.*128).*512|(512|frameSize).*v4',
        service_src, re.IGNORECASE
    ))
    if has_dynamic and not still_480:
        return 1.0

    if not still_480 and has_512:
        return 0.8

    if not still_480:
        return 0.3

    return 0.0


def check_read_interval(controller_src: str) -> float:
    """Check if READ_INTERVAL_MS is reduced for better responsiveness."""
    matches = re.findall(r'READ_INTERVAL_MS\s*=\s*(\d+)', controller_src)
    if not matches:
        interval_matches = re.findall(r'(?:interval|INTERVAL)\w*\s*=\s*(\d+)', controller_src)
        if interval_matches:
            val = int(interval_matches[0])
            if val <= 50:
                return 1.0
            elif val <= 60:
                return 0.8
            elif val < 100:
                return 0.5
        return 0.0

    val = int(matches[0])
    if val <= 50:
        return 1.0
    elif val <= 60:
        return 0.8
    elif val < 100:
        return 0.5
    return 0.0


def check_threshold(types_src: str, controller_src: str) -> float:
    """Check if default probability threshold is lowered from 50."""
    threshold_matches = re.findall(
        r'probabilityThreshold\s*:\s*(\d+)', types_src
    )
    controller_threshold = re.findall(
        r'(?:threshold|probabilityThreshold)\s*(?:=|:)\s*(\d+)', controller_src
    )

    all_thresholds = [int(m) for m in threshold_matches + controller_threshold]

    if not all_thresholds:
        return 0.0

    best = min(all_thresholds)
    if best <= 40:
        return 1.0
    elif best <= 45:
        return 0.8
    elif best < 50:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# HIDDEN-EASY TIER — basic correctness all competent agents pass (20%)
# ---------------------------------------------------------------------------

def check_pipeline_integrity(controller_src: str) -> float:
    """Hidden-easy: The agent preserved the existing correct parts of the pipeline.

    These are things that should NOT be broken. Any competent agent that reads
    the code before modifying it will preserve these. Catches blind copy-paste.
    """
    checks = 0
    total = 4

    # Must still have resampling from 48kHz to 16kHz
    has_resample = bool(re.search(
        r'resample\w*\(.*48000.*16000|resample\w*\(.*48\d*.*16\d*', controller_src
    ))
    if has_resample:
        checks += 1

    # Must still compute RMS/volume
    has_rms = bool(re.search(r'rms|RMS|Math\.sqrt\s*\(', controller_src))
    if has_rms:
        checks += 1

    # Must still have a processing loop (rAF or setInterval)
    has_loop = bool(re.search(
        r'requestAnimationFrame|setInterval|setTimeout', controller_src
    ))
    if has_loop:
        checks += 1

    # Must still call processAudioFrame or equivalent
    has_process_call = bool(re.search(
        r'processAudioFrame|process\s*\(|vadService\w*\.process', controller_src
    ))
    if has_process_call:
        checks += 1

    return checks / total


def check_files_modified(controller_src: str, service_src: str, orig_controller: str, orig_service: str) -> float:
    """Hidden-easy: Files were actually modified (not just discussed).

    Agents that only explain the fix but don't apply it score 0 here.
    Any agent that actually edits the files gets full marks.
    """
    controller_changed = controller_src != orig_controller
    service_changed = service_src != orig_service

    if controller_changed and service_changed:
        return 1.0
    elif controller_changed or service_changed:
        return 0.5
    return 0.0


def check_no_regressions(controller_src: str) -> float:
    """Hidden-easy: Source -> analyser connection preserved, no obvious breakage.

    The original source.connect(analyser) must remain. If removed, audio data
    can never reach the analyser and the whole pipeline is dead.
    """
    has_source_to_analyser = bool(re.search(
        r'sourceNode\w*\.connect\s*\(\s*(this\.)?analyser', controller_src
    )) or bool(re.search(
        r'this\.sourceNode\w*\.connect\s*\(\s*(this\.)?analyser', controller_src
    ))

    # Also check they didn't remove the analyser creation
    has_create_analyser = bool(re.search(
        r'createAnalyser\s*\(\s*\)', controller_src
    ))

    if has_source_to_analyser and has_create_analyser:
        return 1.0
    elif has_source_to_analyser or has_create_analyser:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# HIDDEN-HARD TIER — deep understanding only strong agents show (35%)
# ---------------------------------------------------------------------------

def check_analyser_connection_deep(controller_src: str) -> float:
    """Hidden-hard: AnalyserNode connected to destination via silent GainNode.

    Requires understanding of Chromium's audio graph requirement:
    nodes must be connected to destination to receive scheduled processing.

    Correct topology: source -> analyser -> silentGain(0) -> destination
    This keeps analyser active without producing speaker output.
    """
    score = 0.0

    # Must create a GainNode
    has_gain_node = bool(re.search(
        r'createGain\s*\(\s*\)', controller_src
    ))

    # Must set gain = 0 (silent output)
    has_gain_zero = bool(re.search(
        r'\.gain\s*\.?\s*(value\s*=\s*0|setValueAtTime\s*\(\s*0)', controller_src
    ))

    # Must connect analyser to the gain node
    has_analyser_to_gain = bool(re.search(
        r'analyser\w*\.connect\s*\(\s*(?:this\.)?\w*[Gg]ain', controller_src
    )) or bool(re.search(
        r'this\.analyser\w*\.connect\s*\(\s*(?:this\.)?\w*[Gg]ain', controller_src
    ))

    # Must connect gain node to destination
    has_gain_to_destination = bool(re.search(
        r'[Gg]ain\w*\.connect\s*\(\s*(this\.)?audioContext\w*\.destination\s*\)', controller_src
    ))

    # ANTI-PATTERN: connecting source directly to destination (would cause audio output)
    bad_direct_destination = bool(re.search(
        r'sourceNode\w*\.connect\s*\(\s*(this\.)?audioContext\w*\.destination\s*\)', controller_src
    ))

    if bad_direct_destination:
        return 0.1

    # Score the correct topology
    if has_gain_node and has_gain_zero:
        score += 0.3
    elif has_gain_node:
        score += 0.1

    if has_analyser_to_gain and has_gain_to_destination:
        score += 0.5
    elif has_gain_to_destination:
        score += 0.2
    elif has_analyser_to_gain:
        score += 0.1

    # Bonus for preserving the original source -> analyser connection
    # (only counts if agent actually added a GainNode — otherwise this is just the original code)
    has_source_to_analyser = bool(re.search(
        r'sourceNode\w*\.connect\s*\(\s*(this\.)?analyser', controller_src
    )) or bool(re.search(
        r'this\.sourceNode\w*\.connect\s*\(\s*(this\.)?analyser', controller_src
    ))
    if has_source_to_analyser and has_gain_node:
        score += 0.2

    return min(score, 1.0)


def check_frame_size_via_shared_reference(controller_src: str, service_src: str) -> float:
    """Hidden-hard: Frame size consistency via shared constant or import.

    Strong agents will:
    - Import or reference the service's REQUIRED_SAMPLES constant in the controller
    - Or define a shared constant that both files reference
    - Not just hardcode 512 in two separate places (fragile)

    This tests software engineering quality, not just correctness.
    """
    # Best: controller imports REQUIRED_SAMPLES from service
    imports_constant = bool(re.search(
        r'import\s*\{[^}]*REQUIRED_SAMPLES[^}]*\}\s*from', controller_src
    )) or bool(re.search(
        r'import\s+.*REQUIRED_SAMPLES.*from', controller_src
    ))

    # Good: controller references SileroVADService.REQUIRED_SAMPLES or similar
    references_service = bool(re.search(
        r'SileroVAD\w*\.REQUIRED_SAMPLES|vadService\w*\.\w*REQUIRED|FRAME_SIZE', controller_src
    ))

    # Acceptable: controller uses a named constant (not magic number)
    uses_named_constant = bool(re.search(
        r'(?:const|let|var)\s+(?:REQUIRED_SAMPLES|FRAME_SIZE|frameSize|VAD_FRAME_SIZE)\s*(?:=|:)\s*512',
        controller_src
    ))

    # Basic: just hardcoded 512 (still correct but fragile)
    has_512 = bool(re.search(r'\b512\b', controller_src))
    still_480 = bool(re.search(r'frameSize\s*=\s*480', controller_src))

    if imports_constant:
        return 1.0
    elif references_service:
        return 0.9
    elif uses_named_constant:
        return 0.7
    elif has_512 and not still_480:
        return 0.5
    elif not still_480:
        return 0.3
    return 0.0


def check_gainnode_cleanup(controller_src: str) -> float:
    """Hidden-hard: GainNode properly disconnected/nulled in stopMicrophone.

    Strong agents understand resource management in Web Audio:
    - Disconnect the gain node to break circular refs
    - Null the reference to allow GC
    - Do this in the existing stopMicrophone method

    Weak agents just add the GainNode connection but forget cleanup.
    """
    score = 0.0

    # Check for gain node disconnect in stop/cleanup
    has_gain_disconnect = bool(re.search(
        r'[Gg]ain\w*\.\s*disconnect\s*\(\s*\)', controller_src
    ))

    # Check for nulling the gain reference
    has_gain_null = bool(re.search(
        r'[Gg]ain\w*\s*=\s*null', controller_src
    ))

    # Check that the gain node is stored as an instance variable (not just local)
    # Exclude autoGainControl which is a media constraint, not a Web Audio GainNode
    has_gain_property = bool(re.search(
        r'(?:private|public|protected)\s+\w*[Gg]ainNode\w*\s*(?::|=)', controller_src
    )) or bool(re.search(
        r'this\.\w*[Gg]ain(?:Node)?\w*\s*=\s*(?:this\.audioContext|null)', controller_src
    ))

    if has_gain_disconnect and has_gain_null and has_gain_property:
        return 1.0
    elif has_gain_disconnect and has_gain_property:
        return 0.8
    elif has_gain_disconnect:
        return 0.5
    elif has_gain_property:
        # Stored but not cleaned up
        return 0.2
    return 0.0


def check_audiocontext_state_handling(controller_src: str) -> float:
    """Hidden-hard: AudioContext suspended state handled.

    In Electron/Chromium, AudioContext starts in 'suspended' state until user
    interaction. Strong agents know to call audioContext.resume() after creation,
    or check the state before relying on audio data.

    This is a known gotcha that separates agents who deeply understand the
    Web Audio API from those who just pattern-match the obvious fix.
    """
    # Check for audioContext.resume()
    has_resume = bool(re.search(
        r'audioContext\w*\.resume\s*\(\s*\)', controller_src
    )) or bool(re.search(
        r'this\.audioContext\w*\.resume\s*\(\s*\)', controller_src
    ))

    # Check for state checking (audioContext.state === 'suspended')
    has_state_check = bool(re.search(
        r'audioContext\w*\.state\s*(?:===?|!==?)\s*[\'"]suspended[\'"]', controller_src
    )) or bool(re.search(
        r'this\.audioContext\w*\.state', controller_src
    ))

    if has_resume and has_state_check:
        return 1.0
    elif has_resume:
        return 0.8
    elif has_state_check:
        return 0.4
    return 0.0


def check_disconnect_ordering(controller_src: str) -> float:
    """Hidden-hard: Proper disconnect ordering in stopMicrophone.

    Correct order: disconnect nodes in reverse topology order (leaf -> root),
    then close the AudioContext last. If the context is closed first,
    disconnect calls will throw. Strong agents also handle the gain node
    in the disconnect chain.

    Expected sequence in stopMicrophone:
    1. Stop media tracks
    2. Disconnect gain node (if added)
    3. Disconnect analyser
    4. Disconnect source
    5. Close AudioContext
    """
    # Extract the stopMicrophone method body using brace counting
    idx = controller_src.find('stopMicrophone')
    if idx < 0:
        return 0.0

    brace_start = controller_src.find('{', idx)
    if brace_start < 0:
        return 0.0

    depth = 0
    i = brace_start
    while i < len(controller_src):
        if controller_src[i] == '{':
            depth += 1
        elif controller_src[i] == '}':
            depth -= 1
            if depth == 0:
                break
        i += 1

    body = controller_src[brace_start + 1:i]
    if len(body) < 20:
        return 0.0

    score = 0.0

    # Check that audioContext.close() comes after disconnect calls
    close_pos = body.find('close()')
    disconnect_positions = [m.start() for m in re.finditer(r'disconnect\s*\(\s*\)', body)]

    if close_pos > 0 and disconnect_positions:
        # All disconnects should come before close
        all_before_close = all(pos < close_pos for pos in disconnect_positions)
        if all_before_close:
            score += 0.5

    # Check that gain node is disconnected (if present in stop method)
    has_gain_in_stop = bool(re.search(r'[Gg]ain\w*\.disconnect|[Gg]ain\w*\s*=\s*null', body))
    if has_gain_in_stop:
        score += 0.3

    # Check that tracks are stopped before node disconnection
    tracks_pos = body.find('.stop()')
    if tracks_pos >= 0 and disconnect_positions:
        tracks_before_disconnect = tracks_pos < min(disconnect_positions)
        if tracks_before_disconnect:
            score += 0.2

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# GRADING ORCHESTRATOR
# ---------------------------------------------------------------------------

# Original file content fingerprints (to detect modification)
ORIG_CONTROLLER_FINGERPRINT = "const READ_INTERVAL_MS = 100;"
ORIG_SERVICE_FINGERPRINT = "const REQUIRED_SAMPLES = 480;"


def grade_workspace(ws: Path) -> dict:
    """Grade the VAD fix workspace."""
    vad_dir = ws / "vad-app" / "src" / "composables" / "live-vad"
    if not vad_dir.exists():
        vad_dir = ws / "fixtures" / "vad-app" / "src" / "composables" / "live-vad"

    controller_src = _read(vad_dir / "VADController.ts")
    service_src = _read(vad_dir / "SileroVADService.ts")
    types_src = _read(vad_dir / "types.ts")

    if not controller_src:
        for p in ws.rglob("VADController.ts"):
            controller_src = _read(p)
            break
    if not service_src:
        for p in ws.rglob("SileroVADService.ts"):
            service_src = _read(p)
            break
    if not types_src:
        for p in ws.rglob("types.ts"):
            types_src = _read(p)
            break

    # Determine if files were actually modified
    orig_controller = ORIG_CONTROLLER_FINGERPRINT
    orig_service = ORIG_SERVICE_FINGERPRINT
    controller_modified = orig_controller not in controller_src
    service_modified = orig_service not in service_src

    components = {}

    # --- Visible tier (45% total) ---
    components["samples_512"] = check_required_samples(service_src)
    components["interval_reduced"] = check_read_interval(controller_src)
    components["threshold_lowered"] = check_threshold(types_src, controller_src)

    # --- Hidden-easy tier (20% total) ---
    components["pipeline_integrity"] = check_pipeline_integrity(controller_src)
    components["files_modified"] = (
        1.0 if (controller_modified and service_modified)
        else 0.5 if (controller_modified or service_modified)
        else 0.0
    )
    components["no_regressions"] = check_no_regressions(controller_src)

    # --- Hidden-hard tier (35% total) ---
    components["analyser_connection_deep"] = check_analyser_connection_deep(controller_src)
    components["frame_size_shared_ref"] = check_frame_size_via_shared_reference(controller_src, service_src)
    components["gainnode_cleanup"] = check_gainnode_cleanup(controller_src)
    components["audiocontext_state"] = check_audiocontext_state_handling(controller_src)
    components["disconnect_ordering"] = check_disconnect_ordering(controller_src)

    # Weights: visible=45%, hidden-easy=20%, hidden-hard=35%
    weights = {
        # Visible (45%)
        "samples_512": 0.15,
        "interval_reduced": 0.15,
        "threshold_lowered": 0.15,
        # Hidden-easy (20%)
        "pipeline_integrity": 0.10,
        "files_modified": 0.05,
        "no_regressions": 0.05,
        # Hidden-hard (35%)
        "analyser_connection_deep": 0.12,
        "frame_size_shared_ref": 0.08,
        "gainnode_cleanup": 0.05,
        "audiocontext_state": 0.05,
        "disconnect_ordering": 0.05,
    }

    overall = sum(weights[k] * components[k] for k in weights)

    # Tier breakdowns for analysis
    visible_score = sum(
        weights[k] * components[k]
        for k in ["samples_512", "interval_reduced", "threshold_lowered"]
    )
    hidden_easy_score = sum(
        weights[k] * components[k]
        for k in ["pipeline_integrity", "files_modified", "no_regressions"]
    )
    hidden_hard_score = sum(
        weights[k] * components[k]
        for k in ["analyser_connection_deep", "frame_size_shared_ref",
                  "gainnode_cleanup", "audiocontext_state", "disconnect_ordering"]
    )

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "tier_scores": {
            "visible": round(visible_score, 4),
            "hidden_easy": round(hidden_easy_score, 4),
            "hidden_hard": round(hidden_hard_score, 4),
        },
        "tier_max": {
            "visible": 0.45,
            "hidden_easy": 0.20,
            "hidden_hard": 0.35,
        },
    }


def main():
    ws = Path("/workspace/fixtures")
    if not ws.exists() or not any(ws.rglob("VADController.ts")):
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
