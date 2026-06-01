"""Hidden verifier for CP125 — Bootstrap Icons Emoji Replacement."""
from __future__ import annotations

import json
import re
from pathlib import Path


# Emoji patterns that should be replaced
NAVBAR_EMOJIS = ["📖", "📊", "⚙️", "🔧", "🔑", "🚪", "🔬"]
PAGE_EMOJIS = ["📅", "➕", "📥", "🔄", "🗑️", "📈", "👤", "🏆", "💡", "ℹ️"]
ALL_EMOJIS = NAVBAR_EMOJIS + PAGE_EMOJIS

# Bootstrap Icons class pattern
BI_PATTERN = re.compile(r'class="[^"]*\bbi\s+bi-[a-z0-9-]+[^"]*"', re.IGNORECASE)

# CDN link pattern for Bootstrap Icons
CDN_PATTERN = re.compile(
    r'<link[^>]+href="[^"]*bootstrap-icons[^"]*\.css[^"]*"[^>]*>',
    re.IGNORECASE,
)

# Static/local link pattern for Bootstrap Icons (offline version)
STATIC_PATTERN = re.compile(
    r'<link[^>]+(?:href="[^"]*bootstrap-icons[^"]*\.css[^"]*"|href="\{%\s*static\s+[\'"]css/bootstrap-icons[^"]*[\'"])',
    re.IGNORECASE,
)

# Semantic mapping: emoji -> acceptable Bootstrap Icon class names
SEMANTIC_MAP = {
    "📖": ["bi-book", "bi-book-fill", "bi-journal", "bi-journal-text"],
    "📊": ["bi-bar-chart", "bi-bar-chart-fill", "bi-graph-up", "bi-graph-up-arrow"],
    "⚙️": ["bi-gear", "bi-gear-fill", "bi-gears", "bi-sliders"],
    "🔧": ["bi-wrench", "bi-wrench-adjustable", "bi-tools", "bi-wrench-adjustable-circle"],
    "🔑": ["bi-key", "bi-key-fill", "bi-lock", "bi-unlock"],
    "🚪": ["bi-door-open", "bi-door-open-fill", "bi-door-closed", "bi-box-arrow-right", "bi-box-arrow-left"],
    "🔬": ["bi-eyedropper", "bi-flask", "bi-microscope", "bi-search"],
    "📅": ["bi-calendar", "bi-calendar-fill", "bi-calendar-event", "bi-calendar-week", "bi-calendar3", "bi-calendar2"],
    "➕": ["bi-plus-circle", "bi-plus-circle-fill", "bi-plus", "bi-plus-lg", "bi-plus-square"],
    "📥": ["bi-download", "bi-box-arrow-in-down", "bi-cloud-download", "bi-inbox"],
    "🔄": ["bi-arrow-clockwise", "bi-arrow-repeat", "bi-arrow-counterclockwise", "bi-recycle"],
    "🗑️": ["bi-trash", "bi-trash-fill", "bi-trash3", "bi-trash3-fill", "bi-x-circle"],
    "📈": ["bi-graph-up", "bi-graph-up-arrow", "bi-trending-up", "bi-arrow-up-right"],
    "👤": ["bi-person", "bi-person-fill", "bi-person-circle"],
    "🏆": ["bi-trophy", "bi-trophy-fill", "bi-award", "bi-star"],
    "💡": ["bi-lightbulb", "bi-lightbulb-fill", "bi-lamp", "bi-lamp-fill"],
    "ℹ️": ["bi-info-circle", "bi-info-circle-fill", "bi-info", "bi-info-lg"],
}


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _count_emojis_in_file(content: str) -> int:
    """Count remaining emojis from the known set."""
    count = 0
    for emoji in ALL_EMOJIS:
        count += content.count(emoji)
    return count


def _count_bi_icons(content: str) -> int:
    """Count Bootstrap Icon usages."""
    return len(BI_PATTERN.findall(content))


def _extract_bi_classes(content: str) -> list[str]:
    """Extract all bi-xxx class names used in content."""
    return re.findall(r'\bbi-([a-z0-9-]+)', content)


def _check_semantic_accuracy(all_content: str, templates_dir: Path) -> float:
    """Check that icon choices are semantically appropriate for the emojis replaced.

    We look at each template's expected icon locations and verify that the
    replacement icon class is from the accepted semantic list.
    """
    base_html = _read(templates_dir / "base.html")
    index_html = _read(templates_dir / "index.html")
    stats_html = _read(templates_dir / "stats.html")

    # For each location, check if a semantically correct icon was used
    checks_passed = 0
    checks_total = 0

    # Check navbar icons in base.html — each nav-link should have a
    # semantically appropriate icon
    nav_link_pattern = re.compile(
        r'<a[^>]*class="nav-link"[^>]*title="([^"]*)"[^>]*>([^<]*(?:<[^>]+>[^<]*)*)</a>',
        re.DOTALL,
    )
    title_to_emoji = {
        "使用说明": "📖",
        "统计面板": "📊",
        "系统设置": "⚙️",
        "管理后台": "🔧",
        "登录": "🔑",
        "退出": "🚪",
    }

    for match in nav_link_pattern.finditer(base_html):
        title = match.group(1)
        inner = match.group(2)
        if title in title_to_emoji:
            emoji_key = title_to_emoji[title]
            checks_total += 1
            if emoji_key in SEMANTIC_MAP:
                accepted = SEMANTIC_MAP[emoji_key]
                for cls in accepted:
                    icon_name = cls.replace("bi-", "")
                    if f"bi-{icon_name}" in inner:
                        checks_passed += 1
                        break

    # Check stat cards in stats.html
    stat_emojis = ["📈", "👤", "🏆"]
    for emoji in stat_emojis:
        checks_total += 1
        if emoji not in stats_html:
            # Emoji was replaced, check if an appropriate icon is present
            accepted = SEMANTIC_MAP.get(emoji, [])
            for cls in accepted:
                icon_name = cls.replace("bi-", "")
                if f"bi-{icon_name}" in stats_html:
                    checks_passed += 1
                    break

    # Check index.html icons
    index_emojis = ["📅", "➕", "📥", "🔄", "🗑️"]
    for emoji in index_emojis:
        checks_total += 1
        if emoji not in index_html:
            accepted = SEMANTIC_MAP.get(emoji, [])
            for cls in accepted:
                icon_name = cls.replace("bi-", "")
                if f"bi-{icon_name}" in index_html:
                    checks_passed += 1
                    break

    if checks_total == 0:
        return 0.0
    return round(checks_passed / checks_total, 4)


def _check_svg_chevron_replacement(index_html: str, readme_html: str) -> float:
    """Check that SVG chevron icons are replaced with bi-chevron-left/right."""
    score = 0.0
    total_checks = 0

    # index.html had SVG chevrons for prev/next buttons
    # Check that SVG is gone and bi-chevron is present
    has_svg_chevron = bool(re.search(r'<svg[^>]*>.*?<path[^>]*d="[^"]*[Ll]\d', index_html, re.DOTALL))
    has_bi_chevron_left = "bi-chevron-left" in index_html
    has_bi_chevron_right = "bi-chevron-right" in index_html

    total_checks += 2  # left and right

    if has_bi_chevron_left and not has_svg_chevron:
        score += 1.0
    elif has_bi_chevron_left:
        score += 0.5  # replaced but didn't remove SVG

    if has_bi_chevron_right and not has_svg_chevron:
        score += 1.0
    elif has_bi_chevron_right:
        score += 0.5

    # readme.html had a back button with SVG chevron
    has_svg_readme = bool(re.search(r'<svg[^>]*>.*?<path', readme_html, re.DOTALL))
    has_bi_chevron_back = "bi-chevron-left" in readme_html or "bi-arrow-left" in readme_html

    total_checks += 1
    if has_bi_chevron_back and not has_svg_readme:
        score += 1.0
    elif has_bi_chevron_back:
        score += 0.5

    return round(score / total_checks, 4) if total_checks > 0 else 0.0


def _check_accessibility(all_content: str) -> float:
    """Check that icon elements have proper accessibility attributes.

    Decorative icons (in navlinks, buttons) should have aria-hidden="true"
    or the parent should have an aria-label, so screen readers skip the icon.
    """
    # Find all <i> tags with bi classes
    icon_tags = re.findall(r'<i\s[^>]*class="[^"]*\bbi\s+bi-[^"]*"[^>]*>', all_content)
    if not icon_tags:
        return 0.0

    accessible_count = 0
    for tag in icon_tags:
        # Check if aria-hidden is present on the icon itself
        if 'aria-hidden' in tag:
            accessible_count += 1
        elif 'role="img"' in tag and 'aria-label' in tag:
            accessible_count += 1

    # We expect at least some icons to have aria-hidden for a good score
    ratio = accessible_count / len(icon_tags)
    # Strong models add aria-hidden to all decorative icons
    return round(ratio, 4)


def _check_offline_no_cdn(base_offline: str) -> float:
    """Check that the offline template does NOT use CDN links (should be local only)."""
    cdn_present = bool(re.search(r'https?://cdn', base_offline, re.IGNORECASE))
    static_present = bool(re.search(r'\{%\s*static\s+', base_offline))

    if static_present and not cdn_present:
        return 1.0
    elif static_present and cdn_present:
        # Used static for icons but CDN might still be there for Bootstrap main
        # Check specifically if Bootstrap Icons CSS is via static
        icons_via_static = bool(re.search(
            r'\{%\s*static\s+[\'"][^"]*bootstrap-icons',
            base_offline,
        ))
        icons_via_cdn = bool(re.search(
            r'https?://[^"]*bootstrap-icons[^"]*\.css',
            base_offline,
        ))
        if icons_via_static and not icons_via_cdn:
            return 1.0
        elif icons_via_static and icons_via_cdn:
            return 0.4  # Redundant import
        else:
            return 0.3
    elif cdn_present:
        return 0.2  # Offline template shouldn't use CDN for icons
    else:
        return 0.0


def _check_cdn_version_pinned(base_html: str) -> float:
    """Check that the CDN link uses a specific pinned version, not 'latest' or bare."""
    # Good: bootstrap-icons@1.11.3 or bootstrap-icons@1.13.1
    # Bad: bootstrap-icons/font/ (no version) or bootstrap-icons@latest
    versioned = re.search(
        r'bootstrap-icons@\d+\.\d+\.\d+',
        base_html,
    )
    if versioned:
        return 1.0

    # Has a version but not semver pinned (e.g., @1 or @1.11)
    partial_version = re.search(r'bootstrap-icons@\d+', base_html)
    if partial_version:
        return 0.6

    # Uses CDN but without version pinning
    if 'bootstrap-icons' in base_html and 'cdn' in base_html.lower():
        return 0.3

    return 0.0


def _check_brand_emoji_replaced(base_html: str, base_offline: str) -> float:
    """Check that the navbar-brand emoji (🔬) is also replaced with a bi- icon.

    The prompt says '全站模板里的 emoji 图标统一替换'. Strong models catch the brand
    icon too, not just the nav-link icons. Weak models focus only on the obvious
    nav-link emojis.
    """
    score = 0.0
    total = 2  # base.html and base.offline.html

    for content in [base_html, base_offline]:
        # Check the navbar-brand element specifically
        brand_match = re.search(
            r'<a[^>]*class="navbar-brand"[^>]*>(.*?)</a>', content, re.DOTALL
        )
        if brand_match:
            brand_inner = brand_match.group(1)
            has_emoji = "🔬" in brand_inner
            has_bi_icon = bool(re.search(r'bi-[a-z]', brand_inner))
            if not has_emoji and has_bi_icon:
                score += 1.0
            elif not has_emoji:
                # Emoji removed but no icon replacement (just text)
                score += 0.3
        else:
            # Brand element structure changed significantly — partial credit
            if "🔬" not in content:
                score += 0.5

    return round(score / total, 4)


def _check_footer_emoji_replaced(base_html: str, base_offline: str) -> float:
    """Check that the footer emoji (💡) is replaced with a bi- icon.

    The footer contains '💡 提示：...' which is easy to overlook. Strong models
    do a thorough scan and catch emojis everywhere, including footer text.
    """
    score = 0.0
    total = 2  # base.html and base.offline.html

    for content in [base_html, base_offline]:
        footer_match = re.search(r'<footer[^>]*>(.*?)</footer>', content, re.DOTALL)
        if footer_match:
            footer_inner = footer_match.group(1)
            has_emoji = "💡" in footer_inner
            has_bi_icon = bool(re.search(r'bi-lightbulb|bi-lamp|bi-info', footer_inner))
            if not has_emoji and has_bi_icon:
                score += 1.0
            elif not has_emoji:
                # Emoji removed but no icon added
                score += 0.4
        else:
            # No footer found, check whole content
            if "💡" not in content:
                score += 0.5

    return round(score / total, 4)


def _check_icon_tag_structure(all_content: str) -> float:
    """Check that icon tags follow best practices for icon font usage.

    Strong models produce clean icon markup:
    - <i class="bi bi-xxx"></i> with empty content (no text inside icon tag)
    - Icon tags not wrapping other elements
    - Proper separation between icon and adjacent text (space or wrapper)

    Weak models often produce malformed patterns like:
    - <i class="bi bi-xxx">some text</i>  (text inside icon tag)
    - Missing closing </i> or self-closing <i ... />
    - Icon class on non-standard elements
    """
    # Find all icon tags
    icon_tags = re.findall(
        r'<i\s[^>]*class="[^"]*\bbi\s+bi-[^"]*"[^>]*>(.*?)</i>',
        all_content,
        re.DOTALL,
    )

    if not icon_tags:
        return 0.0

    clean_count = 0
    for inner in icon_tags:
        inner_stripped = inner.strip()
        # Best practice: icon font <i> tags should be empty
        if inner_stripped == "":
            clean_count += 1
        # Also acceptable: only whitespace
        elif inner_stripped.isspace():
            clean_count += 0.8

    ratio = clean_count / len(icon_tags)

    # Also penalize self-closing <i .../> which is invalid for icon fonts
    self_closing = len(re.findall(r'<i\s[^>]*class="[^"]*bi[^"]*"[^>]*/>', all_content))
    if self_closing > 0:
        ratio *= 0.5

    return round(min(ratio, 1.0), 4)


def grade_workspace(ws: Path) -> dict:
    components = {k: 0.0 for k in [
        "icons_css_imported_base",
        "icons_css_imported_offline",
        "navbar_emojis_replaced",
        "page_emojis_replaced",
        "bi_classes_used_correctly",
        "no_broken_html",
        "consistent_icon_style",
        "semantic_accuracy",
        "svg_chevron_replaced",
        "accessibility_attrs",
        "offline_no_cdn",
        "cdn_version_pinned",
        "brand_emoji_replaced",
        "footer_emoji_replaced",
        "icon_tag_structure",
    ]}

    # Possible locations for templates
    templates_dir = None
    for candidate in [
        ws / "lab_booking" / "core" / "templates" / "core",
        ws / "fixtures" / "lab_booking" / "core" / "templates" / "core",
    ]:
        if candidate.exists():
            templates_dir = candidate
            break

    if not templates_dir:
        return {
            "overall_score": 0.0,
            "components": components,
            "error": "templates directory not found",
        }

    base_html = _read(templates_dir / "base.html")
    base_offline = _read(templates_dir / "base.offline.html")
    index_html = _read(templates_dir / "index.html")
    stats_html = _read(templates_dir / "stats.html")
    readme_html = _read(templates_dir / "readme.html")

    all_content = base_html + base_offline + index_html + stats_html + readme_html

    # 1. Check Bootstrap Icons CSS imported in base.html (CDN for online)
    if CDN_PATTERN.search(base_html):
        components["icons_css_imported_base"] = 1.0
    elif BI_PATTERN.search(base_html):
        components["icons_css_imported_base"] = 0.5

    # 2. Check Bootstrap Icons CSS imported in offline version (local static)
    if STATIC_PATTERN.search(base_offline) or CDN_PATTERN.search(base_offline):
        components["icons_css_imported_offline"] = 1.0
    elif "bootstrap-icons" in base_offline.lower():
        components["icons_css_imported_offline"] = 0.7

    # 3. Navbar emojis replaced
    navbar_remaining = 0
    for emoji in NAVBAR_EMOJIS:
        if emoji in base_html or emoji in base_offline:
            navbar_remaining += 1
    navbar_total = len(NAVBAR_EMOJIS)
    replaced_ratio = 1.0 - (navbar_remaining / navbar_total)
    components["navbar_emojis_replaced"] = round(replaced_ratio, 4)

    # 4. Page emojis replaced (across index, stats, readme)
    page_remaining = 0
    page_content = index_html + stats_html + readme_html
    for emoji in PAGE_EMOJIS:
        if emoji in page_content:
            page_remaining += 1
    page_total = len(PAGE_EMOJIS)
    page_replaced_ratio = 1.0 - (page_remaining / page_total)
    components["page_emojis_replaced"] = round(page_replaced_ratio, 4)

    # 5. Bootstrap Icon classes used correctly (bi bi-xxx pattern)
    bi_count = _count_bi_icons(all_content)
    expected_min = 10
    components["bi_classes_used_correctly"] = round(
        min(1.0, bi_count / expected_min), 4
    )

    # 6. No broken HTML (basic check: all <i> or <span> with bi class are closed)
    broken_pattern = re.compile(r'<i\s[^>]*class="[^"]*bi[^"]*"[^>]*>[^<]*$', re.MULTILINE)
    unclosed = len(broken_pattern.findall(all_content))
    open_tags = all_content.count("<i ")
    close_tags = all_content.count("</i>")
    tag_balance = abs(open_tags - close_tags)
    if tag_balance <= 1 and unclosed == 0:
        components["no_broken_html"] = 1.0
    elif tag_balance <= 3:
        components["no_broken_html"] = 0.7
    else:
        components["no_broken_html"] = 0.3

    # 7. Consistent icon style (all icons use same pattern, not mixing approaches)
    uses_i_tag = bool(re.search(r'<i\s+class="bi\s+bi-', all_content))
    uses_span_tag = bool(re.search(r'<span\s+class="bi\s+bi-', all_content))
    remaining_emojis = _count_emojis_in_file(all_content)

    if uses_i_tag and not uses_span_tag and remaining_emojis <= 2:
        components["consistent_icon_style"] = 1.0
    elif (uses_i_tag or uses_span_tag) and remaining_emojis <= 4:
        components["consistent_icon_style"] = 0.7
    elif remaining_emojis <= 6:
        components["consistent_icon_style"] = 0.4
    else:
        components["consistent_icon_style"] = 0.1

    # === HIDDEN CHECKS (harder, differentiate strong from weak models) ===

    # 8. Semantic accuracy — are the chosen icons semantically correct?
    components["semantic_accuracy"] = _check_semantic_accuracy(
        all_content, templates_dir
    )

    # 9. SVG chevron replacement — task explicitly requires this
    components["svg_chevron_replaced"] = _check_svg_chevron_replacement(
        index_html, readme_html
    )

    # 10. Accessibility — aria-hidden on decorative icons
    components["accessibility_attrs"] = _check_accessibility(all_content)

    # 11. Offline template should NOT use CDN
    components["offline_no_cdn"] = _check_offline_no_cdn(base_offline)

    # 12. CDN version should be pinned to a specific version
    components["cdn_version_pinned"] = _check_cdn_version_pinned(base_html)

    # 13. Brand emoji (🔬) in navbar-brand should also be replaced
    components["brand_emoji_replaced"] = _check_brand_emoji_replaced(
        base_html, base_offline
    )

    # 14. Footer emoji (💡) should be replaced too
    components["footer_emoji_replaced"] = _check_footer_emoji_replaced(
        base_html, base_offline
    )

    # 15. Icon tag structure — proper empty <i></i> pattern
    components["icon_tag_structure"] = _check_icon_tag_structure(all_content)

    # Weights: reduce easy checks, add weight to hidden harder checks
    weights = {
        "icons_css_imported_base": 0.05,
        "icons_css_imported_offline": 0.05,
        "navbar_emojis_replaced": 0.07,
        "page_emojis_replaced": 0.06,
        "bi_classes_used_correctly": 0.03,
        "no_broken_html": 0.04,
        "consistent_icon_style": 0.05,
        # Hidden harder checks (total 0.65)
        "semantic_accuracy": 0.12,
        "svg_chevron_replaced": 0.10,
        "accessibility_attrs": 0.15,
        "offline_no_cdn": 0.04,
        "cdn_version_pinned": 0.05,
        "brand_emoji_replaced": 0.08,
        "footer_emoji_replaced": 0.06,
        "icon_tag_structure": 0.05,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    # Try fixtures subpath first, then root
    result = grade_workspace(ws / "fixtures")
    if result.get("error"):
        result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
