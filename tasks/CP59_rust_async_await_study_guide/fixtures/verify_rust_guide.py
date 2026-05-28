"""Hidden verifier for CP59 — Rust async/await study guide.

Scores /workspace/async_study_guide.md on 6 anchors:
- file exists + substantive length
- 5 required topic sections (Future/Pin/poll, Tokio runtime, Arc/Mutex/RwLock/mpsc, Send/Sync, interview Q&A)
- ≥4 rust code blocks
- ≥5 interview Q-style anchors
- Tokio-specific API mentions (spawn / select! / runtime / multi_thread / current_thread)
- existing_notes.md content actually referenced (continuity signal)
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    guide = ws / "async_study_guide.md"
    content = _read(guide)
    notes = _read(ws / "fixtures" / "existing_notes.md")

    components = {k: 0.0 for k in [
        "file", "five_sections", "code_examples", "interview_questions",
        "tokio_specific", "notes_referenced",
    ]}

    if not content.strip():
        return {"overall_score": 0.0, "components": components}

    lower = content.lower()

    # 1. File presence + substantive length
    if len(content) >= 2000:
        components["file"] = 1.0
    elif len(content) >= 800:
        components["file"] = 0.6
    elif len(content) >= 300:
        components["file"] = 0.3

    # 2. Five required topic sections
    topics = [
        any(k in lower for k in ["future trait", "future ", " pin", "poll"]),
        any(k in lower for k in ["tokio", "runtime", "scheduler", "调度"]),
        any(k in lower for k in ["arc", "mutex", "rwlock", "mpsc", "channel"]),
        any(k in lower for k in ["send", "sync"]),
        any(k in lower for k in ["面试", "interview", "q&a", "问题"]),
    ]
    components["five_sections"] = sum(topics) / 5.0

    # 3. Rust code blocks
    code_blocks = re.findall(r"```(?:rust|rs)?\s*\n(.*?)```", content, re.DOTALL)
    components["code_examples"] = min(len(code_blocks) / 5.0, 1.0)

    # 4. Interview-question anchors
    q_patterns = re.findall(
        r"(?:Q\d|问题\s*\d|第\s*\d\s*[题道]|###?\s*\d+[\.、]|\d+\.\s+.{5,}\?)",
        content,
    )
    components["interview_questions"] = min(len(q_patterns) / 5.0, 1.0)

    # 5. Tokio specifics
    tokio_apis = ["spawn", "select!", "runtime::new", "multi_thread", "current_thread", "#[tokio::main]", "tokio::main"]
    api_hits = sum(1 for a in tokio_apis if a in content)
    if "tokio" in lower and api_hits >= 2:
        components["tokio_specific"] = 1.0
    elif "tokio" in lower and api_hits >= 1:
        components["tokio_specific"] = 0.5

    # 6. Notes continuity (does the guide build on existing_notes.md?)
    if notes:
        notes_keywords = set(re.findall(r"\b[a-z_][a-z0-9_]{2,}\b", notes.lower()))
        guide_keywords = set(re.findall(r"\b[a-z_][a-z0-9_]{2,}\b", content.lower()))
        overlap = notes_keywords & guide_keywords
        components["notes_referenced"] = min(len(overlap) / 10.0, 1.0)
    else:
        components["notes_referenced"] = 0.5

    weights = {
        "file": 0.15,
        "five_sections": 0.30,
        "code_examples": 0.20,
        "interview_questions": 0.15,
        "tokio_specific": 0.15,
        "notes_referenced": 0.05,
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
