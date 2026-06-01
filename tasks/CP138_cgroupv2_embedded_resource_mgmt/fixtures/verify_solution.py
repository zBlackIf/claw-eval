"""Hidden verifier for CP138 - cgroup v2 embedded resource management."""
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


def _find_file(base: Path, name: str) -> Path | None:
    """Find a file by name recursively."""
    for p in base.rglob(name):
        return p
    return None


def _find_file_containing(base: Path, pattern: str, suffix: str = ".sh") -> Path | None:
    """Find a file containing a pattern."""
    for p in base.rglob(f"*{suffix}"):
        if pattern in _read(p):
            return p
    # Also check files without extension (init scripts)
    for p in base.rglob("S*"):
        if p.is_file() and pattern in _read(p):
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the cgroup v2 resource management implementation."""
    # Try multiple possible locations for the project
    project = ws / "fixtures" / "buildroot-project"
    if not project.exists():
        project = ws / "buildroot-project"
    if not project.exists():
        # Try current directory
        project = ws

    components = {k: 0.0 for k in [
        "cgroup_setup_script",
        "cgroup_helper_library",
        "business_cgroup_config",
        "irq_affinity_config",
        "service_script_integration",
        "dhd_dpc_handling",
    ]}

    # 1. Check for cgroup setup init script (S0x priority, runs early)
    setup_script = None
    for p in project.rglob("S*cgroup*"):
        if p.is_file():
            setup_script = p
            break
    if not setup_script:
        for p in project.rglob("*cgroup*setup*"):
            if p.is_file() and not p.name.endswith(".py"):
                setup_script = p
                break
    if not setup_script:
        for p in project.rglob("*cgroup*"):
            if p.is_file() and p.suffix in ("", ".sh") and not p.name.endswith(".py"):
                c = _read(p)
                if "case" in c and "start" in c:
                    setup_script = p
                    break

    if setup_script:
        content = _read(setup_script)
        score = 0.0

        # Must be a proper SysV init script with start/stop/restart
        has_case = "case" in content and "start)" in content
        has_stop = "stop)" in content
        has_shebang = content.strip().startswith("#!/bin/sh") or content.strip().startswith("#!/bin/bash")
        score += 0.2 if (has_case and has_stop and has_shebang) else 0.0

        # Must check/verify cgroup v2 is mounted
        has_cgroup_check = ("cgroup.controllers" in content or "mountpoint" in content or
                           "cgroup2" in content or "/sys/fs/cgroup" in content)
        score += 0.2 if has_cgroup_check else 0.0

        # Must enable controllers (cpuset, cpu, memory) via subtree_control
        has_subtree = "subtree_control" in content
        has_controllers = (("cpuset" in content or "cpu" in content) and "memory" in content)
        score += 0.3 if (has_subtree and has_controllers) else (0.15 if has_subtree else 0.0)

        # Must create business/app group directory
        has_mkdir = "mkdir" in content
        has_business = ("business" in content or "app" in content or "services" in content)
        score += 0.15 if (has_mkdir and has_business) else 0.0

        # Early boot priority (S0x number <= S10)
        name = setup_script.name
        match = re.match(r"S(\d+)", name)
        if match:
            priority = int(match.group(1))
            score += 0.15 if priority <= 10 else 0.05
        else:
            score += 0.05

        components["cgroup_setup_script"] = min(score, 1.0)

    # 2. Check for helper library (sourced by other scripts)
    helper = None
    for p in project.rglob("*cgroup*helper*"):
        if p.is_file():
            helper = p
            break
    if not helper:
        for p in project.rglob("*cgroup*.sh"):
            if p.is_file() and "helper" in _read(p).lower():
                helper = p
                break
    # Also accept inline integration without a separate helper
    if not helper:
        # Check if service scripts themselves handle cgroup placement
        modified_scripts = 0
        for script_name in ["S61moonraker", "S99screen", "S50nginx", "S91unisrv"]:
            found = _find_file(project, script_name)
            if found:
                c = _read(found)
                if "cgroup" in c.lower():
                    modified_scripts += 1
        if modified_scripts >= 2:
            components["cgroup_helper_library"] = 0.7  # Acceptable but not ideal
            helper = True  # Flag that we found integration

    if helper and helper is not True:
        content = _read(helper)
        score = 0.0

        # Should have functions for moving processes to cgroups
        has_func = re.search(r"(cgroup_add|move_to_cgroup|add_proc|cgroup_move)", content)
        score += 0.3 if has_func else 0.0

        # Should support PID-based and/or name-based process lookup
        has_pid = ("pid" in content.lower() or "PID" in content or "$!" in content or
                   "pidof" in content or "pgrep" in content)
        score += 0.2 if has_pid else 0.0

        # Should handle cgroup.procs write
        has_procs = "cgroup.procs" in content
        score += 0.3 if has_procs else 0.0

        # Should be sourceable (no standalone execution logic, or has functions)
        has_source_pattern = ("()" in content or "function " in content)
        score += 0.2 if has_source_pattern else 0.0

        components["cgroup_helper_library"] = min(score, 1.0)

    # 3. Check business cgroup configuration (cpuset + memory limits)
    all_scripts = ""
    for p in project.rglob("*"):
        if p.is_file() and p.suffix in ("", ".sh") and not p.name.endswith(".py"):
            all_scripts += _read(p) + "\n"

    score = 0.0
    # cpuset.cpus restriction to subset of CPUs (e.g., 0-1)
    has_cpuset_cpus = "cpuset.cpus" in all_scripts
    score += 0.25 if has_cpuset_cpus else 0.0

    # cpuset.mems configuration
    has_cpuset_mems = "cpuset.mems" in all_scripts
    score += 0.1 if has_cpuset_mems else 0.0

    # memory.max hard limit (around 300MB = 314572800)
    has_memory_max = "memory.max" in all_scripts
    score += 0.25 if has_memory_max else 0.0

    # memory.high soft limit (bonus for best practice)
    has_memory_high = "memory.high" in all_scripts
    score += 0.2 if has_memory_high else 0.0

    # memory.swap.max = 0 (prevent swap usage)
    has_swap_limit = "memory.swap" in all_scripts or "swap.max" in all_scripts
    score += 0.2 if has_swap_limit else 0.0

    components["business_cgroup_config"] = min(score, 1.0)

    # 4. IRQ affinity configuration for UART/USB
    score = 0.0
    has_smp_affinity = "smp_affinity" in all_scripts
    score += 0.4 if has_smp_affinity else 0.0

    # Should identify UART/USB IRQs dynamically (from /proc/interrupts)
    has_proc_interrupts = "/proc/interrupts" in all_scripts or "proc/irq" in all_scripts
    score += 0.3 if has_proc_interrupts else 0.0

    # Should reference UART or USB patterns
    has_uart_usb = (("uart" in all_scripts.lower() or "serial" in all_scripts.lower()) and
                    "usb" in all_scripts.lower())
    score += 0.3 if has_uart_usb else 0.0

    components["irq_affinity_config"] = min(score, 1.0)

    # 5. Service script integration (scripts move processes to cgroup on start/restart)
    score = 0.0
    target_scripts = {
        "S61moonraker": False,
        "S99screen": False,
        "S50nginx": False,
        "S91unisrv": False,
    }
    for script_name in target_scripts:
        found = _find_file(project, script_name)
        if found:
            c = _read(found)
            # Check if script integrates cgroup placement
            has_cgroup_ref = ("cgroup" in c.lower() or "cgroup_helper" in c or
                             "cgroup_add" in c or "business" in c)
            if has_cgroup_ref:
                target_scripts[script_name] = True

    integrated = sum(1 for v in target_scripts.values() if v)
    # At least 3 of 4 scripts should be modified
    if integrated >= 4:
        score = 1.0
    elif integrated >= 3:
        score = 0.8
    elif integrated >= 2:
        score = 0.5
    elif integrated >= 1:
        score = 0.3

    components["service_script_integration"] = score

    # 6. dhd_dpc kernel thread handling (WiFi driver thread, appears late)
    score = 0.0
    has_dhd_dpc = "dhd_dpc" in all_scripts
    score += 0.4 if has_dhd_dpc else 0.0

    # Should handle async appearance (polling/watching/udev/hook)
    has_async = any(k in all_scripts for k in [
        "sleep", "pgrep", "while", "watcher", "poll", "inotify", "udev"
    ])
    if has_dhd_dpc and has_async:
        score += 0.3

    # Should move it to business cgroup
    if has_dhd_dpc and "cgroup.procs" in all_scripts:
        score += 0.3

    components["dhd_dpc_handling"] = min(score, 1.0)

    # Compute overall score with weights
    weights = {
        "cgroup_setup_script": 0.25,
        "cgroup_helper_library": 0.15,
        "business_cgroup_config": 0.20,
        "irq_affinity_config": 0.15,
        "service_script_integration": 0.15,
        "dhd_dpc_handling": 0.10,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try workspace paths
    ws = Path("/workspace")
    if not ws.exists():
        ws = Path(".")

    # Check both possible locations
    if (ws / "fixtures" / "buildroot-project").exists():
        result = grade_workspace(ws / "fixtures")
    elif (ws / "buildroot-project").exists():
        result = grade_workspace(ws)
    else:
        result = grade_workspace(ws)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
