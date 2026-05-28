"""Hidden verifier for CP100 — Docker Compose multi-service deployment debug."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    base = ws / "deer-flow"
    nginx_file = base / "nginx.conf"
    compose_file = base / "docker-compose.yml"
    env_file = base / ".env.example"

    components = {k: 0.0 for k in [
        "nginx_uses_service_names", "kubeconfig_fixed",
        "deer_flow_root_set", "api_urls_fixed", "no_hardcoded_ips",
    ]}

    nginx_c = _read(nginx_file)
    if nginx_c:
        has_hardcoded = bool(re.search(r"proxy_pass\s+http://192\.168", nginx_c))
        uses_svc = bool(re.search(r"proxy_pass\s+http://deer-flow-api", nginx_c))
        if uses_svc and not has_hardcoded:
            components["nginx_uses_service_names"] = 1.0
        elif uses_svc:
            components["nginx_uses_service_names"] = 0.5
        elif not has_hardcoded:
            components["nginx_uses_service_names"] = 0.25

    compose_c = _read(compose_file)
    if compose_c:
        has_dir_mount = bool(re.search(r"kubeconfig:/root/\.kube/config", compose_c))
        has_file_mount = bool(re.search(
            r"\./.*kubeconfig.*:/root/\.kube/config|/.*\.kube/config:/root/\.kube/config",
            compose_c))
        kubeconfig_removed = "kubeconfig" not in compose_c.lower() or not has_dir_mount
        if has_file_mount:
            components["kubeconfig_fixed"] = 1.0
        elif kubeconfig_removed:
            components["kubeconfig_fixed"] = 0.75

    deer_root = False
    for f in [compose_file, base / "Dockerfile.provisioner", base / "Dockerfile.api", env_file]:
        if f.exists():
            c = _read(f)
            for line in c.split("\n"):
                s = line.strip()
                if "DEER_FLOW_ROOT" in s and not s.startswith("#"):
                    deer_root = True
                    break
            if deer_root:
                break
    components["deer_flow_root_set"] = 1.0 if deer_root else 0.0

    fixed = total = 0
    if compose_c and "NEXT_PUBLIC_API_URL" in compose_c:
        total += 1
        if re.search(r"NEXT_PUBLIC_API_URL.*http://deer-flow-api", compose_c):
            fixed += 1
    env_c = _read(env_file)
    if env_c and "LANGGRAPH_API_URL" in env_c:
        total += 1
        for line in env_c.split("\n"):
            if "LANGGRAPH_API_URL" in line and not line.strip().startswith("#"):
                if re.search(r"deer-flow-api|http://api", line):
                    fixed += 1
                    break
    components["api_urls_fixed"] = (fixed / total) if total else 0.0

    # No hardcoded 192.168 IPs anywhere
    ip_count = 0
    for f in [nginx_file, compose_file, env_file]:
        if f.exists():
            ip_count += len(re.findall(r"192\.168\.\d+\.\d+", _read(f)))
    components["no_hardcoded_ips"] = 1.0 if ip_count == 0 else (0.5 if ip_count <= 2 else 0.0)

    weights = {
        "nginx_uses_service_names": 0.25,
        "kubeconfig_fixed": 0.20,
        "deer_flow_root_set": 0.15,
        "api_urls_fixed": 0.25,
        "no_hardcoded_ips": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
