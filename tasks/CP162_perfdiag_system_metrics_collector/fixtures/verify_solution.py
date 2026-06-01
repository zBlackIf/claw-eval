"""Hidden verifier for CP162 — perfdiag System Metrics Collector."""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_project_root(ws: Path) -> Path | None:
    """Find perfdiag project root - could be at workspace level or in a subdirectory."""
    for candidate in [
        ws / "fixtures" / "perfdiag_starter",
        ws / "perfdiag_starter",
        ws / "fixtures" / "perfdiag",
        ws / "perfdiag",
        ws,
    ]:
        if (candidate / "main.py").exists():
            return candidate
    for main_file in ws.rglob("main.py"):
        content = _read(main_file)
        if "collector" in content.lower() or "system_collector" in content.lower():
            return main_file.parent
    return None


def _check_type_annotations(source: str) -> float:
    """Check if functions have return type annotations — discriminates quality."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0.0
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not functions:
        return 0.0
    annotated = sum(1 for f in functions if f.returns is not None)
    return annotated / len(functions)


def _check_serialization_method(source: str) -> bool:
    """Check if the model has a proper to_dict/to_json/asdict serialization method."""
    has_method = bool(re.search(r'def\s+(to_dict|to_json|as_dict|serialize)\s*\(', source))
    has_asdict = "asdict" in source  # dataclasses.asdict
    has_model_dump = "model_dump" in source or "dict()" in source  # pydantic
    return has_method or has_asdict or has_model_dump


def _check_error_handling(source: str) -> float:
    """Check if collector uses proper error handling around psutil calls.

    Strong models wrap system calls in try/except because psutil can raise
    AccessDenied, NoSuchProcess, or OSError on certain platforms. Weak models
    just call raw APIs without any protection.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0.0
    # Count try/except blocks
    try_blocks = [n for n in ast.walk(tree) if isinstance(n, ast.Try)]
    if not try_blocks:
        return 0.0
    # Check if any try block contains a psutil-related call
    for try_node in try_blocks:
        for node in ast.walk(try_node):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "psutil":
                    return 1.0
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "psutil":
                    return 1.0
    # Has try/except but not around psutil — partial credit
    return 0.4


def _check_proper_layering(root: Path) -> float:
    """Verify proper import layering: main -> collector -> model.

    Strong models create a clean dependency chain where:
    - main.py imports from collectors (not from models directly to build metrics)
    - collectors/system_collector.py imports from models/metrics.py
    - models/metrics.py is self-contained (no upward imports)

    Weak models tend to dump everything in main.py or skip the model import chain.
    """
    main_content = _read(root / "main.py") if (root / "main.py").exists() else ""
    collector_content = _read(root / "collectors" / "system_collector.py") if (root / "collectors" / "system_collector.py").exists() else ""
    model_content = _read(root / "models" / "metrics.py") if (root / "models" / "metrics.py").exists() else ""

    score = 0.0
    checks = 0
    total = 4

    # Check 1: collector imports from models (proper dependency direction)
    if collector_content:
        imports_model = bool(
            re.search(r'from\s+(models|\.models|perfdiag_starter\.models)', collector_content)
            or re.search(r'import\s+(models|\.models)', collector_content)
        )
        # Also accept if SystemMetric is referenced AND imported
        if imports_model or ("SystemMetric" in collector_content and "import" in collector_content and "SystemMetric" in collector_content.split("import")[-1] if "import" in collector_content else False):
            checks += 1

    # Check 2: main.py does NOT directly instantiate SystemMetric (delegates to collector)
    if main_content:
        main_instantiates_metric = bool(re.search(r'SystemMetric\s*\(', main_content))
        main_calls_collect = bool(re.search(r'collect|get_metrics|gather', main_content, re.IGNORECASE))
        if main_calls_collect and not main_instantiates_metric:
            checks += 1
        elif main_calls_collect:
            checks += 0.5

    # Check 3: model file is self-contained (no imports from collectors/utils/main)
    if model_content:
        upward_import = bool(re.search(r'from\s+(collectors|utils|main)', model_content))
        if not upward_import:
            checks += 1

    # Check 4: main.py uses json.dumps with indent for pretty output
    if main_content:
        if re.search(r'json\.dumps\s*\([^)]*indent\s*=', main_content):
            checks += 1
        elif "json.dumps" in main_content:
            checks += 0.4

    score = checks / total
    return round(score, 4)


def _check_docstrings_and_documentation(root: Path) -> float:
    """Check for module/class/function docstrings in key files.

    Strong models add meaningful docstrings. Weak models skip documentation entirely.
    This is a subtle quality signal that correlates with overall code quality.
    """
    score = 0.0
    total_checks = 5
    passed = 0

    files_to_check = [
        root / "main.py",
        root / "collectors" / "system_collector.py",
        root / "models" / "metrics.py",
    ]

    for fpath in files_to_check:
        if not fpath.exists():
            continue
        content = _read(fpath)
        if not content.strip():
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        # Check module-level docstring
        if (tree.body and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, (ast.Constant, ast.Str))):
            passed += 1
            break  # At least one module docstring is enough for this check

    # Check class docstring on SystemMetric
    metrics_file = root / "models" / "metrics.py"
    if metrics_file.exists():
        content = _read(metrics_file)
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and "Metric" in node.name:
                    if (node.body and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                        passed += 1
                    break
        except SyntaxError:
            pass

    # Check function docstring on the main collect function
    collector_file = root / "collectors" / "system_collector.py"
    if collector_file.exists():
        content = _read(collector_file)
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and "collect" in node.name.lower():
                    if (node.body and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
                        passed += 1
                    break
        except SyntaxError:
            pass

    # Normalize: need at least 2 out of 3 possible docstring locations for full credit
    if passed >= 3:
        return 1.0
    elif passed == 2:
        return 0.7
    elif passed == 1:
        return 0.35
    return 0.0


def _validate_output_values(data: dict) -> float:
    """Validate that output values are semantically correct (not just present)."""
    score = 0.0
    checks_total = 5
    checks_passed = 0

    # CPU usage should be a number 0-100
    cpu = data.get("cpu_usage")
    if isinstance(cpu, (int, float)) and 0.0 <= cpu <= 100.0:
        checks_passed += 1

    # Memory usage should be a number 0-100
    mem = data.get("memory_usage")
    if isinstance(mem, (int, float)) and 0.0 <= mem <= 100.0:
        checks_passed += 1

    # Disk usage should be a number 0-100
    disk = data.get("disk_usage")
    if isinstance(disk, (int, float)) and 0.0 <= disk <= 100.0:
        checks_passed += 1

    # Load averages should be non-negative floats
    load_ok = True
    for key in ("load_avg_1m", "load_avg_5m", "load_avg_15m"):
        val = data.get(key)
        if not isinstance(val, (int, float)) or val < 0.0:
            load_ok = False
            break
    if load_ok:
        checks_passed += 1

    # Timestamp should be valid ISO 8601
    ts = data.get("timestamp", "")
    if isinstance(ts, str) and ts:
        try:
            # Accept common ISO formats
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            checks_passed += 1
        except (ValueError, TypeError):
            pass

    return checks_passed / checks_total


def grade_workspace(ws: Path) -> dict:
    root = _find_project_root(ws)

    components = {k: 0.0 for k in [
        "project_structure",
        "system_metric_model",
        "collector_implementation",
        "main_outputs_json",
        "no_overengineering",
        "code_quality",
        "runtime_value_correctness",
        "error_resilience",
        "architectural_layering",
        "documentation_quality",
    ]}

    if root is None:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
            "error": "Could not find perfdiag project root with main.py",
        }

    # --- Dimension 1: Project Structure ---
    structure_score = 0.0
    required_files = [
        "main.py",
        "collectors/system_collector.py",
        "models/metrics.py",
        "utils/formatter.py",
    ]
    found_count = sum(1 for rel in required_files if (root / rel).exists())
    structure_score = found_count / len(required_files)

    # __init__.py in packages — required for proper Python packaging
    init_files = ["collectors/__init__.py", "models/__init__.py", "utils/__init__.py"]
    init_count = sum(1 for f in init_files if (root / f).exists())
    if init_count == 3:
        structure_score = min(1.0, structure_score + 0.05)

    components["project_structure"] = round(structure_score, 4)

    # --- Dimension 2: SystemMetric data model ---
    metrics_file = root / "models" / "metrics.py"
    if metrics_file.exists():
        content = _read(metrics_file)
        model_score = 0.0

        # Must have a proper class named SystemMetric (exact name matters)
        if "class" in content and "SystemMetric" in content:
            model_score += 0.15
        elif "class" in content:
            model_score += 0.05  # Partial credit for any class

        # Check required fields — all 9 must be present
        required_fields = [
            "layer", "hostname", "timestamp",
            "cpu_usage", "memory_usage",
            "load_avg_1m", "load_avg_5m", "load_avg_15m",
            "disk_usage",
        ]
        found_fields = sum(1 for f in required_fields if f in content)
        model_score += 0.45 * (found_fields / len(required_fields))

        # Must use a structured type system (dataclass/pydantic/namedtuple)
        if "dataclass" in content or "NamedTuple" in content or "BaseModel" in content:
            model_score += 0.15
        elif "TypedDict" in content:
            model_score += 0.08  # TypedDict is weaker — no runtime validation

        # Must have serialization method (not ad-hoc dict building in main)
        if _check_serialization_method(content):
            model_score += 0.25

        components["system_metric_model"] = round(min(1.0, model_score), 4)

    # --- Dimension 3: Collector implementation ---
    collector_file = root / "collectors" / "system_collector.py"
    if collector_file.exists():
        content = _read(collector_file)
        coll_score = 0.0

        # Must import psutil
        if "import psutil" in content:
            coll_score += 0.2
        elif "psutil" in content:
            coll_score += 0.1

        # Must use psutil.cpu_percent (correct API)
        if "cpu_percent" in content:
            coll_score += 0.15
        elif "cpu" in content.lower():
            coll_score += 0.05

        # Must use psutil.virtual_memory (correct API)
        if "virtual_memory" in content:
            coll_score += 0.15
        elif "memory" in content.lower():
            coll_score += 0.05

        # Must collect load average
        if "getloadavg" in content or "os.getloadavg" in content:
            coll_score += 0.15
        elif "load" in content.lower():
            coll_score += 0.05

        # Must use psutil.disk_usage('/') with root partition
        if "disk_usage" in content and ("'/'" in content or '"/"' in content):
            coll_score += 0.15
        elif "disk_usage" in content:
            coll_score += 0.08

        # Collector must return a SystemMetric instance (not raw dict)
        if "SystemMetric" in content and ("return" in content):
            coll_score += 0.2
        elif "return" in content:
            coll_score += 0.05

        components["collector_implementation"] = round(min(1.0, coll_score), 4)

    # --- Dimension 4: main.py runs and outputs valid JSON ---
    main_file = root / "main.py"
    run_score = 0.0
    output_data = None

    if main_file.exists():
        main_content = _read(main_file)

        # Static: imports collector module properly
        if "from collectors" in main_content or "import collectors" in main_content:
            run_score += 0.1
        elif "collector" in main_content.lower():
            run_score += 0.05

        # Static: uses json module
        if "json" in main_content:
            run_score += 0.05

        # Actually run main.py
        try:
            result = subprocess.run(
                [sys.executable, str(main_file)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(root),
                env={**__import__("os").environ, "PYTHONPATH": str(root)},
            )
            stdout = result.stdout.strip()
            if result.returncode == 0 and stdout:
                try:
                    data = json.loads(stdout)
                    if isinstance(data, dict):
                        run_score += 0.25  # Runs successfully + valid JSON
                        output_data = data
                        # Check all required fields present
                        expected_keys = [
                            "layer", "hostname", "timestamp",
                            "cpu_usage", "memory_usage",
                            "load_avg_1m", "load_avg_5m", "load_avg_15m",
                            "disk_usage",
                        ]
                        found_keys = sum(1 for k in expected_keys if k in data)
                        run_score += 0.35 * (found_keys / len(expected_keys))
                        # layer must equal "SYSTEM"
                        if data.get("layer") == "SYSTEM":
                            run_score += 0.1
                        # hostname must be non-empty string
                        if isinstance(data.get("hostname"), str) and data["hostname"]:
                            run_score += 0.05
                        # JSON should be pretty-printed (indent)
                        if "\n" in stdout and "  " in stdout:
                            run_score += 0.05
                except json.JSONDecodeError:
                    run_score += 0.05
            elif result.returncode != 0:
                # Ran but crashed — minimal credit
                run_score += 0.0
        except (subprocess.TimeoutExpired, Exception):
            pass

    components["main_outputs_json"] = round(min(1.0, run_score), 4)

    # --- Dimension 5: No over-engineering ---
    overeng_score = 1.0
    all_content = ""
    for py_file in root.rglob("*.py"):
        all_content += _read(py_file)

    forbidden = ["flask", "fastapi", "django", "uvicorn", "sqlalchemy",
                 "logging.config", "celery", "redis", "asyncio"]
    for fw in forbidden:
        if fw in all_content.lower():
            overeng_score -= 0.2

    py_count = sum(1 for _ in root.rglob("*.py"))
    if py_count > 15:
        overeng_score -= 0.3
    elif py_count > 10:
        overeng_score -= 0.15

    # Penalize if argparse/click is used (not required for MVP)
    if "argparse" in all_content or "import click" in all_content:
        overeng_score -= 0.15

    components["no_overengineering"] = round(max(0.0, overeng_score), 4)

    # --- Dimension 6: Code Quality (HIDDEN — discriminates strong models) ---
    quality_score = 0.0
    quality_checks = 0
    quality_total = 4

    # 6a: Type annotations in collector and model files
    collector_content = _read(root / "collectors" / "system_collector.py") if (root / "collectors" / "system_collector.py").exists() else ""
    metrics_content = _read(root / "models" / "metrics.py") if (root / "models" / "metrics.py").exists() else ""

    annotation_ratio = 0.0
    combined_source = collector_content + "\n" + metrics_content
    if combined_source.strip():
        annotation_ratio = _check_type_annotations(combined_source)
    if annotation_ratio >= 0.5:
        quality_checks += 1
    elif annotation_ratio >= 0.25:
        quality_checks += 0.5

    # 6b: No wildcard imports anywhere
    has_wildcard = bool(re.search(r'from\s+\S+\s+import\s+\*', all_content))
    if not has_wildcard:
        quality_checks += 1

    # 6c: Collector uses proper function (not just top-level script code)
    if collector_content:
        try:
            tree = ast.parse(collector_content)
            has_collect_func = any(
                isinstance(n, ast.FunctionDef) and "collect" in n.name.lower()
                for n in ast.walk(tree)
            )
            if has_collect_func:
                quality_checks += 1
            else:
                quality_checks += 0.3
        except SyntaxError:
            pass

    # 6d: main.py uses if __name__ == "__main__" guard
    main_content = _read(root / "main.py") if (root / "main.py").exists() else ""
    if '__name__' in main_content and '__main__' in main_content:
        quality_checks += 1
    elif "def main" in main_content:
        quality_checks += 0.5

    quality_score = quality_checks / quality_total
    components["code_quality"] = round(min(1.0, quality_score), 4)

    # --- Dimension 7: Runtime Value Correctness (HIDDEN — validates actual output semantics) ---
    if output_data:
        components["runtime_value_correctness"] = round(
            _validate_output_values(output_data), 4
        )
    else:
        components["runtime_value_correctness"] = 0.0

    # --- Dimension 8: Error Resilience (HIDDEN — strong models protect psutil calls) ---
    collector_src = _read(root / "collectors" / "system_collector.py") if (root / "collectors" / "system_collector.py").exists() else ""
    components["error_resilience"] = round(_check_error_handling(collector_src), 4)

    # --- Dimension 9: Architectural Layering (HIDDEN — proper dependency chain) ---
    components["architectural_layering"] = _check_proper_layering(root)

    # --- Dimension 10: Documentation Quality (HIDDEN — docstrings in key files) ---
    components["documentation_quality"] = _check_docstrings_and_documentation(root)

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        "project_structure": 0.05,
        "system_metric_model": 0.13,
        "collector_implementation": 0.14,
        "main_outputs_json": 0.18,
        "no_overengineering": 0.05,
        "code_quality": 0.13,
        "runtime_value_correctness": 0.10,
        "error_resilience": 0.08,
        "architectural_layering": 0.08,
        "documentation_quality": 0.06,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
