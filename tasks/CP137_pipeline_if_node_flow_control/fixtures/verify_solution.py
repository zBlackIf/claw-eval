"""Hidden verifier for CP137 — Pipeline If Node Flow Control."""
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


def _find_file(root: Path, pattern: str) -> Path | None:
    """Find first file matching glob pattern recursively."""
    for p in root.rglob(pattern):
        if p.is_file():
            return p
    return None


def _find_files(root: Path, pattern: str) -> list[Path]:
    """Find all files matching glob pattern recursively."""
    return [p for p in root.rglob(pattern) if p.is_file()]


def grade_workspace(ws: Path) -> dict:
    # Look for the pipeline-engine directory in multiple locations
    engine_root = None
    for candidate in [
        ws / "fixtures" / "pipeline-engine",
        ws / "pipeline-engine",
    ]:
        if candidate.exists():
            engine_root = candidate
            break

    if engine_root is None:
        return {
            "overall_score": 0.0,
            "components": {},
            "error": "pipeline-engine directory not found",
        }

    components = {k: 0.0 for k in [
        "if_node_model",
        "if_node_discriminator",
        "if_executor_created",
        "condition_evaluation",
        "branch_execution",
        "executor_registered",
        "scope_isolation",
        "scope_isolation_depth",
        "cancellation_propagation",
        "nested_if_support",
        "async_pattern_correctness",
        "condition_guard_clause",
        "scope_cleanup_guarantee",
    ]}

    # 1. Check IfPipelineNode model exists with correct structure
    if_node_file = _find_file(engine_root, "IfPipelineNode.cs")
    if if_node_file is None:
        # Also check if it's defined inline in PipelineNode.cs
        pn_file = _find_file(engine_root, "PipelineNode.cs")
        if pn_file:
            c = _read(pn_file)
            if "IfPipelineNode" in c:
                if_node_file = pn_file

    if if_node_file:
        c = _read(if_node_file)
        has_record_or_class = bool(re.search(r"(record|class)\s+IfPipelineNode", c))
        has_condition = "Condition" in c or "condition" in c
        has_then = bool(re.search(r"[Tt]hen\s*[Cc]hild", c)) or "ThenChildren" in c or "thenChildren" in c or "ThenBranch" in c
        has_else = bool(re.search(r"[Ee]lse\s*[Cc]hild", c)) or "ElseChildren" in c or "elseChildren" in c or "ElseBranch" in c
        has_inherits = "PipelineNode" in c

        score = 0.0
        if has_record_or_class:
            score += 0.2
        if has_condition:
            score += 0.2
        if has_then:
            score += 0.2
        if has_else:
            score += 0.2
        if has_inherits:
            score += 0.2
        components["if_node_model"] = min(score, 1.0)

    # 2. Check polymorphic discriminator registration
    pn_file = _find_file(engine_root, "PipelineNode.cs")
    if pn_file:
        c = _read(pn_file)
        # Check for JsonDerivedType attribute with "if" discriminator
        has_derived_type = bool(re.search(
            r'JsonDerivedType\s*\(\s*typeof\s*\(\s*IfPipelineNode\s*\)', c
        ))
        has_if_disc = '"if"' in c and "IfPipelineNode" in c
        components["if_node_discriminator"] = 1.0 if (has_derived_type and has_if_disc) else (0.5 if has_derived_type or has_if_disc else 0.0)

    # 3. Check IfExecutor exists
    if_executor_file = _find_file(engine_root, "IfExecutor*.cs")
    if if_executor_file is None:
        if_executor_file = _find_file(engine_root, "*IfExecutor*.cs")
    if if_executor_file is None:
        if_executor_file = _find_file(engine_root, "*If*Executor*.cs")
    if if_executor_file is None:
        # Check all .cs files for a class implementing INodeExecutor<IfPipelineNode>
        for f in _find_files(engine_root, "*.cs"):
            c = _read(f)
            if "INodeExecutor<IfPipelineNode>" in c or ("IfPipelineNode" in c and "ExecuteAsync" in c):
                if_executor_file = f
                break

    if if_executor_file:
        c = _read(if_executor_file)
        has_class = bool(re.search(r"class\s+\w*If\w*Executor", c)) or "INodeExecutor<IfPipelineNode>" in c
        has_execute = "ExecuteAsync" in c
        components["if_executor_created"] = 1.0 if (has_class and has_execute) else (0.5 if has_class or has_execute else 0.0)

    # 4. Check condition evaluation logic — stricter: must have DISTINCT code paths
    #    for bool literals, variable resolution, AND comparisons
    if if_executor_file:
        c = _read(if_executor_file)

        # Boolean literal parsing: must explicitly handle "true"/"false" string parsing
        has_bool_literal = bool(re.search(
            r'(bool\.TryParse|bool\.Parse|["\']true["\']|["\']false["\']|'
            r'\.Equals\s*\(\s*["\']true["\']|'
            r'StringComparison\.OrdinalIgnoreCase.*true|'
            r'[Tt]oLower.*==.*"true")',
            c
        ))

        # Variable resolution: must call GetVariable or access context variables
        has_var_resolution = bool(re.search(
            r'(GetVariable|context\s*\.\s*Variables|context\s*\[\s*)',
            c
        ))

        # Comparison operators: must have string splitting or operator detection logic
        has_comparison_logic = bool(re.search(
            r'(Split|IndexOf|Contains\s*\(\s*["\'][=!<>]|'
            r'["\']==["\'"]|["\']!=["\'"]|["\']>=["\'"]|["\']<=["\'"]|'
            r'Operator|CompareOperator|'
            r'\.Trim\(\).*[=!<>])',
            c
        ))

        cond_score = 0.0
        if has_bool_literal:
            cond_score += 0.35
        if has_var_resolution:
            cond_score += 0.35
        if has_comparison_logic:
            cond_score += 0.30
        components["condition_evaluation"] = min(cond_score, 1.0)

    # 5. Check that executor runs then/else branches
    if if_executor_file:
        c = _read(if_executor_file)
        has_then_exec = bool(re.search(r"[Tt]hen", c)) and ("Execute" in c or "foreach" in c.lower() or "for " in c.lower())
        has_else_exec = bool(re.search(r"[Ee]lse", c)) and ("Execute" in c or "foreach" in c.lower())
        has_child_dispatch = "ExecuteNodeAsync" in c or "_registry" in c or "registry" in c

        branch_score = 0.0
        if has_then_exec:
            branch_score += 0.35
        if has_else_exec:
            branch_score += 0.35
        if has_child_dispatch:
            branch_score += 0.3
        components["branch_execution"] = min(branch_score, 1.0)

    # 6. Check executor registration in SystemModule
    sys_module = _find_file(engine_root, "SystemModule.cs")
    if sys_module:
        c = _read(sys_module)
        has_register_call = "Register" in c and "If" in c
        # Stronger check: must pass registry to IfExecutor (like GroupExecutor pattern)
        has_registry_injection = bool(re.search(
            r'new\s+\w*If\w*Executor\s*\(\s*registry\s*\)', c
        ))
        if has_register_call and has_registry_injection:
            components["executor_registered"] = 1.0
        elif has_register_call:
            components["executor_registered"] = 0.6
        else:
            components["executor_registered"] = 0.0

    # 7. Check basic scope isolation (keyword-level, easy check)
    scope_found = False
    for f in _find_files(engine_root, "*.cs"):
        c = _read(f)
        if any(kw in c for kw in ["PushScope", "PopScope", "ScopeStack",
                                    "EnterScope", "LeaveScope", "BeginScope", "EndScope",
                                    "CreateChildContext", "ChildContext", "Fork"]):
            scope_found = True
            break
    ctx_file = _find_file(engine_root, "PipelineContext.cs")
    if ctx_file:
        c = _read(ctx_file)
        has_scope_stack = any(kw in c for kw in [
            "Stack", "Push", "Pop", "nested", "child", "fork"
        ])
        if has_scope_stack:
            scope_found = True
    components["scope_isolation"] = 1.0 if scope_found else 0.0

    # 8. HIDDEN: Scope isolation DEPTH — verify the implementation actually uses
    #    a proper stack-based or hierarchical variable isolation mechanism.
    #    Just having the word "scope" is not enough. Must have:
    #    - A Stack<> or List<> of dictionaries/scopes in PipelineContext
    #    - Both push AND pop (or equivalent enter/leave) in the executor
    #    - Variable lookup that traverses the scope chain (not just top-level)
    scope_depth_score = 0.0
    if ctx_file:
        c = _read(ctx_file)
        # Must have a stack/list of dictionaries for scoping
        has_scope_collection = bool(re.search(
            r'(Stack\s*<\s*Dictionary|List\s*<\s*Dictionary|'
            r'Stack\s*<\s*IDictionary|LinkedList\s*<\s*Dictionary|'
            r'Stack\s*<.*[Ss]cope|List\s*<.*[Ss]cope)',
            c
        ))
        # Must have both push and pop operations defined
        has_push_pop = (
            bool(re.search(r'(Push|Add|Enter|Begin|Create)', c)) and
            bool(re.search(r'(Pop|Remove|Leave|End|Dispose)', c))
        )
        # Variable lookup should check multiple levels (scope chain traversal)
        has_chain_lookup = bool(re.search(
            r'(foreach.*[Ss]cope|for.*[Ss]cope|Reverse|Peek|'
            r'TryGetValue.*\|\||'
            r'First\(|FirstOrDefault|'
            r'Any\(.*ContainsKey|'
            r'_scopes\[|_stack\[)',
            c
        ))
        if has_scope_collection:
            scope_depth_score += 0.4
        if has_push_pop:
            scope_depth_score += 0.3
        if has_chain_lookup:
            scope_depth_score += 0.3
    components["scope_isolation_depth"] = min(scope_depth_score, 1.0)

    # 9. HIDDEN: Cancellation token propagation — the IfExecutor should check
    #    cancellation before/during branch execution (consistent with GroupExecutor pattern)
    if if_executor_file:
        c = _read(if_executor_file)
        # Must propagate ct to child execution AND check IsCancelled or ct.IsCancellationRequested
        has_ct_propagation = bool(re.search(
            r'ExecuteNodeAsync\s*\([^)]*,\s*\w*[Cc](?:t|ancellation)',
            c
        ))
        has_cancel_check = bool(re.search(
            r'(IsCancelled|IsCancellationRequested|ct\.ThrowIfCancellationRequested|'
            r'cancellationToken\.IsCancellationRequested|token\.IsCancellationRequested)',
            c
        ))
        cancel_score = 0.0
        if has_ct_propagation:
            cancel_score += 0.5
        if has_cancel_check:
            cancel_score += 0.5
        components["cancellation_propagation"] = cancel_score

    # 10. HIDDEN: Nested if-node support — the IfExecutor must use the registry
    #     to dispatch child nodes (not inline execution). This enables nested ifs.
    #     Verify the executor takes registry as a dependency AND uses it for children.
    if if_executor_file:
        c = _read(if_executor_file)
        # Must store registry as a field (dependency injection pattern)
        has_registry_field = bool(re.search(
            r'(private|readonly)\s+.*[Rr]egistry\s+_', c
        )) or bool(re.search(
            r'_registry', c
        ))
        # Must call registry.ExecuteNodeAsync (not just inline execution)
        has_registry_dispatch = bool(re.search(
            r'_?[Rr]egistry\s*\.\s*ExecuteNodeAsync', c
        ))
        # Must iterate over children calling the registry (enabling arbitrary nested nodes)
        has_child_loop_dispatch = bool(re.search(
            r'(foreach|for)\s*\(.*\b(child|node|item)\b.*\)\s*\{?\s*\n?\s*.*ExecuteNodeAsync',
            c, re.DOTALL
        )) or bool(re.search(
            r'foreach.*\n\s*\{?\s*\n?\s*.*await.*ExecuteNodeAsync',
            c, re.DOTALL
        ))

        nested_score = 0.0
        if has_registry_field:
            nested_score += 0.3
        if has_registry_dispatch:
            nested_score += 0.4
        if has_child_loop_dispatch:
            nested_score += 0.3
        components["nested_if_support"] = min(nested_score, 1.0)

    # 11. HIDDEN: Proper async pattern — IfExecutor must follow the exact
    #     async Task signature pattern used by GroupExecutor. Must have:
    #     - "async Task ExecuteAsync" method signature (not Task<T>, not void)
    #     - CancellationToken parameter in the method signature
    #     - Proper await usage on child execution calls
    #     Weak models often miss the ct parameter or return wrong type.
    if if_executor_file:
        c = _read(if_executor_file)
        # Must have async Task ExecuteAsync with ct param (exact pattern from interface)
        has_async_task_sig = bool(re.search(
            r'public\s+async\s+Task\s+ExecuteAsync\s*\(',
            c
        ))
        # Must accept CancellationToken (can be named ct, cancellationToken, etc.)
        has_ct_in_sig = bool(re.search(
            r'ExecuteAsync\s*\([^)]*CancellationToken\s+\w+',
            c
        ))
        # Must await child calls (not fire-and-forget)
        has_proper_await = bool(re.search(
            r'await\s+_?[Rr]egistry\s*\.\s*ExecuteNodeAsync',
            c
        ))

        async_score = 0.0
        if has_async_task_sig:
            async_score += 0.35
        if has_ct_in_sig:
            async_score += 0.35
        if has_proper_await:
            async_score += 0.30
        components["async_pattern_correctness"] = min(async_score, 1.0)

    # 12. HIDDEN: Condition null/empty guard — A robust IfExecutor must handle
    #     null or empty Condition gracefully instead of crashing. Should either
    #     default to false (skip then-branch) or throw an explicit exception.
    #     Also checks for trimming whitespace before evaluation.
    if if_executor_file:
        c = _read(if_executor_file)
        # Must check for null/empty/whitespace condition
        has_null_check = bool(re.search(
            r'(string\.IsNullOrEmpty|string\.IsNullOrWhiteSpace|'
            r'Condition\s*==\s*null|Condition\s*is\s+null|'
            r'!\s*string\.IsNullOrEmpty|!\s*string\.IsNullOrWhiteSpace|'
            r'node\.Condition\s*==\s*null|node\.Condition\s*is\s+null)',
            c
        ))
        # Should trim the condition before evaluation (prevents " true " bugs)
        has_trim = bool(re.search(
            r'(\.Trim\s*\(\)|\.Trim\(\)\s*;|Condition\s*\.Trim|'
            r'condition\s*\.Trim|cond\s*\.Trim)',
            c
        ))
        # Should have a clear false-path for invalid conditions (not just crash)
        has_default_false = bool(re.search(
            r'(return\s+false|result\s*=\s*false|default.*false|'
            r'else\s*\{?\s*\n?\s*.*false|'
            r'throw\s+new\s+(ArgumentException|InvalidOperationException|ArgumentNullException))',
            c
        ))

        guard_score = 0.0
        if has_null_check:
            guard_score += 0.40
        if has_trim:
            guard_score += 0.30
        if has_default_false:
            guard_score += 0.30
        components["condition_guard_clause"] = min(guard_score, 1.0)

    # 13. HIDDEN: Scope cleanup guarantee — The scope push/pop must be wrapped
    #     in a try/finally to ensure PopScope happens even if child execution throws.
    #     Without this, an exception in a branch leaks scope permanently.
    #     This is the key robustness pattern that separates strong from weak implementations.
    scope_cleanup_score = 0.0
    if if_executor_file:
        c = _read(if_executor_file)
        # Must have try/finally around scope operations
        has_try_finally = bool(re.search(
            r'try\s*\{[^}]*(?:Push|Enter|Begin|Create)[^}]*\}',
            c, re.DOTALL
        )) or bool(re.search(
            r'(?:Push|Enter|Begin|Create).*\n.*try\s*\{',
            c, re.DOTALL
        ))
        has_finally_pop = bool(re.search(
            r'finally\s*\{[^}]*(?:Pop|Leave|End|Dispose|PopScope)',
            c, re.DOTALL
        ))
        # Alternative: using statement with IDisposable scope
        has_using_scope = bool(re.search(
            r'(using\s*\(.*[Ss]cope|using\s+var\s+\w*[Ss]cope)',
            c
        ))

        if has_using_scope:
            scope_cleanup_score = 1.0
        else:
            if has_try_finally:
                scope_cleanup_score += 0.5
            if has_finally_pop:
                scope_cleanup_score += 0.5
    components["scope_cleanup_guarantee"] = scope_cleanup_score

    # Weights: reduce easy checks, increase weight of hidden checks significantly.
    # Easy/visible checks (6): ~30% total
    # Hard/hidden checks (7): ~70% total
    weights = {
        "if_node_model": 0.07,
        "if_node_discriminator": 0.05,
        "if_executor_created": 0.05,
        "condition_evaluation": 0.10,
        "branch_execution": 0.08,
        "executor_registered": 0.03,
        "scope_isolation": 0.02,
        "scope_isolation_depth": 0.15,
        "cancellation_propagation": 0.10,
        "nested_if_support": 0.10,
        "async_pattern_correctness": 0.10,
        "condition_guard_clause": 0.07,
        "scope_cleanup_guarantee": 0.08,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
