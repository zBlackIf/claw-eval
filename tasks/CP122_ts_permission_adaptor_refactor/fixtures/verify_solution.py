"""Hidden verifier for CP122 — TypeScript Permission Adaptor Refactor."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(base: Path, name: str) -> Path | None:
    """Find a file by name anywhere under base."""
    for p in base.rglob(name):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for the permission adaptor refactor task."""
    # Look in multiple possible locations
    base = ws / "fixtures" / "merch-portal"
    if not base.exists():
        base = ws / "merch-portal"
    if not base.exists():
        # Try finding it anywhere
        for p in ws.rglob("viewImagesDialog.ts"):
            base = p.parent.parent.parent.parent.parent
            break

    components = {k: 0.0 for k in [
        "adaptor_has_permission_param",
        "adaptor_filters_by_permission",
        "adaptor_imports_btn_permission",
        "protocol_handlers_extracted",
        "extracted_fn_accepts_agreement_type",
    ]}

    # --- Check 1: imagesQueryAdaptor has permissFeild/permission parameter ---
    dialog_file = _find_file(base, "viewImagesDialog.ts") if base.exists() else None
    dialog_content = _read(dialog_file) if dialog_file else ""

    if dialog_content:
        # Check if the adaptor function now accepts a permission parameter
        # Pattern: function signature includes permiss/permission parameter
        has_perm_param = bool(re.search(
            r'imagesQueryAdaptor\s*[=(]\s*[^)]*\b(permiss\w*|permission\w*)',
            dialog_content, re.IGNORECASE
        ))
        # Also check for arrow function or wrapper pattern
        if not has_perm_param:
            has_perm_param = bool(re.search(
                r'(permiss\w*|permission\w*)\s*[?:]\s*string',
                dialog_content, re.IGNORECASE
            ))
        components["adaptor_has_permission_param"] = 1.0 if has_perm_param else 0.0

        # Check 2: The adaptor filters based on permission check
        has_filter = bool(re.search(
            r'btnPermission\s*\(.*permiss', dialog_content, re.IGNORECASE
        )) or bool(re.search(
            r'filter\s*\(.*pic_type', dialog_content, re.IGNORECASE
        ))
        # Alternative: check for conditional filtering pattern
        if not has_filter:
            has_filter = bool(re.search(
                r'if\s*\(\s*!?\s*btnPermission', dialog_content
            )) or bool(re.search(
                r'if\s*\(\s*permiss\w*\s*&&', dialog_content, re.IGNORECASE
            ))
        components["adaptor_filters_by_permission"] = 1.0 if has_filter else 0.0

        # Check 3: btnPermission is imported in viewImagesDialog.ts
        has_import = bool(re.search(
            r'import\s*\{[^}]*btnPermission[^}]*\}\s*from',
            dialog_content
        ))
        # Or it's passed as a parameter (also valid)
        if not has_import:
            has_import = bool(re.search(
                r'(permiss\w*|permission\w*)\s*[?:&|]', dialog_content, re.IGNORECASE
            )) and components["adaptor_has_permission_param"] > 0
        components["adaptor_imports_btn_permission"] = 1.0 if has_import else 0.0

    # --- Check 4: Protocol onClick handlers extracted into reusable functions ---
    protocol_file = _find_file(base, "protocolSection.ts") if base.exists() else None
    protocol_content = _read(protocol_file) if protocol_file else ""

    if protocol_content:
        # Count onClick inline async handlers - should be reduced from 4 to fewer
        inline_handlers = len(re.findall(
            r'onClick\s*:\s*async\s*\(', protocol_content
        ))
        # Check for extracted helper functions (named functions that handle the click logic)
        extracted_fns = re.findall(
            r'(?:const|function)\s+\w*(handle|view|download|query)\w*(Contract|Protocol|Agreement|Click)\w*\s*[=(]',
            protocol_content, re.IGNORECASE
        )
        # Also check if the helpers are defined in a separate file
        helpers_file = None
        for name in ["protocolHelpers.ts", "protocolUtils.ts", "merchProtocol.ts"]:
            helpers_file = _find_file(base, name)
            if helpers_file:
                break
        helpers_content = _read(helpers_file) if helpers_file else ""
        if helpers_content:
            extracted_fns += re.findall(
                r'(?:export\s+)?(?:const|function)\s+\w*(handle|view|download|query)\w*\s*[=(]',
                helpers_content, re.IGNORECASE
            )

        # Score: original had 4 inline handlers; extracting them means fewer inline + named fns exist
        if len(extracted_fns) >= 2 and inline_handlers <= 2:
            components["protocol_handlers_extracted"] = 1.0
        elif len(extracted_fns) >= 1 or inline_handlers <= 2:
            components["protocol_handlers_extracted"] = 0.5
        else:
            components["protocol_handlers_extracted"] = 0.0

        # Check 5: Extracted function accepts agreement_type as parameter
        # Must be in a function DEFINITION (const/function), not just inline usage
        all_fn_content = protocol_content + helpers_content
        # Match: const handleXxx = (... agreementType: string ...) or function xxx(agreementType...)
        has_agreement_type_param = bool(re.search(
            r'(?:const|function)\s+\w+\s*[=(]\s*[^{]*\b(agreementType|agreement_type)\b[^{]*[)=]',
            all_fn_content
        ))
        # Also match arrow function with typed param: (agreementType: string) =>
        if not has_agreement_type_param:
            has_agreement_type_param = bool(re.search(
                r'\(\s*(?:\w+\s*[:,]\s*\w+\s*,\s*)*(agreementType|agreement_type)\s*[?:]\s*string',
                all_fn_content
            ))
        # Only count if we also found extracted functions (dependency on check 4)
        if not extracted_fns:
            has_agreement_type_param = False
        components["extracted_fn_accepts_agreement_type"] = 1.0 if has_agreement_type_param else 0.0

    weights = {
        "adaptor_has_permission_param": 0.25,
        "adaptor_filters_by_permission": 0.25,
        "adaptor_imports_btn_permission": 0.15,
        "protocol_handlers_extracted": 0.20,
        "extracted_fn_accepts_agreement_type": 0.15,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try /workspace/fixtures first, then /workspace
    ws = Path("/workspace/fixtures")
    if not ws.exists():
        ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
