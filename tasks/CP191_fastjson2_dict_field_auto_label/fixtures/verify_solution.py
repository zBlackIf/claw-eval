"""Hidden verifier for CP191 — Fastjson2 DictField Auto Label Translation."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_java(base: Path, pattern: str) -> Path | None:
    """Find a java file matching glob pattern recursively."""
    if not base.exists():
        return None
    for p in base.rglob(pattern):
        if p.is_file():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    base = ws / "enterprise-backend" / "src" / "main" / "java"
    # Fallback: also check fixtures path
    if not base.exists():
        base = ws / "fixtures" / "enterprise-backend" / "src" / "main" / "java"

    components = {k: 0.0 for k in [
        "annotation_created",
        "provider_interface",
        "filter_implements_afterfilter",
        "filter_scans_fields_with_reflection",
        "filter_appends_label_key",
        "filter_uses_field_cache",
        "config_registers_filter",
        "entity_annotated",
        # --- Hidden harder checks ---
        "filter_thread_safe_cache",
        "filter_null_safety",
        "filter_class_hierarchy",
        "filter_di_constructor",
        "filter_value_type_conversion",
        "filter_setaccessible_guard",
        "filter_computeifabsent_pattern",
        "annotation_documented",
        # --- Additional hidden checks (strong vs weak) ---
        "filter_writeafter_override",
        "filter_exception_resilience",
        "provider_two_param_contract",
    ]}

    # 1. Check @DictField annotation exists
    annotation_file = _find_java(base, "*DictField*.java")
    if not annotation_file:
        annotation_file = _find_java(base, "*Dict*Field*.java")
    annotation_content = ""
    if annotation_file:
        c = _read(annotation_file)
        annotation_content = c
        has_annotation_decl = "@interface" in c
        has_retention_runtime = "RetentionPolicy.RUNTIME" in c or "RUNTIME" in c
        has_target_field = "ElementType.FIELD" in c or "FIELD" in c
        has_value_method = "value()" in c or "String value" in c
        # All four must be present for full score
        if has_annotation_decl and has_retention_runtime and has_target_field and has_value_method:
            components["annotation_created"] = 1.0
        elif has_annotation_decl and has_retention_runtime and has_value_method:
            components["annotation_created"] = 0.7
        elif has_annotation_decl:
            components["annotation_created"] = 0.3

    # 2. Check DictProvider interface (or equivalent abstraction)
    provider_candidates = []
    if base.exists():
        for jf in base.rglob("*.java"):
            if jf.name == "DictDataSource.java":
                continue
            c = _read(jf)
            if "getLabel" in c or "translate" in c.lower():
                if "DictProvider" in jf.name or "Dict" in jf.name and "Service" in jf.name:
                    provider_candidates.append((jf, c))
    if not provider_candidates and base.exists():
        for jf in base.rglob("*.java"):
            if jf.name == "DictDataSource.java":
                continue
            c = _read(jf)
            if "interface" in c and "getLabel" in c:
                provider_candidates.append((jf, c))
                break

    if provider_candidates:
        interface_found = False
        class_found = False
        for (pf, c) in provider_candidates:
            if "interface" in c and ("getLabel" in c or "translate" in c.lower()):
                interface_found = True
            elif "class" in c and ("getLabel" in c or "translate" in c.lower()):
                class_found = True
        if interface_found:
            components["provider_interface"] = 1.0
        elif class_found:
            components["provider_interface"] = 0.5

    # 3. Check filter extends AfterFilter (Fastjson2 hook)
    filter_file = _find_java(base, "*DictLabel*Filter*.java")
    if not filter_file:
        filter_file = _find_java(base, "*Dict*Filter*.java")
    if not filter_file:
        filter_file = _find_java(base, "*Translate*Filter*.java")
    if not filter_file:
        filter_file = _find_java(base, "*Label*Filter*.java")
    if not filter_file:
        if base.exists():
            for jf in base.rglob("*.java"):
                c = _read(jf)
                if "AfterFilter" in c and "DictField" in c:
                    filter_file = jf
                    break

    filter_content = ""
    if filter_file:
        filter_content = _read(filter_file)
        c = filter_content

        # 3a. Extends AfterFilter — MUST use "extends AfterFilter" (correct API)
        if "extends AfterFilter" in c:
            components["filter_implements_afterfilter"] = 1.0
        elif "AfterFilter" in c:
            components["filter_implements_afterfilter"] = 0.3

        # 3b. Uses reflection to scan @DictField annotated fields
        has_reflection = ("getDeclaredFields" in c or "getFields" in c)
        has_annotation_scan = ("getAnnotation" in c or "isAnnotationPresent" in c)
        has_dictfield_ref = "DictField" in c
        if has_reflection and has_annotation_scan and has_dictfield_ref:
            components["filter_scans_fields_with_reflection"] = 1.0
        elif has_reflection and has_dictfield_ref:
            components["filter_scans_fields_with_reflection"] = 0.6
        elif has_dictfield_ref:
            components["filter_scans_fields_with_reflection"] = 0.2

        # 3c. Appends {fieldName}Label key via writeKeyValue
        # MUST use writeKeyValue (the AfterFilter API) AND construct label key
        has_write_key_value = "writeKeyValue" in c
        has_label_concat = bool(re.search(r'["\']Label["\']', c)) or '+ "Label"' in c
        if has_write_key_value and has_label_concat:
            components["filter_appends_label_key"] = 1.0
        elif has_write_key_value:
            components["filter_appends_label_key"] = 0.6

        # 3d. Caches field scan results — must be a proper Map<Class, ...> pattern
        has_map_class_key = bool(re.search(r'Map<Class<?\??>', c))
        has_computeifabsent = "computeIfAbsent" in c
        if has_map_class_key:
            components["filter_uses_field_cache"] = 1.0
        elif "ConcurrentHashMap" in c or "HashMap" in c:
            components["filter_uses_field_cache"] = 0.5

    # 4. Check WebMvcConfig registers the filter
    config_file = _find_java(base, "*WebMvc*Config*.java")
    if not config_file:
        config_file = _find_java(base, "*FastJson*Config*.java")
    if not config_file:
        config_file = _find_java(base, "*Json*Config*.java")
    if config_file:
        c = _read(config_file)
        filter_registered = ("setWriterFilters" in c or "addWriterFilter" in c)
        has_dict_filter_ref = ("DictLabel" in c or "DictFilter" in c or
                              "dictLabel" in c or "dictFilter" in c)
        if filter_registered and has_dict_filter_ref:
            components["config_registers_filter"] = 1.0
        elif filter_registered:
            components["config_registers_filter"] = 0.4

    # 5. Check UserEntity has @DictField annotations
    entity_file = _find_java(base, "UserEntity.java")
    if entity_file:
        c = _read(entity_file)
        status_annotated = re.search(r'@DictField\s*\(\s*"user_status"\s*\)', c) is not None
        gender_annotated = re.search(r'@DictField\s*\(\s*"gender"\s*\)', c) is not None
        if status_annotated and gender_annotated:
            components["entity_annotated"] = 1.0
        elif status_annotated or gender_annotated:
            components["entity_annotated"] = 0.5
        elif "@DictField" in c:
            components["entity_annotated"] = 0.2

    # =========================================================
    # HIDDEN HARDER CHECKS — differentiate strong vs weak models
    # =========================================================

    if filter_content:
        c = filter_content

        # H1. Thread-safe cache: must use ConcurrentHashMap specifically
        #     (not plain HashMap which has race conditions in multi-threaded servlet env)
        if "ConcurrentHashMap" in c:
            components["filter_thread_safe_cache"] = 1.0
        elif "Collections.synchronizedMap" in c:
            components["filter_thread_safe_cache"] = 0.5
        # HashMap alone = 0, synchronized block alone = 0.3
        elif "synchronized" in c and "HashMap" in c:
            components["filter_thread_safe_cache"] = 0.3

        # H2. Null safety: filter must guard against null dict values
        #     Strict: the null check must be specifically on the label result before writing
        #     Pattern: label = getLabel(...); if (label != null) { writeKeyValue(...) }
        #     OR: if (label != null && !label.isEmpty()) writeKeyValue(...)
        strict_null_pattern = bool(re.search(
            r'(getLabel|translate|dictProvider\.\w+)\s*\([^)]*\)\s*;'
            r'[^;]{0,80}if\s*\(\s*\w+\s*!=\s*null',
            c, re.DOTALL
        ))
        # Also accept inline: if (provider.getLabel(...) != null)
        inline_null_check = bool(re.search(
            r'if\s*\(\s*(getLabel|translate|dictProvider\.\w+)\s*\([^)]*\)\s*!=\s*null',
            c
        ))
        # Weak pattern: just any null check near writeKeyValue
        weak_null_check = bool(re.search(
            r'!=\s*null[^;]{0,60}writeKeyValue', c, re.DOTALL
        ))
        if strict_null_pattern or inline_null_check:
            components["filter_null_safety"] = 1.0
        elif weak_null_check:
            components["filter_null_safety"] = 0.4
        # else stays 0.0 — many models just call writeKeyValue without null checking

        # H3. Class hierarchy support: should walk up superclass fields
        #     getDeclaredFields only gets current class; must explicitly traverse hierarchy
        #     Must have BOTH getSuperclass AND a loop/recursion pattern
        has_getsuperclass = bool(re.search(r'getSuperclass\(\)', c))
        has_loop_pattern = bool(re.search(
            r'(while\s*\(\s*\w+\s*!=\s*(null|Object\.class)|'
            r'for\s*\([^)]*getSuperclass|'
            r'do\s*\{[^}]*getDeclaredFields)',
            c, re.DOTALL
        ))
        has_utility = bool(re.search(
            r'(FieldUtils\.getAllField|ReflectionUtils\.getAll|getAllFields)',
            c
        ))
        if (has_getsuperclass and has_loop_pattern) or has_utility:
            components["filter_class_hierarchy"] = 1.0
        elif has_getsuperclass:
            # Has getSuperclass but no loop — probably incomplete
            components["filter_class_hierarchy"] = 0.4

        # H4. DictProvider via constructor injection (proper DI, not field injection)
        #     Constructor injection is the proper Spring pattern for required deps
        has_constructor_injection = bool(re.search(
            r'(public\s+\w+Filter|public\s+\w+Label\w*)\s*\(\s*(final\s+)?'
            r'(DictProvider|Dict\w*Service|Dict\w*Provider)',
            c
        ))
        # Constructor with any provider-like parameter
        has_constructor_param = bool(re.search(
            r'public\s+\w+\s*\([^)]*(?:Provider|Service)[^)]*\)',
            c
        ))
        # Field injection is inferior but acceptable at lower score
        has_field_injection = bool(re.search(
            r'(@Autowired|@Resource|@Inject)\s+.*?(DictProvider|Dict\w*Service)',
            c, re.DOTALL
        ))
        if has_constructor_injection or has_constructor_param:
            components["filter_di_constructor"] = 1.0
        elif has_field_injection:
            components["filter_di_constructor"] = 0.4
        # If they hardcode new DictProviderImpl() or static call, score 0

        # H5. Value type conversion: status/gender are Integer but getLabel takes String
        #     Must convert: String.valueOf(value), Objects.toString(value), etc.
        #     STRICT: the conversion must be near the getLabel call or field.get() call
        type_conversion_near_label = bool(re.search(
            r'(String\.valueOf|Objects\.toString|\.toString\(\))[^;]{0,80}(getLabel|translate)',
            c, re.DOTALL
        ))
        type_conversion_near_get = bool(re.search(
            r'(field\.get|get\w*\(object\))[^;]{0,80}(String\.valueOf|Objects\.toString|\.toString\(\))',
            c, re.DOTALL
        ))
        # Also accept: passing String.valueOf(fieldValue) directly into getLabel
        inline_conversion = bool(re.search(
            r'(getLabel|translate)\s*\([^)]*String\.valueOf\s*\(',
            c
        ))
        if type_conversion_near_label or type_conversion_near_get or inline_conversion:
            components["filter_value_type_conversion"] = 1.0
        elif bool(re.search(r'String\.valueOf\s*\(', c)):
            # Has conversion somewhere but not clearly tied to the label logic
            components["filter_value_type_conversion"] = 0.5

        # H6. setAccessible(true) for private fields — essential for reflection on private fields
        #     Without this, field.get() would throw IllegalAccessException on private fields
        has_setaccessible = bool(re.search(r'setAccessible\s*\(\s*true\s*\)', c))
        # Also accept AccessibleObject.setAccessible or field.trySetAccessible
        has_trysetaccessible = "trySetAccessible" in c
        if has_setaccessible or has_trysetaccessible:
            components["filter_setaccessible_guard"] = 1.0
        # Without setAccessible, the filter breaks on private fields (which UserEntity has)

        # H7. computeIfAbsent pattern — the CORRECT way to use ConcurrentHashMap cache
        #     Just having ConcurrentHashMap.put is not enough; computeIfAbsent is atomic
        if "computeIfAbsent" in c:
            components["filter_computeifabsent_pattern"] = 1.0
        elif "putIfAbsent" in c:
            components["filter_computeifabsent_pattern"] = 0.5
        # Plain get+put is not atomic and has race conditions

    # H8. Annotation has @Documented — professional annotation should include @Documented
    #     for Javadoc propagation (rarely done by weak models)
    if annotation_content:
        if "@Documented" in annotation_content:
            components["annotation_documented"] = 1.0

    # =========================================================
    # ADDITIONAL HIDDEN CHECKS — further separate strong vs weak
    # =========================================================

    if filter_content:
        c = filter_content

        # H9. writeAfter override with correct signature
        #     AfterFilter's contract is: public void writeAfter(Object object)
        #     Weak models may use wrong method names like "afterWrite", "process",
        #     "doFilter", or miss the @Override annotation.
        #     Strong: @Override + writeAfter(Object ...)
        has_override_writeafter = bool(re.search(
            r'@Override\s+\w*\s*void\s+writeAfter\s*\(\s*Object\s+\w+\s*\)',
            c, re.DOTALL
        ))
        # Medium: writeAfter with Object param but no @Override
        has_writeafter_no_override = bool(re.search(
            r'(?<!@Override\s)void\s+writeAfter\s*\(\s*Object\s+\w+\s*\)',
            c
        ))
        # Also accept: public void writeAfter(Object object) without @Override
        has_writeafter_any = bool(re.search(
            r'void\s+writeAfter\s*\(\s*Object\s+\w+\s*\)', c
        ))
        if has_override_writeafter:
            components["filter_writeafter_override"] = 1.0
        elif has_writeafter_any:
            components["filter_writeafter_override"] = 0.5
        # Wrong method name or signature = 0

        # H10. Exception resilience in the filter loop
        #      A production-quality filter MUST wrap individual field processing in
        #      try-catch so that one bad field doesn't break serialization of the
        #      entire object. This is critical for AfterFilter because an unhandled
        #      exception here corrupts the entire JSON output stream.
        #      Pattern: try { ... field.get ... } catch (... e) { ... }
        #      OR: try { ... writeKeyValue ... } catch
        has_try_catch_in_loop = bool(re.search(
            r'for\s*\([^)]*\)\s*\{[^}]*try\s*\{',
            c, re.DOTALL
        ))
        # Also match: try block containing field.get or writeKeyValue
        has_try_around_field = bool(re.search(
            r'try\s*\{[^}]{0,300}(field\.get|writeKeyValue|getLabel|translate)',
            c, re.DOTALL
        ))
        # Broad catch wrapping the entire processing
        has_broad_try = bool(re.search(
            r'try\s*\{[^}]{100,}(getDeclaredFields|getAnnotation)[^}]{50,}\}\s*catch',
            c, re.DOTALL
        ))
        if has_try_catch_in_loop or has_try_around_field:
            components["filter_exception_resilience"] = 1.0
        elif has_broad_try:
            components["filter_exception_resilience"] = 0.4
        # No try-catch = 0 (filter will crash on any reflection error)

    # H11. DictProvider interface has proper two-parameter contract
    #      The interface MUST accept (String dictType, String dictValue) → String
    #      Weak models sometimes define getLabel(String dictType) or use Object params
    #      or forget to return String. Check the actual interface definition.
    if provider_candidates:
        for (pf, pc) in provider_candidates:
            if "interface" in pc:
                # Strong pattern: String getLabel(String ..., String ...)
                has_two_string_params = bool(re.search(
                    r'String\s+\w+\s*\(\s*String\s+\w+\s*,\s*String\s+\w+\s*\)',
                    pc
                ))
                # Medium: has two params but not both String
                has_two_params = bool(re.search(
                    r'\w+\s+\w+\s*\(\s*\w+\s+\w+\s*,\s*\w+\s+\w+\s*\)',
                    pc
                ))
                if has_two_string_params:
                    components["provider_two_param_contract"] = 1.0
                elif has_two_params:
                    components["provider_two_param_contract"] = 0.5
                break

    # Weights: basic checks total 0.30, hidden checks total 0.70
    weights = {
        # Basic structure (these are expected from any model)
        "annotation_created": 0.05,
        "provider_interface": 0.04,
        "filter_implements_afterfilter": 0.06,
        "filter_scans_fields_with_reflection": 0.04,
        "filter_appends_label_key": 0.04,
        "filter_uses_field_cache": 0.02,
        "config_registers_filter": 0.03,
        "entity_annotated": 0.02,
        # Hidden harder checks (total 0.70 — these separate strong from weak)
        "filter_thread_safe_cache": 0.07,
        "filter_null_safety": 0.10,
        "filter_class_hierarchy": 0.10,
        "filter_di_constructor": 0.06,
        "filter_value_type_conversion": 0.09,
        "filter_setaccessible_guard": 0.08,
        "filter_computeifabsent_pattern": 0.04,
        "annotation_documented": 0.03,
        # Additional hidden checks
        "filter_writeafter_override": 0.05,
        "filter_exception_resilience": 0.05,
        "provider_two_param_contract": 0.03,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace/fixtures")
    if not (ws / "enterprise-backend").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
