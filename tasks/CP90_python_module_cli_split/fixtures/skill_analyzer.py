"""Skill analysis module for agent security assessment.

Contains functions for extracting, analyzing, and reporting on
agent skill configurations. These should be split into standalone
CLI tools in the tools/ directory.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def extract_skill_metadata(skill_path: str) -> Dict:
    """Extract metadata from a SKILL.md file.

    Reads the skill file and extracts name, description, triggers,
    and step definitions.

    Args:
        skill_path: Path to the SKILL.md file

    Returns:
        Dict with keys: name, description, triggers, steps, raw_content
    """
    content = Path(skill_path).read_text(encoding="utf-8")
    metadata = {"raw_content": content, "name": "", "description": "",
                "triggers": [], "steps": []}

    # Extract name from first heading
    name_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if name_match:
        metadata["name"] = name_match.group(1).strip()

    # Extract description
    desc_match = re.search(r"(?:description|Description)[:\s]*(.+?)(?:\n\n|\n#)",
                           content, re.DOTALL)
    if desc_match:
        metadata["description"] = desc_match.group(1).strip()

    # Extract trigger keywords
    trigger_match = re.search(r"(?:trigger|Trigger|TRIGGER)[:\s]*(.+?)(?:\n\n|\n#)",
                              content, re.DOTALL)
    if trigger_match:
        triggers_raw = trigger_match.group(1)
        metadata["triggers"] = [t.strip().strip("-").strip()
                                for t in triggers_raw.split("\n") if t.strip()]

    # Extract steps
    steps = re.findall(r"(?:Step|step)\s*\d+[:\s]*(.+?)(?=(?:Step|step)\s*\d+|\Z)",
                       content, re.DOTALL)
    metadata["steps"] = [s.strip() for s in steps]

    return metadata


def analyze_skill_permissions(skill_metadata: Dict) -> Dict:
    """Analyze what permissions/capabilities a skill requests.

    Checks for file system access, network calls, shell execution,
    and other potentially risky operations.

    Args:
        skill_metadata: Output from extract_skill_metadata()

    Returns:
        Dict with risk_level (low/medium/high/critical) and findings list
    """
    content = skill_metadata.get("raw_content", "")
    findings = []
    risk_level = "low"

    # Check for shell execution patterns
    shell_patterns = [r"execute_command", r"bash\s", r"subprocess",
                      r"os\.system", r"shell=True"]
    for pat in shell_patterns:
        if re.search(pat, content, re.IGNORECASE):
            findings.append(f"Shell execution pattern: {pat}")
            risk_level = "high"

    # Check for file system access
    fs_patterns = [r"read_file", r"write_file", r"delete_file",
                   r"write_to_file", r"replace_in_file"]
    for pat in fs_patterns:
        if re.search(pat, content, re.IGNORECASE):
            findings.append(f"File system access: {pat}")
            if risk_level == "low":
                risk_level = "medium"

    # Check for network access
    net_patterns = [r"web_search", r"webfetch", r"http[s]?://",
                    r"curl\s", r"wget\s", r"api\."]
    for pat in net_patterns:
        if re.search(pat, content, re.IGNORECASE):
            findings.append(f"Network access: {pat}")
            if risk_level == "low":
                risk_level = "medium"

    # Check for credential/secret patterns
    secret_patterns = [r"api[_-]?key", r"password", r"token",
                       r"secret", r"credential"]
    for pat in secret_patterns:
        if re.search(pat, content, re.IGNORECASE):
            findings.append(f"Credential reference: {pat}")
            risk_level = "critical"

    return {"risk_level": risk_level, "findings": findings}


def generate_report(skills_dir: str, output_format: str = "json") -> str:
    """Generate a security assessment report for all skills in a directory.

    Scans the directory for SKILL.md files, analyzes each one,
    and produces a consolidated report.

    Args:
        skills_dir: Directory containing skill subdirectories
        output_format: 'json' or 'text'

    Returns:
        Formatted report string
    """
    skills_path = Path(skills_dir)
    results = []

    for skill_file in sorted(skills_path.rglob("SKILL.md")):
        metadata = extract_skill_metadata(str(skill_file))
        permissions = analyze_skill_permissions(metadata)
        results.append({
            "path": str(skill_file),
            "name": metadata["name"],
            "risk_level": permissions["risk_level"],
            "findings": permissions["findings"],
            "trigger_count": len(metadata["triggers"]),
            "step_count": len(metadata["steps"]),
        })

    if output_format == "json":
        return json.dumps(results, indent=2, ensure_ascii=False)
    else:
        lines = ["=== Skill Security Assessment Report ===\n"]
        for r in results:
            lines.append(f"Skill: {r['name']}")
            lines.append(f"  Path: {r['path']}")
            lines.append(f"  Risk: {r['risk_level'].upper()}")
            for f in r["findings"]:
                lines.append(f"  - {f}")
            lines.append("")
        return "\n".join(lines)


def compare_skills(skill_a_path: str, skill_b_path: str) -> Dict:
    """Compare two skills for overlap in triggers and capabilities.

    Args:
        skill_a_path: Path to first SKILL.md
        skill_b_path: Path to second SKILL.md

    Returns:
        Dict with overlap analysis
    """
    meta_a = extract_skill_metadata(skill_a_path)
    meta_b = extract_skill_metadata(skill_b_path)

    triggers_a = set(t.lower() for t in meta_a["triggers"])
    triggers_b = set(t.lower() for t in meta_b["triggers"])

    perm_a = analyze_skill_permissions(meta_a)
    perm_b = analyze_skill_permissions(meta_b)

    return {
        "skill_a": meta_a["name"],
        "skill_b": meta_b["name"],
        "trigger_overlap": list(triggers_a & triggers_b),
        "unique_to_a": list(triggers_a - triggers_b),
        "unique_to_b": list(triggers_b - triggers_a),
        "risk_comparison": {
            "a": perm_a["risk_level"],
            "b": perm_b["risk_level"],
        },
    }
