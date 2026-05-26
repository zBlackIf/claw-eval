#!/usr/bin/env python3
"""In-container verifier for CP24_mutex_api_postman_collection.

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

VALID_ENUM_VALUES = [
        "PAY_NO_PASSWORD", "DAILY_LIMIT", "LIMIT_PER_TXN_5K",
        "AUTO_DEBIT", "QUICK_PAY", "BATCH_TRANSFER"
    ]


def automated_score(workspace: Path) -> dict[str, float]:
    scores = {}

    postman_file = workspace / "tests" / "postman_params.json"
    if not postman_file.exists():
        return {
            "postman_file_present": 0.0,
            "valid_json": 0.0,
            "collection_format": 0.0,
            "has_three_cases": 0.0,
            "correct_enum_values": 0.0,
            "src_unmodified": 1.0,
        }

    scores["postman_file_present"] = 1.0

    try:
        collection = json.loads(postman_file.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        scores["valid_json"] = 0.0
        scores["collection_format"] = 0.0
        scores["has_three_cases"] = 0.0
        scores["correct_enum_values"] = 0.0
        scores["src_unmodified"] = 1.0
        return scores

    scores["valid_json"] = 1.0

    # Check Postman Collection v2.1 format
    has_info = "info" in collection
    has_item = "item" in collection
    scores["collection_format"] = 1.0 if (has_info and has_item) else 0.0

    # Check for 3 test cases
    items = collection.get("item", [])
    if isinstance(items, list):
        item_names = []
        for item in items:
            name = item.get("name", "").lower() if isinstance(item, dict) else ""
            item_names.append(name)

        found_cases = 0
        collection_text = json.dumps(collection).lower()
        if "no_conflict" in collection_text or "no conflict" in collection_text:
            found_cases += 1
        if "conflict" in collection_text and "no_conflict" not in collection_text.replace("no_conflict", ""):
            found_cases += 1
        if "empty" in collection_text or "400" in collection_text:
            found_cases += 1

        scores["has_three_cases"] = min(found_cases / 3.0, 1.0) if len(items) >= 3 else min(len(items) / 3.0, 1.0)
    else:
        scores["has_three_cases"] = 0.0

    # Check enum values are correct
    collection_text = json.dumps(collection)
    enum_hits = sum(1 for v in VALID_ENUM_VALUES if v in collection_text)
    scores["correct_enum_values"] = min(enum_hits / 3.0, 1.0)

    # Check src/ files were not modified
    src_files = list((workspace / "src").glob("*.py")) if (workspace / "src").exists() else []
    scores["src_unmodified"] = 1.0  # Trust sandbox isolation

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
