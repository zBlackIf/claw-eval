"""Hidden verifier for CP180 — MD to RAG JSON Converter."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _find_script(ws: Path) -> Path | None:
    """Find the conversion script."""
    candidates = [
        ws / "fixtures" / "md_to_rag_json.py",
        ws / "md_to_rag_json.py",
        ws / "fixtures" / "convert.py",
        ws / "convert.py",
        ws / "fixtures" / "converter.py",
        ws / "converter.py",
        ws / "fixtures" / "md2rag.py",
        ws / "md2rag.py",
        ws / "fixtures" / "markdown_to_json.py",
        ws / "markdown_to_json.py",
        ws / "fixtures" / "md_to_json.py",
        ws / "md_to_json.py",
        ws / "fixtures" / "main.py",
        ws / "main.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: find any .py file that looks like the converter
    for p in ws.rglob("*.py"):
        if p.name == "verify_solution.py":
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Broad match: any script that deals with json output and markdown/docs
        indicators = 0
        if "json" in content:
            indicators += 1
        if any(kw in content.lower() for kw in [".md", "markdown", "docs_input", "docs_output"]):
            indicators += 1
        if any(kw in content for kw in ["open(", "Path(", "glob", "walk", "listdir"]):
            indicators += 1
        if indicators >= 2:
            return p
    return None


def _find_output(ws: Path) -> Path | None:
    """Find the JSON output file."""
    candidates = [
        ws / "fixtures" / "docs_output.json",
        ws / "docs_output.json",
        ws / "fixtures" / "output.json",
        ws / "output.json",
        ws / "fixtures" / "rag_output.json",
        ws / "rag_output.json",
        ws / "fixtures" / "result.json",
        ws / "result.json",
        ws / "fixtures" / "documents.json",
        ws / "documents.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: any .json file that looks like a document array
    for p in ws.rglob("*.json"):
        if p.name in ("package.json", "tsconfig.json"):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return p
            # Also accept a dict with a list inside
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list) and len(v) > 0:
                        return p
        except Exception:
            continue
    return None


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "script_exists",
        "script_runs",
        "output_valid_json",
        "all_docs_processed",
        "doc_type_classification",
        "title_extraction",
        "section_extraction",
        "encoding_handling",
        "has_unique_ids",
    ]}

    # 1. Script exists
    script = _find_script(ws)
    if not script:
        return _result(components)
    components["script_exists"] = 1.0

    # 2. Try running the script
    output_file = ws / "fixtures" / "docs_output.json"
    env = os.environ.copy()
    try:
        # Determine best cwd: prefer where docs_input lives
        if (ws / "fixtures" / "docs_input").exists():
            run_cwd = str(ws / "fixtures")
        elif (ws / "docs_input").exists():
            run_cwd = str(ws)
        else:
            run_cwd = str(script.parent)
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=run_cwd,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode == 0:
            components["script_runs"] = 1.0
        else:
            # Partial credit if it ran but had errors
            components["script_runs"] = 0.3
    except Exception:
        components["script_runs"] = 0.0

    # 3. Find and validate output JSON
    output = _find_output(ws)
    if not output:
        return _result(components)

    try:
        data = json.loads(output.read_text(encoding="utf-8"))
    except Exception:
        return _result(components)

    if not isinstance(data, list):
        # Maybe it's wrapped in an object
        if isinstance(data, dict) and "documents" in data:
            data = data["documents"]
        elif isinstance(data, dict) and "data" in data:
            data = data["data"]
        else:
            return _result(components)

    if len(data) == 0:
        return _result(components)

    components["output_valid_json"] = 1.0

    # 4. All docs processed (9 .md files total, one is GBK-encoded)
    total_md_files = 9
    # Allow some tolerance: at least 7 out of 8
    doc_count = len(data)
    if doc_count >= total_md_files:
        components["all_docs_processed"] = 1.0
    elif doc_count >= total_md_files - 1:
        components["all_docs_processed"] = 0.8
    elif doc_count >= total_md_files - 2:
        components["all_docs_processed"] = 0.5
    else:
        components["all_docs_processed"] = max(0.0, doc_count / total_md_files)

    # 5. Document type classification
    type_score = _check_doc_type_classification(data)
    components["doc_type_classification"] = type_score

    # 6. Title extraction
    title_score = _check_title_extraction(data)
    components["title_extraction"] = title_score

    # 7. Section/heading extraction
    section_score = _check_section_extraction(data)
    components["section_extraction"] = section_score

    # 8. Encoding handling (the GBK file should be processed)
    encoding_score = _check_encoding_handling(data)
    components["encoding_handling"] = encoding_score

    # 9. Unique IDs
    id_score = _check_unique_ids(data)
    components["has_unique_ids"] = id_score

    return _result(components)


def _check_doc_type_classification(data: list) -> float:
    """Check if documents have type/category classification derived from path."""
    classified = 0
    for doc in data:
        # Look for type/category/doc_type field (broad set of common field names)
        doc_type = ""
        for key in ["type", "doc_type", "category", "document_type", "classification",
                    "file_type", "kind", "doc_category", "label"]:
            if key in doc:
                doc_type = str(doc[key]).lower()
                break

        # Also check if path-based classification exists
        source = ""
        for key in ["source_path", "path", "file_path", "source", "relative_path",
                    "filename", "file_name", "file"]:
            if key in doc:
                source = str(doc[key]).lower()
                break

        if doc_type:
            # Has a type/category field — check if it's a meaningful classification
            type_keywords = ["command", "命令", "cmd", "reference", "alarm", "告警",
                            "alert", "notification", "log", "日志", "syslog", "event",
                            "mib", "snmp", "oid"]
            if any(kw in doc_type for kw in type_keywords):
                # Good classification — full credit
                classified += 1
            elif len(doc_type) > 0 and doc_type not in ("unknown", "other", "none", ""):
                # Has a non-empty type field that's not a generic placeholder
                classified += 0.7
            else:
                classified += 0.3
        elif source:
            # No explicit type field, but if the path clearly contains type info,
            # give partial credit — the agent at least preserved the path
            if any(d in source for d in ["commands", "alarms", "logs", "mib"]):
                classified += 0.4

    if len(data) == 0:
        return 0.0
    return min(1.0, classified / len(data))


def _check_title_extraction(data: list) -> float:
    """Check if titles are correctly extracted from markdown headings."""
    # Keywords that should appear somewhere in the title for each document.
    # We match on partial keywords from the filenames/content.
    expected_keywords = [
        ["routing", "route", "ip routing"],
        ["vlanif", "interface"],
        ["bgp", "peer"],
        ["arp", "display arp"],
        ["ospf", "nbr"],
        ["ifnet", "link_down", "link down"],
        ["sece", "login"],
        ["ntp", "sync"],
        ["temperature", "threshold", "hwentity"],
    ]

    found = 0
    for doc in data:
        title = ""
        for key in ["title", "name", "heading", "doc_title", "document_title",
                    "header", "main_title"]:
            if key in doc:
                title = str(doc[key]).lower().strip()
                break
        if not title:
            continue

        # Normalize for comparison
        normalized_title = title.replace("_", " ").replace("-", " ").replace("/", " ")

        matched = False
        for keyword_group in expected_keywords:
            for kw in keyword_group:
                if kw in title or kw in normalized_title:
                    matched = True
                    break
            if matched:
                break

        if matched:
            found += 1
        elif len(title) > 3:
            # Has a non-trivial title — partial credit even if we can't match it
            found += 0.4

    if len(data) == 0:
        return 0.0
    return min(1.0, found / min(len(data), 9))


def _check_section_extraction(data: list) -> float:
    """Check if section structure (## headings) is extracted."""
    has_sections = 0
    for doc in data:
        # Look for sections/headings/structure field
        sections = None
        for key in ["sections", "headings", "structure", "toc", "chapters",
                    "section_titles", "headers", "outline", "section_list",
                    "sub_sections", "subsections", "heading_list", "sections_count",
                    "heading_count", "num_sections", "table_of_contents"]:
            if key in doc and doc[key]:
                sections = doc[key]
                break

        if sections:
            if isinstance(sections, list) and len(sections) > 0:
                has_sections += 1
            elif isinstance(sections, int) and sections > 0:
                has_sections += 0.7
            elif isinstance(sections, dict) and len(sections) > 0:
                has_sections += 0.8
            elif isinstance(sections, str) and len(sections) > 5:
                has_sections += 0.6
        else:
            # Check if content contains section info in other ways
            content = str(doc.get("content", ""))
            # Also check for metadata fields that indicate structure awareness
            has_structural_field = any(
                k in doc for k in ["tables_count", "table_count", "num_tables",
                                   "heading_level", "depth", "word_count",
                                   "char_count", "keywords", "summary"]
            )
            if has_structural_field:
                has_sections += 0.5
            elif "##" in content:
                # They included raw content which has headings - partial credit
                has_sections += 0.3

    if len(data) == 0:
        return 0.0
    return min(1.0, has_sections / len(data))


def _check_encoding_handling(data: list) -> float:
    """Check if the GBK-encoded file (display_arp.md) was processed."""
    for doc in data:
        source = ""
        for key in ["source_path", "path", "file_path", "source", "relative_path",
                    "filename", "file_name", "file"]:
            if key in doc:
                source = str(doc[key]).lower()
                break

        title = ""
        for key in ["title", "name", "heading", "doc_title", "document_title",
                    "header", "main_title"]:
            if key in doc:
                title = str(doc[key]).lower()
                break

        if "arp" in source or "arp" in title:
            # The GBK file was processed
            content = str(doc.get("content", ""))
            if "arp" in content.lower() and len(content) > 50:
                return 1.0
            # Even if content is short, the file was found and processed
            return 0.7
    return 0.0


def _check_unique_ids(data: list) -> float:
    """Check if each document has a unique identifier."""
    ids = set()
    has_id_field = 0
    for doc in data:
        doc_id = None
        for key in ["id", "doc_id", "document_id", "uid", "hash", "uuid"]:
            if key in doc and doc[key]:
                doc_id = str(doc[key])
                break

        if doc_id is None:
            # Accept source_path as unique ID
            for key in ["source_path", "path", "file_path"]:
                if key in doc and doc[key]:
                    doc_id = str(doc[key])
                    break

        if doc_id:
            has_id_field += 1
            ids.add(doc_id)

    if len(data) == 0:
        return 0.0

    # All docs have IDs
    has_field_score = has_id_field / len(data)
    # All IDs are unique
    unique_score = len(ids) / len(data) if has_id_field > 0 else 0.0

    return min(1.0, (has_field_score + unique_score) / 2)


def _result(components: dict) -> dict:
    weights = {
        "script_exists": 0.10,
        "script_runs": 0.15,
        "output_valid_json": 0.15,
        "all_docs_processed": 0.10,
        "doc_type_classification": 0.15,
        "title_extraction": 0.10,
        "section_extraction": 0.10,
        "encoding_handling": 0.10,
        "has_unique_ids": 0.05,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try multiple workspace roots — the sandbox may mount files differently.
    # Priority: /workspace (standard), /workspace/fixtures, script's own directory.
    candidates = [
        Path("/workspace"),
        Path("/workspace/fixtures"),
        Path(__file__).resolve().parent,          # same dir as verify_solution.py
        Path(__file__).resolve().parent.parent,   # one level up from verify
    ]
    best_result = None
    for ws in candidates:
        if not ws.exists():
            continue
        result = grade_workspace(ws)
        if best_result is None or result["overall_score"] > best_result["overall_score"]:
            best_result = result
        if best_result["overall_score"] > 0:
            break
    if best_result is None:
        best_result = grade_workspace(Path("/workspace"))
    print(json.dumps(best_result, ensure_ascii=False))


if __name__ == "__main__":
    main()
