"""Hidden verifier for CP134 — Vue 3 i18n integration for IoT dashboard."""
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


def _find_files(base: Path, pattern: str) -> list[Path]:
    """Find all files matching pattern recursively."""
    return list(base.rglob(pattern))


def grade_workspace(ws: Path) -> dict:
    """Grade the i18n integration task."""
    # Try both possible root locations
    project = ws / "fixtures" / "smartfishery-web"
    if not project.exists():
        project = ws / "smartfishery-web"
    if not project.exists():
        # Search for it
        for candidate in [
            ws / "fixtures" / "smartfishery-web",
            ws / "smartfishery-web",
        ]:
            if candidate.exists():
                project = candidate
                break

    src = project / "src" if project.exists() else ws / "src"

    components = {k: 0.0 for k in [
        "vue_i18n_installed",
        "i18n_module_created",
        "locale_detection",
        "zh_cn_messages",
        "en_us_messages",
        "main_ts_integration",
        "element_plus_locale",
        "locale_switch_composable",
        "layout_hardcoded_removed",
    ]}

    # 1. Check vue-i18n is in package.json dependencies
    pkg_json = project / "package.json" if project.exists() else ws / "package.json"
    if pkg_json.exists():
        pkg_content = _read(pkg_json)
        if "vue-i18n" in pkg_content:
            components["vue_i18n_installed"] = 1.0
        elif "vue-i18n" in pkg_content.lower():
            components["vue_i18n_installed"] = 0.5

    # 2. Check i18n module was created (index.ts or similar)
    i18n_dir = None
    for candidate in [src / "i18n", src / "locale", src / "locales", src / "lang"]:
        if candidate.exists() and candidate.is_dir():
            i18n_dir = candidate
            break

    i18n_entry = None
    if i18n_dir:
        for name in ["index.ts", "index.js", "i18n.ts", "i18n.js", "setup.ts"]:
            f = i18n_dir / name
            if f.exists():
                i18n_entry = f
                break
        if not i18n_entry:
            # Check for any ts/js file in the i18n dir
            ts_files = list(i18n_dir.glob("*.ts")) + list(i18n_dir.glob("*.js"))
            if ts_files:
                i18n_entry = ts_files[0]

    if i18n_entry:
        content = _read(i18n_entry)
        has_create_i18n = "createI18n" in content
        has_legacy_false = "legacy" in content and "false" in content
        has_messages = "messages" in content
        if has_create_i18n and has_messages:
            components["i18n_module_created"] = 1.0
        elif has_create_i18n:
            components["i18n_module_created"] = 0.7
        else:
            components["i18n_module_created"] = 0.3

        # 3. Check locale auto-detection (browser language / localStorage)
        has_navigator = "navigator.language" in content or "navigator.languages" in content
        has_localstorage = "localStorage" in content or "storage" in content.lower()
        if has_navigator and has_localstorage:
            components["locale_detection"] = 1.0
        elif has_navigator or has_localstorage:
            components["locale_detection"] = 0.6
    else:
        # Also check if i18n setup is in main.ts directly
        main_ts = src / "main.ts"
        if main_ts.exists():
            main_content = _read(main_ts)
            if "createI18n" in main_content:
                components["i18n_module_created"] = 0.5

    # 4. Check Chinese locale messages exist with IoT-relevant content
    zh_file = None
    if i18n_dir:
        for candidate_name in ["zh-CN.ts", "zh-cn.ts", "zh.ts", "zh-CN.json", "zh.json",
                                "zh-CN.js", "zh.js"]:
            f = i18n_dir / candidate_name
            if f.exists():
                zh_file = f
                break
        if not zh_file:
            # Check in locales subdirectory
            locales_sub = i18n_dir / "locales"
            if locales_sub.exists():
                for candidate_name in ["zh-CN.ts", "zh-cn.ts", "zh.ts", "zh-CN.json"]:
                    f = locales_sub / candidate_name
                    if f.exists():
                        zh_file = f
                        break

    if zh_file:
        zh_content = _read(zh_file)
        # Check for IoT-domain translations
        iot_terms = ["dashboard", "device", "sensor", "alert", "monitor", "control",
                     "temperature", "online"]
        found_terms = sum(1 for t in iot_terms if t.lower() in zh_content.lower()
                         or any(cn in zh_content for cn in ["看板", "设备", "传感", "告警", "监控", "控制", "温度", "在线"]))
        if found_terms >= 5:
            components["zh_cn_messages"] = 1.0
        elif found_terms >= 3:
            components["zh_cn_messages"] = 0.7
        elif found_terms >= 1:
            components["zh_cn_messages"] = 0.4
        else:
            components["zh_cn_messages"] = 0.2

    # 5. Check English locale messages
    en_file = None
    if i18n_dir:
        for candidate_name in ["en-US.ts", "en-us.ts", "en.ts", "en-US.json", "en.json",
                                "en-US.js", "en.js"]:
            f = i18n_dir / candidate_name
            if f.exists():
                en_file = f
                break
        if not en_file:
            locales_sub = i18n_dir / "locales"
            if locales_sub.exists():
                for candidate_name in ["en-US.ts", "en-us.ts", "en.ts", "en-US.json"]:
                    f = locales_sub / candidate_name
                    if f.exists():
                        en_file = f
                        break

    if en_file:
        en_content = _read(en_file)
        en_terms = ["dashboard", "device", "sensor", "alert", "monitor", "control",
                    "temperature", "online", "water"]
        found_en = sum(1 for t in en_terms if t.lower() in en_content.lower())
        if found_en >= 5:
            components["en_us_messages"] = 1.0
        elif found_en >= 3:
            components["en_us_messages"] = 0.7
        elif found_en >= 1:
            components["en_us_messages"] = 0.4
        else:
            components["en_us_messages"] = 0.2

    # 6. Check main.ts integrates i18n plugin
    main_ts = src / "main.ts"
    if main_ts.exists():
        main_content = _read(main_ts)
        # Must have: import i18n, app.use(i18n)
        has_i18n_import = ("i18n" in main_content and "import" in main_content
                          and ("from" in main_content))
        has_app_use = "app.use" in main_content and "i18n" in main_content.lower()
        if has_i18n_import and has_app_use:
            components["main_ts_integration"] = 1.0
        elif has_i18n_import or has_app_use:
            components["main_ts_integration"] = 0.5

    # 7. Check Element Plus locale integration
    # Should import element-plus locale and pass to ElConfigProvider or ElementPlus config
    all_ts_files = _find_files(src, "*.ts") + _find_files(src, "*.vue")
    ep_locale_integrated = False
    for f in all_ts_files:
        content = _read(f)
        # Check for element-plus locale imports
        if ("element-plus" in content and "locale" in content.lower()
                and ("lang/zh" in content or "lang/en" in content
                     or "zhCn" in content or "zh-cn" in content)):
            ep_locale_integrated = True
            break
        # Also check for el-config-provider with locale prop
        if "el-config-provider" in content.lower() and "locale" in content:
            ep_locale_integrated = True
            break
        if "ElConfigProvider" in content and "locale" in content:
            ep_locale_integrated = True
            break

    components["element_plus_locale"] = 1.0 if ep_locale_integrated else 0.0

    # 8. Check for a locale switching composable/hook
    composable_found = False
    composable_quality = 0.0
    hook_files = _find_files(src, "use*ocal*.ts") + _find_files(src, "use*ang*.ts") + \
                 _find_files(src, "use*18n*.ts")
    if not hook_files:
        # Look in hooks/composables directories
        for dir_name in ["hooks", "composables", "utils"]:
            d = src / dir_name
            if d.exists():
                for f in d.iterdir():
                    fname = f.name.lower()
                    if ("locale" in fname or "lang" in fname or "i18n" in fname) and f.suffix in (".ts", ".js"):
                        hook_files.append(f)

    for hf in hook_files:
        content = _read(hf)
        if "useI18n" in content or "useLocale" in content:
            composable_found = True
            # Check if it has language switching logic
            has_switch = ("changeLocale" in content or "setLocale" in content
                         or "toggleLocale" in content or "switchLang" in content
                         or "locale.value" in content)
            has_persist = "localStorage" in content or "storage" in content
            if has_switch and has_persist:
                composable_quality = 1.0
            elif has_switch:
                composable_quality = 0.7
            else:
                composable_quality = 0.4
            break

    components["locale_switch_composable"] = composable_quality if composable_found else 0.0

    # 9. Check that hardcoded Chinese strings in layout/dashboard are replaced with $t() or t()
    layout_file = _find_file(src, "DefaultLayout.vue")
    dashboard_file = _find_file(src, "Dashboard.vue")
    hardcoded_removed_score = 0.0

    files_to_check = []
    if layout_file:
        files_to_check.append(layout_file)
    if dashboard_file:
        files_to_check.append(dashboard_file)

    if files_to_check:
        total_files = len(files_to_check)
        replaced_count = 0
        for f in files_to_check:
            content = _read(f)
            # Check if $t() or t() is used in template
            uses_t = ("$t(" in content or "t(" in content) and ("{{" in content or "v-" in content)
            # Check if hardcoded Chinese is significantly reduced
            # Original had: 数据看板, 设备管理, 实时监控, 告警中心, 远程控制, 报表分析,
            #               智慧渔业, 个人设置, 退出登录, 传感器, 在线设备, etc.
            chinese_pattern = re.compile(r'[一-鿿]{2,}')
            template_section = content
            # Try to extract just the template part
            template_match = re.search(r'<template>(.*?)</template>', content, re.DOTALL)
            if template_match:
                template_section = template_match.group(1)

            hardcoded_chinese = chinese_pattern.findall(template_section)
            # Filter out Chinese in comments
            if uses_t and len(hardcoded_chinese) <= 3:
                replaced_count += 1
            elif uses_t and len(hardcoded_chinese) <= 8:
                replaced_count += 0.5

        hardcoded_removed_score = replaced_count / total_files if total_files > 0 else 0.0

    components["layout_hardcoded_removed"] = min(1.0, hardcoded_removed_score)

    # Calculate weighted overall score
    weights = {
        "vue_i18n_installed": 0.08,
        "i18n_module_created": 0.18,
        "locale_detection": 0.12,
        "zh_cn_messages": 0.14,
        "en_us_messages": 0.14,
        "main_ts_integration": 0.10,
        "element_plus_locale": 0.10,
        "locale_switch_composable": 0.08,
        "layout_hardcoded_removed": 0.06,
    }
    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    # Try fixtures subdir first
    if (ws / "fixtures" / "smartfishery-web").exists():
        result = grade_workspace(ws / "fixtures")
    elif (ws / "smartfishery-web").exists():
        result = grade_workspace(ws)
    else:
        result = grade_workspace(ws / "fixtures")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
