"""Hidden verifier for CP94 — local-business-ai 3 engine modules."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    score_engine = ws / "core" / "score_engine" / "engine.py"
    rank_engine = ws / "core" / "rank_chase" / "engine.py"
    promo_engine = ws / "core" / "promotion" / "engine.py"

    components = {k: 0.0 for k in [
        "score_engine_exists", "rank_engine_exists", "promo_engine_exists",
        "score_calls_diagnoser", "rank_uses_adapter",
        "promo_has_review_gate", "promo_no_auto_charge",
        "test_files_exist", "engines_have_async",
    ]}

    score_text = _read(score_engine)
    if len(score_text) >= 500:
        components["score_engine_exists"] = 1.0
    elif len(score_text) >= 200:
        components["score_engine_exists"] = 0.5

    rank_text = _read(rank_engine)
    if len(rank_text) >= 500:
        components["rank_engine_exists"] = 1.0
    elif len(rank_text) >= 200:
        components["rank_engine_exists"] = 0.5

    promo_text = _read(promo_engine)
    if len(promo_text) >= 500:
        components["promo_engine_exists"] = 1.0
    elif len(promo_text) >= 200:
        components["promo_engine_exists"] = 0.5

    if re.search(r"(from.*diagnoser|import.*diagnoser|Diagnoser|diagnos)", score_text, re.I):
        components["score_calls_diagnoser"] = 1.0
    if re.search(r"(from.*industry_adapter|import.*industry_adapter|IndustryAdapter|IndustryRankConfig)",
                  rank_text, re.I):
        components["rank_uses_adapter"] = 1.0

    review_kw = ["人工审核", "manual", "review", "approval", "审批", "confirm",
                 "human_review", "manual_review", "审核", "确认后",
                 "pending_review", "待审核", "人工确认"]
    if any(kw.lower() in promo_text.lower() for kw in review_kw):
        components["promo_has_review_gate"] = 1.0

    # No auto-charge: should NOT contain bare 'charge()' or 'auto_pay' style without review
    auto_charge_bad = bool(re.search(r"auto.?(charge|pay|deduct)|自动扣费|自动支付", promo_text, re.I))
    if not auto_charge_bad:
        components["promo_no_auto_charge"] = 1.0
    elif components["promo_has_review_gate"] > 0:
        components["promo_no_auto_charge"] = 0.5

    test_files = list((ws / "tests").glob("test_*.py")) if (ws / "tests").is_dir() else []
    if len(test_files) >= 3:
        components["test_files_exist"] = 1.0
    elif len(test_files) >= 1:
        components["test_files_exist"] = 0.5

    async_count = sum(1 for t in [score_text, rank_text, promo_text]
                       if re.search(r"async\s+def|asyncio|await\s+", t))
    components["engines_have_async"] = min(async_count / 2.0, 1.0)

    weights = {
        "score_engine_exists": 0.10,
        "rank_engine_exists": 0.10,
        "promo_engine_exists": 0.10,
        "score_calls_diagnoser": 0.15,
        "rank_uses_adapter": 0.15,
        "promo_has_review_gate": 0.15,
        "promo_no_auto_charge": 0.10,
        "test_files_exist": 0.10,
        "engines_have_async": 0.05,
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
