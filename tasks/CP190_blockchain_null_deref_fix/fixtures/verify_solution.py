"""Hidden verifier for CP190 — Blockchain Null Deref Fix.

Tiered scoring:
  - EASY tier (visible-like, weight 0.30): null check added, no null propagation,
    basic test exists, code style preserved. All reasonable agents pass these.
  - HARD tier (hidden, weight 0.35): route_info also guarded, caller abort on
    invalid chain, contextual error info. Only strong agents pass these.
  - EXPERT tier (hidden, weight 0.35): test covers path composition invariant,
    test verifies both failure paths, exception message quality. Only the best pass.

Hidden checks (HARD + EXPERT) total weight = 0.70 (>= 30% requirement).
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


def grade_workspace(ws: Path) -> dict:
    """Grade the null-pointer fix in BlockSyncFileQueryProcessor.getChainType()."""

    # Find the main source file
    processor_file = None
    for candidate in [
        ws / "fixtures" / "chain-sync-service" / "src" / "main" / "java" / "com" / "web3" / "chainsync" / "service" / "BlockSyncFileQueryProcessor.java",
        ws / "chain-sync-service" / "src" / "main" / "java" / "com" / "web3" / "chainsync" / "service" / "BlockSyncFileQueryProcessor.java",
    ]:
        if candidate.exists():
            processor_file = candidate
            break

    if not processor_file:
        for p in ws.rglob("BlockSyncFileQueryProcessor.java"):
            if "src/main" in str(p):
                processor_file = p
                break

    components = {k: 0.0 for k in [
        # EASY tier
        "null_check_added",
        "no_null_propagation",
        "basic_test_exists",
        "code_style_preserved",
        # HARD tier (hidden)
        "route_info_chaintype_guarded",
        "caller_abort_on_invalid_chain",
        "contextual_error_info",
        # EXPERT tier (hidden)
        "test_path_composition_invariant",
        "test_both_failure_paths",
        "exception_message_quality",
    ]}

    if not processor_file:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "BlockSyncFileQueryProcessor.java not found",
        }

    content = _read(processor_file)

    # =====================================================================
    # EASY TIER (total weight: 0.30) — all reasonable agents pass these
    # =====================================================================

    # --- E1: Null check added (0.10) ---
    has_null_check = False
    null_check_patterns = [
        r'nodeEntity\s*!=\s*null',
        r'null\s*!=\s*nodeEntity',
        r'Objects\.nonNull\s*\(\s*nodeEntity\s*\)',
        r'Optional\.ofNullable\s*\(\s*nodeEntity\s*\)',
    ]
    for pat in null_check_patterns:
        if re.search(pat, content):
            has_null_check = True
            break

    original_bug_pattern = re.search(
        r'chainType\s*=\s*nodeEntity\.getChainType\(\)\s*;',
        content
    )
    if original_bug_pattern and has_null_check:
        null_pos = -1
        for pat in null_check_patterns:
            m = re.search(pat, content)
            if m:
                null_pos = m.start()
                break
        call_pos = original_bug_pattern.start()
        if null_pos >= 0 and null_pos < call_pos:
            components["null_check_added"] = 1.0
        else:
            components["null_check_added"] = 0.3
    elif has_null_check and not original_bug_pattern:
        # Likely restructured the code — that's fine
        components["null_check_added"] = 1.0
    elif has_null_check:
        components["null_check_added"] = 0.8
    else:
        components["null_check_added"] = 0.0

    # --- E2: No null propagation (0.08) ---
    assigns_null = re.search(r'chainType\s*=\s*null\s*;', content)
    ternary_null = re.search(
        r'nodeEntity\s*!=\s*null\s*\?\s*nodeEntity\.getChainType\(\)\s*:\s*null',
        content
    )
    if assigns_null or ternary_null:
        components["no_null_propagation"] = 0.0
    elif has_null_check:
        has_default = bool(re.search(
            r'(chainType\s*=\s*"[^"]+"|throw\s+new\s+\w+Exception)',
            content
        ))
        components["no_null_propagation"] = 1.0 if has_default else 0.4
    else:
        components["no_null_propagation"] = 0.0

    # --- E3: Basic test exists (0.07) ---
    all_test_content = ""
    for test_file in ws.rglob("*Test*.java"):
        tc = _read(test_file)
        if "BlockSyncFileQueryProcessor" in tc or "getChainType" in tc or "nodeEntity" in tc:
            all_test_content = tc
            break

    test_basic_score = 0.0
    if all_test_content:
        has_null_test = bool(re.search(
            r'(null|getNodeByIdentifier|getChainType.*null|nodeEntity.*null)',
            all_test_content, re.IGNORECASE
        ))
        has_mock = bool(re.search(r'(mock|Mock|when|verify|Mockito|spy|stub)', all_test_content))
        has_assertion = bool(re.search(r'(assert|Assert|assertEquals|assertNotNull|assertThrows)', all_test_content))
        if has_null_test and has_assertion and has_mock:
            test_basic_score = 1.0
        elif has_null_test and has_assertion:
            test_basic_score = 0.6
        elif has_null_test:
            test_basic_score = 0.3
    components["basic_test_exists"] = test_basic_score

    # --- E4: Code style preserved (0.05) ---
    has_class_decl = "class BlockSyncFileQueryProcessor" in content
    has_method = "String getChainType" in content
    has_balanced_braces = content.count('{') == content.count('}')
    style_score = sum([has_class_decl, has_method, has_balanced_braces]) / 3.0
    components["code_style_preserved"] = round(style_score, 4)

    # =====================================================================
    # HARD TIER — HIDDEN (total weight: 0.35)
    # Requires understanding the full data flow beyond the explicit prompt.
    # =====================================================================

    # Extract method body for reuse
    method_match = re.search(
        r'(private\s+)?String\s+getChainType\s*\([^)]*\)\s*\{(.*?)\n\s{4}\}',
        content, re.DOTALL
    )
    method_body = method_match.group(2) if method_match else ""
    has_log = bool(re.search(r'log\.(error|warn)\s*\(', method_body))
    has_throw = bool(re.search(r'throw\s+new\s+\w+', method_body))

    # --- H1: Route info chainType also guarded (0.12) ---
    # SUBTLE BUG: Even when routeInfo != null && routeInfo.getResult() == 1,
    # routeInfo.getChainType() can STILL return null (e.g., data corruption,
    # partial cache entry). The original code on line 72 just does:
    #   chainType = routeInfo.getChainType();
    # without any validation. A truly thorough fix guards BOTH paths.
    #
    # Most models only fix the nodeEntity null case because the prompt
    # mentions it explicitly. Only strong models notice the routeInfo path
    # has the same latent issue.
    route_guard_score = 0.0

    route_chaintype_patterns = [
        r'routeInfo\.getChainType\(\).*\n.*(?:chainType\s*(?:!=\s*null|==\s*null)|StringUtils)',
        r'chainType\s*=\s*routeInfo\.getChainType\(\)\s*;.*\n\s*if\s*\(\s*chainType\s*(?:==\s*null|!=\s*null)',
        r'routeInfo\.getChainType\(\)\s*!=\s*null',
        r'StringUtils\s*\.\s*(?:isNotBlank|isNotEmpty)\s*\(\s*routeInfo\.getChainType',
        r'routeInfo\.getChainType\(\)\s*!=\s*null\s*\?\s*routeInfo\.getChainType',
        r'routeInfo\s*!=\s*null\s*&&\s*routeInfo\.getResult\(\)\s*==\s*1\s*&&\s*(?:routeInfo\.getChainType|StringUtils)',
    ]
    for pat in route_chaintype_patterns:
        if re.search(pat, content, re.DOTALL):
            route_guard_score = 1.0
            break

    if route_guard_score == 0.0:
        blanket_patterns = [
            r'}\s*\n\s*if\s*\(\s*chainType\s*==\s*null\s*(?:\|\|\s*chainType\s*\.(?:isEmpty|isBlank|trim))?',
            r'StringUtils\s*\.\s*(?:isBlank|isEmpty)\s*\(\s*chainType\s*\)',
            r'chainType\s*==\s*null[^}]*(?:throw|log\.(?:error|warn))[^}]*\n\s*(?:}|\s*return)',
        ]
        for pat in blanket_patterns:
            if re.search(pat, content, re.DOTALL):
                route_guard_score = 0.8
                break

    if route_guard_score == 0.0:
        if re.search(r'if\s*\(\s*chainType\s*==\s*null', content):
            route_guard_score = 0.4
        elif re.search(r'chainType\s*==\s*null', content):
            route_guard_score = 0.2

    components["route_info_chaintype_guarded"] = route_guard_score

    # --- H2: Caller abort on invalid chain type (0.13) ---
    # The REAL bug impact: if getChainType returns a bad value (null, empty,
    # "UNKNOWN"), processBlockSyncQuery continues and:
    #   1. Creates path "/data/blocks/UNKNOWN/sync" (data written to wrong location)
    #   2. Downloads blocks for a chain type that might not exist
    #   3. Uploads files to an invalid storage path
    #
    # The BEST fix either:
    #   (a) Throws from getChainType so processBlockSyncQuery stops via exception
    #   (b) In processBlockSyncQuery, checks chainType validity before proceeding
    #   (c) Uses a checked exception pattern that forces the caller to handle
    caller_abort_score = 0.0

    has_illegal_state = bool(re.search(
        r'throw\s+new\s+IllegalStateException', method_body
    ))
    has_illegal_arg = bool(re.search(
        r'throw\s+new\s+IllegalArgumentException', method_body
    ))
    has_custom_exception = bool(re.search(
        r'throw\s+new\s+\w*(Chain|Node|Registry|Sync)\w*Exception', method_body
    ))

    if has_illegal_state or has_custom_exception:
        caller_abort_score = 1.0
    elif has_illegal_arg:
        caller_abort_score = 0.9
    elif has_throw:
        caller_abort_score = 0.7
    else:
        process_match = re.search(
            r'(public\s+)?void\s+processBlockSyncQuery\s*\([^)]*\)\s*\{(.*?)\n\s{4}\}',
            content, re.DOTALL
        )
        process_body = process_match.group(2) if process_match else ""

        if re.search(r'try\s*\{[^}]*getChainType[^}]*\}\s*catch', process_body, re.DOTALL):
            caller_abort_score = 0.7
        elif re.search(r'chainType\s*==\s*null[^}]*return\s*;', process_body, re.DOTALL):
            caller_abort_score = 0.6
        elif re.search(r'if\s*\([^)]*chainType[^)]*\)\s*\{[^}]*return', process_body, re.DOTALL):
            caller_abort_score = 0.5
        elif re.search(r'chainType\s*=\s*"UNKNOWN"', content):
            caller_abort_score = 0.15
        elif re.search(r'chainType\s*=\s*"[A-Z_]+"', content):
            caller_abort_score = 0.1

    components["caller_abort_on_invalid_chain"] = caller_abort_score

    # --- H3: Contextual error information (0.10) ---
    # When the fix logs an error or throws, does it include the nodeIdentifier
    # so operators can debug which node caused the failure?
    context_score = 0.0

    if method_body:
        if re.search(r'throw\s+new\s+\w+Exception\s*\([^)]*nodeIdentifier', method_body):
            context_score = 1.0
        elif re.search(r'log\.(error|warn)\s*\([^)]*nodeIdentifier', method_body):
            context_score = 0.8
        elif re.search(r'(nodeIdentifier|nodeId|identifier)\s*[,+]', method_body):
            context_score = 0.6
        elif has_log or has_throw:
            context_score = 0.2

    components["contextual_error_info"] = context_score

    # =====================================================================
    # EXPERT TIER — HIDDEN (total weight: 0.35)
    # Tests deep understanding of invariants and thorough testing practice.
    # =====================================================================

    # --- X1: Test covers path composition invariant (0.15) ---
    # The CORE invariant the test should verify:
    # "The system must NEVER create a storage path containing literal 'null' or
    #  'UNKNOWN' as the chain type segment."
    test_invariant_score = 0.0

    if all_test_content:
        invariant_signals = 0

        # Signal 1: Tests that exception is thrown (assertThrows)
        if re.search(r'assertThrows\s*\(\s*\w+Exception\.class', all_test_content):
            invariant_signals += 1.5
        elif re.search(r'assertThrows', all_test_content):
            invariant_signals += 1.0

        # Signal 2: Verifies exception message contains useful context
        if re.search(r'(getMessage|assertThat.*message|contains\s*\(\s*".*(?:node|identifier|registry|not found))', all_test_content, re.IGNORECASE):
            invariant_signals += 1.0

        # Signal 3: Tests path composition (the actual downstream impact)
        if re.search(r'(getRemoteStoragePath|/data/blocks/|assertFalse.*null|assertThat.*not.*contain.*null|"/null/")', all_test_content, re.IGNORECASE):
            invariant_signals += 1.5

        # Signal 4: Multiple test methods specifically for null scenarios
        null_test_methods = len(re.findall(r'@Test\s+\w+\s+\w+(?:Null|null|NPE|Invalid|Missing|NotFound)', all_test_content))
        if null_test_methods == 0:
            test_blocks = re.split(r'@Test', all_test_content)
            null_blocks = sum(1 for b in test_blocks if re.search(r'(null|Null|NPE|exception|Exception)', b))
            null_test_methods = null_blocks

        if null_test_methods >= 3:
            invariant_signals += 1.0
        elif null_test_methods >= 2:
            invariant_signals += 0.5

        test_invariant_score = min(invariant_signals / 5.0, 1.0)

    components["test_path_composition_invariant"] = round(test_invariant_score, 4)

    # --- X2: Test covers BOTH failure paths (0.10) ---
    # nodeEntity null path AND routeInfo chainType null path.
    # Most agents only test the one path mentioned in the prompt.
    both_paths_score = 0.0

    if all_test_content:
        has_route_test = bool(re.search(
            r'(getCachedRouteInfo|routeInfo|getResult.*0|result.*null)',
            all_test_content
        ))
        has_entity_test = bool(re.search(
            r'(getNodeByIdentifier.*null|nodeEntity.*null|ChainRegistryHelper.*null)',
            all_test_content, re.DOTALL
        ))
        # Best: separate test methods for each path
        route_test_method = bool(re.search(
            r'@Test[^@]*(?:routeInfo|route|RouteInfo|CachedRoute)[^@]*(?:null|Null|invalid|Invalid)',
            all_test_content, re.DOTALL
        ))
        entity_test_method = bool(re.search(
            r'@Test[^@]*(?:nodeEntity|node|Node|registry|Registry)[^@]*(?:null|Null|NotFound)',
            all_test_content, re.DOTALL
        ))

        if route_test_method and entity_test_method:
            both_paths_score = 1.0
        elif has_route_test and has_entity_test:
            both_paths_score = 0.7
        elif has_entity_test:
            # Only tested the explicitly mentioned path
            both_paths_score = 0.3
        elif has_route_test:
            both_paths_score = 0.2

    components["test_both_failure_paths"] = both_paths_score

    # --- X3: Exception message quality (0.10) ---
    # Does the exception/log message explain WHY and include actionable context?
    # Great: "Node entity not found in registry for identifier '%s', cannot determine chain type"
    # Weak: "NPE" or "null check failed"
    msg_quality_score = 0.0

    if method_body:
        # Best: message includes BOTH what failed and the identifier
        if re.search(r'(throw|log\.\w+)\s*\([^)]*(?:registry|Registry|not\s*found|lookup\s*failed)[^)]*nodeIdentifier', method_body, re.DOTALL):
            msg_quality_score = 1.0
        elif re.search(r'(throw|log\.\w+)\s*\([^)]*nodeIdentifier[^)]*(?:null|not\s*found|registry|failed)', method_body, re.DOTALL):
            msg_quality_score = 1.0
        # Good: includes identifier with some explanation
        elif re.search(r'(throw|log\.\w+)\s*\(\s*(?:String\.format|"[^"]*%s|"[^"]*"\s*\+)[^)]*nodeIdentifier', method_body, re.DOTALL):
            msg_quality_score = 0.8
        # OK: includes identifier but generic message
        elif re.search(r'(throw|log\.\w+)\s*\([^)]*nodeIdentifier', method_body):
            msg_quality_score = 0.6
        # Weak: has a message but no identifier
        elif re.search(r'(throw\s+new\s+\w+Exception\s*\(\s*"[^"]{10,}"|log\.\w+\s*\(\s*"[^"]{10,}")', method_body):
            msg_quality_score = 0.3
        # Minimal: just throws with short/no message
        elif has_throw or has_log:
            msg_quality_score = 0.1

    components["exception_message_quality"] = msg_quality_score

    # =====================================================================
    # Compute overall with tiered weights
    # EASY: 0.30 | HARD (hidden): 0.35 | EXPERT (hidden): 0.35
    # Hidden total: 0.70 (>= 30% requirement)
    # =====================================================================
    weights = {
        # EASY tier (0.30 total) — all agents should pass
        "null_check_added": 0.10,
        "no_null_propagation": 0.08,
        "basic_test_exists": 0.07,
        "code_style_preserved": 0.05,
        # HARD tier (0.35 total) — hidden, only strong agents pass
        "route_info_chaintype_guarded": 0.12,
        "caller_abort_on_invalid_chain": 0.13,
        "contextual_error_info": 0.10,
        # EXPERT tier (0.35 total) — hidden, only the best pass
        "test_path_composition_invariant": 0.15,
        "test_both_failure_paths": 0.10,
        "exception_message_quality": 0.10,
    }

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "tiers": {
            "easy": {"weight": 0.30, "checks": ["null_check_added", "no_null_propagation", "basic_test_exists", "code_style_preserved"]},
            "hard_hidden": {"weight": 0.35, "checks": ["route_info_chaintype_guarded", "caller_abort_on_invalid_chain", "contextual_error_info"]},
            "expert_hidden": {"weight": 0.35, "checks": ["test_path_composition_invariant", "test_both_failure_paths", "exception_message_quality"]},
        },
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws / "fixtures")
    if result.get("overall_score", 0) == 0 and "not found" in result.get("error", ""):
        result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
