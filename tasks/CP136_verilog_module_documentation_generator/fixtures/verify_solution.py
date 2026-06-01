"""Hidden verifier for CP136 — Verilog Module Documentation Generator.

Checks that documentation was generated for all 3 Verilog modules with
correct structure, accurate port analysis, and proper technical content.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def _find_docs(ws: Path) -> list[Path]:
    """Find all generated markdown documentation files."""
    docs = []
    # Check multiple plausible output locations
    search_dirs = [
        ws / "rtl_project" / "docs",
        ws / "rtl_project" / "doc",
        ws / "rtl_project" / "documentation",
        ws / "docs",
        ws / "doc",
        ws / "documentation",
        ws / "rtl_project",
        ws,
    ]
    for d in search_dirs:
        if d.exists():
            for f in d.rglob("*.md"):
                if f.name.lower() != "readme.md":
                    docs.append(f)
    # Deduplicate
    return list(set(docs))


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _check_module_doc(content: str, module_name: str, checks: dict) -> dict:
    """Check if documentation for a specific module meets quality criteria."""
    result = {}
    cl = content.lower()

    # 1. Module name mentioned
    result["module_mentioned"] = 1.0 if module_name.lower() in cl else 0.0

    # 2. Port table or structured port listing
    has_port_table = bool(re.search(r'\|.*\|.*\|', content))
    has_port_listing = bool(re.search(r'(input|output)\s+', cl))
    has_port_section = bool(re.search(r'(port|端口|接口|信号)', cl))
    result["port_documentation"] = min(1.0, (0.4 if has_port_table else 0.0) +
                                       (0.3 if has_port_listing else 0.0) +
                                       (0.3 if has_port_section else 0.0))

    # 3. Key technical terms for this module
    terms_found = sum(1 for t in checks.get("key_terms", []) if t.lower() in cl)
    total_terms = len(checks.get("key_terms", []))
    result["technical_accuracy"] = terms_found / max(total_terms, 1)

    # 4. Parameters documented
    params = checks.get("parameters", [])
    params_found = sum(1 for p in params if p.lower() in cl)
    result["parameters_documented"] = params_found / max(len(params), 1)

    # 5. Functional description (not just port list)
    has_description = len(content) > 300
    has_sections = content.count("#") >= 2 or content.count("##") >= 1
    has_explanation = bool(re.search(r'(功能|function|purpose|description|说明|原理|工作)', cl))
    result["functional_description"] = min(1.0, (0.3 if has_description else 0.0) +
                                           (0.3 if has_sections else 0.0) +
                                           (0.4 if has_explanation else 0.0))

    return result


def grade_workspace(ws: Path) -> dict:
    """Grade the generated documentation."""
    components = {
        "fifo_doc_exists": 0.0,
        "spi_doc_exists": 0.0,
        "uart_doc_exists": 0.0,
        "fifo_quality": 0.0,
        "spi_quality": 0.0,
        "uart_quality": 0.0,
        "all_modules_covered": 0.0,
        "structured_format": 0.0,
    }

    # Module-specific checks
    module_checks = {
        "fifo_async": {
            "key_terms": ["gray code", "asynchronous", "pointer", "synchroni",
                         "full", "empty", "clock domain", "depth"],
            "parameters": ["DATA_WIDTH", "ADDR_WIDTH", "DEPTH"],
        },
        "spi_master": {
            "key_terms": ["cpol", "cpha", "clock", "shift", "state machine",
                         "mosi", "miso", "chip select", "divider"],
            "parameters": ["CLK_DIV_WIDTH", "DATA_WIDTH"],
        },
        "uart_tx": {
            "key_terms": ["baud", "start bit", "stop bit", "transmit",
                         "shift", "serial", "state"],
            "parameters": ["CLK_FREQ", "BAUD_RATE"],
        },
    }

    docs = _find_docs(ws)
    all_content = "\n".join(_read(d) for d in docs)

    # Check each module doc
    for module_name, checks in module_checks.items():
        # Find the doc that covers this module
        best_content = ""
        for doc in docs:
            content = _read(doc)
            if module_name.lower() in content.lower() or \
               module_name.replace("_", " ").lower() in content.lower():
                if len(content) > len(best_content):
                    best_content = content

        # If no dedicated doc found, check combined doc
        if not best_content and module_name.lower() in all_content.lower():
            best_content = all_content

        exists_key = f"{module_name.split('_')[0]}_doc_exists"
        quality_key = f"{module_name.split('_')[0]}_quality"

        if best_content:
            components[exists_key] = 1.0
            quality_checks = _check_module_doc(best_content, module_name, checks)
            components[quality_key] = round(sum(quality_checks.values()) / len(quality_checks), 4)
        else:
            components[exists_key] = 0.0
            components[quality_key] = 0.0

    # All modules covered
    covered = sum(1 for k in ["fifo_doc_exists", "spi_doc_exists", "uart_doc_exists"]
                  if components[k] > 0)
    components["all_modules_covered"] = covered / 3.0

    # Structured format: check for consistent structure across docs
    structured_count = 0
    for doc in docs:
        content = _read(doc)
        has_headings = content.count("##") >= 2
        has_table = bool(re.search(r'\|.*\|.*\|', content))
        has_code_block = "```" in content
        if has_headings and (has_table or has_code_block):
            structured_count += 1
    components["structured_format"] = min(1.0, structured_count / max(len(docs), 1))

    weights = {
        "fifo_doc_exists": 0.10,
        "spi_doc_exists": 0.10,
        "uart_doc_exists": 0.10,
        "fifo_quality": 0.20,
        "spi_quality": 0.20,
        "uart_quality": 0.15,
        "all_modules_covered": 0.05,
        "structured_format": 0.10,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # The agent sees files at /workspace/fixtures/rtl_project/src/
    # and is asked to write docs to rtl_project/docs/
    # Try multiple plausible workspace roots
    candidates = [
        Path("/workspace/fixtures/rtl_project"),
        Path("/workspace/rtl_project"),
        Path("/workspace/fixtures"),
        Path("/workspace"),
    ]
    ws = Path("/workspace")
    for c in candidates:
        if c.exists() and any(c.rglob("*.v")):
            ws = c
            break
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
