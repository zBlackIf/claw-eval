#!/usr/bin/env python3
"""In-container verifier for CP30_catalog_alignment_biblio.

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

EXPECTED = {
    "CAT-NLC-50001": {
        "correct": ["exact_match", "same_edition"],
        "weight": 1.0,
        "confidence": (80, 100),
        "anchors": ["宋", "国子监", "国家图书馆"],
    },
    "CAT-BJ-60234": {
        "correct": ["no_relation"],
        "weight": 1.0,
        "confidence": (0, 35),
        "anchors": ["明", "万历", "萬曆"],
    },
    "CAT-SH-70345": {
        "correct": ["same_edition", "related_content"],
        "weight": 1.0,
        "confidence": (45, 85),
        "anchors": ["宋", "建阳", "建陽", "孔颖达", "孔穎達"],
    },
    "CAT-NLC-50002": {
        "correct": ["related_content", "same_edition"],
        "weight": 1.0,
        "confidence": (45, 85),
        "anchors": ["残本", "卷一", "卷十", "宋"],
    },
    "CAT-JP-80456": {
        "correct": ["no_relation"],
        "weight": 1.0,
        "confidence": (0, 35),
        "anchors": ["清", "嘉庆", "嘉慶", "注疏"],
    },
}

REQUIRED_FIELDS = ("title", "author", "edition", "collection")


def _normalize_relation(value: object) -> str:
    text = str(value or "").strip().lower()
    text = text.replace(" ", "_").replace("-", "_")
    aliases = {
        "match": "exact_match",
        "same": "exact_match",
        "same_version": "same_edition",
        "same_print": "same_edition",
        "related": "related_content",
        "partial": "related_content",
        "partial_match": "related_content",
        "none": "no_relation",
        "reject": "no_relation",
        "different_edition": "no_relation",
        "unrelated": "no_relation",
        "无关系": "no_relation",
        "同版本": "same_edition",
        "相关内容": "related_content",
        "完全匹配": "exact_match",
    }
    return aliases.get(text, text)


def _as_number(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value * 100 if 0 <= value <= 1 else value)
    if isinstance(value, str):
        match = re.search(r"\d+(?:\.\d+)?", value)
        if match:
            number = float(match.group(0))
            return number * 100 if "%" not in value and 0 <= number <= 1 else number
    return None


def _field_blob(result: dict) -> tuple[dict, str]:
    fields = result.get("field_comparison", result.get("fields", result.get("comparison", {})))
    if not isinstance(fields, dict):
        fields = {}
    return fields, json.dumps(result, ensure_ascii=False).lower()


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    # Find output file
    output = workspace / "alignment_result.json"
    if not output.exists():
        for f in workspace.glob("*.json"):
            if "alignment" in f.name or "result" in f.name or "output" in f.name:
                output = f
                break

    if not output or not output.exists():
        return {
            "output_created": 0.0,
            "all_compared": 0.0,
            "relation_accuracy": 0.0,
            "field_details": 0.0,
            "has_confidence": 0.0,
        }

    try:
        data = json.loads(output.read_text(encoding="utf-8"))
        scores["output_created"] = 1.0
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "output_created": 0.5,
            "all_compared": 0.0,
            "relation_accuracy": 0.0,
            "field_details": 0.0,
            "has_confidence": 0.0,
        }

    # Normalize to list of comparisons
    results_list = []
    if isinstance(data, list):
        results_list = data
    elif isinstance(data, dict):
        results_list = data.get("results", data.get("comparisons", data.get("items", [])))
        if not results_list and "candidate_id" in data:
            results_list = [data]

    candidate_map = {}
    for r in results_list:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("candidate_id", r.get("id", "")))
        for cid in EXPECTED:
            if cid in rid or cid.split("-")[-1] in rid:
                candidate_map[cid] = r
                break

    scores["all_compared"] = len(candidate_map) / len(EXPECTED)

    # Check relation accuracy
    correct_count = 0
    total_weight = 0
    for cid, expected in EXPECTED.items():
        total_weight += expected["weight"]
        r = candidate_map.get(cid)
        if not r:
            continue
        relation = _normalize_relation(r.get("relation", r.get("relationship", r.get("type", ""))))
        if relation in expected["correct"]:
            correct_count += expected["weight"]

    scores["relation_accuracy"] = round(correct_count / total_weight, 2) if total_weight > 0 else 0.0

    detailed = 0
    for r in candidate_map.values():
        fields, blob = _field_blob(r)
        field_hits = 0
        for field in REQUIRED_FIELDS:
            zh = {
                "title": "题名",
                "author": "责任",
                "edition": "版本",
                "collection": "馆藏",
            }[field]
            if field in fields or zh in fields or re.search(field + r"|"+ zh, blob):
                field_hits += 1
        detailed += field_hits / len(REQUIRED_FIELDS)
    scores["field_details"] = detailed / len(EXPECTED)

    evidence_hits = 0
    confidence_hits = 0
    for cid, expected in EXPECTED.items():
        r = candidate_map.get(cid)
        if not r:
            continue
        blob = json.dumps(r, ensure_ascii=False)
        if any(anchor in blob for anchor in expected["anchors"]):
            evidence_hits += 1
        confidence = _as_number(r.get("confidence", r.get("score", r.get("置信度"))))
        if confidence is not None:
            low, high = expected["confidence"]
            confidence_hits += 1 if low <= confidence <= high else 0
    scores["evidence_anchors"] = evidence_hits / len(EXPECTED)
    scores["confidence_calibrated"] = confidence_hits / len(EXPECTED)

    # Check confidence scores present
    scores["has_confidence"] = 1.0 if confidence_hits == len(EXPECTED) else confidence_hits / len(EXPECTED)

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
