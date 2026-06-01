#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hidden verifier for CP163 — RDC Call Reduction & Domain Fallback.

Checks:
1. Domain fallback: _resolve_domain_from_rdc uses fetch_data when System_AreaPath empty
2. Known type passthrough: _step1_resolve_functions uses known_type to skip redundant API call
3. Aggregated children query: uses batch_get_children_by_type instead of separate calls
4. Overall RDC call reduction: analyze("RAN-1455434") uses <= 10 calls (was 50+)
5. Correctness: analyze("RAN-5620900") still returns correct entities with domain filtering
6. Known type wiring: _analyze_single passes known_type to _step1_resolve_functions
7. Fallback robustness: domain fallback handles missing/malformed fetch_data gracefully
8. Strict call budget: analyze("RAN-5620900") within tight call budget
9. No redundant root type query: root entity also gets known_type in entities loop
10. fetch_data conditional: fetch_data NOT called when System_AreaPath already has value
11. Complete grandchild coverage: all expected grandchild USs present with correct types
"""
from __future__ import annotations

import json
import sys
import os
from pathlib import Path

# Add the project to path
ws = Path("/workspace/fixtures/precision_testing")
if not ws.exists():
    ws = Path("/workspace/precision_testing")
sys.path.insert(0, str(ws))


def check_domain_fallback() -> float:
    """Check that _resolve_domain_from_rdc falls back to fetch_data."""
    try:
        from core.rdc import reset_rdc_call_count
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer

        reset_rdc_call_count()
        analyzer = RequirementImpactAnalyzer()

        # RAN-1455434 has empty System_AreaPath but Area = "07-5G-SPA" in fetch_data
        domain = analyzer._resolve_domain_from_rdc("RAN-1455434")

        if not domain:
            return 0.0
        if domain[0] == "07-5G-SPA":
            return 1.0
        return 0.3  # Got something but wrong value
    except Exception as e:
        return 0.0


def check_known_type_passthrough() -> float:
    """Check that _step1_resolve_functions uses known_type to skip API call."""
    try:
        from core.rdc import reset_rdc_call_count, get_rdc_call_stats
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer

        analyzer = RequirementImpactAnalyzer()

        # Call with known_type="PR" — should NOT call judge_pr_or_mr_or_us
        reset_rdc_call_count()
        result = analyzer._step1_resolve_functions("RAN-5620901", known_type="PR")

        calls = get_rdc_call_stats()
        if calls == 0:
            # Perfect: no RDC call when type is known
            if result.get("type") == "PR":
                return 1.0
            return 0.7  # Skipped call but wrong result
        elif calls == 1:
            # Still calling judge_pr_or_mr_or_us despite known_type
            return 0.0
        return 0.0
    except Exception as e:
        return 0.0


def check_aggregated_children_query() -> float:
    """Check that _analyze_single uses batch_get_children_by_type (1 call)
    instead of separate batch_get_child_prs_from_mr + batch_get_child_uss_from_pr (2+ calls).
    """
    try:
        from core.rdc import reset_rdc_call_count, get_rdc_call_stats
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer
        import core.rdc_handler as handler

        # Track which functions get called
        calls_log = []
        original_batch_children = handler.batch_get_children_by_type
        original_child_prs = handler.batch_get_child_prs_from_mr
        original_child_uss = handler.batch_get_child_uss_from_pr

        def tracked_batch_children(*args, **kwargs):
            calls_log.append("batch_get_children_by_type")
            return original_batch_children(*args, **kwargs)

        def tracked_child_prs(*args, **kwargs):
            calls_log.append("batch_get_child_prs_from_mr")
            return original_child_prs(*args, **kwargs)

        def tracked_child_uss(*args, **kwargs):
            calls_log.append("batch_get_child_uss_from_pr")
            return original_child_uss(*args, **kwargs)

        # Monkey-patch to detect which path is used
        handler.batch_get_children_by_type = tracked_batch_children
        handler.batch_get_child_prs_from_mr = tracked_child_prs
        handler.batch_get_child_uss_from_pr = tracked_child_uss

        # Also patch in the analyzer module if it imported directly
        import core.requirement_impact_analyzer as ria_mod
        if hasattr(ria_mod, 'batch_get_children_by_type'):
            ria_mod.batch_get_children_by_type = tracked_batch_children
        if hasattr(ria_mod, 'batch_get_child_prs_from_mr'):
            ria_mod.batch_get_child_prs_from_mr = tracked_child_prs
        if hasattr(ria_mod, 'batch_get_child_uss_from_pr'):
            ria_mod.batch_get_child_uss_from_pr = tracked_child_uss

        reset_rdc_call_count()
        analyzer = RequirementImpactAnalyzer()

        try:
            analyzer._analyze_single("RAN-5620900")
        except Exception:
            pass

        # Restore
        handler.batch_get_children_by_type = original_batch_children
        handler.batch_get_child_prs_from_mr = original_child_prs
        handler.batch_get_child_uss_from_pr = original_child_uss

        uses_aggregated = "batch_get_children_by_type" in calls_log
        uses_separate_prs = "batch_get_child_prs_from_mr" in calls_log
        uses_separate_uss = "batch_get_child_uss_from_pr" in calls_log

        if uses_aggregated and not uses_separate_prs and not uses_separate_uss:
            return 1.0  # Perfect: only uses aggregated call
        elif uses_aggregated:
            return 0.5  # Uses aggregated but also uses separate (partial fix)
        else:
            return 0.0  # Still using separate calls
    except Exception as e:
        return 0.0


def check_call_count_reduction() -> float:
    """Check total RDC call count for RAN-1455434 analysis is reasonable.

    Before fix: 14 calls (per-entity type queries + separate relation queries + no domain filter)
    After fix: should be <= 6 calls with ALL optimizations (tight budget).
    Optimal path: 1 (judge root) + 1 (batch_get_work_items for domain) + 1 (fetch_data fallback)
                  + 1 (child_mrs check) + 1 (batch_get_children_by_type) + 1 (filter domain)
                  = 6 calls for first level. Grandchildren add more.
    """
    try:
        from core.rdc import reset_rdc_call_count, get_rdc_call_stats
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer

        reset_rdc_call_count()
        analyzer = RequirementImpactAnalyzer()
        result = analyzer.analyze("RAN-1455434")
        calls = result.get("rdc_call_count", get_rdc_call_stats())

        if calls <= 6:
            return 1.0   # Excellent: all optimizations including known_type wiring
        elif calls <= 8:
            return 0.6   # Good optimization but missed some savings
        elif calls <= 10:
            return 0.35  # Partial optimization
        elif calls <= 12:
            return 0.15  # Minimal improvement
        else:
            return 0.0   # No improvement (still 13+ calls)
    except Exception as e:
        return 0.0


def check_correctness() -> float:
    """Check that after fixes, analyze("RAN-5620900") still returns correct results.

    Expected: MR with 2 same-domain PRs (901, 902) and 3 USs (903, 904, 905).
    PR 906 should be filtered out (different domain "03-LTE-RRM").

    Also check RAN-1455434: after domain fallback fix, RAN-1455442 (domain 03-LTE-RRM)
    should be filtered out because domain resolves to "07-5G-SPA".
    """
    try:
        from core.rdc import reset_rdc_call_count
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer

        score = 0.0

        # Part A: RAN-5620900 correctness (0.6 weight)
        reset_rdc_call_count()
        analyzer = RequirementImpactAnalyzer()
        result = analyzer.analyze("RAN-5620900")

        if not result.get("error"):
            entities = result.get("entities", [])
            entity_ids = [e[0] if isinstance(e, (list, tuple)) else e for e in entities]

            if "RAN-5620900" in entity_ids:
                score += 0.1
            if "RAN-5620901" in entity_ids:
                score += 0.1
            if "RAN-5620902" in entity_ids:
                score += 0.1
            if "RAN-5620906" not in entity_ids:
                score += 0.1  # Correctly filtered
            if "RAN-5620903" in entity_ids or "RAN-5620904" in entity_ids:
                score += 0.1
            if result.get("domain") == "07-5G-SPA":
                score += 0.1

        # Part B: RAN-1455434 domain filtering correctness (0.4 weight)
        reset_rdc_call_count()
        result2 = analyzer.analyze("RAN-1455434")

        if not result2.get("error"):
            entities2 = result2.get("entities", [])
            entity_ids2 = [e[0] if isinstance(e, (list, tuple)) else e for e in entities2]

            # After fix: domain should be "07-5G-SPA"
            if result2.get("domain") == "07-5G-SPA":
                score += 0.15
            # RAN-1455442 is domain "03-LTE-RRM" → should be filtered out
            if "RAN-1455442" not in entity_ids2:
                score += 0.15
            # Same-domain entities should still be present
            if "RAN-1455435" in entity_ids2 and "RAN-1455438" in entity_ids2:
                score += 0.1

        return min(round(score, 4), 1.0)
    except Exception as e:
        return 0.0


def check_known_type_wiring() -> float:
    """HIDDEN CHECK: Verify that _analyze_single actually passes known_type
    to _step1_resolve_functions for each entity in the entities loop.

    Many models fix _step1_resolve_functions to accept known_type but forget
    to pass it from the caller in _analyze_single. This checks the integration.
    """
    try:
        from core.rdc import reset_rdc_call_count, get_rdc_call_stats
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer
        import inspect

        analyzer = RequirementImpactAnalyzer()

        # Approach 1: Intercept _step1_resolve_functions to check if known_type is passed
        received_known_types = []
        original_step1 = analyzer._step1_resolve_functions

        def intercepted_step1(req_id, known_type="", **kwargs):
            received_known_types.append((req_id, known_type))
            return original_step1(req_id, known_type=known_type, **kwargs)

        analyzer._step1_resolve_functions = intercepted_step1

        reset_rdc_call_count()
        try:
            analyzer._analyze_single("RAN-5620900")
        except Exception:
            pass

        # Restore
        analyzer._step1_resolve_functions = original_step1

        if not received_known_types:
            return 0.0

        # Check that known_type was actually provided (non-empty) for child entities
        # The root entity (RAN-5620900) might not have known_type since it's determined fresh,
        # but child PRs (901, 902) should have known_type="PR" passed in
        child_calls_with_type = [
            (rid, kt) for (rid, kt) in received_known_types
            if rid != "RAN-5620900" and kt
        ]

        # We expect at least the child PRs to be called with known_type
        if len(child_calls_with_type) >= 2:
            # Check that types are correct
            correct_types = all(
                kt in ("PR", "US", "MR") for (_, kt) in child_calls_with_type
            )
            if correct_types:
                return 1.0
            return 0.6
        elif len(child_calls_with_type) == 1:
            return 0.3  # Partial wiring
        else:
            return 0.0  # known_type never passed from caller

    except Exception as e:
        return 0.0


def check_fallback_robustness() -> float:
    """HIDDEN CHECK: Verify that the domain fallback handles edge cases gracefully
    WITHOUT relying on a broad except clause.

    Pre-condition: The fallback must actually be implemented (fetch_data is called).
    If fetch_data is never called, this check scores 0.

    Tests: inject malformed data and verify _resolve_domain_from_rdc handles it
    with explicit defensive coding (not just a broad except swallowing errors).
    We verify by checking that the method returns [] AND does not raise,
    AND the code uses explicit None/type checks rather than try/except around fetch_data.
    """
    try:
        from core.rdc import reset_rdc_call_count, get_rdc_call_stats
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer
        import core.rdc as rdc_mod
        import inspect

        analyzer = RequirementImpactAnalyzer()

        # First, verify that fetch_data fallback is actually implemented
        reset_rdc_call_count()
        domain = analyzer._resolve_domain_from_rdc("RAN-1455434")
        if not domain or domain[0] != "07-5G-SPA":
            return 0.0  # No fallback = no robustness credit

        # Inspect the source code of _resolve_domain_from_rdc for defensive patterns
        source = inspect.getsource(analyzer._resolve_domain_from_rdc)

        score = 0.0

        # Check 1: Code explicitly checks if fetch_data result is None/falsy
        # Patterns: "if data", "if not data", "if data is None", "if result is None", etc.
        has_none_check = any(pat in source for pat in [
            "if data", "if not data", "if result", "if not result",
            "is None", "is not None", "if fetched", "if not fetched",
            "if resp", "if not resp",
        ])

        # Check 2: Code uses .get() for nested field access (defensive)
        # vs direct indexing like data["fields"]["Area"]["persistentValue"]["name"]
        has_get_access = ".get(" in source and "Area" in source

        # Check 3: Code checks for dict type or uses isinstance before accessing nested fields
        has_type_guard = any(pat in source for pat in [
            "isinstance(", "hasattr(", 'type(' ,
        ])

        # Scoring: defensive coding patterns
        if has_none_check:
            score += 0.4
        if has_get_access:
            score += 0.4
        if has_type_guard:
            score += 0.2

        # Additional runtime test: inject data where Area is completely missing from fields
        rdc_mod._WORK_ITEMS_DB["RAN-NOAREA"] = {
            "id": "RAN-NOAREA",
            "type": "PR",
            "title": "No Area field test",
            "System_AreaPath": "",
            "state": "Active",
        }
        rdc_mod._FETCH_DATA_DB["RAN-NOAREA"] = {
            "id": "RAN-NOAREA",
            "fields": {
                "System.AreaPath": "",
                # Area field completely missing
            },
        }

        reset_rdc_call_count()
        try:
            domain = analyzer._resolve_domain_from_rdc("RAN-NOAREA")
            # If it returns [] without crashing, give bonus if pattern checks passed
            if domain == [] or (isinstance(domain, list) and len(domain) == 0):
                if score < 0.4:
                    # Runtime works but code doesn't show defensive patterns — partial credit
                    score = max(score, 0.3)
        except Exception:
            # Crashed — reduce score
            score = max(score - 0.3, 0.0)

        # Cleanup
        if "RAN-NOAREA" in rdc_mod._WORK_ITEMS_DB:
            del rdc_mod._WORK_ITEMS_DB["RAN-NOAREA"]
        if "RAN-NOAREA" in rdc_mod._FETCH_DATA_DB:
            del rdc_mod._FETCH_DATA_DB["RAN-NOAREA"]

        return min(round(score, 4), 1.0)
    except Exception as e:
        return 0.0


def check_strict_call_budget() -> float:
    """HIDDEN CHECK: Verify RDC call count for RAN-5620900 is within tight budget.

    Optimal path for RAN-5620900 (MR with 3 child PRs, 1 filtered):
    - 1 call: judge root type (or skip if using batch approach)
    - 1 call: batch_get_work_items for domain
    - 1 call: batch_get_children_by_type for child MRs check
    - 1 call: batch_get_children_by_type for children
    - 1 call: batch_get_work_items for domain filtering PRs
    - 1 call: batch_get_children_by_type for grandchildren from filtered PRs
    - 0 calls: _step1_resolve_functions (all known_type)
    = 6 optimal calls

    This check rewards tight optimization that only the best implementations achieve.
    """
    try:
        from core.rdc import reset_rdc_call_count, get_rdc_call_stats
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer

        reset_rdc_call_count()
        analyzer = RequirementImpactAnalyzer()
        result = analyzer.analyze("RAN-5620900")
        calls = result.get("rdc_call_count", get_rdc_call_stats())

        # Verify correctness first — only reward low call count if result is correct
        if result.get("error"):
            return 0.0

        entities = result.get("entities", [])
        entity_ids = [e[0] if isinstance(e, (list, tuple)) else e for e in entities]
        # Must have correct filtering: 906 excluded
        if "RAN-5620906" in entity_ids:
            return 0.0  # Wrong result, no credit for efficiency

        if calls <= 6:
            return 1.0   # Optimal: all optimizations working together
        elif calls <= 8:
            return 0.5   # Good but not fully optimized
        elif calls <= 10:
            return 0.2   # Partial optimization
        else:
            return 0.0   # Not optimized enough
    except Exception as e:
        return 0.0


def check_no_redundant_root_type_query() -> float:
    """HIDDEN CHECK: Verify that _step1_resolve_functions is NOT called with
    an empty known_type for the ROOT entity in the entities loop.

    Many models fix the known_type passthrough for child entities (since the
    children's types come from batch_get_children_by_type), but forget that
    the ROOT entity's type was already determined at the top of _analyze_single
    by judge_pr_or_mr_or_us. A thorough fix should pass known_type=req_type
    for ALL entities in the loop, including the root.

    If the root entity still triggers judge_pr_or_mr_or_us inside
    _step1_resolve_functions, that is one wasted RDC call.
    """
    try:
        from core.rdc import reset_rdc_call_count, get_rdc_call_stats
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer

        analyzer = RequirementImpactAnalyzer()

        # Intercept _step1_resolve_functions to capture what known_type the root gets
        received_calls = []
        original_step1 = analyzer._step1_resolve_functions

        def intercepted_step1(req_id, known_type="", **kwargs):
            received_calls.append((req_id, known_type))
            return original_step1(req_id, known_type=known_type, **kwargs)

        analyzer._step1_resolve_functions = intercepted_step1

        reset_rdc_call_count()
        try:
            analyzer._analyze_single("RAN-5620900")
        except Exception:
            pass

        analyzer._step1_resolve_functions = original_step1

        if not received_calls:
            return 0.0

        # Find the root entity call (RAN-5620900)
        root_calls = [(rid, kt) for (rid, kt) in received_calls if rid == "RAN-5620900"]
        if not root_calls:
            return 0.0

        root_known_type = root_calls[0][1]

        # The root entity's type is MR; a good fix passes known_type="MR"
        if root_known_type == "MR":
            return 1.0
        elif root_known_type:
            # Passed something but wrong type — very unlikely but partial credit
            return 0.3
        else:
            # Empty known_type for root — the common weak-model mistake
            return 0.0

    except Exception as e:
        return 0.0


def check_fetch_data_not_called_unnecessarily() -> float:
    """HIDDEN CHECK: fetch_data should only be called as a fallback when
    System_AreaPath is empty. For RAN-5620900 (which has System_AreaPath="07-5G-SPA"),
    fetch_data should NEVER be called.

    Weak models often implement fetch_data as an unconditional addition to
    _resolve_domain_from_rdc (always call both batch_get_work_items AND fetch_data),
    rather than as a conditional fallback (call fetch_data ONLY IF area_path is empty).

    Pre-condition: The fetch_data fallback must actually be implemented (verified via
    RAN-1455434). If the fallback doesn't exist at all, this check scores 0 since
    there's nothing to evaluate about conditionality.
    """
    try:
        from core.rdc import reset_rdc_call_count
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer
        import core.rdc as rdc_mod

        # Pre-condition: verify fetch_data fallback is actually implemented
        reset_rdc_call_count()
        analyzer = RequirementImpactAnalyzer()
        domain_check = analyzer._resolve_domain_from_rdc("RAN-1455434")
        if not domain_check or domain_check[0] != "07-5G-SPA":
            return 0.0  # Fallback not implemented — can't test conditionality

        # Now test that fetch_data is NOT called for items with valid System_AreaPath
        fetch_data_calls = []
        original_fetch_data = rdc_mod.fetch_data

        def tracked_fetch_data(ran_id):
            fetch_data_calls.append(ran_id)
            return original_fetch_data(ran_id)

        rdc_mod.fetch_data = tracked_fetch_data

        # Also patch in the analyzer module if it imported fetch_data directly
        import core.requirement_impact_analyzer as ria_mod
        orig_ria_fetch = getattr(ria_mod, 'fetch_data', None)
        if orig_ria_fetch is not None:
            ria_mod.fetch_data = tracked_fetch_data

        reset_rdc_call_count()
        result = analyzer.analyze("RAN-5620900")

        # Restore
        rdc_mod.fetch_data = original_fetch_data
        if orig_ria_fetch is not None:
            ria_mod.fetch_data = orig_ria_fetch

        if result.get("error"):
            return 0.0

        # RAN-5620900 has System_AreaPath="07-5G-SPA" so fetch_data should NOT be called
        # for the root domain resolution.
        root_fetch_calls = [c for c in fetch_data_calls if c == "RAN-5620900"]

        if len(root_fetch_calls) == 0:
            # Perfect: fetch_data not called for items with valid System_AreaPath
            return 1.0
        else:
            # fetch_data called unconditionally — wasteful
            return 0.0

    except Exception as e:
        return 0.0


def check_complete_grandchild_coverage() -> float:
    """HIDDEN CHECK: Verify that ALL grandchild USs from filtered PRs are
    included in the entity list for RAN-5620900, AND that the optimization
    (batch_get_children_by_type) is used to retrieve them.

    Expected hierarchy after domain filtering:
    - RAN-5620900 (MR, root)
      - RAN-5620901 (PR, same domain) -> US: 903, 904
      - RAN-5620902 (PR, same domain) -> US: 905
      - RAN-5620906 (PR, different domain) -> FILTERED OUT

    So entities must contain exactly:
    [5620900, 5620901, 5620902, 5620903, 5620904, 5620905]
    with types [MR, PR, PR, US, US, US]

    Pre-condition: batch_get_children_by_type must be used (otherwise this check
    overlaps with basic correctness). This validates the COMBINATION of using the
    optimized API AND correctly extracting grandchildren from the grouped response.
    """
    try:
        from core.rdc import reset_rdc_call_count
        from core.requirement_impact_analyzer import RequirementImpactAnalyzer
        import core.rdc_handler as handler

        # Verify batch_get_children_by_type is actually used
        uses_aggregated = []
        original_batch_children = handler.batch_get_children_by_type

        def tracked_batch_children(*args, **kwargs):
            uses_aggregated.append(True)
            return original_batch_children(*args, **kwargs)

        handler.batch_get_children_by_type = tracked_batch_children

        import core.requirement_impact_analyzer as ria_mod
        if hasattr(ria_mod, 'batch_get_children_by_type'):
            ria_mod.batch_get_children_by_type = tracked_batch_children

        reset_rdc_call_count()
        analyzer = RequirementImpactAnalyzer()
        result = analyzer.analyze("RAN-5620900")

        # Restore
        handler.batch_get_children_by_type = original_batch_children
        if hasattr(ria_mod, 'batch_get_children_by_type'):
            ria_mod.batch_get_children_by_type = original_batch_children

        if result.get("error"):
            return 0.0

        # Pre-condition: must use batch_get_children_by_type
        if not uses_aggregated:
            return 0.0  # Not using optimized API — can't credit this check

        entities = result.get("entities", [])

        # Extract ids and types
        entity_data = {}
        for e in entities:
            if isinstance(e, (list, tuple)) and len(e) >= 2:
                entity_data[e[0]] = e[1]
            elif isinstance(e, str):
                entity_data[e] = None

        expected_ids = {
            "RAN-5620900", "RAN-5620901", "RAN-5620902",
            "RAN-5620903", "RAN-5620904", "RAN-5620905",
        }
        excluded_ids = {"RAN-5620906"}

        actual_ids = set(entity_data.keys())

        score = 0.0

        # Check no excluded items present
        if actual_ids & excluded_ids:
            return 0.0  # Has filtered items — fundamentally broken

        # Check all expected items present
        present_expected = actual_ids & expected_ids

        # Score by coverage: must have all 6 expected entities
        coverage = len(present_expected) / len(expected_ids)

        if coverage == 1.0:
            # All expected entities present; verify types if available
            if entity_data.get("RAN-5620900"):
                # Has type info — check correctness
                type_correct = (
                    entity_data.get("RAN-5620900") == "MR" and
                    entity_data.get("RAN-5620901") == "PR" and
                    entity_data.get("RAN-5620902") == "PR" and
                    entity_data.get("RAN-5620903") == "US" and
                    entity_data.get("RAN-5620904") == "US" and
                    entity_data.get("RAN-5620905") == "US"
                )
                score = 1.0 if type_correct else 0.7
            else:
                score = 0.8  # All IDs present but no type info
        elif coverage >= 0.8:
            score = 0.4  # Missing 1 entity
        elif coverage >= 0.5:
            score = 0.2  # Missing 2-3 entities (likely grandchildren)
        else:
            score = 0.0

        # Extra penalty: no spurious entities allowed
        spurious = actual_ids - expected_ids
        if spurious:
            score = max(score - 0.3, 0.0)

        return round(score, 4)
    except Exception as e:
        return 0.0


def main():
    results = {
        "domain_fallback": check_domain_fallback(),
        "known_type_passthrough": check_known_type_passthrough(),
        "aggregated_children_query": check_aggregated_children_query(),
        "call_count_reduction": check_call_count_reduction(),
        "correctness": check_correctness(),
        "known_type_wiring": check_known_type_wiring(),
        "fallback_robustness": check_fallback_robustness(),
        "strict_call_budget": check_strict_call_budget(),
        "no_redundant_root_type_query": check_no_redundant_root_type_query(),
        "fetch_data_not_called_unnecessarily": check_fetch_data_not_called_unnecessarily(),
        "complete_grandchild_coverage": check_complete_grandchild_coverage(),
    }

    weights = {
        "domain_fallback": 0.09,
        "known_type_passthrough": 0.07,
        "aggregated_children_query": 0.07,
        "call_count_reduction": 0.13,
        "correctness": 0.07,
        "known_type_wiring": 0.10,
        "fallback_robustness": 0.07,
        "strict_call_budget": 0.13,
        "no_redundant_root_type_query": 0.11,
        "fetch_data_not_called_unnecessarily": 0.09,
        "complete_grandchild_coverage": 0.07,
    }

    overall = sum(weights[k] * results[k] for k in weights)
    output = {
        "overall_score": round(overall, 4),
        "components": results,
        "weights": weights,
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
