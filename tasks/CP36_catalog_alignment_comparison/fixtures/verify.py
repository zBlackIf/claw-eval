#!/usr/bin/env python3
"""In-container verifier for CP36_catalog_alignment_comparison.

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

SHOULD_REJECT = {"CAT-PKU-20891", "CAT-TW-40123", "CAT-JP-50789"}
BEST_MATCH = "CAT-NLC-10234"
EXPECTED = {
    "CAT-NLC-10234": {
        "relations": {"exact_match", "same_edition", "same_version"},
        "confidence": (80, 100),
        "anchors": ["宋", "国家图书馆", "國家圖書館", "国子监", "國子監"],
    },
    "CAT-PKU-20891": {
        "relations": {"no_relation"},
        "confidence": (0, 35),
        "anchors": ["明", "嘉靖"],
    },
    "CAT-SH-30456": {
        "relations": {"same_edition", "related_content", "related"},
        "confidence": (45, 85),
        "anchors": ["宋", "建阳", "建陽", "孔穎達", "孔颖达"],
    },
    "CAT-TW-40123": {
        "relations": {"no_relation"},
        "confidence": (0, 35),
        "anchors": ["清", "嘉庆", "嘉慶", "注疏"],
    },
    "CAT-NLC-10235": {
        "relations": {"related_content", "same_edition"},
        "confidence": (40, 85),
        "anchors": ["卷一", "卷三", "残本", "殘本", "宋"],
    },
    "CAT-JP-50789": {
        "relations": {"no_relation"},
        "confidence": (0, 35),
        "anchors": ["元", "至正"],
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


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    output_file = workspace / "alignment_output.json"
    if not output_file.exists():
        for f in workspace.glob("*.json"):
            if "alignment" in f.name or "output" in f.name:
                output_file = f
                break

    if not output_file.exists():
        return {
            "output_created": 0.0,
            "valid_json": 0.0,
            "all_candidates_compared": 0.0,
            "version_rejection": 0.0,
            "best_match_identified": 0.0,
            "field_details": 0.0,
        }

    try:
        data = json.loads(output_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        scores["output_created"] = 1.0
        scores["valid_json"] = 0.0
        scores["all_candidates_compared"] = 0.0
        scores["version_rejection"] = 0.0
        scores["best_match_identified"] = 0.0
        scores["field_details"] = 0.0
        return scores

    scores["output_created"] = 1.0
    scores["valid_json"] = 1.0

    results_list = (
        data if isinstance(data, list)
        else data.get("results", data.get("comparisons", data.get("items", [])))
    )
    if not isinstance(results_list, list):
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

    scores["all_candidates_compared"] = len(candidate_map) / len(EXPECTED)

    rejected_ids = set()
    for r in candidate_map.values():
        cid = r.get("candidate_id", r.get("id", ""))
        relation = _normalize_relation(r.get("relation", r.get("alignment_type", "")))
        if relation == "no_relation":
            rejected_ids.add(cid)

    correctly_rejected = SHOULD_REJECT.intersection(rejected_ids)
    scores["version_rejection"] = len(correctly_rejected) / len(SHOULD_REJECT)

    matched_best = False
    for r in candidate_map.values():
        cid = r.get("candidate_id", r.get("id", ""))
        relation = _normalize_relation(r.get("relation", r.get("alignment_type", "")))
        if BEST_MATCH in cid and relation in (
            "exact_match", "same_edition", "same_version"
        ):
            matched_best = True
    scores["best_match_identified"] = 1.0 if matched_best else 0.0

    detailed = 0.0
    for r in candidate_map.values():
        fc = r.get("field_comparison", r.get("fields", {}))
        if not isinstance(fc, dict):
            fc = {}
        blob = json.dumps(r, ensure_ascii=False).lower()
        field_hits = 0
        for field in REQUIRED_FIELDS:
            zh = {
                "title": "题名",
                "author": "责任",
                "edition": "版本",
                "collection": "馆藏",
            }[field]
            if field in fc or zh in fc or re.search(field + r"|"+ zh, blob):
                field_hits += 1
        detailed += field_hits / len(REQUIRED_FIELDS)
    scores["field_details"] = detailed / len(EXPECTED)

    relation_hits = 0
    evidence_hits = 0
    confidence_hits = 0
    for cid, expected in EXPECTED.items():
        r = candidate_map.get(cid)
        if not r:
            continue
        relation = _normalize_relation(r.get("relation", r.get("alignment_type", "")))
        if relation in expected["relations"]:
            relation_hits += 1
        blob = json.dumps(r, ensure_ascii=False)
        if any(anchor in blob for anchor in expected["anchors"]):
            evidence_hits += 1
        confidence = _as_number(r.get("confidence", r.get("score", r.get("置信度"))))
        if confidence is not None:
            low, high = expected["confidence"]
            confidence_hits += 1 if low <= confidence <= high else 0
    scores["relation_accuracy"] = relation_hits / len(EXPECTED)
    scores["evidence_anchors"] = evidence_hits / len(EXPECTED)
    scores["confidence_calibrated"] = confidence_hits / len(EXPECTED)

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
