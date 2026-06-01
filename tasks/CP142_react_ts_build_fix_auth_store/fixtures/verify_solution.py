"""Hidden verifier for CP142 — React TypeScript Build Fix (Auth Store).

Checks:
1. authStore file extension is .tsx (JSX requires .tsx in strict TS)
2. authStore contains valid AuthProvider with JSX (Context.Provider)
3. services/auth.ts exports getCurrentUser and loginApi functions
4. TypeScript would not error on the auth store (no JSX in .ts)
5. Login.tsx imports resolve correctly
"""
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


def _find_file(base: Path, name_pattern: str) -> Path | None:
    """Find a file matching pattern recursively."""
    for p in base.rglob(name_pattern):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    # Try both possible locations
    project_dir = ws / "fixtures" / "sanitary-leads-frontend"
    if not project_dir.exists():
        project_dir = ws / "sanitary-leads-frontend"
    if not project_dir.exists():
        # Try to find it anywhere
        for candidate in ws.rglob("package.json"):
            content = _read(candidate)
            if "sanitary-leads-frontend" in content:
                project_dir = candidate.parent
                break

    src_dir = project_dir / "src" if project_dir.exists() else ws / "src"

    components = {k: 0.0 for k in [
        "auth_store_tsx_extension",
        "auth_store_has_provider_jsx",
        "auth_store_exports_hook",
        "services_auth_exports_login",
        "services_auth_exports_get_user",
        "no_ts_jsx_conflict",
        "login_page_compiles",
    ]}

    # 1. Check if authStore has been renamed to .tsx
    auth_store_tsx = None
    auth_store_ts = None

    # Search for the auth store file
    if src_dir.exists():
        for p in src_dir.rglob("authStore.tsx"):
            auth_store_tsx = p
            break
        for p in src_dir.rglob("authStore.ts"):
            if not str(p).endswith(".tsx"):
                auth_store_ts = p
                break

    # Also check if they created a new file with different name
    if not auth_store_tsx and src_dir.exists():
        for p in src_dir.rglob("*auth*Store*.tsx"):
            auth_store_tsx = p
            break
        for p in src_dir.rglob("*Auth*Provider*.tsx"):
            auth_store_tsx = p
            break

    if auth_store_tsx:
        components["auth_store_tsx_extension"] = 1.0
    elif auth_store_ts:
        # Check if they removed JSX from the .ts file (alternative valid fix)
        content = _read(auth_store_ts)
        if "<" not in content or "Provider" not in content:
            # They removed JSX - check if there's a separate .tsx file for the provider
            for p in src_dir.rglob("*.tsx"):
                c = _read(p)
                if "AuthProvider" in c and "AuthContext.Provider" in c:
                    components["auth_store_tsx_extension"] = 0.8
                    auth_store_tsx = p
                    break
            if not auth_store_tsx:
                components["auth_store_tsx_extension"] = 0.5
        else:
            components["auth_store_tsx_extension"] = 0.0

    # 2. Check AuthProvider with JSX
    auth_file = auth_store_tsx or auth_store_ts
    if auth_file:
        content = _read(auth_file)
        has_provider = "AuthProvider" in content
        has_context_provider = "Context.Provider" in content or "Provider" in content
        has_jsx_return = ("<" in content and ">" in content and "return" in content)
        has_children = "children" in content

        score = 0.0
        if has_provider:
            score += 0.3
        if has_context_provider:
            score += 0.3
        if has_jsx_return:
            score += 0.2
        if has_children:
            score += 0.2
        components["auth_store_has_provider_jsx"] = min(score, 1.0)

    # 3. Check useAuth hook export
    if auth_file:
        content = _read(auth_file)
        has_use_auth = "useAuth" in content
        has_export = "export" in content and "useAuth" in content
        components["auth_store_exports_hook"] = 1.0 if (has_use_auth and has_export) else (0.5 if has_use_auth else 0.0)
    else:
        # Maybe they split into separate files
        if src_dir.exists():
            for p in src_dir.rglob("*.ts*"):
                c = _read(p)
                if "export" in c and "useAuth" in c:
                    components["auth_store_exports_hook"] = 1.0
                    break

    # 4. Check services/auth exports loginApi
    services_auth = None
    if src_dir.exists():
        for p in src_dir.rglob("auth.ts"):
            if "services" in str(p) or "service" in str(p):
                services_auth = p
                break
        if not services_auth:
            for p in src_dir.rglob("auth.tsx"):
                if "services" in str(p) or "service" in str(p):
                    services_auth = p
                    break

    if services_auth:
        content = _read(services_auth)
        # Check for loginApi export (function or const)
        has_login_export = bool(
            re.search(r'export\s+(async\s+)?function\s+loginApi', content) or
            re.search(r'export\s+const\s+loginApi', content) or
            re.search(r'export\s*\{[^}]*loginApi[^}]*\}', content) or
            ("loginApi" in content and "export" in content)
        )
        components["services_auth_exports_login"] = 1.0 if has_login_export else 0.0

    # 5. Check services/auth exports getCurrentUser
    if services_auth:
        content = _read(services_auth)
        has_get_user_export = bool(
            re.search(r'export\s+(async\s+)?function\s+getCurrentUser', content) or
            re.search(r'export\s+const\s+getCurrentUser', content) or
            re.search(r'export\s*\{[^}]*getCurrentUser[^}]*\}', content) or
            ("getCurrentUser" in content and "export" in content)
        )
        components["services_auth_exports_get_user"] = 1.0 if has_get_user_export else 0.0

    # 6. No .ts file with JSX conflict
    has_conflict = False
    if src_dir.exists():
        for p in src_dir.rglob("*.ts"):
            if str(p).endswith(".tsx"):
                continue
            c = _read(p)
            # Check if this .ts file has JSX-like patterns (opening tags after return)
            if re.search(r'return\s*\(\s*<[A-Z]', c) or re.search(r'return\s+<[A-Z]', c):
                has_conflict = True
                break
    components["no_ts_jsx_conflict"] = 0.0 if has_conflict else 1.0

    # 7. Login.tsx imports should resolve (loginApi from services/auth)
    login_page = None
    if src_dir.exists():
        for p in src_dir.rglob("Login.tsx"):
            login_page = p
            break
    if login_page:
        content = _read(login_page)
        imports_login_api = "loginApi" in content
        imports_auth_store = "useAuth" in content or "authStore" in content
        # Check that what it imports actually exists
        if imports_login_api and services_auth:
            svc_content = _read(services_auth)
            login_resolves = "loginApi" in svc_content
        else:
            login_resolves = False

        components["login_page_compiles"] = 1.0 if login_resolves else (0.3 if imports_login_api else 0.0)
    else:
        components["login_page_compiles"] = 0.0

    weights = {
        "auth_store_tsx_extension": 0.25,
        "auth_store_has_provider_jsx": 0.15,
        "auth_store_exports_hook": 0.10,
        "services_auth_exports_login": 0.20,
        "services_auth_exports_get_user": 0.15,
        "no_ts_jsx_conflict": 0.10,
        "login_page_compiles": 0.05,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Check /workspace/fixtures first, then /workspace
    ws = Path("/workspace/fixtures")
    if not (ws / "sanitary-leads-frontend").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
