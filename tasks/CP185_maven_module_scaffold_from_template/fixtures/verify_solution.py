"""Hidden verifier for CP185 - Maven module scaffold from template."""
from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_pom(p: Path) -> ET.Element | None:
    try:
        tree = ET.parse(p)
        return tree.getroot()
    except Exception:
        return None


def grade_workspace(ws: Path) -> dict:
    """Grade the dc-print-vision module scaffolding."""
    # Look in multiple possible locations
    vision_root = None
    for candidate in [
        ws / "dc-print-vision",
        ws / "fixtures" / "dc-print-vision",
    ]:
        if candidate.exists():
            vision_root = candidate
            break

    components = {k: 0.0 for k in [
        "parent_pom_structure",
        "api_submodule",
        "biz_submodule_pom",
        "biz_domain_classes",
        "biz_mapper_layer",
        "biz_service_layer",
        "biz_controller_layer",
        "correct_package_naming",
        "mybatis_xml_mappers",
        "root_pom_updated",
        "both_entities_complete",
        "domain_quality_depth",
        "service_method_bodies",
        "controller_crud_completeness",
        "cross_layer_consistency",
        "pom_version_management",
        "dto_vo_separation",
        "xml_base_column_list",
        "service_interface_contract",
        "api_module_interface_quality",
        "mapper_generic_type_binding",
        "module_naming_and_description",
    ]}

    if not vision_root:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
        }

    # 1. Parent POM structure: dc-print-vision/pom.xml with packaging=pom, modules
    parent_pom = vision_root / "pom.xml"
    if parent_pom.exists():
        root = _parse_pom(parent_pom)
        if root is not None:
            packaging = root.find("m:packaging", NS)
            modules = root.find("m:modules", NS)
            has_pom_packaging = packaging is not None and packaging.text == "pom"
            has_modules = modules is not None and len(modules.findall("m:module", NS)) >= 2
            parent_el = root.find("m:parent", NS)
            has_parent = parent_el is not None
            artifact = root.find("m:artifactId", NS)
            correct_artifact = artifact is not None and "vision" in (artifact.text or "").lower()

            score = 0.0
            if has_pom_packaging:
                score += 0.3
            if has_modules:
                score += 0.3
            if has_parent:
                score += 0.2
            if correct_artifact:
                score += 0.2
            components["parent_pom_structure"] = min(score, 1.0)

    # 2. API submodule: dc-print-vision-api/pom.xml exists with correct parent
    api_pom = None
    for candidate in vision_root.glob("*api*/pom.xml"):
        api_pom = candidate
        break
    if api_pom and api_pom.exists():
        root = _parse_pom(api_pom)
        if root is not None:
            parent_el = root.find("m:parent", NS)
            has_parent = parent_el is not None
            if has_parent:
                parent_art = parent_el.find("m:artifactId", NS)
                correct_parent = parent_art is not None and "vision" in (parent_art.text or "").lower()
            else:
                correct_parent = False
            artifact = root.find("m:artifactId", NS)
            has_api_artifact = artifact is not None and "api" in (artifact.text or "").lower()

            # Check for any Java source in api module
            api_dir = api_pom.parent
            has_java = any(api_dir.rglob("*.java"))

            score = 0.0
            if has_parent and correct_parent:
                score += 0.4
            if has_api_artifact:
                score += 0.3
            if has_java:
                score += 0.3
            components["api_submodule"] = min(score, 1.0)

    # 3. BIZ submodule POM: correct dependencies (api dependency, mybatis, web)
    biz_pom = None
    for candidate in vision_root.glob("*biz*/pom.xml"):
        biz_pom = candidate
        break
    biz_dir = biz_pom.parent if biz_pom else None

    if biz_pom and biz_pom.exists():
        content = _read(biz_pom)
        root = _parse_pom(biz_pom)
        if root is not None:
            parent_el = root.find("m:parent", NS)
            has_parent = parent_el is not None
            # Check dependencies
            has_api_dep = "vision" in content and "api" in content
            has_mybatis = "mybatis" in content.lower()
            has_web = "web" in content.lower()

            score = 0.0
            if has_parent:
                score += 0.25
            if has_api_dep:
                score += 0.25
            if has_mybatis:
                score += 0.25
            if has_web:
                score += 0.25
            components["biz_submodule_pom"] = min(score, 1.0)

    # 4. Domain classes: at least one domain/entity class with fields
    if biz_dir and biz_dir.exists():
        domain_files = list(biz_dir.rglob("**/domain/*.java")) + list(biz_dir.rglob("**/entity/*.java"))
        if domain_files:
            # Check quality: has fields, annotations
            best_score = 0.0
            for df in domain_files[:5]:
                c = _read(df)
                has_fields = c.count("private ") >= 2
                has_annotation = "@Table" in c or "@Data" in c or "@Entity" in c
                has_class = "class " in c
                s = 0.0
                if has_class:
                    s += 0.3
                if has_fields:
                    s += 0.4
                if has_annotation:
                    s += 0.3
                best_score = max(best_score, s)
            components["biz_domain_classes"] = min(best_score, 1.0) if len(domain_files) >= 1 else 0.5

    # 5. Mapper layer: mapper interfaces
    if biz_dir and biz_dir.exists():
        mapper_files = list(biz_dir.rglob("**/mapper/*Mapper.java"))
        if mapper_files:
            best_score = 0.0
            for mf in mapper_files[:5]:
                c = _read(mf)
                has_interface = "interface" in c
                has_mapper_anno = "@Mapper" in c
                has_base_mapper = "BaseMapper" in c
                s = 0.0
                if has_interface:
                    s += 0.4
                if has_mapper_anno:
                    s += 0.3
                if has_base_mapper:
                    s += 0.3
                best_score = max(best_score, s)
            components["biz_mapper_layer"] = min(best_score, 1.0)

    # 6. Service layer: interface + impl
    if biz_dir and biz_dir.exists():
        svc_interfaces = list(biz_dir.rglob("**/service/*Service.java"))
        svc_impls = list(biz_dir.rglob("**/service/impl/*ServiceImpl.java"))
        score = 0.0
        if svc_interfaces:
            score += 0.5
        if svc_impls:
            # Check quality
            for si in svc_impls[:3]:
                c = _read(si)
                if "implements" in c and "@Service" in c:
                    score += 0.5
                    break
            else:
                score += 0.3
        components["biz_service_layer"] = min(score, 1.0)

    # 7. Controller layer: REST controllers
    if biz_dir and biz_dir.exists():
        ctrl_files = list(biz_dir.rglob("**/controller/**/*Controller.java"))
        if not ctrl_files:
            ctrl_files = list(biz_dir.rglob("**/controller/*Controller.java"))
        if ctrl_files:
            best_score = 0.0
            for cf in ctrl_files[:5]:
                c = _read(cf)
                has_rest = "@RestController" in c
                has_mapping = "@RequestMapping" in c or "@GetMapping" in c or "@PostMapping" in c
                has_inject = "@RequiredArgsConstructor" in c or "Autowired" in c or "Resource" in c
                s = 0.0
                if has_rest:
                    s += 0.4
                if has_mapping:
                    s += 0.3
                if has_inject:
                    s += 0.3
                best_score = max(best_score, s)
            components["biz_controller_layer"] = min(best_score, 1.0)

    # 8. Correct package naming: cn.iocoder.yudao.module.vision
    if biz_dir and biz_dir.exists():
        all_java = list(biz_dir.rglob("*.java"))
        vision_pkg_count = 0
        for jf in all_java[:20]:
            c = _read(jf)
            if "package cn.iocoder.yudao.module.vision" in c:
                vision_pkg_count += 1
        if all_java:
            ratio = vision_pkg_count / min(len(all_java), 20)
            components["correct_package_naming"] = min(ratio * 1.2, 1.0)

    # 9. MyBatis XML mappers
    if biz_dir and biz_dir.exists():
        xml_files = list(biz_dir.rglob("**/mapper/*.xml")) + list(biz_dir.rglob("**/resources/mapper/*.xml"))
        # Deduplicate
        xml_files = list({str(x): x for x in xml_files}.values())
        if xml_files:
            best_score = 0.0
            for xf in xml_files[:5]:
                c = _read(xf)
                has_mapper_ns = "namespace=" in c and "vision" in c.lower()
                has_sql = "<select" in c or "<insert" in c or "<sql" in c
                s = 0.0
                if has_mapper_ns:
                    s += 0.5
                if has_sql:
                    s += 0.5
                best_score = max(best_score, s)
            components["mybatis_xml_mappers"] = min(best_score, 1.0)

    # 10. Root pom.xml updated to include vision module
    root_pom = ws / "pom.xml"
    if not root_pom.exists():
        root_pom = ws / "fixtures" / "pom.xml"
    if root_pom.exists():
        content = _read(root_pom)
        if "vision" in content.lower() and "<module" in content:
            components["root_pom_updated"] = 1.0
        elif "vision" in content.lower():
            components["root_pom_updated"] = 0.5

    # ========== HIDDEN CHECKS (harder, differentiate strong from weak) ==========

    # 11. Both entities must be fully implemented across all layers
    # Task requires VisionTask AND VisionResult — both must have domain, mapper, service, controller
    if biz_dir and biz_dir.exists():
        all_java_content = {}
        for jf in list(biz_dir.rglob("*.java"))[:50]:
            all_java_content[jf.name] = _read(jf)

        # Check VisionTask completeness
        has_vision_task_domain = any(
            "VisionTask" in c and ("class " in c) and "private " in c
            for name, c in all_java_content.items()
            if "domain" in str(name).lower() or "entity" in str(name).lower() or "VisionTask" in name
        )
        has_vision_task_mapper = any(
            "VisionTask" in c and "interface" in c
            for name, c in all_java_content.items()
            if "Mapper" in name
        )
        has_vision_task_service = any(
            "VisionTask" in c and ("interface" in c or "class " in c)
            for name, c in all_java_content.items()
            if "Service" in name and "Impl" not in name
        )
        has_vision_task_controller = any(
            "VisionTask" in c or "vision-task" in c or "visionTask" in c
            for name, c in all_java_content.items()
            if "Controller" in name
        )

        # Check VisionResult completeness
        has_vision_result_domain = any(
            "VisionResult" in c and ("class " in c) and "private " in c
            for name, c in all_java_content.items()
            if "domain" in str(name).lower() or "entity" in str(name).lower() or "VisionResult" in name
        )
        has_vision_result_mapper = any(
            "VisionResult" in c and "interface" in c
            for name, c in all_java_content.items()
            if "Mapper" in name
        )
        has_vision_result_service = any(
            "VisionResult" in c and ("interface" in c or "class " in c)
            for name, c in all_java_content.items()
            if "Service" in name and "Impl" not in name
        )
        has_vision_result_controller = any(
            "VisionResult" in c or "vision-result" in c or "visionResult" in c
            for name, c in all_java_content.items()
            if "Controller" in name
        )

        task_layers = sum([has_vision_task_domain, has_vision_task_mapper,
                          has_vision_task_service, has_vision_task_controller])
        result_layers = sum([has_vision_result_domain, has_vision_result_mapper,
                            has_vision_result_service, has_vision_result_controller])
        # Full score only if BOTH entities have all 4 layers
        components["both_entities_complete"] = (task_layers + result_layers) / 8.0

    # 12. Domain quality depth: mirroring the template's quality strictly
    # Template has: @Data, @TableName("..."), @TableId(type=IdType.AUTO), typed fields including
    # Long id, String fields, Integer fields, LocalDateTime createTime/updateTime
    if biz_dir and biz_dir.exists():
        domain_files = list(biz_dir.rglob("**/domain/*.java")) + list(biz_dir.rglob("**/entity/*.java"))
        if domain_files:
            total_quality = 0.0
            entity_count = 0
            for df in domain_files[:6]:
                c = _read(df)
                if "class " not in c:
                    continue
                entity_count += 1
                q = 0.0
                # Must have @TableName with actual table name string (snake_case)
                table_name_match = re.search(r'@TableName\s*\(\s*"([^"]+)"\s*\)', c)
                if table_name_match:
                    tname = table_name_match.group(1)
                    # Table name should be snake_case and vision-related
                    if re.match(r'^[a-z][a-z0-9_]+$', tname) and "vision" in tname:
                        q += 0.12
                    elif re.match(r'^[a-z][a-z0-9_]+$', tname):
                        q += 0.06
                # Must have @TableId with IdType
                if "@TableId" in c and "IdType" in c:
                    q += 0.10
                # Must have at least 5 meaningful fields (mirroring template's 8 fields)
                field_matches = re.findall(r'private\s+(\w+)\s+(\w+)', c)
                field_count = len(field_matches)
                if field_count >= 6:
                    q += 0.15
                elif field_count >= 4:
                    q += 0.08
                # Must have timestamp fields (createTime AND updateTime — both required)
                has_create_time = bool(re.search(r'(LocalDateTime|Date)\s+(createTime|create_time|gmtCreate)', c, re.IGNORECASE))
                has_update_time = bool(re.search(r'(LocalDateTime|Date)\s+(updateTime|update_time|gmtModified)', c, re.IGNORECASE))
                if has_create_time and has_update_time:
                    q += 0.12
                elif has_create_time or has_update_time:
                    q += 0.04
                # Must use DIVERSE field types (not all String — template uses Long, String, Integer, LocalDateTime)
                field_types = set(ft for ft, _ in field_matches)
                diverse_types = field_types - {"String"}
                if len(diverse_types) >= 3:
                    q += 0.12
                elif len(diverse_types) >= 2:
                    q += 0.06
                # Must use domain-appropriate field names (vision-related, semantically meaningful)
                vision_fields = re.findall(
                    r'private\s+\w+\s+(taskId|taskCode|resultId|imageUrl|imagePath|detectType|'
                    r'detectionType|visionType|score|confidence|label|labelName|bbox|boundingBox|'
                    r'status|taskStatus|resultStatus|defectType|inspectResult|modelName|modelVersion)',
                    c, re.IGNORECASE)
                if len(vision_fields) >= 3:
                    q += 0.20
                elif len(vision_fields) >= 2:
                    q += 0.12
                elif len(vision_fields) >= 1:
                    q += 0.05
                # Must have @Data annotation (like template)
                if "@Data" in c:
                    q += 0.05
                # Must have proper imports (at least mybatis-plus imports)
                if "com.baomidou.mybatisplus" in c:
                    q += 0.07
                # Relationship field: VisionResult should reference VisionTask via taskId
                if "VisionResult" in df.name or "vision_result" in df.name.lower():
                    if re.search(r'private\s+(Long|Integer|String)\s+taskId', c):
                        q += 0.07
                total_quality += min(q, 1.0)

            if entity_count >= 2:
                components["domain_quality_depth"] = total_quality / entity_count
            elif entity_count == 1:
                components["domain_quality_depth"] = total_quality * 0.4
        # else stays 0

    # 13. Service method bodies: not empty stubs — must have actual logic
    # Template has: query with LambdaQueryWrapper, pagination, CRUD methods with actual impl
    if biz_dir and biz_dir.exists():
        svc_impls = list(biz_dir.rglob("**/service/impl/*ServiceImpl.java"))
        if svc_impls:
            impl_quality_total = 0.0
            impl_count = 0
            for si in svc_impls[:4]:
                c = _read(si)
                if "class " not in c:
                    continue
                impl_count += 1
                q = 0.0
                # Must inject mapper via constructor or field
                if "Mapper" in c and ("@RequiredArgsConstructor" in c or "Autowired" in c or "private final" in c):
                    q += 0.15
                # Must have multiple methods (not just one)
                method_count = len(re.findall(r'(public|protected)\s+\w+[\w<>,\s]*\s+\w+\s*\(', c))
                if method_count >= 4:
                    q += 0.15
                elif method_count >= 2:
                    q += 0.08
                # Methods must have non-trivial bodies (call mapper methods)
                mapper_calls = len(re.findall(r'\w+Mapper\.\w+', c))
                if mapper_calls >= 3:
                    q += 0.15
                elif mapper_calls >= 1:
                    q += 0.08
                # Must have conditional query building (like template's LambdaQueryWrapper)
                if "LambdaQueryWrapper" in c:
                    q += 0.15
                elif "QueryWrapper" in c or "Wrapper" in c:
                    q += 0.08
                # Must have pagination support using Page class
                if "Page<" in c and ("selectPage" in c or "page(" in c):
                    q += 0.15
                elif "Page" in c:
                    q += 0.05
                # Must have null-check conditional logic (like template's if searchDTO.getXxx() != null)
                null_checks = len(re.findall(r'if\s*\([^)]*!=\s*null', c))
                if null_checks >= 2:
                    q += 0.15
                elif null_checks >= 1:
                    q += 0.08
                # Should return PageResult (like template)
                if "PageResult" in c:
                    q += 0.10
                impl_quality_total += min(q, 1.0)

            if impl_count >= 2:
                components["service_method_bodies"] = impl_quality_total / impl_count
            elif impl_count == 1:
                components["service_method_bodies"] = impl_quality_total * 0.4

    # 14. Controller CRUD completeness: must have full CRUD endpoints like template
    # Template has: @GetMapping("/page"), @GetMapping("/{id}"), @PostMapping("/create"),
    # Swagger @Operation annotations, CommonResult wrapper, @Tag
    if biz_dir and biz_dir.exists():
        ctrl_files = list(biz_dir.rglob("**/controller/**/*Controller.java"))
        if not ctrl_files:
            ctrl_files = list(biz_dir.rglob("**/controller/*Controller.java"))
        if ctrl_files:
            ctrl_quality_total = 0.0
            ctrl_count = 0
            for cf in ctrl_files[:4]:
                c = _read(cf)
                if "@RestController" not in c:
                    continue
                ctrl_count += 1
                q = 0.0
                # Must have multiple HTTP method mappings (full CRUD)
                get_count = len(re.findall(r'@GetMapping', c))
                post_count = len(re.findall(r'@PostMapping', c))
                put_count = len(re.findall(r'@PutMapping', c))
                delete_count = len(re.findall(r'@DeleteMapping', c))
                total_endpoints = get_count + post_count + put_count + delete_count
                if total_endpoints >= 4:
                    q += 0.15
                elif total_endpoints >= 3:
                    q += 0.10
                elif total_endpoints >= 2:
                    q += 0.05
                # Must have @Tag class-level annotation (like template)
                if "@Tag" in c and "name" in c[c.find("@Tag"):c.find("@Tag")+50]:
                    q += 0.12
                elif "@Tag" in c:
                    q += 0.06
                # Must have per-method @Operation annotations with summary
                op_matches = re.findall(r'@Operation\s*\(\s*summary\s*=', c)
                if len(op_matches) >= 3:
                    q += 0.15
                elif len(op_matches) >= 2:
                    q += 0.08
                # Must use CommonResult wrapper (like template)
                if "CommonResult" in c and "success(" in c:
                    q += 0.15
                elif "CommonResult" in c:
                    q += 0.08
                # Must have path variable for detail endpoint /{id}
                if "@PathVariable" in c and re.search(r'@GetMapping\s*\(\s*"/\{', c):
                    q += 0.12
                elif "@PathVariable" in c:
                    q += 0.06
                # Must have @RequestBody for create/update
                if "@RequestBody" in c:
                    q += 0.10
                # Must have pagination endpoint ("/page")
                if '"/page"' in c or "page" in c.lower().split("getmapping")[0] if "GetMapping" in c else False:
                    q += 0.12
                elif re.search(r'@GetMapping.*page', c, re.IGNORECASE):
                    q += 0.12
                # Must inject service (not mapper directly)
                if "Service" in c and ("@RequiredArgsConstructor" in c or "Autowired" in c):
                    q += 0.09
                ctrl_quality_total += min(q, 1.0)

            if ctrl_count >= 2:
                components["controller_crud_completeness"] = ctrl_quality_total / ctrl_count
            elif ctrl_count == 1:
                components["controller_crud_completeness"] = ctrl_quality_total * 0.4

    # 15. Cross-layer consistency: XML namespace must match mapper interface FQN,
    # AND resultType must match domain FQN, AND Base_Column_List must match domain fields
    if biz_dir and biz_dir.exists():
        xml_files = list(biz_dir.rglob("**/mapper/*.xml")) + list(biz_dir.rglob("**/resources/mapper/*.xml"))
        xml_files = list({str(x): x for x in xml_files}.values())
        mapper_java_files = list(biz_dir.rglob("**/mapper/*Mapper.java"))

        if xml_files and mapper_java_files:
            # Extract FQNs from Java mapper files
            mapper_fqns = set()
            for mf in mapper_java_files[:5]:
                c = _read(mf)
                pkg_match = re.search(r'package\s+([\w.]+)\s*;', c)
                class_match = re.search(r'interface\s+(\w+)', c)
                if pkg_match and class_match:
                    mapper_fqns.add(f"{pkg_match.group(1)}.{class_match.group(1)}")

            # Check XML namespace references match
            matched = 0
            total_xml = 0
            has_result_type_correct = 0
            has_base_column = 0
            for xf in xml_files[:5]:
                c = _read(xf)
                ns_match = re.search(r'namespace="([^"]+)"', c)
                if ns_match:
                    total_xml += 1
                    if ns_match.group(1) in mapper_fqns:
                        matched += 1
                # Check resultType uses full domain FQN
                if re.search(r'resultType="cn\.iocoder\.yudao\.module\.vision\.(domain|entity)\.\w+"', c):
                    has_result_type_correct += 1
                # Check Base_Column_List sql fragment exists with proper columns
                if '<sql id="Base_Column_List">' in c:
                    col_match = re.search(r'<sql id="Base_Column_List">\s*([^<]+)\s*</sql>', c)
                    if col_match:
                        cols = col_match.group(1).strip()
                        # Must have at least 5 columns (matching domain fields)
                        col_count = len([c.strip() for c in cols.split(",") if c.strip()])
                        if col_count >= 5:
                            has_base_column += 1

            if total_xml > 0:
                score = 0.0
                # Namespace correctness (40%)
                score += (matched / total_xml) * 0.40
                # ResultType correctness (30%)
                score += (has_result_type_correct / total_xml) * 0.30
                # Base_Column_List presence and quality (30%)
                score += (has_base_column / total_xml) * 0.30
                components["cross_layer_consistency"] = min(score, 1.0)

    # 16. POM version management: should use ${revision} like the template, not hardcoded
    if vision_root and vision_root.exists():
        pom_files = list(vision_root.rglob("pom.xml"))
        if pom_files:
            uses_revision = 0
            has_hardcoded = 0
            total_checked = 0
            for pf in pom_files[:5]:
                c = _read(pf)
                total_checked += 1
                if "${revision}" in c:
                    uses_revision += 1
                # Check for hardcoded version in parent/dependency version fields
                version_tags = re.findall(r'<version>([^<$]+)</version>', c)
                for v in version_tags:
                    if re.match(r'^\d+\.\d+', v.strip()) and "spring" not in c[max(0, c.find(v)-100):c.find(v)].lower():
                        has_hardcoded += 1
                        break

            score = 0.0
            if total_checked > 0:
                # All POMs must use ${revision} (parent + both submodules = 3)
                if uses_revision >= 3:
                    score += 0.6
                elif uses_revision >= 2:
                    score += 0.4
                elif uses_revision >= 1:
                    score += 0.2
                # Penalize hardcoded versions in module POMs
                if has_hardcoded == 0:
                    score += 0.4
                elif has_hardcoded <= 1:
                    score += 0.15
            components["pom_version_management"] = min(score, 1.0)

    # ========== NEW HIDDEN CHECKS (very discriminating) ==========

    # 17. DTO/VO separation: template uses SearchDTO for query params and VO for response
    # Strong models will replicate this pattern for vision entities
    if biz_dir and biz_dir.exists():
        dto_files = list(biz_dir.rglob("**/dto/*.java")) + list(biz_dir.rglob("**/pojo/dto/*.java"))
        vo_files = list(biz_dir.rglob("**/vo/*.java")) + list(biz_dir.rglob("**/pojo/vo/*.java"))

        score = 0.0
        # Must have DTO for search/query parameters
        has_search_dto = False
        dto_quality = 0.0
        for df in dto_files[:6]:
            c = _read(df)
            if "class " in c and ("Search" in c or "Query" in c or "Page" in c or "DTO" in df.name):
                has_search_dto = True
                # Quality: has page fields (pageNo, pageSize) like template's MesJobRecordSearchDTO
                if re.search(r'private\s+(Integer|int|Long)\s+(pageNo|pageNum|page)', c):
                    dto_quality += 0.15
                if re.search(r'private\s+(Integer|int|Long)\s+(pageSize|size)', c):
                    dto_quality += 0.15
                # Has actual filter fields
                filter_fields = len(re.findall(r'private\s+\w+\s+\w+', c))
                if filter_fields >= 3:
                    dto_quality += 0.15
                elif filter_fields >= 2:
                    dto_quality += 0.08

        # Must have VO for response objects
        has_vo = False
        vo_quality = 0.0
        for vf in vo_files[:6]:
            c = _read(vf)
            if "class " in c and ("VO" in vf.name or "Vo" in vf.name):
                has_vo = True
                # Quality: different from domain (has formatted/derived fields)
                vo_fields = len(re.findall(r'private\s+\w+\s+\w+', c))
                if vo_fields >= 3:
                    vo_quality += 0.15

        if has_search_dto:
            score += 0.30 + min(dto_quality, 0.30)
        if has_vo:
            score += 0.20 + min(vo_quality, 0.20)

        components["dto_vo_separation"] = min(score, 1.0)

    # 18. XML Base_Column_List and custom SQL: template has <sql id="Base_Column_List"> with
    # all table columns, and a custom <select> query. Strong models will mirror this pattern
    # with columns that match domain fields (snake_case of camelCase fields)
    if biz_dir and biz_dir.exists():
        xml_files = list(biz_dir.rglob("**/mapper/*.xml")) + list(biz_dir.rglob("**/resources/mapper/*.xml"))
        xml_files = list({str(x): x for x in xml_files}.values())
        domain_files = list(biz_dir.rglob("**/domain/*.java")) + list(biz_dir.rglob("**/entity/*.java"))

        # Extract field names from domain classes
        domain_fields_per_entity = {}
        for df in domain_files[:6]:
            c = _read(df)
            if "class " not in c:
                continue
            class_match = re.search(r'class\s+(\w+)', c)
            if class_match:
                fields = re.findall(r'private\s+\w+\s+(\w+)', c)
                domain_fields_per_entity[class_match.group(1)] = fields

        score = 0.0
        xml_checked = 0
        for xf in xml_files[:5]:
            c = _read(xf)
            if '<mapper' not in c:
                continue
            xml_checked += 1
            xf_score = 0.0

            # Must have Base_Column_List
            col_match = re.search(r'<sql\s+id="Base_Column_List">\s*([^<]+)\s*</sql>', c)
            if col_match:
                cols_str = col_match.group(1).strip()
                cols = [col.strip() for col in cols_str.split(",") if col.strip()]
                if len(cols) >= 5:
                    xf_score += 0.25
                elif len(cols) >= 3:
                    xf_score += 0.12

                # Check columns are snake_case versions of domain fields
                # Convert camelCase to snake_case for comparison
                def camel_to_snake(name):
                    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
                    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

                # Find which entity this XML corresponds to
                for entity_name, fields in domain_fields_per_entity.items():
                    snake_fields = {camel_to_snake(f) for f in fields}
                    col_set = {col.strip() for col in cols}
                    # Calculate overlap
                    overlap = len(col_set & snake_fields)
                    if overlap >= 4:
                        xf_score += 0.25
                        break
                    elif overlap >= 2:
                        xf_score += 0.12
                        break

            # Must have <include refid="Base_Column_List"/> in a select
            if '<include refid="Base_Column_List"/>' in c:
                xf_score += 0.20

            # Must have a custom select with WHERE clause
            if re.search(r'<select[^>]+>.*WHERE', c, re.DOTALL):
                xf_score += 0.15

            # Must use #{} parameter binding (not ${})
            param_bindings = re.findall(r'#\{\w+\}', c)
            if len(param_bindings) >= 1:
                xf_score += 0.15

            score += min(xf_score, 1.0)

        if xml_checked >= 2:
            components["xml_base_column_list"] = score / xml_checked
        elif xml_checked == 1:
            components["xml_base_column_list"] = score * 0.5

    # 19. Service interface contract quality: template service has typed return values,
    # PageResult<T>, getById, create, and domain-specific methods
    if biz_dir and biz_dir.exists():
        svc_interfaces = list(biz_dir.rglob("**/service/*Service.java"))
        # Exclude impl files
        svc_interfaces = [f for f in svc_interfaces if "impl" not in str(f).lower()]

        if svc_interfaces:
            iface_quality_total = 0.0
            iface_count = 0
            for sf in svc_interfaces[:4]:
                c = _read(sf)
                if "interface" not in c:
                    continue
                iface_count += 1
                q = 0.0
                # Must declare multiple methods
                method_decls = re.findall(r'([\w<>,\s]+)\s+(\w+)\s*\(([^)]*)\)\s*;', c)
                if len(method_decls) >= 4:
                    q += 0.20
                elif len(method_decls) >= 3:
                    q += 0.12
                elif len(method_decls) >= 2:
                    q += 0.06
                # Must have a pagination method returning PageResult<T>
                if re.search(r'PageResult\s*<\s*\w+\s*>\s+\w+', c):
                    q += 0.20
                # Must have getById with typed return
                if re.search(r'(Vision\w+|VisionTask|VisionResult)\s+getById\s*\(', c):
                    q += 0.15
                elif re.search(r'\w+\s+get(ById|Detail)\s*\(', c):
                    q += 0.08
                # Must have create method accepting domain/DTO
                if re.search(r'void\s+create\s*\(', c) or re.search(r'\w+\s+create\s*\(', c):
                    q += 0.12
                # Must have update method
                if re.search(r'void\s+update\w*\s*\(', c) or re.search(r'\w+\s+update\w*\s*\(', c):
                    q += 0.12
                # Must accept SearchDTO parameter (not raw params)
                if "SearchDTO" in c or "QueryDTO" in c or "PageDTO" in c:
                    q += 0.12
                # Must import from vision package (not external)
                if "cn.iocoder.yudao.module.vision" in c:
                    q += 0.09
                iface_quality_total += min(q, 1.0)

            if iface_count >= 2:
                components["service_interface_contract"] = iface_quality_total / iface_count
            elif iface_count == 1:
                components["service_interface_contract"] = iface_quality_total * 0.4

    # ========== ADDITIONAL HIDDEN CHECKS (high discrimination) ==========

    # 20. API module interface quality: template has VisionApi.java with proper Javadoc,
    # typed RPC-style methods (not CRUD but inter-module API). Weak models either skip
    # the API submodule entirely, put nothing meaningful in it, or just copy service methods.
    if api_pom and api_pom.exists():
        api_dir = api_pom.parent
        api_java_files = list(api_dir.rglob("*.java"))
        if api_java_files:
            api_quality_total = 0.0
            api_iface_count = 0
            for af in api_java_files[:5]:
                c = _read(af)
                if "interface" not in c:
                    continue
                api_iface_count += 1
                q = 0.0
                # Must be in vision.api package (correct package naming for API module)
                if "package cn.iocoder.yudao.module.vision.api" in c:
                    q += 0.15
                elif "package" in c and "vision" in c and "api" in c:
                    q += 0.08
                # Must have Javadoc comment on the interface (template has /** ... */ before interface)
                if re.search(r'/\*\*[^*]*\*/', c, re.DOTALL):
                    q += 0.15
                # Must declare at least 2 methods (template has 2 RPC methods)
                method_decls = re.findall(r'^\s*(?:[\w<>,\s]+)\s+\w+\s*\([^)]*\)\s*;', c, re.MULTILINE)
                if len(method_decls) >= 2:
                    q += 0.20
                elif len(method_decls) >= 1:
                    q += 0.10
                # Methods should have return types (not all void — these are query APIs)
                non_void_methods = re.findall(r'^\s*(?!.*void)[\w<>,\s]+\s+\w+\s*\([^)]*\)\s*;', c, re.MULTILINE)
                if len(non_void_methods) >= 1:
                    q += 0.15
                # Methods should have Javadoc per method (template has /** */ before each method)
                method_javadocs = re.findall(r'/\*\*[^*]*\*/\s*\n\s*\w', c, re.DOTALL)
                if len(method_javadocs) >= 2:
                    q += 0.15
                elif len(method_javadocs) >= 1:
                    q += 0.08
                # Interface name should contain "Vision" and "Api"
                iface_name_match = re.search(r'interface\s+(\w*Vision\w*Api\w*|\w*Api\w*)', c)
                if iface_name_match and "vision" in iface_name_match.group(1).lower():
                    q += 0.10
                elif iface_name_match:
                    q += 0.05
                # Should NOT just be a copy of the service interface (no PageResult, no SearchDTO)
                # API module is for inter-module RPC, not internal CRUD
                if "PageResult" not in c and "SearchDTO" not in c:
                    q += 0.10
                api_quality_total += min(q, 1.0)

            if api_iface_count >= 1:
                components["api_module_interface_quality"] = api_quality_total / max(api_iface_count, 1)

    # 21. Mapper extends BaseMapper<T> with correct generic type binding:
    # Template uses `extends BaseMapper<MesJobRecord>` — both VisionTask and VisionResult
    # mappers must extend BaseMapper with their respective entity type. Weak models often
    # forget the generic parameter or use raw type.
    if biz_dir and biz_dir.exists():
        mapper_files = list(biz_dir.rglob("**/mapper/*Mapper.java"))
        if mapper_files:
            correct_generics = 0
            total_mappers = 0
            has_both_entities = False
            entity_types_in_mappers = set()
            for mf in mapper_files[:6]:
                c = _read(mf)
                if "interface" not in c:
                    continue
                total_mappers += 1
                # Must extend BaseMapper<SomeEntity> with proper generic
                base_mapper_match = re.search(
                    r'interface\s+\w+Mapper\s+extends\s+BaseMapper\s*<\s*(\w+)\s*>', c)
                if base_mapper_match:
                    entity_name = base_mapper_match.group(1)
                    entity_types_in_mappers.add(entity_name)
                    # The generic type should be a Vision entity
                    if "Vision" in entity_name:
                        correct_generics += 1
                    else:
                        correct_generics += 0.3  # partial credit for wrong entity name
                # Check correct imports (must import the domain class)
                if re.search(r'import\s+cn\.iocoder\.yudao\.module\.vision\.(domain|entity)\.\w+', c):
                    correct_generics += 0.2

            # Check that BOTH VisionTask and VisionResult have mappers
            has_both_entities = ("VisionTask" in entity_types_in_mappers and
                                "VisionResult" in entity_types_in_mappers)

            score = 0.0
            if total_mappers >= 2 and has_both_entities:
                score += 0.50
            elif total_mappers >= 2:
                score += 0.30
            elif total_mappers >= 1:
                score += 0.15
            # Generic correctness
            if total_mappers > 0:
                generic_ratio = correct_generics / total_mappers
                score += min(generic_ratio * 0.50, 0.50)
            components["mapper_generic_type_binding"] = min(score, 1.0)

    # 22. POM description fields and module naming convention: template has <description> in
    # every pom.xml, and follows exact naming: dc-print-vision (parent), dc-print-vision-api,
    # dc-print-vision-biz. Weak models often use wrong naming (e.g. vision-api instead of
    # dc-print-vision-api) or skip <description> entirely.
    if vision_root and vision_root.exists():
        pom_files = list(vision_root.rglob("pom.xml"))
        if pom_files:
            has_desc_count = 0
            correct_naming_count = 0
            total_pom_checked = 0
            for pf in pom_files[:5]:
                c = _read(pf)
                root = _parse_pom(pf)
                if root is None:
                    continue
                total_pom_checked += 1

                # Check <description> element exists and is non-empty
                desc_el = root.find("m:description", NS)
                if desc_el is not None and desc_el.text and len(desc_el.text.strip()) > 0:
                    has_desc_count += 1

                # Check artifactId follows naming convention: dc-print-vision[-api|-biz]
                art_el = root.find("m:artifactId", NS)
                if art_el is not None and art_el.text:
                    art_text = art_el.text.strip()
                    # Must start with "dc-print-vision"
                    if art_text == "dc-print-vision" or art_text in (
                        "dc-print-vision-api", "dc-print-vision-biz"):
                        correct_naming_count += 1
                    elif art_text.startswith("dc-print-vision"):
                        correct_naming_count += 0.5

            score = 0.0
            if total_pom_checked > 0:
                # Description presence (40%) — must be in all POMs like template
                desc_ratio = has_desc_count / total_pom_checked
                if desc_ratio >= 0.8:
                    score += 0.40
                elif desc_ratio >= 0.5:
                    score += 0.20
                elif desc_ratio > 0:
                    score += 0.10

                # Naming convention (60%) — strict dc-print-vision-* pattern
                naming_ratio = correct_naming_count / total_pom_checked
                if naming_ratio >= 0.8:
                    score += 0.60
                elif naming_ratio >= 0.5:
                    score += 0.35
                elif naming_ratio > 0:
                    score += 0.15

            components["module_naming_and_description"] = min(score, 1.0)

    weights = _weights()
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def _weights() -> dict:
    return {
        # Basic structural checks (low weight — easy for all models)
        "parent_pom_structure": 0.03,
        "api_submodule": 0.02,
        "biz_submodule_pom": 0.02,
        "biz_domain_classes": 0.03,
        "biz_mapper_layer": 0.02,
        "biz_service_layer": 0.03,
        "biz_controller_layer": 0.03,
        "correct_package_naming": 0.02,
        "mybatis_xml_mappers": 0.02,
        "root_pom_updated": 0.02,
        # Hidden harder checks (high weight)
        "both_entities_complete": 0.10,
        "domain_quality_depth": 0.13,
        "service_method_bodies": 0.12,
        "controller_crud_completeness": 0.09,
        "cross_layer_consistency": 0.06,
        "pom_version_management": 0.03,
        # Very-discriminating checks (high weight — strong vs weak differentiators)
        "dto_vo_separation": 0.06,
        "xml_base_column_list": 0.05,
        "service_interface_contract": 0.03,
        "api_module_interface_quality": 0.04,
        "mapper_generic_type_binding": 0.03,
        "module_naming_and_description": 0.02,
    }


def main():
    # Try /workspace first, then /workspace/fixtures
    ws = Path("/workspace")
    if not (ws / "dc-print-vision").exists() and (ws / "fixtures" / "dc-print-vision").exists():
        pass  # grade_workspace handles both
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
