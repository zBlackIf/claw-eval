"""Hidden verifier for CP193 — Spring Boot module scaffolding."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(base: Path, pattern: str) -> Path | None:
    """Find a file matching pattern recursively."""
    for p in base.rglob(pattern):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for the spring boot module scaffolding task.

    Hidden grading dimensions (basic):
    1. module_pom_exists: Does dc-print-module-mobile/pom.xml exist with correct parent?
    2. parent_pom_updated: Is the module registered in the parent pom.xml?
    3. application_class: Does a valid SpringBoot Application class exist?
    4. multi_env_configs: Are environment-specific config files created (dev/test/prod)?
    5. mysql_configured: Is MySQL configured (not H2) following dc-print-server pattern?
    6. tenant_support: Is multi-tenant (yudao.tenant) configured?
    7. spring_boot_plugin: Does pom.xml have spring-boot-maven-plugin for independent run?

    Hidden grading dimensions (advanced — discriminating):
    8. port_no_conflict: Dev port must differ from dc-print-server's 48080
    9. env_differentiation: Each environment file must have genuinely different values
    10. scan_base_packages: Application class should have scanBasePackages like the reference
    11. druid_autoconfigure_exclude: Should exclude DruidDataSourceAutoConfigure per reference pattern
    12. pom_dependency_completeness: Should include all critical deps (mysql-connector, druid, dynamic-ds)

    Hidden grading dimensions (expert — pattern fidelity):
    13. prod_security_hardening: Prod config should use env vars for secrets, non-localhost hosts
    14. redis_db_isolation: Each environment should use different Redis database numbers
    15. base_config_yudao_structure: Base application.yaml should follow yudao structure exactly
    16. correct_group_id_and_package: Java package and pom groupId must match project conventions
    17. all_envs_have_port: Every env file (not just dev) must declare its own port

    Hidden grading dimensions (deep pattern — hardest to get right):
    18. correct_java_directory_structure: Java source path on disk must follow cn/iocoder/yudao
        convention (NOT com/docod/print). The groupId is com.docod.print but actual code
        uses cn.iocoder.yudao package — a subtle trap.
    19. spring_boot_plugin_version_inherited: spring-boot-maven-plugin must reference
        ${spring.boot.version} (inheriting from parent property), NOT hardcode a version string.
    20. dynamic_datasource_structure: Datasource config must follow the exact nested structure
        spring.datasource.dynamic.druid + spring.datasource.dynamic.datasource.master pattern,
        not a flat spring.datasource.url config. This is the dynamic-datasource-spring-boot-starter
        specific layout that weak models almost never produce correctly.
    """
    # Try multiple possible locations
    project_root = ws / "dc-print-api"
    if not project_root.exists():
        # Fallback: maybe files placed directly in workspace
        project_root = ws

    mobile_module = project_root / "dc-print-module-mobile"

    components = {k: 0.0 for k in [
        "module_pom_exists",
        "parent_pom_updated",
        "application_class",
        "multi_env_configs",
        "mysql_configured",
        "tenant_support",
        "spring_boot_plugin",
        "port_no_conflict",
        "env_differentiation",
        "scan_base_packages",
        "druid_autoconfigure_exclude",
        "pom_dependency_completeness",
        "prod_security_hardening",
        "redis_db_isolation",
        "base_config_yudao_structure",
        "correct_group_id_and_package",
        "all_envs_have_port",
        "correct_java_directory_structure",
        "spring_boot_plugin_version_inherited",
        "dynamic_datasource_structure",
    ]}

    # 1. Check module pom.xml exists with correct parent
    mobile_pom = mobile_module / "pom.xml"
    pom_content = ""
    if mobile_pom.exists():
        pom_content = _read(mobile_pom)
        has_parent = "dc-print-api" in pom_content
        has_artifact = "dc-print-module-mobile" in pom_content
        has_jar_packaging = "<packaging>jar</packaging>" in pom_content
        has_revision = "${revision}" in pom_content
        score = 0.0
        if has_parent:
            score += 0.3
        if has_artifact:
            score += 0.3
        if has_jar_packaging:
            score += 0.2
        if has_revision:
            score += 0.2
        components["module_pom_exists"] = min(score, 1.0)

    # 2. Check parent pom.xml has the module registered (uncommented)
    parent_pom = project_root / "pom.xml"
    if parent_pom.exists():
        parent_content = _read(parent_pom)
        lines = parent_content.split("\n")
        found_uncommented = False
        for line in lines:
            stripped = line.strip()
            if "dc-print-module-mobile" in stripped:
                if not stripped.startswith("<!--") and not stripped.startswith("//"):
                    found_uncommented = True
                    break
        components["parent_pom_updated"] = 1.0 if found_uncommented else 0.0

    # 3. Check Application class exists
    app_class = None
    app_class_content = ""
    app_class_path = None
    if mobile_module.exists():
        for java_file in mobile_module.rglob("*.java"):
            content = _read(java_file)
            if "@SpringBootApplication" in content and "public static void main" in content:
                app_class = java_file
                app_class_content = content
                app_class_path = str(java_file)
                break

    if app_class:
        has_annotation = "@SpringBootApplication" in app_class_content
        has_main = "public static void main" in app_class_content
        has_spring_run = "SpringApplication.run" in app_class_content
        has_package = "package " in app_class_content
        score = 0.0
        if has_annotation:
            score += 0.3
        if has_main:
            score += 0.3
        if has_spring_run:
            score += 0.2
        if has_package:
            score += 0.2
        components["application_class"] = min(score, 1.0)

    # 4. Check multi-environment config files
    resources_dir = None
    if mobile_module.exists():
        for d in mobile_module.rglob("resources"):
            if d.is_dir() and "main" in str(d):
                resources_dir = d
                break

    env_config_contents = {}  # env_name -> content
    base_config_content = ""
    if resources_dir:
        env_configs_found = 0
        for env in ["dev", "test", "prod"]:
            patterns = [
                f"application-{env}.yaml",
                f"application-{env}.yml",
                f"application-{env}.properties",
            ]
            for pattern in patterns:
                fp = resources_dir / pattern
                if fp.exists():
                    env_configs_found += 1
                    env_config_contents[env] = _read(fp)
                    break

        for f_name in ["application.yaml", "application.yml", "application.properties"]:
            fp = resources_dir / f_name
            if fp.exists():
                base_config_content = _read(fp)
                break

        base_config = bool(base_config_content)
        score = 0.0
        if base_config:
            score += 0.25
        score += (env_configs_found / 3.0) * 0.75
        components["multi_env_configs"] = min(score, 1.0)

    # 5. Check MySQL is configured (not H2)
    all_config_content = ""
    if resources_dir:
        for f in resources_dir.rglob("*"):
            if f.is_file() and f.suffix in [".yaml", ".yml", ".properties"]:
                all_config_content += _read(f)

        has_mysql = "mysql" in all_config_content.lower() or "com.mysql" in all_config_content
        has_h2_only = "h2" in all_config_content.lower() and not has_mysql
        has_druid = "druid" in all_config_content.lower()
        has_dynamic_ds = "dynamic" in all_config_content.lower() and "datasource" in all_config_content.lower()

        score = 0.0
        if has_mysql:
            score += 0.4
        if has_druid:
            score += 0.3
        if has_dynamic_ds:
            score += 0.3
        if has_h2_only:
            score = 0.1
        components["mysql_configured"] = min(score, 1.0)

    if mobile_pom.exists() and pom_content:
        if "mysql" in pom_content.lower() or "dynamic-datasource" in pom_content.lower():
            components["mysql_configured"] = min(components["mysql_configured"] + 0.2, 1.0)

    # 6. Check multi-tenant support
    if all_config_content:
        has_tenant_config = "tenant" in all_config_content.lower()
        has_tenant_enable = "enable" in all_config_content.lower() and has_tenant_config

        score = 0.0
        if has_tenant_config:
            score += 0.5
        if has_tenant_enable:
            score += 0.5
        components["tenant_support"] = min(score, 1.0)

    if mobile_pom.exists() and pom_content:
        if "tenant" in pom_content.lower() or "biz-tenant" in pom_content.lower():
            components["tenant_support"] = min(components["tenant_support"] + 0.3, 1.0)

    if app_class_content:
        if "tenant" in app_class_content.lower():
            components["tenant_support"] = min(components["tenant_support"] + 0.2, 1.0)

    # 7. Check spring-boot-maven-plugin for independent run
    if mobile_pom.exists() and pom_content:
        has_sb_plugin = "spring-boot-maven-plugin" in pom_content
        has_repackage = "repackage" in pom_content
        score = 0.0
        if has_sb_plugin:
            score += 0.7
        if has_repackage:
            score += 0.3
        components["spring_boot_plugin"] = min(score, 1.0)

    # ==================== ADVANCED HIDDEN CHECKS ====================

    # 8. Port no conflict: dev port must NOT be 48080 (dc-print-server's port)
    # and should be a valid port number
    if "dev" in env_config_contents:
        dev_content = env_config_contents["dev"]
        # Extract port numbers from config
        port_matches = re.findall(r"port:\s*(\d+)", dev_content)
        if port_matches:
            dev_port = int(port_matches[0])
            if dev_port != 48080 and 1024 < dev_port < 65535:
                components["port_no_conflict"] = 1.0
            elif dev_port == 48080:
                components["port_no_conflict"] = 0.0  # Directly conflicts
            else:
                components["port_no_conflict"] = 0.3  # Invalid port range
        else:
            components["port_no_conflict"] = 0.0  # No port specified at all
    else:
        components["port_no_conflict"] = 0.0

    # 9. Environment differentiation: each env file should have genuinely different values
    # Check that port numbers differ across envs and db names differ
    if len(env_config_contents) >= 2:
        score = 0.0
        # Check ports differ
        env_ports = {}
        for env, content in env_config_contents.items():
            port_matches = re.findall(r"port:\s*(\d+)", content)
            if port_matches:
                env_ports[env] = port_matches[0]

        if len(env_ports) >= 2 and len(set(env_ports.values())) == len(env_ports):
            score += 0.4  # All ports are unique across environments

        # Check db names differ across envs
        env_dbs = {}
        for env, content in env_config_contents.items():
            # Look for database name in JDBC URL or name property
            db_matches = re.findall(r"(?:name:\s*|/)(dc[_-]print[_\w]*(?:dev|test|prod|mobile)[_\w]*)", content, re.IGNORECASE)
            if not db_matches:
                db_matches = re.findall(r"/(\w+)\?", content)
            if db_matches:
                env_dbs[env] = db_matches[0]

        if len(env_dbs) >= 2 and len(set(env_dbs.values())) == len(env_dbs):
            score += 0.4  # DB names differ across environments

        # Check pool sizes differ between dev and prod
        if "dev" in env_config_contents and "prod" in env_config_contents:
            dev_max = re.findall(r"max-active:\s*(\d+)", env_config_contents["dev"])
            prod_max = re.findall(r"max-active:\s*(\d+)", env_config_contents["prod"])
            if dev_max and prod_max and dev_max[0] != prod_max[0]:
                score += 0.2  # Pool sizes differ between dev and prod

        components["env_differentiation"] = min(score, 1.0)

    # 10. scanBasePackages: Application class should have scanBasePackages
    # The reference uses scanBasePackages to cover tenant/module packages
    if app_class_content:
        has_scan_packages = "scanBasePackages" in app_class_content
        # Check it covers module packages (not just the default single package)
        has_multi_package = False
        if has_scan_packages:
            # Check for curly braces indicating multiple packages or a base package reference
            if "{" in app_class_content and "}" in app_class_content:
                has_multi_package = True
            elif "yudao.info.base-package" in app_class_content:
                has_multi_package = True
            elif re.search(r'scanBasePackages\s*=\s*"[^"]*\.(module|server|framework)', app_class_content):
                has_multi_package = True

        score = 0.0
        if has_scan_packages:
            score += 0.5
        if has_multi_package:
            score += 0.5
        components["scan_base_packages"] = min(score, 1.0)

    # 11. Druid autoconfigure exclude: Following dc-print-server's pattern,
    # the env configs should exclude DruidDataSourceAutoConfigure
    # This is a subtle but essential pattern from the reference.
    if all_config_content:
        has_exclude = "DruidDataSourceAutoConfigure" in all_config_content
        has_autoconfigure_exclude = "autoconfigure" in all_config_content.lower() and "exclude" in all_config_content.lower()
        score = 0.0
        if has_exclude:
            score = 1.0
        elif has_autoconfigure_exclude:
            score = 0.4  # Has some exclude pattern but not the right class
        components["druid_autoconfigure_exclude"] = score

    # 12. POM dependency completeness: Should include all 3 critical DB deps
    # (mysql-connector-java, druid-spring-boot-starter, dynamic-datasource-spring-boot-starter)
    # AND spring-boot-starter-web. This follows the dc-print-server pattern exactly.
    if pom_content:
        deps_found = 0
        total_deps = 4
        if "mysql-connector-java" in pom_content or "mysql-connector-j" in pom_content:
            deps_found += 1
        if "druid-spring-boot-starter" in pom_content or "druid" in pom_content.lower():
            deps_found += 1
        if "dynamic-datasource" in pom_content:
            deps_found += 1
        if "spring-boot-starter-web" in pom_content:
            deps_found += 1
        components["pom_dependency_completeness"] = deps_found / total_deps

    # ==================== EXPERT HIDDEN CHECKS ====================

    # 13. Prod security hardening: prod config should NOT use hardcoded passwords
    # and should use non-localhost database/redis hosts (following dc-print-server prod pattern)
    if "prod" in env_config_contents:
        prod_content = env_config_contents["prod"]
        score = 0.0

        # Check for environment variable references in passwords (${...})
        has_env_var_password = bool(re.search(r'password:\s*\$\{', prod_content))
        # Check for non-localhost database host
        has_non_localhost_db = bool(re.search(
            r'url:\s*jdbc:mysql://(?!127\.0\.0\.1|localhost)',
            prod_content
        ))
        # Check for non-localhost redis host
        has_non_localhost_redis = bool(re.search(
            r'host:\s*(?!127\.0\.0\.1|localhost)\S+',
            prod_content
        ))
        # Check allowPublicKeyRetrieval is false in prod (security)
        has_secure_retrieval = "allowPublicKeyRetrieval=false" in prod_content

        if has_env_var_password:
            score += 0.35
        if has_non_localhost_db:
            score += 0.3
        if has_non_localhost_redis:
            score += 0.2
        if has_secure_retrieval:
            score += 0.15

        components["prod_security_hardening"] = min(score, 1.0)

    # 14. Redis database isolation: each env should use different redis database numbers
    # (dc-print-server uses db 0 for dev, db 1 for test, db 0 for prod)
    if len(env_config_contents) >= 2:
        redis_dbs = {}
        for env, content in env_config_contents.items():
            db_match = re.findall(r'database:\s*(\d+)', content)
            # Take the last database number (which is typically the redis one after datasource)
            if db_match:
                redis_dbs[env] = db_match[-1]

        score = 0.0
        if len(redis_dbs) >= 2:
            # At least some redis database configuration exists
            score += 0.4
            # Check that at least dev and test use different db numbers
            if redis_dbs.get("dev") != redis_dbs.get("test"):
                score += 0.6
            elif len(set(redis_dbs.values())) > 1:
                score += 0.3  # Some differentiation exists

        components["redis_db_isolation"] = min(score, 1.0)

    # 15. Base application.yaml should follow the yudao structure:
    # Must have yudao.info section with base-package AND yudao.tenant section
    # AND spring.application.name should reference mobile (not just copy server's name)
    if base_config_content:
        score = 0.0

        # Check yudao.info.base-package is present
        has_yudao_info = "yudao:" in base_config_content and "info:" in base_config_content
        has_base_package = "base-package:" in base_config_content
        # Check application name references mobile, not just copies "dc-print-api"
        app_name_match = re.search(r'name:\s*(.+)', base_config_content)
        has_mobile_name = False
        if app_name_match:
            name_val = app_name_match.group(1).strip()
            has_mobile_name = "mobile" in name_val.lower()

        # Check tenant config in base
        has_tenant_in_base = "tenant:" in base_config_content and "enable:" in base_config_content

        # Check profiles.active is set
        has_profiles_active = "profiles:" in base_config_content and "active:" in base_config_content

        if has_yudao_info and has_base_package:
            score += 0.3
        if has_mobile_name:
            score += 0.25
        if has_tenant_in_base:
            score += 0.25
        if has_profiles_active:
            score += 0.2

        components["base_config_yudao_structure"] = min(score, 1.0)

    # 16. Correct groupId and Java package convention:
    # The project uses groupId=com.docod.print but package=cn.iocoder.yudao
    # The mobile module should follow the SAME package convention (cn.iocoder.yudao.*)
    # AND the pom groupId should be com.docod.print (matching parent)
    if app_class_content and pom_content:
        score = 0.0

        # Check Java package follows cn.iocoder.yudao convention
        package_match = re.search(r'package\s+([\w.]+)', app_class_content)
        if package_match:
            pkg = package_match.group(1)
            if pkg.startswith("cn.iocoder.yudao"):
                score += 0.5
            elif "docod" in pkg or "print" in pkg:
                # Used groupId as package — common mistake, partial credit
                score += 0.15

        # Check pom groupId matches parent (com.docod.print)
        has_correct_group_id = "<groupId>com.docod.print</groupId>" in pom_content
        # Also accept if it inherits from parent (no explicit groupId)
        inherits_group = "<groupId>" not in pom_content.split("<parent>")[0] if "<parent>" in pom_content else False

        if has_correct_group_id or inherits_group:
            score += 0.5

        components["correct_group_id_and_package"] = min(score, 1.0)

    # 17. All env files must declare their own port (not just dev).
    # Weak models often only set port in dev, missing test/prod ports.
    # The reference dc-print-server sets port in ALL env files.
    if len(env_config_contents) >= 2:
        envs_with_port = 0
        for env, content in env_config_contents.items():
            if re.search(r'port:\s*\d+', content):
                envs_with_port += 1

        if len(env_config_contents) > 0:
            ratio = envs_with_port / len(env_config_contents)
            if ratio >= 1.0:
                components["all_envs_have_port"] = 1.0
            elif ratio >= 0.66:
                components["all_envs_have_port"] = 0.4
            else:
                components["all_envs_have_port"] = 0.1

    # ==================== DEEP PATTERN HIDDEN CHECKS ====================

    # 18. Correct Java directory structure on disk:
    # The project's ACTUAL package convention is cn.iocoder.yudao (see dc-print-server
    # Application class). The groupId com.docod.print is a Maven-level identifier only.
    # A correct solution puts Java source under src/main/java/cn/iocoder/yudao/module/mobile/
    # Weak models often confuse groupId with package and use com/docod/print/mobile/.
    if mobile_module.exists():
        # Look for any .java file under the module
        java_files = list(mobile_module.rglob("*.java"))
        if java_files:
            score = 0.0
            # Check the actual file path on disk
            any_correct_path = False
            any_wrong_groupid_path = False
            for jf in java_files:
                rel_path = str(jf.relative_to(mobile_module))
                # Correct: uses cn/iocoder/yudao in the path
                if "cn/iocoder/yudao" in rel_path or "cn\\iocoder\\yudao" in rel_path:
                    any_correct_path = True
                # Wrong: uses com/docod/print in path (confused groupId with package)
                if "com/docod/print" in rel_path or "com\\docod\\print" in rel_path:
                    any_wrong_groupid_path = True

            if any_correct_path and not any_wrong_groupid_path:
                score = 1.0
            elif any_correct_path:
                score = 0.6  # Has correct path but also wrong ones
            elif any_wrong_groupid_path:
                score = 0.15  # Common mistake: used groupId as package path
            else:
                score = 0.3  # Some other package, partial credit

            components["correct_java_directory_structure"] = score

    # 19. spring-boot-maven-plugin version must use ${spring.boot.version} property
    # The dc-print-server reference uses <version>${spring.boot.version}</version>.
    # Weak models often hardcode something like <version>2.7.18</version> or
    # <version>2.7.6</version> which breaks version alignment.
    if pom_content and "spring-boot-maven-plugin" in pom_content:
        score = 0.0
        # Check for property reference (correct pattern)
        has_property_version = bool(re.search(
            r'spring-boot-maven-plugin.*?<version>\s*\$\{spring\.boot\.version\}\s*</version>',
            pom_content, re.DOTALL
        ))
        # Check for ANY version element near the plugin (to detect hardcoded versions)
        has_hardcoded_version = bool(re.search(
            r'spring-boot-maven-plugin.*?<version>\s*\d+\.\d+',
            pom_content, re.DOTALL
        ))
        # Check for no version at all (also acceptable if parent pluginManagement provides it)
        plugin_section = pom_content[pom_content.find("spring-boot-maven-plugin"):]
        # Look within next 200 chars for version tag
        nearby = plugin_section[:300]
        has_no_version = "<version>" not in nearby

        if has_property_version:
            score = 1.0
        elif has_no_version:
            # Acceptable: relying on parent pluginManagement (but parent doesn't
            # manage this plugin's version, so it might fail — partial credit)
            score = 0.5
        elif has_hardcoded_version:
            score = 0.2  # Hardcoded version — works but violates DRY/consistency

        components["spring_boot_plugin_version_inherited"] = score

    # 20. Dynamic datasource structure: the config must follow the exact nested layout
    # that dynamic-datasource-spring-boot-starter expects:
    #   spring.datasource.dynamic.druid.initial-size / min-idle / max-active
    #   spring.datasource.dynamic.datasource.master.url / username / password
    # Weak models often produce a flat spring.datasource.url or spring.datasource.username
    # which does NOT work with dynamic-datasource. This is the #1 functional correctness signal.
    if env_config_contents:
        score = 0.0
        configs_with_dynamic_structure = 0
        configs_with_flat_datasource = 0

        for env, content in env_config_contents.items():
            # Correct: has dynamic.datasource.master or dynamic: datasource: master: pattern
            has_dynamic_master = bool(re.search(
                r'dynamic:.*?datasource:.*?master:', content, re.DOTALL
            ))
            # Also check for the indentation pattern (YAML nested)
            has_dynamic_druid = bool(re.search(
                r'dynamic:.*?druid:', content, re.DOTALL
            ))
            # Wrong: flat datasource (spring.datasource.url directly)
            has_flat_url = bool(re.search(
                r'datasource:\s*\n\s+url:\s*jdbc:', content
            ))
            # Wrong: flat username/password at datasource level (not under master)
            has_flat_credentials = bool(re.search(
                r'datasource:\s*\n(?:\s+\w+:.*\n)*?\s+username:', content
            ))

            if has_dynamic_master:
                configs_with_dynamic_structure += 1
            if has_flat_url or (has_flat_credentials and not has_dynamic_master):
                configs_with_flat_datasource += 1

        total_env = len(env_config_contents)
        if total_env > 0:
            if configs_with_dynamic_structure == total_env and configs_with_flat_datasource == 0:
                score = 1.0
            elif configs_with_dynamic_structure > 0:
                # Partial: some configs are correct
                score = 0.3 + 0.5 * (configs_with_dynamic_structure / total_env)
            elif configs_with_flat_datasource > 0:
                score = 0.1  # Flat datasource — functionally broken with dynamic-ds

        components["dynamic_datasource_structure"] = min(score, 1.0)

    # ==================== SCORING ====================
    # Weights rebalanced: basic checks significantly reduced, hard checks dominate
    # Strong model target: 0.70-0.85, Weak model target: 0.40-0.60
    weights = {
        # Basic checks — easy to get, low weight (total: 0.20)
        "module_pom_exists": 0.04,
        "parent_pom_updated": 0.03,
        "application_class": 0.04,
        "multi_env_configs": 0.03,
        "mysql_configured": 0.02,
        "tenant_support": 0.02,
        "spring_boot_plugin": 0.02,
        # Advanced discriminating checks (total: 0.25)
        "port_no_conflict": 0.05,
        "env_differentiation": 0.06,
        "scan_base_packages": 0.05,
        "druid_autoconfigure_exclude": 0.05,
        "pom_dependency_completeness": 0.04,
        # Expert hidden checks — pattern fidelity (total: 0.30)
        "prod_security_hardening": 0.07,
        "redis_db_isolation": 0.06,
        "base_config_yudao_structure": 0.07,
        "correct_group_id_and_package": 0.06,
        "all_envs_have_port": 0.04,
        # Deep pattern checks — hardest (total: 0.25)
        "correct_java_directory_structure": 0.09,
        "spring_boot_plugin_version_inherited": 0.07,
        "dynamic_datasource_structure": 0.09,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try workspace/fixtures/dc-print-api first, then workspace/dc-print-api, then workspace
    ws = Path("/workspace/fixtures")
    if not (ws / "dc-print-api").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
