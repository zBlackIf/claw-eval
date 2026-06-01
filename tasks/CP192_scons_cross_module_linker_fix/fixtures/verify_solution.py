"""Hidden verifier for CP192 — SCons Cross-Module Linker Fix.

Checks that the agent correctly fixed the build configuration to resolve
the undefined reference to `fs_set_sync_timer` from the OEM module.

Tiered hidden-check architecture:
  - Visible checks (25%): basic correctness, all competent agents pass
  - Hidden-easy checks (35%): structural correctness most good agents get
  - Hidden-hard checks (40%): deep build-system expertise, only strong agents pass

Hidden checks combined = 75% (>= 30% requirement satisfied).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    project = ws / "modem_project"
    if not project.exists():
        project = ws
        if not (project / "core").exists():
            project = ws / "fixtures" / "modem_project"

    components = {k: 0.0 for k in [
        # --- Visible checks (25% total) — all agents should pass ---
        "efs_scons_includes_rmts_pm",
        "oem_scons_has_efs_inc_path",
        "oem_source_includes_header",
        "linker_has_efs_dependency",
        "build_succeeds",
        # --- Hidden-easy checks (35% total) — most good agents pass ---
        "module_boundary_clean",
        "makefile_has_rmts_compile_rule",
        "makefile_oem_has_efs_include",
        "no_workaround_hacks",
        "include_in_header_section",
        # --- Hidden-hard checks (40% total) — only strong agents pass ---
        "restricted_api_pattern_used",
        "linker_order_correct",
        "makefile_archive_membership",
        "include_ordering_after_fibo_svc",
        "sconstruct_uses_library_object",
        "makefile_efs_inc_in_rmts_rule",
    ]}

    # ===================================================================
    # VISIBLE CHECKS (25% total) — basic correctness
    # ===================================================================

    # --- Check 1: efs.scons now compiles fs_rmts_pm.c ---
    efs_scons = project / "core" / "storage" / "efs" / "build" / "efs.scons"
    if efs_scons.exists():
        content = _read(efs_scons)
        if "fs_rmts_pm" in content:
            lines = content.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "fs_rmts_pm" in stripped and ".c" in stripped:
                    components["efs_scons_includes_rmts_pm"] = 1.0
                    break

    # --- Check 2: fibo_qmi.scons has efs/inc in CPPPATH ---
    oem_scons = project / "oem" / "fibo_qmi" / "build" / "fibo_qmi.scons"
    if oem_scons.exists():
        content = _read(oem_scons)
        if re.search(r"core/storage/efs/inc|CORE_STORAGE_EFS|efs.*inc", content):
            lines = content.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if re.search(r"core/storage/efs/inc|CORE_STORAGE_EFS", stripped):
                    components["oem_scons_has_efs_inc_path"] = 1.0
                    break

    # --- Check 3: qmi_fibo_svc.c includes fs_rmts_pm.h ---
    oem_src = project / "oem" / "fibo_qmi" / "src" / "qmi_fibo_svc.c"
    if oem_src.exists():
        content = _read(oem_src)
        if re.search(r'#include\s*[<"]fs_rmts_pm\.h[>"]', content):
            components["oem_source_includes_header"] = 1.0

    # --- Check 4: Linker configuration includes efs library ---
    sconstruct = project / "SConstruct"
    if sconstruct.exists():
        content = _read(sconstruct)
        if "efs" in content:
            if re.search(r"LIBS.*efs|efs.*lib|core_libs.*efs", content, re.DOTALL):
                components["linker_has_efs_dependency"] = 1.0

    core_scons = project / "core" / "build" / "core.scons"
    if core_scons.exists() and components["linker_has_efs_dependency"] < 1.0:
        content = _read(core_scons)
        if "efs" in content:
            components["linker_has_efs_dependency"] = 0.3

    # --- Check 5: Attempt actual build ---
    makefile = project / "Makefile"
    if makefile.exists():
        try:
            subprocess.run(
                ["make", "-C", str(project), "clean"],
                capture_output=True, timeout=10
            )
            result = subprocess.run(
                ["make", "-C", str(project), "all"],
                capture_output=True, timeout=30,
                text=True,
            )
            if result.returncode == 0:
                components["build_succeeds"] = 1.0
            elif ("undefined reference" not in result.stderr
                  and "undeclared function" not in result.stderr
                  and "implicit declaration" not in result.stderr):
                components["build_succeeds"] = 0.3
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            try:
                compile_ok = True
                src_files = [
                    (project / "core/storage/efs/src/efs_core.c",
                     ["-Icore/api/common", "-Icore/api/common/storage", "-Icore/storage/efs/inc"]),
                    (project / "core/storage/efs/src/fs_rmts_pm.c",
                     ["-Icore/storage/efs/inc"]),
                    (project / "core/mproc/qmi/src/qmi_csi_common.c",
                     ["-Icore/mproc/qmi/inc"]),
                    (project / "oem/fibo_qmi/src/qmi_fibo_svc.c",
                     ["-Icore/api/common/storage", "-Icore/mproc/qmi/inc",
                      "-Ioem/fibo_qmi/inc", "-Icore/storage/efs/inc"]),
                ]
                objs = []
                for src, incs in src_files:
                    if not src.exists():
                        compile_ok = False
                        break
                    obj = str(project / "build" / "libs" / (src.stem + ".o"))
                    os.makedirs(os.path.dirname(obj), exist_ok=True)
                    cmd = ["gcc", "-Wall", "-std=c99", "-c", str(src), "-o", obj] + [
                        f"-I{project}/{inc.lstrip('-I')}" for inc in incs
                    ]
                    r = subprocess.run(cmd, capture_output=True, timeout=10, cwd=str(project))
                    if r.returncode != 0:
                        compile_ok = False
                        break
                    objs.append(obj)

                if compile_ok and objs:
                    out = str(project / "build" / "oem_pd_img")
                    r = subprocess.run(
                        ["gcc", "-o", out] + objs,
                        capture_output=True, timeout=10, text=True
                    )
                    if r.returncode == 0:
                        components["build_succeeds"] = 1.0
                    elif "undefined reference" not in r.stderr:
                        components["build_succeeds"] = 0.3
            except Exception:
                pass

    # ===================================================================
    # HIDDEN-EASY CHECKS (35% total) — structural correctness
    # Most good agents get these right because they follow logical steps,
    # but weak agents that use shortcuts/workarounds will fail.
    # ===================================================================

    # --- Check 6: Module boundary completely clean ---
    # No copying files across modules, no stubs, no commented-out calls,
    # no weak symbols, no extern hacks. Any violation = 0.
    components["module_boundary_clean"] = 1.0  # start optimistic

    # (a) Check if fs_rmts_pm.c was copied to OEM directory
    oem_rmts_copy = project / "oem" / "fibo_qmi" / "src" / "fs_rmts_pm.c"
    if oem_rmts_copy.exists():
        components["module_boundary_clean"] = 0.0

    # (b) Check if fs_rmts_pm.c was added to OEM scons sources
    if oem_scons.exists() and components["module_boundary_clean"] > 0:
        oem_scons_content = _read(oem_scons)
        lines = oem_scons_content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "fs_rmts_pm.c" in stripped:
                components["module_boundary_clean"] = 0.0
                break

    # (c) Check for stub/redefinition of fs_set_sync_timer in OEM source
    if oem_src.exists() and components["module_boundary_clean"] > 0:
        oem_content = _read(oem_src)
        if re.search(r'(int|void)\s+fs_set_sync_timer\s*\(', oem_content):
            components["module_boundary_clean"] = 0.0

    # (d) Function call must still be active (not commented/removed)
    if oem_src.exists() and components["module_boundary_clean"] > 0:
        oem_content = _read(oem_src)
        if not re.search(r'^\s*fs_set_sync_timer\s*\(', oem_content, re.MULTILINE):
            if re.search(r'//.*fs_set_sync_timer|/\*.*fs_set_sync_timer', oem_content):
                components["module_boundary_clean"] = 0.0
            elif "fs_set_sync_timer" not in oem_content:
                components["module_boundary_clean"] = 0.0

    # Check for copies in any OEM subdirectory
    oem_src_dir = project / "oem" / "fibo_qmi" / "src"
    if oem_src_dir.exists() and components["module_boundary_clean"] > 0:
        for f in oem_src_dir.iterdir():
            if f.suffix == ".c" and f.name != "qmi_fibo_svc.c":
                c = _read(f)
                if "fs_set_sync_timer" in c and re.search(r'(int|void)\s+fs_set_sync_timer\s*\(', c):
                    components["module_boundary_clean"] = 0.0
                    break

    # --- Check 7: Makefile has fs_rmts_pm.c compilation rule ---
    # The Makefile must have a rule to compile fs_rmts_pm.c into an object file.
    # This is a straightforward requirement that good agents catch.
    components["makefile_has_rmts_compile_rule"] = 0.0

    if makefile.exists():
        mf_content = _read(makefile)
        if re.search(r'fs_rmts_pm\.o.*:.*fs_rmts_pm\.c|fs_rmts_pm\.c.*-o.*fs_rmts_pm\.o', mf_content):
            components["makefile_has_rmts_compile_rule"] = 1.0
        elif re.search(r'fs_rmts_pm', mf_content) and "fs_rmts_pm.c" in mf_content:
            # Mentioned but rule not properly formed
            components["makefile_has_rmts_compile_rule"] = 0.4

    # --- Check 8: Makefile OEM compile line includes efs include path ---
    # qmi_fibo_svc.c compilation must have -Icore/storage/efs/inc or $(EFS_INC)
    components["makefile_oem_has_efs_include"] = 0.0

    if makefile.exists():
        mf_content = _read(makefile)
        oem_rule_match = re.search(
            r'qmi_fibo_svc\.o.*\n\s*\$\(CC\)(.+)', mf_content)
        if oem_rule_match:
            oem_compile_flags = oem_rule_match.group(1)
            if "EFS_INC" in oem_compile_flags or "core/storage/efs/inc" in oem_compile_flags:
                components["makefile_oem_has_efs_include"] = 1.0
        elif re.search(r'qmi_fibo_svc.*EFS_INC|qmi_fibo_svc.*efs/inc', mf_content, re.DOTALL):
            components["makefile_oem_has_efs_include"] = 0.7

    # --- Check 9: No workaround hacks ---
    # Checks for weak symbols, extern declarations instead of proper include,
    # conditional compilation guards to bypass the issue, etc.
    components["no_workaround_hacks"] = 1.0  # start optimistic

    if oem_src.exists():
        oem_content = _read(oem_src)
        # weak symbol workaround
        if re.search(r'__attribute__.*weak|__weak|#pragma\s+weak', oem_content):
            components["no_workaround_hacks"] = 0.0
        # extern declaration instead of proper include
        elif re.search(r'extern\s+(int|void)\s+fs_set_sync_timer', oem_content):
            components["no_workaround_hacks"] = 0.0
        # dlsym/dlopen workaround
        elif re.search(r'dlsym|dlopen', oem_content):
            components["no_workaround_hacks"] = 0.0
        # ifdef guard to skip the call entirely
        elif re.search(r'#if.*defined.*SKIP.*fs_set_sync|#ifdef\s+NO_EFS', oem_content):
            components["no_workaround_hacks"] = 0.0

    # --- Check 10: Include is in header section (not inside function body) ---
    # The #include "fs_rmts_pm.h" must be at file top, not inside a function.
    components["include_in_header_section"] = 0.0

    if oem_src.exists():
        oem_content = _read(oem_src)
        lines = oem_content.split("\n")
        include_rmts_line = -1
        first_code_line = -1

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#include") and "fs_rmts_pm" in stripped:
                include_rmts_line = i
            if (first_code_line < 0 and stripped
                    and not stripped.startswith("#")
                    and not stripped.startswith("//")
                    and not stripped.startswith("/*")
                    and not stripped.startswith("*")
                    and not stripped == ""):
                first_code_line = i

        if include_rmts_line >= 0:
            # Must be before first code line
            if first_code_line < 0 or include_rmts_line < first_code_line:
                # Also must not be inside braces
                depth_at_include = 0
                for j in range(include_rmts_line):
                    depth_at_include += lines[j].count("{") - lines[j].count("}")
                if depth_at_include == 0:
                    components["include_in_header_section"] = 1.0
                else:
                    components["include_in_header_section"] = 0.3

    # ===================================================================
    # HIDDEN-HARD CHECKS (40% total) — deep build-system expertise
    # Only strong agents with genuine understanding of SCons, static
    # linking semantics, and build-system conventions will pass these.
    # ===================================================================

    # --- Check 11: RESTRICTED_API pattern usage ---
    # The efs.scons file exports a RESTRICTED_APIS dict. A truly expert fix would
    # reference this pattern in fibo_qmi.scons (e.g. using RequireRestrictedApi,
    # or referencing CORE_STORAGE_EFS). A naive fix just hardcodes the path.
    components["restricted_api_pattern_used"] = 0.0

    if oem_scons.exists():
        oem_content = _read(oem_scons)
        # Highest credit: uses the RESTRICTED_APIS pattern explicitly
        if re.search(r'RESTRICTED_API|RequireRestrictedApi|CORE_STORAGE_EFS', oem_content, re.IGNORECASE):
            components["restricted_api_pattern_used"] = 1.0
        elif re.search(r'#.*restricted|#.*internal.*api|#.*efs.*private', oem_content, re.IGNORECASE):
            # Acknowledges restricted API in a comment
            components["restricted_api_pattern_used"] = 0.3

    # --- Check 12: Linker order correctness in SConstruct ---
    # In static linking, the library that DEFINES a symbol must come AFTER
    # the library that REFERENCES it. oem_lib before core_libs['efs'].
    components["linker_order_correct"] = 0.0

    if sconstruct.exists():
        content = _read(sconstruct)
        libs_lines = []
        for line in content.split("\n"):
            if "LIBS" in line:
                libs_lines.append(line)

        for libs_line in libs_lines:
            if "efs" not in libs_line:
                continue
            oem_idx = -1
            efs_idx = -1
            for m in re.finditer(r'oem_lib|fibo', libs_line, re.IGNORECASE):
                if oem_idx < 0:
                    oem_idx = m.start()
            for m in re.finditer(r'efs', libs_line, re.IGNORECASE):
                efs_idx = m.start()
            if oem_idx >= 0 and efs_idx > oem_idx:
                components["linker_order_correct"] = 1.0
            elif oem_idx >= 0 and efs_idx >= 0 and efs_idx < oem_idx:
                # Wrong order
                components["linker_order_correct"] = 0.15
            elif efs_idx >= 0:
                # efs present but no oem reference on same line
                components["linker_order_correct"] = 0.3
            break

    # --- Check 13: Makefile libefs.a archive includes fs_rmts_pm.o ---
    # Beyond just having a compile rule, the object must be archived into libefs.a.
    # This requires understanding that static libraries are ar archives.
    components["makefile_archive_membership"] = 0.0

    if makefile.exists():
        mf_content = _read(makefile)
        # Check that fs_rmts_pm.o is part of the libefs.a archive command
        if re.search(r'libefs\.a.*fs_rmts_pm\.o|ar\s+\w+\s+.*libefs.*fs_rmts_pm', mf_content):
            components["makefile_archive_membership"] = 1.0
        elif re.search(r'fs_rmts_pm\.o.*libefs\.a', mf_content):
            components["makefile_archive_membership"] = 1.0
        elif re.search(r'EFS_OBJS.*fs_rmts_pm|fs_rmts_pm.*EFS_OBJS', mf_content):
            # Uses a variable that feeds into the archive
            components["makefile_archive_membership"] = 0.8

    # --- Check 14: Include ordering — fs_rmts_pm.h AFTER qmi_fibo_svc.h ---
    # fs_rmts_pm.h must come after qmi_fibo_svc.h because
    # FIBO_SLEEP_RMT_SYNC_TIMEOUT (defined in qmi_fibo_svc.h) is used as
    # argument to fs_set_sync_timer. Only a model that traces data dependencies
    # across headers will get this ordering right.
    components["include_ordering_after_fibo_svc"] = 0.0

    if oem_src.exists():
        oem_content = _read(oem_src)
        lines = oem_content.split("\n")
        include_rmts_line = -1
        include_fibo_svc_line = -1

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#include") and "fs_rmts_pm" in stripped:
                include_rmts_line = i
            if stripped.startswith("#include") and "qmi_fibo_svc" in stripped:
                include_fibo_svc_line = i

        if include_rmts_line >= 0 and include_fibo_svc_line >= 0:
            if include_rmts_line > include_fibo_svc_line:
                components["include_ordering_after_fibo_svc"] = 1.0
            else:
                # Wrong order — placed before qmi_fibo_svc.h
                components["include_ordering_after_fibo_svc"] = 0.0
        elif include_rmts_line >= 0:
            # qmi_fibo_svc.h not found (maybe removed?) — can't verify ordering
            components["include_ordering_after_fibo_svc"] = 0.2

    # --- Check 15: SConstruct uses library object reference (not string) ---
    # The SConstruct uses library objects returned from SConscript, not string
    # names. Proper fix uses core_libs['efs'], not string 'efs' in LIBS.
    # This tests understanding of SCons Library node objects vs string names.
    components["sconstruct_uses_library_object"] = 0.0

    if sconstruct.exists():
        content = _read(sconstruct)
        # Best: uses core_libs['efs'] or core_libs.get('efs', ...)
        if re.search(r"core_libs\[.efs.\]|core_libs\.get\(.efs.", content):
            components["sconstruct_uses_library_object"] = 1.0
        # Acceptable: uses efs_lib variable if extracted separately
        elif re.search(r"efs_lib\b", content) and re.search(r"LIBS.*efs_lib|efs_lib.*LIBS", content, re.DOTALL):
            components["sconstruct_uses_library_object"] = 0.7
        # Weak: uses string name 'efs' — works with LIBPATH but not idiomatic
        elif re.search(r"LIBS.*['\"]efs['\"]", content):
            components["sconstruct_uses_library_object"] = 0.3
        # Very weak: just mentions efs somewhere near LIBS
        elif re.search(r"LIBS.*efs", content, re.DOTALL):
            components["sconstruct_uses_library_object"] = 0.15

    # --- Check 16: Makefile fs_rmts_pm compile rule has correct include flags ---
    # The compilation rule for fs_rmts_pm.c must use -Icore/storage/efs/inc
    # (or EFS_INC variable). This is separate from the OEM include check —
    # it verifies the agent understands that fs_rmts_pm.c itself needs its
    # own module's headers to compile.
    components["makefile_efs_inc_in_rmts_rule"] = 0.0

    if makefile.exists():
        mf_content = _read(makefile)
        rmts_rule = re.search(
            r'fs_rmts_pm\.o.*\n\s*\$\(CC\)(.+)', mf_content)
        if rmts_rule:
            rule_flags = rmts_rule.group(1)
            if "EFS_INC" in rule_flags or "core/storage/efs/inc" in rule_flags:
                components["makefile_efs_inc_in_rmts_rule"] = 1.0
            elif "efs" in rule_flags.lower():
                components["makefile_efs_inc_in_rmts_rule"] = 0.4
        elif re.search(r'fs_rmts_pm.*EFS_INC|fs_rmts_pm.*core/storage/efs/inc', mf_content):
            components["makefile_efs_inc_in_rmts_rule"] = 0.7

    # ===================================================================
    # SCORING WITH TIERED WEIGHTS
    # ===================================================================
    # Visible (25%) — basic correctness, all agents pass
    # Hidden-easy (35%) — structural correctness, good agents pass
    # Hidden-hard (40%) — deep expertise, only strong agents pass
    #
    # Hidden total = 35% + 40% = 75% (satisfies >= 30% requirement)
    weights = {
        # Visible (25%)
        "efs_scons_includes_rmts_pm": 0.07,
        "oem_scons_has_efs_inc_path": 0.06,
        "oem_source_includes_header": 0.05,
        "linker_has_efs_dependency": 0.04,
        "build_succeeds": 0.03,
        # Hidden-easy (35%)
        "module_boundary_clean": 0.09,
        "makefile_has_rmts_compile_rule": 0.08,
        "makefile_oem_has_efs_include": 0.07,
        "no_workaround_hacks": 0.06,
        "include_in_header_section": 0.05,
        # Hidden-hard (40%)
        "restricted_api_pattern_used": 0.08,
        "linker_order_correct": 0.08,
        "makefile_archive_membership": 0.07,
        "include_ordering_after_fibo_svc": 0.07,
        "sconstruct_uses_library_object": 0.06,
        "makefile_efs_inc_in_rmts_rule": 0.04,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "tiers": {
            "visible": round(sum(
                weights[k] * components[k] for k in [
                    "efs_scons_includes_rmts_pm", "oem_scons_has_efs_inc_path",
                    "oem_source_includes_header", "linker_has_efs_dependency",
                    "build_succeeds",
                ]
            ), 4),
            "hidden_easy": round(sum(
                weights[k] * components[k] for k in [
                    "module_boundary_clean", "makefile_has_rmts_compile_rule",
                    "makefile_oem_has_efs_include", "no_workaround_hacks",
                    "include_in_header_section",
                ]
            ), 4),
            "hidden_hard": round(sum(
                weights[k] * components[k] for k in [
                    "restricted_api_pattern_used", "linker_order_correct",
                    "makefile_archive_membership", "include_ordering_after_fibo_svc",
                    "sconstruct_uses_library_object", "makefile_efs_inc_in_rmts_rule",
                ]
            ), 4),
        },
    }


def main():
    # Try multiple locations
    ws = Path("/workspace/fixtures/modem_project")
    if not ws.exists():
        ws = Path("/workspace/modem_project")
    if not ws.exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
