"""Hidden verifier for CP87 — pytest test generation for order_processor."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


METHODS = ["validate_order", "calculate_subtotal", "apply_discount",
           "calculate_tax", "check_stock", "estimate_delivery", "process_order"]


def grade_workspace(ws: Path) -> dict:
    test_file = ws / "test_order_processor.py"
    components = {k: 0.0 for k in [
        "file_created", "valid_python", "imports_pytest", "imports_module",
        "test_methods_coverage", "uses_fixtures_or_helpers",
        "uses_pytest_raises", "exception_tests",
    ]}
    if not test_file.exists():
        return {"overall_score": 0.0, "components": components}

    components["file_created"] = 1.0
    content = test_file.read_text(encoding="utf-8", errors="ignore")

    try:
        ast.parse(content)
        components["valid_python"] = 1.0
    except SyntaxError:
        components["valid_python"] = 0.0

    if "pytest" in content:
        components["imports_pytest"] = 1.0

    if "order_processor" in content or "OrderProcessor" in content:
        components["imports_module"] = 1.0

    # Method coverage: each method referenced in a test
    covered = sum(1 for m in METHODS if m in content)
    components["test_methods_coverage"] = min(covered / 6.0, 1.0)

    # Fixtures / helpers
    if "@pytest.fixture" in content or "def make_" in content or "def build_" in content:
        components["uses_fixtures_or_helpers"] = 1.0

    if "pytest.raises" in content or "with pytest.raises" in content:
        components["uses_pytest_raises"] = 1.0

    # Exception tests
    if "InvalidOrderError" in content:
        components["exception_tests"] = 1.0

    weights = {
        "file_created": 0.05,
        "valid_python": 0.10,
        "imports_pytest": 0.10,
        "imports_module": 0.10,
        "test_methods_coverage": 0.30,
        "uses_fixtures_or_helpers": 0.15,
        "uses_pytest_raises": 0.10,
        "exception_tests": 0.10,
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
