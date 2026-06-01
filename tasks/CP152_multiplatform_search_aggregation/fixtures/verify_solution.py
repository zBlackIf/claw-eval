"""Hidden verifier for CP152 — Multi-platform Search Aggregation Page.

Tiered grading:
  EASY tier  (visible, all agents pass): platform_tabs, platform_badge, basic_concurrent
  HARD tier  (hidden, only strong pass): error_resilience_deep, state_machine_correctness,
             race_condition_guard, loading_ux_advanced
  Hidden checks >= 32% weight.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_comments(content: str) -> str:
    """Remove HTML comments and single-line // comments to avoid false positives."""
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    content = re.sub(r'(?<!:)//[^\n]*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    return content


def _find_search_page(ws: Path) -> str:
    """Find the search page index.vue content."""
    candidates = [
        ws / "fixtures" / "ecommerce-app" / "src" / "pages" / "search" / "index.vue",
        ws / "ecommerce-app" / "src" / "pages" / "search" / "index.vue",
    ]
    for c in candidates:
        if c.exists():
            return _read(c)
    for p in ws.rglob("pages/search/index.vue"):
        return _read(p)
    return ""


def _extract_script(vue_content: str) -> str:
    """Extract <script> section from .vue file."""
    m = re.search(r'<script[^>]*>(.*?)</script>', vue_content, re.DOTALL)
    return m.group(1) if m else ""


def _extract_template(vue_content: str) -> str:
    """Extract <template> section from .vue file."""
    m = re.search(r'<template[^>]*>(.*?)</template>', vue_content, re.DOTALL)
    return m.group(1) if m else ""


def _extract_style(vue_content: str) -> str:
    """Extract <style> section from .vue file."""
    m = re.search(r'<style[^>]*>(.*?)</style>', vue_content, re.DOTALL)
    return m.group(1) if m else ""


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        # --- EASY TIER (visible, high pass-rate) ---
        "platform_tabs",           # 0.12
        "basic_concurrent",        # 0.12
        "platform_badge",          # 0.10
        "infinite_scroll",         # 0.10
        "merge_logic",             # 0.10
        # Total easy: 0.54
        # --- HARD TIER (hidden, discriminating) ---
        "error_resilience_deep",       # 0.12
        "state_machine_correctness",   # 0.11
        "race_condition_guard",        # 0.12
        "loading_ux_advanced",         # 0.11
        # Total hard: 0.46  (hidden >= 32% satisfied, actually 46%)
    ]}

    search_raw = _find_search_page(ws)
    weights = {
        "platform_tabs": 0.12,
        "basic_concurrent": 0.12,
        "platform_badge": 0.10,
        "infinite_scroll": 0.10,
        "merge_logic": 0.10,
        "error_resilience_deep": 0.12,
        "state_machine_correctness": 0.11,
        "race_condition_guard": 0.12,
        "loading_ux_advanced": 0.11,
    }

    if not search_raw:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": weights,
        }

    search_content = _strip_comments(search_raw)
    script_section = _strip_comments(_extract_script(search_raw))
    template_section = _strip_comments(_extract_template(search_raw))
    style_section = _strip_comments(_extract_style(search_raw))

    # ===================================================================
    # EASY TIER — These checks are straightforward; any reasonable agent
    # that follows the prompt will pass them.
    # ===================================================================

    # --- EASY 1: Platform Tabs (0.12) ---
    # Labels can be in template (hardcoded) or script (dynamic array)
    platform_labels_in_tpl = sum(
        1 for label in ["全部", "淘宝", "京东", "拼多多"]
        if label in template_section
    )
    platform_labels_in_script = sum(
        1 for label in ["全部", "淘宝", "京东", "拼多多"]
        if label in script_section
    )
    platform_labels_count = max(platform_labels_in_tpl, platform_labels_in_script)
    has_platform_state = bool(
        re.search(r'(currentPlatform|activePlatform|selectedPlatform|activeTab|tabIndex)\s*[=:]', script_section)
        or re.search(r'ref\s*[<(]\s*(number|string|Platform)', script_section)
    )
    has_platform_click = bool(
        re.search(r'@(click|tap).*[pP]latform|@(click|tap).*[tT]ab', template_section)
    )
    # v-for tab rendering pattern counts as having tabs in template
    has_vfor_tabs = bool(
        re.search(r'v-for.*tab|v-for.*platform', template_section, re.IGNORECASE)
    )

    if platform_labels_count >= 3 and has_platform_state and (has_platform_click or has_vfor_tabs):
        components["platform_tabs"] = 1.0
    elif platform_labels_count >= 3 and (has_platform_state or has_platform_click):
        components["platform_tabs"] = 0.7
    elif platform_labels_count >= 2 and has_platform_state:
        components["platform_tabs"] = 0.5
    elif has_platform_state and has_platform_click:
        components["platform_tabs"] = 0.3

    # --- EASY 2: Basic Concurrent Requests (0.12) ---
    # Checks that some form of concurrent/parallel request is used
    has_all_settled = bool(
        re.search(r'Promise\.allSettled\s*\(', script_section)
    )
    has_promise_all = bool(
        re.search(r'Promise\.all\s*\(', script_section)
    )
    platform_call_count = len(re.findall(
        r'(searchGoods|search)\s*\(\s*\{[^}]*platform\s*:\s*[123]', script_section, re.DOTALL
    ))
    has_map_pattern = bool(
        re.search(r'\[\s*1\s*,\s*2\s*,\s*3\s*\]\.map', script_section)
        or re.search(r'platforms.*\.map\(', script_section)
    )

    if (has_all_settled or has_promise_all) and (platform_call_count >= 2 or has_map_pattern):
        components["basic_concurrent"] = 1.0
    elif has_all_settled or has_promise_all:
        components["basic_concurrent"] = 0.7
    elif platform_call_count >= 3 or has_map_pattern:
        components["basic_concurrent"] = 0.4

    # --- EASY 3: Platform Badge/Indicator (0.10) ---
    has_badge_element = bool(
        re.search(r'(class|:class).*["\'].*(?:badge|tag|label|platform)[^"\']*["\']', template_section, re.IGNORECASE)
        and re.search(r'(item|goods|product)\.(platform|source)', template_section)
    )
    has_platform_text = bool(
        re.search(r'(===?\s*1.*淘宝|===?\s*2.*京东|===?\s*3.*拼多多)', script_section)
        or re.search(r'(淘宝|京东|拼多多).*===?\s*[123]', script_section)
        or (re.search(r'v-if.*platform\s*===?\s*[123]', template_section)
            and sum(1 for l in ["淘宝", "京东", "拼多多"] if l in template_section) >= 2)
    )
    has_platform_map = bool(
        re.search(r'(platformName|platformLabel|platformColor|getPlatform|platformMap|PLATFORM)', script_section)
    )
    has_distinct_colors = bool(
        (re.search(r'(orange|#[fF]{2}[0-9a-fA-F]{4}|#[eE][0-9a-fA-F]{5})', script_section + style_section)
         and re.search(r'(red|#[eE][0-3]|#[cC][0-3])', script_section + style_section))
        or len(re.findall(r'(background|color)\s*:\s*[\'"]?(#[0-9a-fA-F]{3,8}|[a-z]+)', script_section)) >= 2
        or re.search(r'\{[^}]*(1|taobao)[^}]*(color|bg)[^}]*\}', script_section, re.DOTALL)
    )

    if (has_badge_element or has_platform_map) and has_platform_text and has_distinct_colors:
        components["platform_badge"] = 1.0
    elif has_platform_text and has_distinct_colors:
        components["platform_badge"] = 0.8
    elif has_platform_text or has_platform_map:
        components["platform_badge"] = 0.6
    elif has_badge_element:
        components["platform_badge"] = 0.3

    # --- EASY 4: Infinite Scroll (0.10) ---
    has_scroll_event = bool(
        re.search(r'(@scrolltolower|onReachBottom|@reach-bottom)', search_content, re.IGNORECASE)
        or re.search(r'scroll-view.*scrolltolower', template_section, re.IGNORECASE | re.DOTALL)
    )
    has_page_state = bool(
        re.search(r'(const|let|var)\s+page\s*=\s*ref', script_section)
        or re.search(r'page\s*:\s*ref\(', script_section)
    )
    has_page_increment = bool(
        re.search(r'page\s*(\+\+|\.value\s*\+\+|\.value\s*\+=\s*1|\s*\+=\s*1)', script_section)
    )
    has_more_check = bool(
        re.search(r'(hasMore|has_more|noMore|isEnd|finished)', script_section)
    )

    if has_scroll_event and has_page_increment and has_more_check:
        components["infinite_scroll"] = 1.0
    elif has_scroll_event and has_page_increment:
        components["infinite_scroll"] = 0.7
    elif has_scroll_event and has_page_state:
        components["infinite_scroll"] = 0.4

    # --- EASY 5: Merge Logic (0.10) ---
    has_all_branch = bool(
        re.search(r'(currentPlatform|activePlatform|selectedPlatform)\.?(value)?\s*===?\s*(0|\'all\'|"all")', script_section)
        or re.search(r'if\s*\(.*[pP]latform.*===?\s*0', script_section)
    )
    has_limit_per_platform = bool(
        re.search(r'\.slice\s*\(\s*0\s*,\s*3\s*\)', script_section)
        or re.search(r'size\s*:\s*3', script_section)
        or re.search(r'pageSize\s*:\s*3', script_section)
    )
    has_merge = bool(
        re.search(r'(\.\.\.|concat)\s*.*(?:result|list|goods|data)', script_section, re.DOTALL)
    )

    if has_all_branch and has_limit_per_platform and has_merge:
        components["merge_logic"] = 1.0
    elif has_all_branch and (has_limit_per_platform or has_merge):
        components["merge_logic"] = 0.6
    elif has_all_branch:
        components["merge_logic"] = 0.3

    # ===================================================================
    # HARD TIER — These checks require deeper understanding and careful
    # implementation. Only strong agents will satisfy them fully.
    # ===================================================================

    # --- HARD 1: Error Resilience Deep (0.12) ---
    # Requires BOTH: (a) using allSettled specifically (not Promise.all),
    # AND (b) properly filtering by status==='fulfilled' before accessing .value,
    # AND (c) handling rejected results (showing error or logging).
    # Weak agents use Promise.all (no partial failure) or allSettled without
    # checking .status before accessing .value.

    has_fulfilled_check = bool(
        re.search(r'(status\s*===?\s*[\'"]fulfilled[\'"]|\.status\s*===?\s*[\'"]fulfilled[\'"])', script_section)
    )
    has_rejected_handling = bool(
        re.search(r'(status\s*===?\s*[\'"]rejected[\'"]|\.reason)', script_section)
    )
    has_filter_fulfilled = bool(
        re.search(r'\.filter\(\s*\w+\s*=>\s*\w+\.status\s*===?\s*[\'"]fulfilled[\'"]', script_section)
        or re.search(r'for\s*\(.*of\s+\w+\)\s*\{[^}]*status\s*===?\s*[\'"]fulfilled', script_section, re.DOTALL)
        or re.search(r'forEach.*status\s*===?\s*[\'"]fulfilled', script_section, re.DOTALL)
    )
    # Penalty: blindly accesses .value on allSettled results without checking status
    has_blind_value_access = bool(
        re.search(r'allSettled.*?\n[^}]*\.\s*map\(\s*\w+\s*=>\s*\w+\.value', script_section, re.DOTALL)
        and not has_fulfilled_check
    )
    # Bonus: shows user which platforms failed
    has_failure_ui = bool(
        re.search(r'(failedPlatform|errorPlatform|platformError|失败|平台.*错误)', script_section + template_section)
    )

    if has_all_settled and has_fulfilled_check and has_filter_fulfilled and has_rejected_handling:
        components["error_resilience_deep"] = 1.0
    elif has_all_settled and has_fulfilled_check and has_filter_fulfilled:
        components["error_resilience_deep"] = 0.85
    elif has_all_settled and has_fulfilled_check:
        components["error_resilience_deep"] = 0.6
    elif has_all_settled and not has_blind_value_access:
        components["error_resilience_deep"] = 0.25
    elif has_promise_all and not has_all_settled:
        # Used Promise.all — zero resilience to partial failures
        components["error_resilience_deep"] = 0.0
    if has_failure_ui and components["error_resilience_deep"] >= 0.6:
        components["error_resilience_deep"] = min(components["error_resilience_deep"] + 0.1, 1.0)

    # --- HARD 2: State Machine Correctness (0.11) ---
    # When switching tabs, a strong agent must:
    # (a) Reset page to 1 AND clear the goods list AND reset hasMore
    # (b) Do this atomically in the tab-switch handler (not just anywhere)
    # (c) Immediately trigger a new search after reset
    # Weak agents forget to reset page or list, causing stale data bugs.

    has_page_reset = bool(
        re.search(r'(page\s*\.value\s*=\s*1|page\s*=\s*1)', script_section)
    )
    has_list_clear = bool(
        re.search(r'(goodsList|list|goods)\s*\.?(value)?\s*=\s*\[\s*\]', script_section)
    )
    has_more_reset = bool(
        re.search(r'(hasMore|noMore|finished|isEnd)\s*\.?(value)?\s*=\s*(true|false)', script_section)
    )
    # Reset must happen in same handler/watcher as platform change
    has_reset_in_switch = bool(
        re.search(
            r'(switchPlatform|changePlatform|onTabChange|selectPlatform|handleTab|handlePlatformChange)[^{]*\{[^}]*(page\s*\.?v?a?l?u?e?\s*=\s*1|=\s*\[\s*\])',
            script_section, re.DOTALL
        )
        or re.search(
            r'(currentPlatform|activePlatform)\s*\.?v?a?l?u?e?\s*=\s*[^;]*;[^}]*(page\s*\.?v?a?l?u?e?\s*=\s*1|=\s*\[\s*\])',
            script_section, re.DOTALL
        )
    )
    has_watch_reset = bool(
        re.search(r'watch\(\s*(currentPlatform|activePlatform|selectedPlatform)', script_section)
        and has_page_reset
    )
    # After resetting, must trigger search again
    has_search_after_reset = bool(
        re.search(
            r'(switchPlatform|changePlatform|onTabChange|selectPlatform|handleTab)[^}]*(handleSearch|doSearch|search\(|fetchGoods|loadGoods)',
            script_section, re.DOTALL
        )
        or (has_watch_reset and re.search(r'watch\([^)]*\)[^}]*(handleSearch|doSearch|search\(|fetchGoods)', script_section, re.DOTALL))
    )

    if (has_reset_in_switch or has_watch_reset) and has_page_reset and has_list_clear and has_more_reset and has_search_after_reset:
        components["state_machine_correctness"] = 1.0
    elif (has_reset_in_switch or has_watch_reset) and has_page_reset and has_list_clear and has_search_after_reset:
        components["state_machine_correctness"] = 0.8
    elif (has_reset_in_switch or has_watch_reset) and has_page_reset and has_list_clear:
        components["state_machine_correctness"] = 0.6
    elif has_page_reset and has_list_clear:
        # Reset exists but not properly tied to switch handler
        components["state_machine_correctness"] = 0.3
    elif has_page_reset or has_list_clear:
        components["state_machine_correctness"] = 0.15

    # --- HARD 3: Race Condition Guard (0.12) ---
    # A strong agent prevents race conditions:
    # (a) Loading guard: if (loading) return — prevents double-triggers
    # (b) Request cancellation or staleness check on tab switch
    #     (e.g., AbortController, or comparing request ID / platform at resolve time)
    # (c) Debounce on search input to prevent rapid-fire requests
    # Weak agents have no guards, leading to out-of-order responses.

    has_loading_guard = bool(
        re.search(r'if\s*\(\s*(loading|isLoading)\.?(value)?\s*\)\s*return', script_section)
    )
    has_abort_controller = bool(
        re.search(r'AbortController|abortController|controller\.abort', script_section)
    )
    has_staleness_check = bool(
        # Pattern: save platform/requestId before async, compare after await
        re.search(r'(const|let)\s+(current|saved|expected)(Platform|Request|Id)', script_section)
        or re.search(r'if\s*\(.*!==.*currentPlatform', script_section)
        or re.search(r'(requestId|searchId|fetchId)', script_section)
    )
    has_debounce = bool(
        re.search(r'(debounce|setTimeout.*search|clearTimeout.*timer|searchTimer)', script_section)
    )
    # Loading state set/unset pattern: loading = true ... finally { loading = false }
    has_loading_finally = bool(
        re.search(r'finally\s*\{[^}]*(loading|isLoading)\s*\.?(value)?\s*=\s*false', script_section, re.DOTALL)
    )
    # hasMore guard in loadMore to prevent loading when no more data
    has_more_guard = bool(
        re.search(r'if\s*\(\s*!(hasMore|has_more)\.?(value)?\s*\)\s*return', script_section)
        or re.search(r'if\s*\(\s*(noMore|isEnd|finished)\.?(value)?\s*\)\s*return', script_section)
    )

    race_score = 0.0
    if has_loading_guard:
        race_score += 0.30
    if has_abort_controller or has_staleness_check:
        race_score += 0.30
    if has_debounce:
        race_score += 0.15
    if has_loading_finally:
        race_score += 0.15
    if has_more_guard:
        race_score += 0.10
    components["race_condition_guard"] = min(race_score, 1.0)

    # --- HARD 4: Loading UX Advanced (0.11) ---
    # Beyond basic loading state, a strong agent implements:
    # (a) Separate loading states for initial load vs load-more (skeleton vs bottom spinner)
    # (b) Empty state with meaningful message
    # (c) Error retry mechanism
    # (d) Loading indicator in template that is conditionally rendered
    # Weak agents just have a boolean loading flag with no template usage.

    has_loading_state = bool(
        re.search(r'(const|let|var)\s+(loading|isLoading)\s*=\s*ref', script_section)
    )
    has_separate_loading = bool(
        re.search(r'(loadingMore|isLoadMore|refreshing|loadMoreLoading)', script_section)
    )
    has_empty_state = bool(
        re.search(r'(v-if|v-show).*?(goodsList|list|goods).*?(length\s*===?\s*0|\.length\s*<\s*1|!.*?\.length)', template_section)
        or re.search(r'(暂无|没有|无结果|empty|no.?result)', template_section, re.IGNORECASE)
    )
    has_loading_in_template = bool(
        re.search(r'(v-if|v-show).*?(loading|isLoading)', template_section)
        or re.search(r'(加载中|loading|spinner|uni-load-more)', template_section, re.IGNORECASE)
    )
    has_error_retry = bool(
        re.search(r'(retry|重试|重新加载|reload)', script_section + template_section, re.IGNORECASE)
    )
    has_skeleton = bool(
        re.search(r'(skeleton|骨架)', script_section + template_section, re.IGNORECASE)
        or re.search(r'class=.*placeholder', template_section, re.IGNORECASE)
    )
    # Bottom loading indicator specifically for load-more
    has_bottom_loading = bool(
        re.search(r'(加载更多|loadMore|load-more|没有更多|no.more|到底了)', template_section, re.IGNORECASE)
    )

    ux_score = 0.0
    if has_loading_state and has_loading_in_template:
        ux_score += 0.20
    if has_separate_loading:
        ux_score += 0.25
    if has_empty_state:
        ux_score += 0.20
    if has_error_retry:
        ux_score += 0.15
    if has_skeleton or has_bottom_loading:
        ux_score += 0.10
    if has_loading_state and not has_loading_in_template:
        # Declared loading but never used it in template — weak pattern
        ux_score += 0.05
    components["loading_ux_advanced"] = min(ux_score, 1.0)

    # ===================================================================
    # Score calculation
    # ===================================================================
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "tier_info": {
            "easy_weight": 0.54,
            "hard_weight": 0.46,
            "hidden_pct": "46%",
        },
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
