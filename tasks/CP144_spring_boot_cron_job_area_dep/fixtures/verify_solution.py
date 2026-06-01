"""Hidden verifier for CP144 — Spring Boot Cron Job: AreaDepUpdate."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_java(root: Path, pattern: str) -> Path | None:
    """Glob for a Java file matching pattern."""
    if not root.exists():
        return None
    for p in root.rglob(pattern):
        if p.is_file():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for CP144 AreaDepUpdate scheduled job."""
    base = ws / "jeecg-boot-module-family" / "src" / "main" / "java" / "org" / "jeecg" / "modules" / "mobileHospital"

    # Also check if agent placed files directly under fixtures path
    alt_base = ws / "fixtures" / "jeecg-boot-module-family" / "src" / "main" / "java" / "org" / "jeecg" / "modules" / "mobileHospital"
    if not base.exists() and alt_base.exists():
        base = alt_base

    components = {k: 0.0 for k in [
        "job_class_created",
        "mapper_interface_created",
        "mapper_xml_created",
        "service_layer_created",
        "correct_sql_logic",
        "truncate_before_insert",
        "proper_error_handling",
    ]}

    # 1. Job class - must implement Job interface, have proper logging
    job_file = _find_java(base / "job", "*AreaDep*Job*.java")
    if not job_file:
        job_file = _find_java(base / "job", "*Area*Dep*Job*.java")
    if not job_file:
        # broader search in the whole project
        job_file = _find_java(ws, "*AreaDep*Job*.java")

    if job_file:
        c = _read(job_file)
        has_job_iface = "implements Job" in c or "implements org.quartz.Job" in c
        has_component = "@Component" in c or "@DisallowConcurrentExecution" in c
        has_execute = "execute(" in c or "executeInternal(" in c
        has_log = "log." in c.lower() or "logger." in c.lower()
        has_autowired = "@Autowired" in c or "@Resource" in c or "constructor" in c.lower()

        score = 0.0
        if has_job_iface or has_component:
            score += 0.3
        if has_execute:
            score += 0.3
        if has_log:
            score += 0.2
        if has_autowired:
            score += 0.2
        components["job_class_created"] = min(1.0, score)

    # 2. Mapper interface
    mapper_file = _find_java(base / "mapper", "*AreaDep*Mapper*.java")
    if not mapper_file:
        mapper_file = _find_java(ws, "*AreaDep*Mapper*.java")

    if mapper_file:
        c = _read(mapper_file)
        has_mapper_anno = "@Mapper" in c or "interface" in c
        has_truncate_method = "truncate" in c.lower() or "delete" in c.lower() or "clear" in c.lower()
        has_insert_method = "insert" in c.lower() or "add" in c.lower() or "save" in c.lower()

        score = 0.0
        if has_mapper_anno and "interface" in c:
            score += 0.4
        if has_truncate_method:
            score += 0.3
        if has_insert_method:
            score += 0.3
        components["mapper_interface_created"] = min(1.0, score)

    # 3. Mapper XML
    xml_file = None
    for search_root in [base / "mapper" / "xml", base / "mapper", ws]:
        if search_root.exists():
            for p in search_root.rglob("*AreaDep*Mapper*.xml"):
                xml_file = p
                break
        if xml_file:
            break

    if xml_file:
        c = _read(xml_file)
        has_namespace = "namespace" in c
        has_truncate = "truncate" in c.lower() or "delete from" in c.lower()
        has_insert = "insert into" in c.lower() or "INSERT INTO" in c

        score = 0.0
        if has_namespace:
            score += 0.3
        if has_truncate:
            score += 0.35
        if has_insert:
            score += 0.35
        components["mapper_xml_created"] = min(1.0, score)

    # 4. Service layer (interface + impl)
    svc_iface = _find_java(base / "service", "*AreaDep*Service*.java")
    if not svc_iface:
        svc_iface = _find_java(ws, "*AreaDep*Service*.java")

    svc_impl = _find_java(base / "service" / "impl", "*AreaDep*Service*Impl*.java")
    if not svc_impl:
        svc_impl = _find_java(ws, "*AreaDep*ServiceImpl*.java")

    score = 0.0
    if svc_iface:
        c = _read(svc_iface)
        if "interface" in c:
            score += 0.4
        elif "class" in c:
            score += 0.2
    if svc_impl:
        c = _read(svc_impl)
        if "@Service" in c or "implements" in c:
            score += 0.4
        if "@Transactional" in c:
            score += 0.2
    elif svc_iface:
        # Some agents might put it all in one file
        c = _read(svc_iface)
        if "@Service" in c and "class" in c:
            score += 0.3
    components["service_layer_created"] = min(1.0, score)

    # 5. Correct SQL logic - the join query with sys_depart + t_area hierarchy
    all_java_and_xml = []
    for ext in ["*.java", "*.xml"]:
        if ws.exists():
            all_java_and_xml.extend(ws.rglob(ext))

    sql_score = 0.0
    for f in all_java_and_xml:
        c = _read(f)
        c_lower = c.lower()
        # Check for the core SQL structure
        has_sys_depart = "sys_depart" in c_lower
        has_t_area = "t_area" in c_lower
        has_join = "join" in c_lower
        has_group_by = "group by" in c_lower or "group_by" in c_lower
        has_count = "count(" in c_lower or "count (" in c_lower
        has_parent_id = "parent_id" in c_lower
        has_depart_name = "depart_name" in c_lower
        has_area_name = "area_name" in c_lower

        file_score = 0.0
        if has_sys_depart:
            file_score += 0.15
        if has_t_area:
            file_score += 0.15
        if has_join:
            file_score += 0.15
        if has_group_by:
            file_score += 0.15
        if has_count:
            file_score += 0.15
        if has_parent_id:
            file_score += 0.1
        if has_depart_name and has_area_name:
            file_score += 0.15

        sql_score = max(sql_score, file_score)

    components["correct_sql_logic"] = min(1.0, sql_score)

    # 6. Truncate before insert pattern
    truncate_score = 0.0
    for f in all_java_and_xml:
        c = _read(f)
        c_lower = c.lower()
        if ("truncate" in c_lower or "delete from t_area_dep" in c_lower) and \
           ("insert" in c_lower or "t_area_dep" in c_lower):
            # Check ordering: truncate should come before insert in the flow
            trunc_pos = c_lower.find("truncate")
            if trunc_pos == -1:
                trunc_pos = c_lower.find("delete from t_area_dep")
            insert_pos = c_lower.find("insert")
            if insert_pos == -1:
                insert_pos = c_lower.find("insertareadep")

            if trunc_pos >= 0:
                truncate_score = 0.6
                if insert_pos > trunc_pos:
                    truncate_score = 1.0
                break

    # Also check service/job level for truncate-then-insert pattern
    if truncate_score < 1.0:
        for f in all_java_and_xml:
            c = _read(f)
            if ("truncate" in c.lower() or "clear" in c.lower() or "deleteAll" in c) and \
               ("insert" in c.lower() or "save" in c.lower() or "archiveData" in c.lower()):
                truncate_score = max(truncate_score, 0.8)
                break

    components["truncate_before_insert"] = truncate_score

    # 7. Proper error handling
    error_score = 0.0
    if job_file:
        c = _read(job_file)
        if "try" in c and "catch" in c:
            error_score += 0.5
        if "log.error" in c or "logger.error" in c or "log.warn" in c:
            error_score += 0.3
        if "JobExecutionException" in c or "throw" in c:
            error_score += 0.2
    components["proper_error_handling"] = min(1.0, error_score)

    # Weighted overall score
    weights = {
        "job_class_created": 0.20,
        "mapper_interface_created": 0.15,
        "mapper_xml_created": 0.15,
        "service_layer_created": 0.15,
        "correct_sql_logic": 0.20,
        "truncate_before_insert": 0.10,
        "proper_error_handling": 0.05,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try /workspace/fixtures first (where sandbox_files land), then /workspace
    ws = Path("/workspace/fixtures")
    if not (ws / "jeecg-boot-module-family").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
