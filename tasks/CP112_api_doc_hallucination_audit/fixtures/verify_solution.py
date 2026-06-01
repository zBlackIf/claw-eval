"""Hidden verifier for CP112 — API Doc Hallucination Audit.

Checks that the agent correctly identified and fixed hallucinated/fabricated
information in API interface documents by comparing them against the actual
Java source code.

Scoring uses tiered hidden checks for discrimination:
  - Easy hidden (Tier 1): Surface-level fixes all models should catch (35% weight)
    → Province removal, obvious method fix, add missing param
  - Medium hidden (Tier 2): Structural accuracy requiring cross-referencing (30% weight)
    → Correct entity fields, correct body structure, correct path
  - Hard hidden (Tier 3): Only strong models pass these (35% weight)
    → Precise generic types (List<BrandProportionEntity>), correct ResultModel<T>
      expansion, Content-Type headers, annotation-level precision (behavior_id
      vs behaviorId), response type expansion, cross-controller path awareness

Expected issues to find and fix:
1. Doc 01: Fabricated 'province' Query param (code has NO province param for upload behavior)
2. Doc 02: Fabricated 'province' Query param (code has NO params for download behavior)
3. Doc 03: province location wrong - should be FormData not Query (code uses @FormDataParam)
4. Doc 04: Completely fabricated request body structure (code uses List<BrandProportionEntity>
   with fields: id, nfSubServiceType, brand, proportion, province, updateTime)
5. Doc 05: Completely fabricated fields (sourceName/targetName/mappingType vs actual
   MappingAddRequest with screenId/simulationId/descriptionZh/descriptionEn/sortOrder/enabled)
6. Doc 06: Wrong HTTP method (DELETE vs actual POST) AND wrong path (/screen vs /screen/delete)
   AND wrong body (List<Long> vs MappingDeleteRequest with screenId + mappingIds)
7. Doc 07: Incomplete body - only 3 fields documented vs TerminalProfileEntity with 13 fields
8. Doc 08: Missing 'brand' query parameter
9. Doc 09: Missing 'brand' query parameter + HTTP method must be PUT
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())


# =============================================================================
# TIER 1 (EASY HIDDEN): Surface-level hallucination removal (35% total)
# All models — weak or strong — should pass these.
# =============================================================================

def check_doc_01_basic(docs_dir: Path) -> float:
    """Doc 01: Should NOT have province parameter."""
    doc = _read(docs_dir / "01_upload_terminal_behavior.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    has_province = "province" in doc_lower
    has_file = "file" in doc_lower
    if not has_province and has_file:
        return 1.0
    elif not has_province:
        return 0.7
    return 0.0


def check_doc_02_basic(docs_dir: Path) -> float:
    """Doc 02: Should NOT have any request parameters."""
    doc = _read(docs_dir / "02_download_terminal_behavior.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    has_province = "province" in doc_lower
    if not has_province:
        return 1.0
    return 0.0


def check_doc_03_basic(docs_dir: Path) -> float:
    """Doc 03: province should be FormData, not Query."""
    doc = _read(docs_dir / "03_upload_access_rate.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    lines = doc.lower().split('\n')
    for line in lines:
        if 'province' in line and 'query' in line and 'formdata' not in line:
            return 0.0  # Still has Query - not fixed
    province_is_formdata = False
    for line in lines:
        if 'province' in line and 'formdata' in line:
            province_is_formdata = True
    if province_is_formdata:
        return 1.0
    if "province" in doc_lower and "formdata" in doc_lower:
        return 0.8
    return 0.0


def check_doc_06_method(docs_dir: Path) -> float:
    """Doc 06: HTTP method should be POST, not DELETE."""
    doc = _read(docs_dir / "06_delete_screen_mapping.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    has_post_in_path = bool(re.search(r'`\s*post\s+/api', doc_lower))
    has_delete_in_path = bool(re.search(r'`\s*delete\s+/api', doc_lower))
    if has_post_in_path and not has_delete_in_path:
        return 1.0
    elif "post" in doc_lower and not has_delete_in_path:
        return 0.7
    return 0.0


def check_doc_08_brand(docs_dir: Path) -> float:
    """Doc 08: Should have 'brand' as a Query parameter listed in the param table."""
    doc = _read(docs_dir / "08_get_brand_proportion.md")
    if not doc:
        return 0.0
    # Look for brand as a row in the parameter table
    lines = doc.split('\n')
    in_params_section = False
    has_brand_param_row = False
    for line in lines:
        line_lower = line.lower().strip()
        if 'request parameters' in line_lower or 'request params' in line_lower:
            in_params_section = True
        elif line_lower.startswith('#') and in_params_section:
            in_params_section = False
        if in_params_section and '|' in line:
            cells = [c.strip().lower() for c in line.split('|')]
            if 'brand' in cells and ('query' in cells or any('query' in c for c in cells)):
                has_brand_param_row = True
    if has_brand_param_row:
        return 1.0
    # Fallback: brand mentioned in param section context
    param_section = ""
    parts = re.split(r'(?i)###?\s*request\s*parameters?', doc)
    if len(parts) > 1:
        remainder = parts[1]
        next_section = re.search(r'###?\s', remainder)
        param_section = remainder[:next_section.start()] if next_section else remainder
    param_lower = _normalize(param_section)
    if 'brand' in param_lower and 'query' in param_lower:
        return 0.8
    elif 'brand' in param_lower:
        return 0.5
    return 0.0


def check_doc_09_brand(docs_dir: Path) -> float:
    """Doc 09: Should have 'brand' query parameter."""
    doc = _read(docs_dir / "09_restore_base_station_default.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    has_brand_query = bool(re.search(r'brand.*query|query.*brand', doc_lower))
    has_brand = "brand" in doc_lower
    if has_brand_query:
        return 1.0
    elif has_brand:
        return 0.7
    return 0.0


# =============================================================================
# TIER 2 (MEDIUM HIDDEN): Structural accuracy (30% total)
# Requires cross-referencing entity definitions with controller code.
# =============================================================================

def check_doc_04_structure(docs_dir: Path) -> float:
    """Doc 04: Body should use BrandProportionEntity fields, NOT fabricated structure."""
    doc = _read(docs_dir / "04_update_brand_proportion.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    # Should NOT have fabricated fields
    has_brand_name_fabricated = "brandname" in doc_lower or "brand_name" in doc_lower
    has_brand_proportions_key = "brandproportions" in doc_lower or "brand_proportions" in doc_lower
    if has_brand_name_fabricated or has_brand_proportions_key:
        return 0.0
    # Should have actual entity fields
    has_nf_sub_service = "nfsubservicetype" in doc_lower or "nf_sub_service_type" in doc_lower
    has_proportion = "proportion" in doc_lower
    has_brand = "brand" in doc_lower
    has_province = "province" in doc_lower
    score = 0.0
    if has_nf_sub_service:
        score += 0.3
    if has_proportion:
        score += 0.25
    if has_brand:
        score += 0.25
    if has_province:
        score += 0.2
    return min(score, 1.0)


def check_doc_05_structure(docs_dir: Path) -> float:
    """Doc 05: Body should be MappingAddRequest fields, NOT fabricated fields."""
    doc = _read(docs_dir / "05_add_screen_mapping.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    # Should NOT have fabricated fields
    has_source_name = "sourcename" in doc_lower or "source_name" in doc_lower
    has_target_name = "targetname" in doc_lower or "target_name" in doc_lower
    has_mapping_type = "mappingtype" in doc_lower or "mapping_type" in doc_lower
    if has_source_name or has_target_name or has_mapping_type:
        return 0.0
    # Should have actual fields
    has_screen_id = "screenid" in doc_lower or "screen_id" in doc_lower
    has_simulation_id = "simulationid" in doc_lower or "simulation_id" in doc_lower
    has_description = "description" in doc_lower
    has_sort_order = "sortorder" in doc_lower or "sort_order" in doc_lower
    has_enabled = "enabled" in doc_lower
    score = 0.0
    if has_screen_id:
        score += 0.25
    if has_simulation_id:
        score += 0.25
    if has_description:
        score += 0.2
    if has_sort_order:
        score += 0.15
    if has_enabled:
        score += 0.15
    return min(score, 1.0)


def check_doc_06_body(docs_dir: Path) -> float:
    """Doc 06: Body should be MappingDeleteRequest (screenId + mappingIds), path /screen/delete."""
    doc = _read(docs_dir / "06_delete_screen_mapping.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    score = 0.0
    # Check path includes /delete
    has_delete_path = "/screen/delete" in doc_lower
    if has_delete_path:
        score += 0.3
    # Check body structure
    has_screen_id = "screenid" in doc_lower or "screen_id" in doc_lower
    has_mapping_ids = "mappingids" in doc_lower or "mapping_ids" in doc_lower
    if has_screen_id:
        score += 0.35
    if has_mapping_ids:
        score += 0.35
    return min(score, 1.0)


def check_doc_07_fields(docs_dir: Path) -> float:
    """Doc 07: Body should have all 13 fields of TerminalProfileEntity."""
    doc = _read(docs_dir / "07_update_terminal_behavior.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    logical_fields = {
        "id": ["id"],
        "brand": ["brand"],
        "behaviorId": ["behaviorid", "behavior_id"],
        "behaviorName": ["behaviorname", "behavior_name"],
        "callRatio": ["callratio", "call_ratio"],
        "dataRatio": ["dataratio", "data_ratio"],
        "smsRatio": ["smsratio", "sms_ratio"],
        "voLteRatio": ["volteratio", "volte_ratio"],
        "vonrRatio": ["vonrratio", "vonr_ratio"],
        "networkType": ["networktype", "network_type"],
        "province": ["province"],
        "nfSubServiceType": ["nfsubservicetype", "nf_sub_service_type"],
        "updateTime": ["updatetime", "update_time"],
    }
    found = 0
    for field_name, variants in logical_fields.items():
        for v in variants:
            if v in doc_lower:
                found += 1
                break
    if found >= 11:
        return 1.0
    elif found >= 9:
        return 0.8
    elif found >= 7:
        return 0.5
    elif found >= 5:
        return 0.3
    return 0.0


# =============================================================================
# TIER 3 (HARD HIDDEN): Only strong models pass (35% total)
# Requires: precise Java generics awareness, annotation-level accuracy,
# Content-Type inference from @Consumes, ResultModel<T> generic expansion,
# and correct cross-controller endpoint differentiation.
# =============================================================================

def check_doc_04_list_generic(docs_dir: Path) -> float:
    """Hard: Doc 04 body must be List<BrandProportionEntity>, not a single object.
    The controller signature is: @Body List<BrandProportionEntity> proportions
    Strong models recognize the List wrapper and document it explicitly.
    Weak models just show a single JSON object or omit the array context."""
    doc = _read(docs_dir / "04_update_brand_proportion.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    # Prerequisite: fabricated structure must be gone
    if "brandname" in doc_lower or "brand_name" in doc_lower:
        return 0.0
    if "brandproportions" in doc_lower or "brand_proportions" in doc_lower:
        return 0.0
    score = 0.0
    # Check for explicit List/Array wrapper documentation
    has_list_generic = bool(
        re.search(r'list\s*<\s*brandproportionentity\s*>', doc_lower) or
        re.search(r'list\s*<\s*brand_proportion_entity\s*>', doc_lower)
    )
    has_array_notation = bool(
        re.search(r'array\s+of\s+brandproportion', doc_lower) or
        re.search(r'\[\s*\{', doc)  # JSON array example starting with [{
    )
    has_list_keyword = "list<" in doc_lower or "array of" in doc_lower
    if has_list_generic:
        score += 0.5
    elif has_array_notation:
        score += 0.35
    elif has_list_keyword:
        score += 0.2
    # Check all 6 fields documented with types
    type_patterns = [
        (r'\bid\b.*(?:long|integer)', 0.1),
        (r'proportion.*(?:double|number|float)', 0.1),
        (r'(?:nfsubservicetype|nf_sub_service_type).*string', 0.1),
        (r'(?:updatetime|update_time).*string', 0.1),
        (r'brand.*string', 0.05),
        (r'province.*string', 0.05),
    ]
    for pattern, weight in type_patterns:
        if re.search(pattern, doc_lower):
            score += weight
    return min(score, 1.0)


def check_doc_05_precise_types(docs_dir: Path) -> float:
    """Hard: Doc 05 must have precise types matching MappingAddRequest source.
    screenId (Long), simulationId (Long), descriptionZh (String),
    descriptionEn (String), sortOrder (Integer), enabled (Boolean).
    Strong models get ALL types right; weak models omit types or guess wrong."""
    doc = _read(docs_dir / "05_add_screen_mapping.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    # Prerequisite
    if "sourcename" in doc_lower or "targetname" in doc_lower:
        return 0.0
    score = 0.0
    type_checks = [
        # (field_pattern, type_pattern, weight)
        (r'screen.?id', r'long|integer', 0.15),
        (r'simulation.?id', r'long|integer', 0.15),
        (r'description.?zh', r'string', 0.15),
        (r'description.?en', r'string', 0.15),
        (r'sort.?order', r'integer|int', 0.2),
        (r'enabled', r'boolean|bool', 0.2),
    ]
    for field_pat, type_pat, weight in type_checks:
        # Look for field followed by type on same or nearby line
        if re.search(field_pat + r'.*?' + type_pat, doc_lower):
            score += weight
        elif re.search(type_pat + r'.*?' + field_pat, doc_lower):
            score += weight * 0.7
    return min(score, 1.0)


def check_doc_06_request_class_name(docs_dir: Path) -> float:
    """Hard: Doc 06 must reference MappingDeleteRequest by name and document
    mappingIds as List<Long> (nested generic).
    The controller has: @Body MappingDeleteRequest request
    where MappingDeleteRequest.mappingIds is List<Long>.
    Strong models trace through both the controller AND entity to get this right."""
    doc = _read(docs_dir / "06_delete_screen_mapping.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    score = 0.0
    # Must not have the old plain array pattern
    if re.search(r'\[\s*\d+\s*,\s*\d+', doc):
        return 0.0
    # Check for MappingDeleteRequest name
    has_request_name = "mappingdeleterequest" in doc_lower or "mapping_delete_request" in doc_lower
    if has_request_name:
        score += 0.35
    # Check mappingIds documented as List<Long> or Array of Long (nested generic)
    has_mapping_ids_typed = bool(
        re.search(r'mapping.?ids.*list\s*<\s*long\s*>', doc_lower) or
        re.search(r'mapping.?ids.*array.*long', doc_lower) or
        re.search(r'list\s*<\s*long\s*>.*mapping.?ids', doc_lower)
    )
    if has_mapping_ids_typed:
        score += 0.35
    elif "mappingids" in doc_lower or "mapping_ids" in doc_lower:
        score += 0.1
    # Check screenId has Long type
    has_screen_typed = bool(re.search(r'screen.?id.*long', doc_lower))
    if has_screen_typed:
        score += 0.3
    elif "screenid" in doc_lower or "screen_id" in doc_lower:
        score += 0.1
    return min(score, 1.0)


def check_doc_07_entity_name_and_types(docs_dir: Path) -> float:
    """Hard: Doc 07 must name TerminalProfileEntity explicitly AND document
    ratio fields as Double and id as Long.
    Weak models might list fields but never name the entity class or get types wrong."""
    doc = _read(docs_dir / "07_update_terminal_behavior.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    score = 0.0
    # Entity name mentioned
    has_entity_name = "terminalprofileentity" in doc_lower or "terminal_profile_entity" in doc_lower
    if has_entity_name:
        score += 0.3
    # Ratio fields have Double/Number type
    ratio_fields = ["callratio", "call_ratio", "dataratio", "data_ratio",
                    "smsratio", "sms_ratio", "volteratio", "volte_ratio",
                    "vonrratio", "vonr_ratio"]
    ratio_typed = 0
    for rf in ratio_fields:
        if rf in doc_lower:
            pattern = rf + r'.*?(?:double|number|float|decimal)'
            if re.search(pattern, doc_lower):
                ratio_typed += 1
    # Need at least 3 of 5 ratio pairs typed correctly
    if ratio_typed >= 3:
        score += 0.3
    elif ratio_typed >= 1:
        score += 0.1
    # id field has Long type
    has_id_long = bool(re.search(r'\bid\b.*(?:long|integer)', doc_lower))
    if has_id_long:
        score += 0.2
    # networkType has String type
    has_network_string = bool(re.search(r'network.?type.*string', doc_lower))
    if has_network_string:
        score += 0.2
    return min(score, 1.0)


def check_doc_08_nf_sub_service_type_param(docs_dir: Path) -> float:
    """Hard: Doc 08 getBrandProportion has TWO query params from source:
    @QueryParam("nf_sub_service_type") String nfSubServiceType
    @QueryParam("brand") String brand
    Strong models document BOTH in the params table with correct snake_case names
    AND correct types. Weak models only have nf_sub_service_type (already present)
    but miss brand in the table, or omit types."""
    doc = _read(docs_dir / "08_get_brand_proportion.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    score = 0.0
    # Check BOTH params exist in the parameter table (not just in title/text)
    lines = doc.split('\n')
    in_params_section = False
    has_nf_in_table = False
    has_brand_in_table = False
    has_brand_typed_string = False
    has_nf_typed_string = False
    for line in lines:
        line_lower = line.lower().strip()
        if 'request parameters' in line_lower or 'request params' in line_lower:
            in_params_section = True
        elif line_lower.startswith('#') and in_params_section:
            in_params_section = False
        if in_params_section and '|' in line:
            cells = [c.strip().lower() for c in line.split('|')]
            if any('nf_sub_service_type' in c for c in cells):
                has_nf_in_table = True
                if any('string' in c for c in cells):
                    has_nf_typed_string = True
            if 'brand' in cells:
                has_brand_in_table = True
                if any('string' in c for c in cells):
                    has_brand_typed_string = True
    # Both params in table = strong model behavior
    if has_nf_in_table and has_brand_in_table:
        score += 0.4
    elif has_brand_in_table:
        score += 0.2  # Added brand but somehow lost nf
    # nf uses correct snake_case (annotation name)
    if has_nf_in_table:
        score += 0.1  # Already present in original, but confirm preserved
    # Both have String type annotations
    if has_nf_typed_string and has_brand_typed_string:
        score += 0.3
    elif has_brand_typed_string:
        score += 0.15
    # Check for additional precision: Required field marked correctly
    # brand is not required in source (no @Required annotation), nf_sub_service_type also optional
    # Strong models mark both as optional or don't mark required
    if has_brand_in_table:
        for line in lines:
            if '|' in line and 'brand' in line.lower():
                cells = [c.strip().lower() for c in line.split('|')]
                # If correctly marked as No/Optional for required
                if any('no' in c or 'optional' in c or 'false' in c for c in cells):
                    score += 0.2
                    break
                # If incorrectly marked yes, no bonus
                elif any('yes' in c or 'true' in c for c in cells):
                    break
                # Not explicitly marked either way is acceptable
                else:
                    score += 0.1
                    break
    return min(score, 1.0)


def check_doc_09_method_preserved(docs_dir: Path) -> float:
    """Hard: Doc 09 method must stay PUT (not mistakenly changed to POST/GET).
    The source has @PUT for restoreBaseStationDefault. Weak models might change it
    to POST when editing, especially since many other endpoints are POST.
    Also brand param must have type String and be explicitly marked Query."""
    doc = _read(docs_dir / "09_restore_base_station_default.md")
    if not doc:
        return 0.0
    doc_lower = _normalize(doc)
    score = 0.0
    # Check PUT preserved in API path line
    has_put_in_path = bool(re.search(r'`\s*put\s+/api', doc_lower))
    has_post_in_path = bool(re.search(r'`\s*post\s+/api', doc_lower))
    has_get_in_path = bool(re.search(r'`\s*get\s+/api', doc_lower))
    if has_put_in_path and not has_post_in_path and not has_get_in_path:
        score += 0.4
    elif "put" in doc_lower and not has_post_in_path:
        score += 0.2
    # Check brand has type String documented
    has_brand_string = bool(re.search(r'brand.*string', doc_lower))
    if has_brand_string:
        score += 0.3
    # Check brand is in param table with Query location and String type
    lines = doc.split('\n')
    in_params = False
    for line in lines:
        ll = line.lower().strip()
        if 'request parameters' in ll or 'request params' in ll:
            in_params = True
        elif ll.startswith('#') and in_params:
            in_params = False
        if in_params and '|' in line:
            cells = [c.strip().lower() for c in line.split('|')]
            if 'brand' in cells:
                if any('query' in c for c in cells) and any('string' in c for c in cells):
                    score += 0.3
                elif any('query' in c for c in cells):
                    score += 0.2
    return min(score, 1.0)


def check_content_type_headers(docs_dir: Path) -> float:
    """Hard: Docs should explicitly document Content-Type based on @Consumes annotations.
    - Docs 04, 05, 06: application/json (from @Consumes(MediaType.APPLICATION_JSON))
    - Docs 01, 03: multipart/form-data (from @Consumes(MediaType.MULTIPART_FORM_DATA))
    Strong models infer Content-Type from annotations; weak models omit headers entirely."""
    score = 0.0
    checks_passed = 0
    total_checks = 5

    # Docs 04, 05, 06 should mention application/json or Content-Type
    for docname in ["04_update_brand_proportion.md", "05_add_screen_mapping.md",
                    "06_delete_screen_mapping.md"]:
        doc = _read(docs_dir / docname)
        if not doc:
            continue
        doc_lower = _normalize(doc)
        if "application/json" in doc_lower or "content-type" in doc_lower:
            checks_passed += 1

    # Doc 01 should mention multipart/form-data
    doc01 = _read(docs_dir / "01_upload_terminal_behavior.md")
    if doc01:
        doc01_lower = _normalize(doc01)
        if "multipart/form-data" in doc01_lower:
            checks_passed += 1

    # Doc 03 should mention multipart/form-data
    doc03 = _read(docs_dir / "03_upload_access_rate.md")
    if doc03:
        doc03_lower = _normalize(doc03)
        if "multipart/form-data" in doc03_lower:
            checks_passed += 1

    return checks_passed / total_checks


def check_response_resultmodel_generic(docs_dir: Path) -> float:
    """Hard: Response should show ResultModel<T> generic structure.
    Source code: ResultModel<T> { Integer code; String message; T data; }
    For doc 08 (getBrandProportion), data type should be List<BrandProportionEntity>
    or at minimum reference BrandProportionEntity.
    For doc 04 (updateBrandProportion), data is typically null/void.
    Strong models expand the generic; weak ones just show {"code":200,"message":"success"}."""
    score = 0.0

    # Check doc 08 response references BrandProportionEntity or expands data
    doc08 = _read(docs_dir / "08_get_brand_proportion.md")
    if doc08:
        doc08_lower = _normalize(doc08)
        # Must NOT just have "data": null or "data": "Object"
        has_entity_ref = "brandproportionentity" in doc08_lower or "brand_proportion_entity" in doc08_lower
        has_resultmodel_ref = "resultmodel" in doc08_lower or "result_model" in doc08_lower
        has_data_expansion = bool(re.search(r'"data".*(?:proportion|brand|nfsubservice)', doc08_lower))
        if has_entity_ref and has_resultmodel_ref:
            score += 0.6
        elif has_entity_ref:
            score += 0.4
        elif has_data_expansion:
            score += 0.25
        elif has_resultmodel_ref:
            score += 0.2

    # Check doc 05 response mentions ResultModel or has proper structure
    doc05 = _read(docs_dir / "05_add_screen_mapping.md")
    if doc05:
        doc05_lower = _normalize(doc05)
        has_resultmodel = "resultmodel" in doc05_lower or "result_model" in doc05_lower
        has_code_msg = '"code"' in doc05_lower and '"message"' in doc05_lower
        if has_resultmodel:
            score += 0.4
        elif has_code_msg:
            score += 0.15

    return min(score, 1.0)


# =============================================================================
# MAIN GRADING
# =============================================================================

def grade_workspace(ws: Path) -> dict:
    """Grade the entire workspace with tiered hidden scoring for discrimination.

    Tier 1 (Easy): 35% — all models should pass
    Tier 2 (Medium): 30% — requires cross-referencing
    Tier 3 (Hard): 35% — only strong models pass
    """
    docs_dir = None
    candidates = [
        ws / "fixtures" / "signaling-sim-project" / "docs" / "interfaces",
        ws / "signaling-sim-project" / "docs" / "interfaces",
    ]
    for c in candidates:
        if c.exists():
            docs_dir = c
            break

    if docs_dir is None:
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "Could not find interface docs directory"
        }

    # --- Tier 1: Easy hidden — surface hallucination removal (35% of total) ---
    tier1 = {
        "t1_doc01_remove_province": check_doc_01_basic(docs_dir),
        "t1_doc02_remove_province": check_doc_02_basic(docs_dir),
        "t1_doc03_fix_location": check_doc_03_basic(docs_dir),
        "t1_doc06_fix_method": check_doc_06_method(docs_dir),
        "t1_doc08_add_brand": check_doc_08_brand(docs_dir),
        "t1_doc09_add_brand": check_doc_09_brand(docs_dir),
    }
    tier1_weights = {
        "t1_doc01_remove_province": 0.18,
        "t1_doc02_remove_province": 0.18,
        "t1_doc03_fix_location": 0.18,
        "t1_doc06_fix_method": 0.18,
        "t1_doc08_add_brand": 0.14,
        "t1_doc09_add_brand": 0.14,
    }
    tier1_score = sum(tier1_weights[k] * tier1[k] for k in tier1_weights)

    # --- Tier 2: Medium hidden — structural accuracy (30% of total) ---
    tier2 = {
        "t2_doc04_structure": check_doc_04_structure(docs_dir),
        "t2_doc05_structure": check_doc_05_structure(docs_dir),
        "t2_doc06_body": check_doc_06_body(docs_dir),
        "t2_doc07_fields": check_doc_07_fields(docs_dir),
    }
    tier2_weights = {
        "t2_doc04_structure": 0.25,
        "t2_doc05_structure": 0.25,
        "t2_doc06_body": 0.25,
        "t2_doc07_fields": 0.25,
    }
    tier2_score = sum(tier2_weights[k] * tier2[k] for k in tier2_weights)

    # --- Tier 3: Hard hidden — only strong models pass (35% of total) ---
    tier3 = {
        "t3_doc04_list_generic": check_doc_04_list_generic(docs_dir),
        "t3_doc05_precise_types": check_doc_05_precise_types(docs_dir),
        "t3_doc06_request_class": check_doc_06_request_class_name(docs_dir),
        "t3_doc07_entity_types": check_doc_07_entity_name_and_types(docs_dir),
        "t3_doc08_nf_param": check_doc_08_nf_sub_service_type_param(docs_dir),
        "t3_doc09_method_preserved": check_doc_09_method_preserved(docs_dir),
        "t3_content_type": check_content_type_headers(docs_dir),
        "t3_response_generic": check_response_resultmodel_generic(docs_dir),
    }
    tier3_weights = {
        "t3_doc04_list_generic": 0.14,
        "t3_doc05_precise_types": 0.14,
        "t3_doc06_request_class": 0.14,
        "t3_doc07_entity_types": 0.13,
        "t3_doc08_nf_param": 0.13,
        "t3_doc09_method_preserved": 0.12,
        "t3_content_type": 0.10,
        "t3_response_generic": 0.10,
    }
    tier3_score = sum(tier3_weights[k] * tier3[k] for k in tier3_weights)

    # Final weighted score: Tier1=35%, Tier2=30%, Tier3=35%
    overall = 0.35 * tier1_score + 0.30 * tier2_score + 0.35 * tier3_score

    components = {}
    components.update(tier1)
    components.update(tier2)
    components.update(tier3)

    return {
        "overall_score": round(overall, 4),
        "tier1_easy_score": round(tier1_score, 4),
        "tier2_medium_score": round(tier2_score, 4),
        "tier3_hard_score": round(tier3_score, 4),
        "tier_weights": {"easy": 0.35, "medium": 0.30, "hard": 0.35},
        "components": {k: round(v, 4) for k, v in components.items()},
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
