"""Hidden verifier for CP119 — MyBatis Entity + Mapper XML Bug Fix.

Checks:
1. Product.java has @TableField annotations for processValue1-5 mapping to process_value_1 through process_value_5
2. AccessoryPolicyMapper.xml exists with correct namespace and required SQL statements
3. The XML has selectPageWithFilters with proper MyBatis dynamic SQL
4. The XML has selectBySupplierId query
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, List


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(ws: Path, name: str) -> Optional[Path]:
    """Find a file by name anywhere in the workspace."""
    try:
        for p in ws.rglob(name):
            return p
    except Exception:
        pass
    return None


def _find_file_multi(roots: List[Path], name: str) -> Optional[Path]:
    """Find a file by name across multiple root paths."""
    for root in roots:
        try:
            if root.exists():
                for p in root.rglob(name):
                    return p
        except Exception:
            continue
    return None


def grade_workspace(ws: Path) -> dict:
    components = {
        "product_tablefield_annotations": 0.0,
        "mapper_xml_exists": 0.0,
        "mapper_xml_namespace": 0.0,
        "mapper_xml_select_page": 0.0,
        "mapper_xml_select_by_supplier": 0.0,
    }

    # Search multiple possible roots where agents might place files
    # Agents may edit in-place, copy to /workspace root, or create new dirs
    candidate_roots = [
        ws / "fixtures" / "hof-base-data",
        ws / "hof-base-data",
        ws / "fixtures",
        ws / "src",
        ws / "project",
        ws,
    ]
    # Also check home directory in case agent works there
    home = Path.home()
    if home != ws:
        candidate_roots.extend([
            home / "hof-base-data",
            home / "project",
            home,
        ])
    search_roots = [p for p in candidate_roots if p.exists()]

    # --- Dimension 1: Product.java @TableField annotations for processValue1-5 ---
    product_file = _find_file_multi(search_roots, "Product.java")
    if product_file:
        content = _read(product_file)
        # Check for @TableField annotations on processValue fields
        # Must map processValue1 -> process_value_1 (with underscore before digit)
        correct_mappings = 0
        for i in range(1, 6):
            # Accept various annotation patterns:
            # @TableField("process_value_1")
            # @TableField(value = "process_value_1")
            # @TableField(value="process_value_1")
            # @TableField(value = "process_value_1", ...)
            # Also handle multiline annotations
            patterns = [
                # Standard @TableField with process_value_N
                rf'@TableField\s*\([^)]*?["\']process_value_{i}["\']',
                # @Column annotation (JPA style)
                rf'@Column\s*\([^)]*?["\']process_value_{i}["\']',
                # Relaxed: annotation with name= or column= containing process_value_N
                rf'@\w+\s*\([^)]*?name\s*=\s*["\']process_value_{i}["\']',
                rf'@\w+\s*\([^)]*?column\s*=\s*["\']process_value_{i}["\']',
            ]
            found = False
            for pat in patterns:
                if re.search(pat, content, re.DOTALL):
                    found = True
                    break
            if found:
                correct_mappings += 1
        components["product_tablefield_annotations"] = correct_mappings / 5.0

    # --- Dimension 2: AccessoryPolicyMapper.xml exists ---
    mapper_xml = _find_file_multi(search_roots, "AccessoryPolicyMapper.xml")
    if mapper_xml:
        components["mapper_xml_exists"] = 1.0
        xml_content = _read(mapper_xml)

        # --- Dimension 3: Correct namespace ---
        if "com.hof.basedata.mapper.AccessoryPolicyMapper" in xml_content:
            components["mapper_xml_namespace"] = 1.0
        elif "AccessoryPolicyMapper" in xml_content:
            # Partial credit for having the mapper name referenced
            components["mapper_xml_namespace"] = 0.5

        # --- Dimension 4: selectPageWithFilters with dynamic SQL ---
        has_select_page = bool(re.search(
            r'(selectPageWithFilters|selectPage|pageWithFilters|findPage|listPage|queryPage)',
            xml_content, re.IGNORECASE
        ))
        # Also accept any <select> tag that looks like a paging query
        if not has_select_page:
            has_select_page = bool(re.search(
                r'<select\s[^>]*id\s*=\s*["\'][^"\']*[Pp]age[^"\']*["\']',
                xml_content
            ))
        if has_select_page:
            score = 0.3
            # Check for proper dynamic SQL elements
            if "<if" in xml_content or "<where" in xml_content or "<choose" in xml_content:
                score += 0.2
            # Check it queries the right table
            if "supplier_accessory_policy" in xml_content or "accessory_policy" in xml_content:
                score += 0.2
            # Check for deleted = 0 filter (soft delete)
            if "deleted" in xml_content or "is_deleted" in xml_content:
                score += 0.15
            # Check for ORDER BY
            if re.search(r'ORDER\s+BY|order\s+by', xml_content):
                score += 0.15
            components["mapper_xml_select_page"] = min(1.0, score)

        # --- Dimension 5: selectBySupplierId query ---
        has_supplier_query = bool(re.search(
            r'(selectBySupplierId|BySupplierId|findBySupplierId|queryBySupplierId|getBySupplier)',
            xml_content, re.IGNORECASE
        ))
        # Also accept any select that references supplier_id
        if not has_supplier_query:
            has_supplier_query = bool(re.search(
                r'<select\s[^>]*id\s*=\s*["\'][^"\']*[Ss]upplier[^"\']*["\']',
                xml_content
            ))
        # Fallback: just check if supplier_id is used in a WHERE clause
        if not has_supplier_query:
            has_supplier_query = "supplier_id" in xml_content

        if has_supplier_query:
            score = 0.4
            # Check it uses the supplier_id parameter
            if "supplierId" in xml_content or "supplier_id" in xml_content:
                score += 0.3
            # Check it filters deleted
            if "deleted" in xml_content or "is_deleted" in xml_content:
                score += 0.3
            components["mapper_xml_select_by_supplier"] = min(1.0, score)

    weights = {
        "product_tablefield_annotations": 0.30,
        "mapper_xml_exists": 0.15,
        "mapper_xml_namespace": 0.15,
        "mapper_xml_select_page": 0.25,
        "mapper_xml_select_by_supplier": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Always search from /workspace to cover all possible file locations
    ws = Path("/workspace")
    if not ws.exists():
        # Fallback: use current working directory
        ws = Path.cwd()
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
