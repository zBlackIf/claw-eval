"""Hidden verifier for CP164 - ES to MyBatis-Plus Query Migration."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def check_es_removed(impl_dir: Path) -> dict:
    """Check that ES dependencies are removed from all service impls."""
    results = {}
    for java_file in impl_dir.rglob("*.java"):
        content = _read(java_file)
        fname = java_file.name
        has_es_import = "UniversalSearchService" in content or "UniversalSearchAuthFilter" in content
        has_es_autowired = "@Autowired" in content and "universalSearchService" in content
        has_es_usage = "universalSearchService." in content
        if has_es_import or has_es_autowired or has_es_usage:
            results[fname] = False
        else:
            results[fname] = True
    return results


def check_message_service(ws: Path) -> dict:
    """Check MessageServiceImpl conversion - basic + quality checks."""
    impl_path = ws / "ruoyi-safe" / "src" / "main" / "java" / "com" / "ruoyi" / "safe" / "service" / "impl" / "MessageServiceImpl.java"
    if not impl_path.exists():
        return {"exists": False, "score": 0.0}

    content = _read(impl_path)
    checks = {
        "no_es_dependency": "UniversalSearchService" not in content and "universalSearchService" not in content,
        "uses_lambda_wrapper": "LambdaQueryWrapper" in content,
        "has_keyword_like": ".like(" in content and "Message::getTitle" in content and "Message::getContent" in content,
        "has_or_for_keyword": ".or(" in content or ".or()." in content,
        "filters_del_flag": "Message::getDelFlag" in content and ".eq(" in content,
        "filters_msg_type": "Message::getMsgType" in content and ".eq(" in content,
        "has_pagination": "page(" in content,
        "preserves_convert_vo": "toDetailVO" in content,
    }

    # --- HIDDEN QUALITY CHECKS ---

    # 1. Keyword search must be wrapped in .and() to avoid polluting outer AND logic
    #    Correct: wrapper.and(w -> w.like(...).or().like(...))
    #    Wrong: wrapper.like(...).or().like(...)  (breaks outer AND conditions)
    has_and_wrapper_for_keyword = bool(re.search(
        r'\.and\s*\(\s*\w+\s*->', content
    ))
    checks["keyword_wrapped_in_and"] = has_and_wrapper_for_keyword

    # 2. Conditional filter building - msgType should only be added when not null
    #    Must use conditional check before .eq for msgType
    has_conditional_msgtype = bool(re.search(
        r'(form\.getMsgType\(\)\s*!=\s*null|Objects\.nonNull\(form\.getMsgType|Optional)',
        content
    )) or bool(re.search(
        r'\.eq\s*\(\s*form\.getMsgType\(\)\s*!=\s*null', content
    ))
    # Also accept MyBatis-Plus condition overload: .eq(condition, col, val)
    has_conditional_eq_overload = bool(re.search(
        r'\.eq\s*\(\s*form\.getMsgType\s*\(\s*\)\s*!=\s*null\s*,', content
    )) or bool(re.search(
        r'\.eq\s*\(\s*\w+\s*!=\s*null\s*,\s*Message::getMsgType', content
    ))
    checks["conditional_filter_msgtype"] = has_conditional_msgtype or has_conditional_eq_overload

    # 3. Conditional keyword - keyword should only apply when not blank
    has_keyword_guard = bool(re.search(
        r'(StrUtil\.isNotBlank|StringUtils\.isNotBlank|StringUtils\.hasText|!.*\.isEmpty\(\)|\.isNotBlank)',
        content
    )) or bool(re.search(
        r'keyword\s*!=\s*null\s*&&', content
    ))
    checks["keyword_null_guarded"] = has_keyword_guard

    # 4. Dead code removal - the old buildBaseWrapper helper is now unnecessary
    checks["removed_dead_helper"] = "buildBaseWrapper" not in content

    # 5. Removed stale imports (HashMap/Map no longer needed if using LambdaQueryWrapper inline)
    has_hashmap_import = "import java.util.HashMap" in content
    has_map_import = "import java.util.Map" in content
    # Only penalize if both HashMap AND Map are still imported but never used in new code
    uses_map_elsewhere = "Map<" in content.split("class")[1] if "class" in content else False
    checks["cleaned_stale_imports"] = not has_hashmap_import or uses_map_elsewhere

    # 6. HIDDEN: Deterministic pagination ordering.
    #    After removing ES (which uses relevance scoring), DB queries need explicit
    #    ORDER BY for deterministic pagination. Without it, paged results are unstable.
    #    Strong models add .orderByDesc(Message::getCreateTime) or .orderByDesc(Message::getId).
    has_order_clause = bool(re.search(
        r'\.(orderByDesc|orderByAsc|orderBy)\s*\(\s*Message::(getCreateTime|getId|getCreateDate)',
        content
    ))
    checks["pagination_has_explicit_order"] = has_order_clause

    # 7. HIDDEN: LambdaQueryWrapper import must be added (original file lacks it).
    #    This is not in the original imports — agent must add it for compilation.
    has_lambda_import = "import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper" in content
    checks["lambda_wrapper_import_added"] = has_lambda_import

    # Weighted scoring: hard hidden checks worth 2x
    hard_checks = {"keyword_wrapped_in_and", "pagination_has_explicit_order",
                   "removed_dead_helper", "cleaned_stale_imports", "lambda_wrapper_import_added"}
    total_weight = sum(2.0 if k in hard_checks else 1.0 for k in checks)
    earned = sum((2.0 if k in hard_checks else 1.0) for k, v in checks.items() if v)
    score = earned / total_weight if total_weight > 0 else 0.0
    return {"exists": True, "checks": checks, "score": round(score, 4)}


def check_message_user_service(ws: Path) -> dict:
    """Check MessageUserServiceImpl conversion - basic + quality checks."""
    impl_path = ws / "ruoyi-safe" / "src" / "main" / "java" / "com" / "ruoyi" / "safe" / "service" / "impl" / "MessageUserServiceImpl.java"
    if not impl_path.exists():
        return {"exists": False, "score": 0.0}

    content = _read(impl_path)

    # Extract countUnreadByUserId method body
    count_method_uses_lambda = False
    if "countUnread" in content:
        count_section = content[content.index("countUnread"):]
        method_end = count_section.find("}\n")
        if method_end > 0:
            count_body = count_section[:method_end]
            count_method_uses_lambda = "LambdaQueryWrapper" in count_body or "count(" in count_body

    checks = {
        "no_es_dependency": "UniversalSearchService" not in content and "universalSearchService" not in content,
        "count_uses_lambda_not_es": count_method_uses_lambda or ("count(" in content and "LambdaQueryWrapper" in content),
        "filters_user_id_in_count": "MessageUser::getUserId" in content,
        "filters_read_flag_in_count": "MessageUser::getReadFlag" in content or "READ_FLAG_UN_READ" in content,
        "no_es_count_call": "universalSearchService.count" not in content,
    }

    # --- HIDDEN QUALITY CHECKS ---

    # 1. Return type correctness: MyBatis-Plus count() returns long (primitive).
    #    The method signature returns Long (boxed). Weak models may cast incorrectly
    #    or produce compile errors. Best: direct return (auto-boxing handles it).
    #    Check that there is no incorrect int cast.
    has_int_cast = "(int)" in content and "count" in content
    checks["no_incorrect_int_cast"] = not has_int_cast

    # 2. Removed stale HashMap/Map imports (no longer needed for count)
    has_hashmap_import = "import java.util.HashMap" in content
    has_map_import = "import java.util.Map" in content
    # After migration, HashMap/Map should not be needed in this file
    checks["cleaned_stale_imports"] = not has_hashmap_import and not has_map_import

    # 3. The method should use READ_FLAG_UN_READ constant, not hardcoded 0
    #    Check that the count query references the constant, not a magic number
    if "countUnread" in content:
        count_section = content[content.index("countUnread"):]
        method_end = count_section.find("}\n")
        count_body = count_section[:method_end] if method_end > 0 else count_section[:200]
        uses_constant = "READ_FLAG_UN_READ" in count_body or "MessageUser.READ_FLAG_UN_READ" in count_body
        uses_magic_zero = bool(re.search(r'\.eq\s*\([^)]*,\s*0\s*\)', count_body))
        checks["uses_constant_not_magic_number"] = uses_constant and not uses_magic_zero
    else:
        checks["uses_constant_not_magic_number"] = False

    # 4. HIDDEN: The file should NOT still have HashMap/Map imports since countUnread
    #    was the only method using them.  Also must remove the UniversalSearchService import line.
    has_search_import = "import com.ruoyi.safe.service.search.UniversalSearchService" in content
    checks["removed_search_import_line"] = not has_search_import

    # Weighted scoring: hard hidden checks worth 2x
    hard_checks = {"cleaned_stale_imports", "uses_constant_not_magic_number",
                   "removed_search_import_line"}
    total_weight = sum(2.0 if k in hard_checks else 1.0 for k in checks)
    earned = sum((2.0 if k in hard_checks else 1.0) for k, v in checks.items() if v)
    score = earned / total_weight if total_weight > 0 else 0.0
    return {"exists": True, "checks": checks, "score": round(score, 4)}


def check_hazard_service(ws: Path) -> dict:
    """Check HazardServiceImpl conversion - basic + quality checks."""
    impl_path = ws / "ruoyi-safe" / "src" / "main" / "java" / "com" / "ruoyi" / "safe" / "service" / "impl" / "HazardServiceImpl.java"
    if not impl_path.exists():
        return {"exists": False, "score": 0.0}

    content = _read(impl_path)
    checks = {
        "no_es_dependency": "UniversalSearchService" not in content and "universalSearchService" not in content,
        "uses_lambda_wrapper": "LambdaQueryWrapper" in content,
        "filters_hazard_level_lambda": "Hazard::getHazardLevel" in content and ".eq(" in content,
        "filters_status_lambda": "Hazard::getStatus" in content and ".eq(" in content,
        "filters_dept_id_lambda": "Hazard::getDeptId" in content and ".eq(" in content,
        "filters_responsible_lambda": "Hazard::getResponsibleId" in content and ".eq(" in content,
        "filters_del_flag_lambda": "Hazard::getDelFlag" in content and ".eq(" in content,
        "has_pagination": "page(" in content,
    }

    # --- HIDDEN QUALITY CHECKS ---

    # 1. All THREE keyword fields must be covered with .like()
    #    hazardNo, description, location — weak models often miss location
    has_hazardno_like = "Hazard::getHazardNo" in content and ".like(" in content
    has_desc_like = "Hazard::getDescription" in content and ".like(" in content
    has_location_like = "Hazard::getLocation" in content and ".like(" in content
    checks["keyword_covers_all_three_fields"] = has_hazardno_like and has_desc_like and has_location_like

    # 2. Keyword search must be wrapped in .and() to isolate OR from outer AND
    has_and_wrapper_for_keyword = bool(re.search(
        r'\.and\s*\(\s*\w+\s*->', content
    ))
    checks["keyword_wrapped_in_and"] = has_and_wrapper_for_keyword

    # 3. All filter conditions should be conditional (null-guarded)
    #    At minimum hazardLevel, status, hazardType, responsibleId, deptId
    #    should not be unconditionally applied
    conditional_patterns = [
        r'(getHazardLevel\(\)\s*!=\s*null|\.eq\s*\(\s*\w+\s*!=\s*null\s*,\s*Hazard::getHazardLevel)',
        r'(getStatus\(\)\s*!=\s*null|\.eq\s*\(\s*\w+\s*!=\s*null\s*,\s*Hazard::getStatus)',
        r'(getResponsibleId\(\)\s*!=\s*null|\.eq\s*\(\s*\w+\s*!=\s*null\s*,\s*Hazard::getResponsibleId)',
        r'(getDeptId\(\)\s*!=\s*null|\.eq\s*\(\s*\w+\s*!=\s*null\s*,\s*Hazard::getDeptId)',
    ]
    conditional_count = sum(1 for p in conditional_patterns if re.search(p, content))
    # Also accept if-then-eq pattern
    if_then_patterns = [
        r'if\s*\(\s*form\.getHazardLevel\(\)\s*!=\s*null\s*\)',
        r'if\s*\(\s*form\.getStatus\(\)\s*!=\s*null\s*\)',
        r'if\s*\(\s*form\.getResponsibleId\(\)\s*!=\s*null\s*\)',
        r'if\s*\(\s*form\.getDeptId\(\)\s*!=\s*null\s*\)',
    ]
    if_count = sum(1 for p in if_then_patterns if re.search(p, content))
    total_conditional = max(conditional_count, if_count)
    checks["all_filters_null_guarded"] = total_conditional >= 4

    # 4. HazardType uses StrUtil.isNotBlank (it's a String, not Integer)
    has_hazardtype_str_check = bool(re.search(
        r'(StrUtil\.isNotBlank|StringUtils\.isNotBlank|StringUtils\.hasText)\s*\(\s*(form\.getHazardType|hazardType)',
        content
    )) or bool(re.search(
        r'form\.getHazardType\(\)\s*!=\s*null\s*&&\s*!.*form\.getHazardType',
        content
    ))
    checks["hazardtype_uses_string_check"] = has_hazardtype_str_check

    # 5. Dead code removal - buildQueryFilter helper no longer needed
    checks["removed_dead_helper"] = "buildQueryFilter" not in content

    # 6. Removed stale HashMap/Map imports
    has_hashmap_import = "import java.util.HashMap" in content
    uses_map_elsewhere = "Map<" in content.split("class")[1] if "class" in content else False
    checks["cleaned_stale_imports"] = not has_hashmap_import or uses_map_elsewhere

    # 7. HIDDEN: Deterministic pagination ordering.
    #    Same as MessageServiceImpl — DB queries need explicit ORDER BY for stable paging.
    #    Strong models add .orderByDesc(Hazard::getCreateTime) or .orderByDesc(Hazard::getId).
    has_order_clause = bool(re.search(
        r'\.(orderByDesc|orderByAsc|orderBy)\s*\(\s*Hazard::(getCreateTime|getId|getCreateDate)',
        content
    ))
    checks["pagination_has_explicit_order"] = has_order_clause

    # 8. HIDDEN: LambdaQueryWrapper import must be added (original file does not have it).
    has_lambda_import = "import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper" in content
    checks["lambda_wrapper_import_added"] = has_lambda_import

    # Weighted scoring: hard hidden checks worth 2x
    hard_checks = {"keyword_wrapped_in_and", "all_filters_null_guarded",
                   "pagination_has_explicit_order", "removed_dead_helper",
                   "cleaned_stale_imports", "lambda_wrapper_import_added",
                   "keyword_covers_all_three_fields"}
    total_weight = sum(2.0 if k in hard_checks else 1.0 for k in checks)
    earned = sum((2.0 if k in hard_checks else 1.0) for k, v in checks.items() if v)
    score = earned / total_weight if total_weight > 0 else 0.0
    return {"exists": True, "checks": checks, "score": round(score, 4)}


def check_no_compilation_issues(ws: Path) -> dict:
    """Check for common compilation issues in the converted code."""
    impl_dir = ws / "ruoyi-safe" / "src" / "main" / "java" / "com" / "ruoyi" / "safe" / "service" / "impl"
    if not impl_dir.exists():
        return {"score": 0.0}

    issues = []
    for java_file in impl_dir.glob("*.java"):
        content = _read(java_file)
        fname = java_file.name

        # Check for leftover ES search package imports
        if "import com.ruoyi.safe.service.search" in content:
            issues.append(f"{fname}: still imports search package")

        # Check for UniversalSearchAuthFilter import without usage
        if "UniversalSearchAuthFilter" in content:
            issues.append(f"{fname}: still references UniversalSearchAuthFilter")

    score = 1.0 if not issues else max(0.0, 1.0 - len(issues) * 0.3)
    return {"issues": issues, "score": round(score, 4)}


def check_import_hygiene(ws: Path) -> dict:
    """Hidden check: verify that unused imports are cleaned across all impl files."""
    impl_dir = ws / "ruoyi-safe" / "src" / "main" / "java" / "com" / "ruoyi" / "safe" / "service" / "impl"
    if not impl_dir.exists():
        return {"score": 0.0}

    violations = 0
    total_files = 0

    for java_file in impl_dir.glob("*.java"):
        content = _read(java_file)
        total_files += 1

        # After class declaration, check if HashMap is actually used
        class_body = content.split("class")[1] if "class" in content else ""

        if "import java.util.HashMap" in content and "HashMap" not in class_body:
            violations += 1
        if "import java.util.Map" in content and "Map" not in class_body:
            violations += 1
        # Check UniversalSearchAuthFilter import leftover
        if "import com.ruoyi.safe.service.search.UniversalSearchAuthFilter" in content:
            violations += 1
        if "import com.ruoyi.safe.service.search.UniversalSearchService" in content:
            violations += 1

    if total_files == 0:
        return {"score": 0.0}
    score = max(0.0, 1.0 - violations * 0.2)
    return {"violations": violations, "score": round(score, 4)}


def grade_workspace(ws: Path) -> dict:
    """Grade the complete workspace conversion."""
    components = {}

    # Dimension 1: MessageServiceImpl conversion (weight: 0.25)
    msg_result = check_message_service(ws)
    components["message_service_converted"] = msg_result.get("score", 0.0)

    # Dimension 2: MessageUserServiceImpl conversion (weight: 0.15)
    msg_user_result = check_message_user_service(ws)
    components["message_user_service_converted"] = msg_user_result.get("score", 0.0)

    # Dimension 3: HazardServiceImpl conversion (weight: 0.25)
    hazard_result = check_hazard_service(ws)
    components["hazard_service_converted"] = hazard_result.get("score", 0.0)

    # Dimension 4: No residual ES references (weight: 0.05)
    impl_dir = ws / "ruoyi-safe" / "src" / "main" / "java" / "com" / "ruoyi" / "safe" / "service" / "impl"
    if impl_dir.exists():
        es_checks = check_es_removed(impl_dir)
        all_clean = all(es_checks.values()) if es_checks else False
        components["es_fully_removed"] = 1.0 if all_clean else (0.5 if sum(es_checks.values()) / max(len(es_checks), 1) > 0.5 else 0.0)
    else:
        components["es_fully_removed"] = 0.0

    # Dimension 5: No compilation issues (weight: 0.05)
    compile_result = check_no_compilation_issues(ws)
    components["no_compilation_issues"] = compile_result.get("score", 0.0)

    # Dimension 6: Import hygiene — hidden quality check (weight: 0.25)
    hygiene_result = check_import_hygiene(ws)
    components["import_hygiene"] = hygiene_result.get("score", 0.0)

    weights = {
        "message_service_converted": 0.30,
        "message_user_service_converted": 0.15,
        "hazard_service_converted": 0.35,
        "es_fully_removed": 0.05,
        "no_compilation_issues": 0.05,
        "import_hygiene": 0.10,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "details": {
            "message_service": msg_result,
            "message_user_service": msg_user_result,
            "hazard_service": hazard_result,
            "compilation": compile_result,
            "import_hygiene": hygiene_result,
        },
    }


def main():
    # Try workspace paths with fallback
    ws = Path("/workspace/fixtures/ruoyi-safe")
    if not ws.exists():
        ws_alt = Path("/workspace/ruoyi-safe")
        if ws_alt.exists():
            ws = ws_alt

    # Grade from parent directory of ruoyi-safe
    ws_root = ws.parent if ws.name == "ruoyi-safe" else ws
    print(json.dumps(grade_workspace(ws_root), ensure_ascii=False))


if __name__ == "__main__":
    main()
