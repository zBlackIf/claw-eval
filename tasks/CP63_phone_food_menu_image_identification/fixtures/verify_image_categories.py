"""Hidden verifier for CP63 — phone/food/menu image identification.

Ground truth (visually verified):
  item_a.jpg = phone (iPhone home screen)
  item_b.jpg = food (pizza in box)
  item_c.jpg = menu (crumpled grocery store receipt)
"""
from __future__ import annotations

import json
from pathlib import Path


TRUTH = {
    "phone": "images/item_a.jpg",
    "food": "images/item_b.jpg",
    "menu": "images/item_c.jpg",
}
VALID_PATHS = set(TRUTH.values())


def grade_workspace(ws: Path) -> dict:
    out = ws / "image_categories.json"
    components = {k: 0.0 for k in [
        "file_created", "valid_json_shape", "has_required_categories",
        "values_are_valid_paths", "uses_each_image_once",
        "phone_correct", "food_correct", "menu_correct",
    ]}

    if not out.exists():
        return {"overall_score": 0.0, "components": components}
    components["file_created"] = 1.0

    try:
        payload = json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return {"overall_score": 0.06, "components": components}

    if not isinstance(payload, dict):
        return {"overall_score": 0.06, "components": components}
    components["valid_json_shape"] = 1.0

    required = {"phone", "food", "menu"}
    if required.issubset(set(payload.keys())):
        components["has_required_categories"] = 1.0
    else:
        # Partial credit if any required key present
        components["has_required_categories"] = len(set(payload.keys()) & required) / 3.0

    values = [payload.get("phone"), payload.get("food"), payload.get("menu")]
    if all(isinstance(v, str) and v in VALID_PATHS for v in values):
        components["values_are_valid_paths"] = 1.0
    elif any(isinstance(v, str) and v in VALID_PATHS for v in values):
        components["values_are_valid_paths"] = 0.5

    string_vals = [v for v in values if isinstance(v, str)]
    if len(string_vals) == 3 and len(set(string_vals)) == 3:
        components["uses_each_image_once"] = 1.0

    if payload.get("phone") == TRUTH["phone"]:
        components["phone_correct"] = 1.0
    if payload.get("food") == TRUTH["food"]:
        components["food_correct"] = 1.0
    if payload.get("menu") == TRUTH["menu"]:
        components["menu_correct"] = 1.0

    weights = {
        "file_created": 0.05,
        "valid_json_shape": 0.05,
        "has_required_categories": 0.10,
        "values_are_valid_paths": 0.10,
        "uses_each_image_once": 0.10,
        "phone_correct": 0.20,
        "food_correct": 0.20,
        "menu_correct": 0.20,
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
