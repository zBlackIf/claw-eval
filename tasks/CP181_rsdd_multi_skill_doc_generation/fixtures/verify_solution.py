"""Hidden verifier for CP181 — RSDD Multi-Skill Document Generation."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_chapter(content: str, chapter_num: int) -> str:
    """Extract content belonging to a specific chapter (between its heading and next chapter heading)."""
    # Match headings like ## 1. or # 1. or ## 1
    pattern = rf"(^|\n)(##?\s*{chapter_num}[\.\s])"
    next_pattern = rf"(^|\n)(##?\s*{chapter_num + 1}[\.\s])"

    start_match = re.search(pattern, content)
    if not start_match:
        return ""
    start_pos = start_match.start()

    if chapter_num < 5:
        end_match = re.search(next_pattern, content)
        end_pos = end_match.start() if end_match else len(content)
    else:
        end_pos = len(content)

    return content[start_pos:end_pos]


def _check_chapter_structure(content: str) -> dict:
    """Check that all 5 chapters exist with proper heading structure."""
    chapters = {
        "ch1_requirements": 0.0,
        "ch2_environment": 0.0,
        "ch3_scenarios": 0.0,
        "ch4_architecture": 0.0,
        "ch5_interfaces": 0.0,
    }

    ch1_content = _extract_chapter(content, 1)

    # Chapter 1: Requirements - must contain VoC content from voc.md
    ch1_patterns = [
        r"##?\s*1[\.\s].*[Rr]equirement",
        r"VoC|Voice of Customer|原始",
        r"WANT-20250301|WANT.*20250301",
    ]
    ch1_score = sum(1 for p in ch1_patterns if re.search(p, ch1_content or content)) / len(ch1_patterns)
    # Must contain verbatim content from voc.md
    verbatim_markers = [
        "API Gateway Rate Limiting Enhancement",
        "per-tenant rate limiting",
        "MegaCorp",
        "noisy-neighbor",
    ]
    verbatim_score = sum(1 for m in verbatim_markers if m in (ch1_content or content)) / len(verbatim_markers)
    chapters["ch1_requirements"] = round(ch1_score * 0.4 + verbatim_score * 0.6, 4)

    ch2_content = _extract_chapter(content, 2)

    # Chapter 2: Environment - must have topology and environment factors
    ch2_patterns = [
        r"##?\s*2[\.\s].*[Ee]nvironment",
        r"[Tt]opology|[Nn]etwork.*[Tt]opology",
        r"[Kk]ubernetes|[Cc]loud.native|[Mm]icroservice",
        r"[Rr]edis",
        r"\|.*[Ff]actor.*\||\|.*[Dd]eployment.*\||\|.*[Pp]latform.*\|",
    ]
    chapters["ch2_environment"] = round(
        sum(1 for p in ch2_patterns if re.search(p, ch2_content or content)) / len(ch2_patterns), 4
    )

    ch3_content = _extract_chapter(content, 3)

    # Chapter 3: Scenarios - must have scenario inventory with IDs and assessment
    ch3_patterns = [
        r"##?\s*3[\.\s].*[Ss]cenario",
        r"S\d+|[Ss]cenario.?\d+",
        r"[Vv]alue.*[Aa]ssess|[Bb]usiness.*[Vv]alue|H/M/L|High|Medium|Low",
        r"[Cc]omplexity",
        r"\|.*\|.*\|",  # table format
    ]
    chapters["ch3_scenarios"] = round(
        sum(1 for p in ch3_patterns if re.search(p, ch3_content or content)) / len(ch3_patterns), 4
    )

    ch4_content = _extract_chapter(content, 4)

    # Chapter 4: Architecture - must have system diagram and component list
    ch4_patterns = [
        r"##?\s*4[\.\s].*[Aa]rchitect",
        r"API\s*Gateway|[Gg]ateway",
        r"[Cc]omponent|[Mm]odule|[Ss]ystem",
        r"```|\+[-+]+\+|[\[\(].*[\]\)].*[-=]",  # diagram markers
        r"\|.*\|.*\|",  # table
    ]
    chapters["ch4_architecture"] = round(
        sum(1 for p in ch4_patterns if re.search(p, ch4_content or content)) / len(ch4_patterns), 4
    )

    ch5_content = _extract_chapter(content, 5)

    # Chapter 5: Interfaces - must have protocol spec and interface list
    ch5_patterns = [
        r"##?\s*5[\.\s].*[Ii]nterface",
        r"REST|[Gg]RPC|HTTP|API\s*[Ss]tyle",
        r"IF-\d+|[Ii]nterface.?\d+",
        r"GET|POST|PUT|DELETE|PATCH",
        r"[Mm]etrics|[Qq]uota|[Rr]ate.?[Ll]imit",
        r"/api/|endpoint|path",
    ]
    chapters["ch5_interfaces"] = round(
        sum(1 for p in ch5_patterns if re.search(p, ch5_content or content)) / len(ch5_patterns), 4
    )

    return chapters


def _check_skill_compliance(content: str) -> float:
    """Check that the document follows skill template structure."""
    compliance_points = 0.0
    total_points = 6

    # 1. Document title present
    if re.search(r"#\s+RSDD|#\s+.*[Ss]olution.*[Dd]esign", content):
        compliance_points += 1

    # 2. Uses proper markdown heading hierarchy (## for chapters, ### for sections)
    if re.search(r"^##\s", content, re.MULTILINE) and re.search(r"^###\s", content, re.MULTILINE):
        compliance_points += 1

    # 3. Contains tables (as required by templates)
    table_count = len(re.findall(r"^\|.*\|.*\|", content, re.MULTILINE))
    if table_count >= 3:
        compliance_points += 1

    # 4. Chapters are in correct order (1 before 2 before 3 before 4 before 5)
    positions = []
    for i in range(1, 6):
        match = re.search(rf"##?\s*{i}[\.\s]", content)
        if match:
            positions.append(match.start())
    if len(positions) >= 4 and positions == sorted(positions):
        compliance_points += 1

    # 5. No template placeholders left unfilled (<!-- ... -->)
    placeholder_count = len(re.findall(r"<!--.*?-->", content))
    if placeholder_count == 0:
        compliance_points += 1
    elif placeholder_count <= 2:
        compliance_points += 0.5

    # 6. Content is substantial (not just headers)
    word_count = len(content.split())
    if word_count >= 500:
        compliance_points += 1
    elif word_count >= 300:
        compliance_points += 0.5

    return round(compliance_points / total_points, 4)


def _check_domain_accuracy(content: str) -> float:
    """Check that generated content is technically accurate to the domain."""
    accuracy_points = 0.0
    total_points = 8

    # Must mention token bucket algorithm (from requirement)
    if re.search(r"[Tt]oken.?[Bb]ucket", content):
        accuracy_points += 1

    # Must mention the 3 tiers correctly
    tiers_found = 0
    if re.search(r"100\s*req/s|Basic.*100", content):
        tiers_found += 1
    if re.search(r"1000\s*req/s|Pro.*1000", content):
        tiers_found += 1
    if re.search(r"10000\s*req/s|Enterprise.*10000", content):
        tiers_found += 1
    accuracy_points += min(tiers_found / 3, 1.0)

    # Must mention burst handling (2x for 30s)
    if re.search(r"[Bb]urst.*2x|2x.*[Bb]urst|burst.*30\s*s", content):
        accuracy_points += 1

    # Must mention Redis for distributed counters
    if re.search(r"[Rr]edis.*counter|[Rr]edis.*distribut|distribut.*[Rr]edis", content):
        accuracy_points += 1

    # Must mention metrics/Prometheus
    if re.search(r"[Pp]rometheus|metrics.*endpoint|exposition.*format", content):
        accuracy_points += 1

    # Must mention zero-downtime migration
    if re.search(r"[Zz]ero.?down|[Mm]igrat|[Bb]ackward.*compat", content):
        accuracy_points += 1

    # Must mention latency requirements (< 1ms)
    if re.search(r"<?\s*1\s*ms|sub.?millisecond|latency.*1ms", content):
        accuracy_points += 1

    # Must mention webhook/alert for threshold
    if re.search(r"[Ww]ebhook|[Aa]lert.*threshold|80%.*quota|threshold.*alert", content):
        accuracy_points += 1

    return round(accuracy_points / total_points, 4)


def _check_template_subsection_fidelity(content: str) -> float:
    """HIDDEN CHECK: Verify strict adherence to template subsection structure.

    Each skill template defines exact subsections (e.g., 3.1, 3.2, 3.3, 3.4).
    A strong agent follows the template numbering precisely rather than inventing
    its own structure.
    """
    score = 0.0
    total = 10.0

    # Ch2 must have subsections 2.1 Network Topology AND 2.2 Key Environment Factors
    ch2_content = _extract_chapter(content, 2)
    if re.search(r"###?\s*2\.1\b.*[Tt]opology|###?\s*2\.1\b.*[Nn]etwork", ch2_content):
        score += 1
    if re.search(r"###?\s*2\.2\b.*[Ff]actor|###?\s*2\.2\b.*[Ee]nvironment", ch2_content):
        score += 1

    # Ch3 must have ALL four subsections: 3.1 Inventory, 3.2 Value, 3.3 Complexity, 3.4 Similar
    ch3_content = _extract_chapter(content, 3)
    if re.search(r"###?\s*3\.1\b.*[Ii]nventory|###?\s*3\.1\b.*[Ss]cenario", ch3_content):
        score += 1
    if re.search(r"###?\s*3\.2\b.*[Vv]alue", ch3_content):
        score += 1
    if re.search(r"###?\s*3\.3\b.*[Cc]omplexity", ch3_content):
        score += 1
    if re.search(r"###?\s*3\.4\b.*[Ss]imilar", ch3_content):
        score += 1

    # Ch4 must have 4.1, 4.2, 4.3
    ch4_content = _extract_chapter(content, 4)
    if re.search(r"###?\s*4\.1\b.*[Aa]rchitect|###?\s*4\.1\b.*[Ss]ystem", ch4_content):
        score += 1
    if re.search(r"###?\s*4\.2\b.*[Aa]pplicable|###?\s*4\.2\b.*[Ss]ystem", ch4_content):
        score += 1

    # Ch5 must have 5.1 Protocol AND 5.2 Interface List
    ch5_content = _extract_chapter(content, 5)
    if re.search(r"###?\s*5\.1\b.*[Pp]rotocol", ch5_content):
        score += 1
    if re.search(r"###?\s*5\.2\b.*[Ii]nterface.*[Ll]ist|###?\s*5\.2\b.*[Ll]ist", ch5_content):
        score += 1

    return round(score / total, 4)


def _check_interface_detail_blocks(content: str) -> float:
    """HIDDEN CHECK: Verify that interface chapter has proper detail blocks.

    Per template, each interface must have:
    - ID (IF-XX format)
    - Method + Path in table
    - Detail block showing Request/Response structure

    Weak models list interfaces in a table but omit the detail blocks.
    """
    ch5_content = _extract_chapter(content, 5)
    if not ch5_content:
        return 0.0

    score = 0.0
    total = 5.0

    # Count IF-XX style interface IDs
    if_ids = re.findall(r"IF-\d+", ch5_content)
    unique_ifs = set(if_ids)

    # Must have at least 4 distinct interfaces (rate-limit CRUD + metrics + webhook + quota)
    if len(unique_ifs) >= 6:
        score += 1.0
    elif len(unique_ifs) >= 4:
        score += 0.5

    # Must have detail blocks with Request/Response for interfaces
    detail_blocks = re.findall(
        r"(IF-\d+).*?[Dd]etail.*?[Rr]equest.*?[Rr]esponse",
        ch5_content, re.DOTALL
    )
    # Alternative: look for Request: { ... } / Response: { ... } pattern
    req_resp_blocks = re.findall(
        r"[Rr]equest\s*[:：]\s*[`{].*?[Rr]esponse\s*[:：]\s*[`{]",
        ch5_content, re.DOTALL
    )
    detail_count = max(len(detail_blocks), len(req_resp_blocks))
    if detail_count >= 4:
        score += 1.5
    elif detail_count >= 2:
        score += 0.75
    elif detail_count >= 1:
        score += 0.25

    # Must have error codes specified per interface (template shows 400/404/500)
    error_code_mentions = re.findall(r"[Ee]rror\s*[Cc]ode|4\d{2}|5\d{2}", ch5_content)
    if len(error_code_mentions) >= 6:
        score += 1.0
    elif len(error_code_mentions) >= 3:
        score += 0.5

    # Interfaces must be grouped by module (template shows #### Module headings)
    module_headings = re.findall(r"^#{3,4}\s+.*(Module|[Rr]ate|[Mm]etric|[Qq]uota|[Ww]ebhook|[Mm]anage)", ch5_content, re.MULTILINE)
    if len(module_headings) >= 3:
        score += 1.0
    elif len(module_headings) >= 2:
        score += 0.5

    # Must specify authentication method in 5.1 protocol table
    if re.search(r"[Aa]uthenticat|OAuth|[Tt]oken|mTLS|[Bb]earer|API.?[Kk]ey", ch5_content):
        score += 0.5

    return round(score / total, 4)


def _check_cross_chapter_consistency(content: str) -> float:
    """HIDDEN CHECK: Verify that chapters reference each other consistently.

    A well-structured RSDD has traceability:
    - Ch3 scenarios should trace back to Ch1 requirements
    - Ch4 components should correspond to Ch2 topology systems
    - Ch5 interfaces should cover all Ch3 scenarios

    Weak models generate chapters independently without cross-references.
    """
    score = 0.0
    total = 5.0

    ch3_content = _extract_chapter(content, 3)
    ch4_content = _extract_chapter(content, 4)
    ch5_content = _extract_chapter(content, 5)

    # 1. Ch3 scenarios must cover the 4 core functional areas from requirements:
    #    per-tenant limiting, burst handling, metrics reporting, quota management
    scenario_areas = 0
    if re.search(r"[Pp]er.?tenant.*limit|[Tt]enant.*rate", ch3_content):
        scenario_areas += 1
    if re.search(r"[Bb]urst.*handl|[Bb]urst.*detect|[Bb]urst.*allow", ch3_content):
        scenario_areas += 1
    if re.search(r"[Mm]etrics.*report|[Uu]sage.*metric|[Mm]etrics.*expos", ch3_content):
        scenario_areas += 1
    if re.search(r"[Qq]uota.*manag|[Cc]onfigur.*quota|[Tt]ier.*manag", ch3_content):
        scenario_areas += 1
    if scenario_areas >= 4:
        score += 1.5
    elif scenario_areas >= 3:
        score += 1.0
    elif scenario_areas >= 2:
        score += 0.5

    # 2. Ch4 must list specific components matching the topology in Ch2
    #    (API Gateway, Rate Limiter, Redis, Metrics Service, Management Portal)
    ch4_components = 0
    if re.search(r"[Rr]ate\s*[Ll]imit(er|ing)\s*([Mm]odule|[Cc]omponent|[Ss]ervice)", ch4_content):
        ch4_components += 1
    if re.search(r"[Mm]etrics?\s*([Ss]ervice|[Cc]ollect|[Cc]omponent)", ch4_content):
        ch4_components += 1
    if re.search(r"[Mm]anagement\s*([Pp]ortal|[Dd]ashboard|[Cc]onsole)", ch4_content):
        ch4_components += 1
    if re.search(r"[Rr]edis\s*([Cc]luster|[Ss]tore|[Cc]omponent|[Cc]ache)", ch4_content):
        ch4_components += 1
    if ch4_components >= 4:
        score += 1.5
    elif ch4_components >= 3:
        score += 1.0
    elif ch4_components >= 2:
        score += 0.5

    # 3. Ch5 must have interfaces covering ALL Ch3 scenario domains
    #    (rate-limit config, metrics query, webhook, quota endpoints)
    interface_coverage = 0
    if re.search(r"(rate.?limit|config).*(GET|POST|PUT|DELETE|PATCH)", ch5_content, re.IGNORECASE):
        interface_coverage += 1
    if re.search(r"(metric|usage).*(GET|query|endpoint)", ch5_content, re.IGNORECASE):
        interface_coverage += 1
    if re.search(r"(webhook|notif|alert).*(POST|register|subscri)", ch5_content, re.IGNORECASE):
        interface_coverage += 1
    if re.search(r"(quota|tenant|tier).*(GET|POST|PUT|CRUD|manag)", ch5_content, re.IGNORECASE):
        interface_coverage += 1
    if interface_coverage >= 4:
        score += 1.5
    elif interface_coverage >= 3:
        score += 1.0
    elif interface_coverage >= 2:
        score += 0.5

    # 4. Ch4 architecture diagram must show data flow (arrows/connections between components)
    # Not just a list but actual topology representation
    has_diagram_flow = bool(re.search(
        r"(-->|->|<--|<-|==>|=>|\|.*\|.*\|.*-->|─|━|├|└|┌|┐)",
        ch4_content
    ))
    if has_diagram_flow:
        score += 0.5

    return round(score / total, 4)


def _check_interface_json_schemas(content: str) -> float:
    """HIDDEN CHECK: Verify that interfaces have complete JSON schema definitions.

    The template shows Request/Response blocks. A strong agent provides complete
    JSON examples with realistic field names, types, and nested structures
    specific to the rate-limiting domain. Weak models give generic placeholders
    like { ... } or omit fields.
    """
    ch5_content = _extract_chapter(content, 5)
    if not ch5_content:
        return 0.0

    score = 0.0
    total = 8.0

    # 1. Rate-limit config interface must have tenant_id, tier, limits fields
    config_fields = 0
    if re.search(r"tenant[_\-]?id", ch5_content, re.IGNORECASE):
        config_fields += 1
    if re.search(r"\"tier\"|tier[_\-]?name|tier[_\-]?level", ch5_content, re.IGNORECASE):
        config_fields += 1
    if re.search(r"requests[_\-]?per[_\-]?second|rate[_\-]?limit|max[_\-]?requests", ch5_content, re.IGNORECASE):
        config_fields += 1
    if re.search(r"burst[_\-]?(limit|allowance|factor|multiplier)", ch5_content, re.IGNORECASE):
        config_fields += 1
    if config_fields >= 4:
        score += 2.0
    elif config_fields >= 3:
        score += 1.5
    elif config_fields >= 2:
        score += 0.75

    # 2. Metrics query response must have specific metric field names
    metrics_fields = 0
    if re.search(r"current[_\-]?(usage|rate|count)|request[_\-]?count", ch5_content, re.IGNORECASE):
        metrics_fields += 1
    if re.search(r"reject(ed)?[_\-]?(count|rate)|throttl(ed|ing)[_\-]?count", ch5_content, re.IGNORECASE):
        metrics_fields += 1
    if re.search(r"remaining[_\-]?(quota|limit|allowance)|quota[_\-]?remaining", ch5_content, re.IGNORECASE):
        metrics_fields += 1
    if re.search(r"window[_\-]?(start|end|duration)|time[_\-]?window", ch5_content, re.IGNORECASE):
        metrics_fields += 1
    if metrics_fields >= 4:
        score += 2.0
    elif metrics_fields >= 3:
        score += 1.5
    elif metrics_fields >= 2:
        score += 0.75

    # 3. Webhook registration must have callback_url, event types, secret/auth
    webhook_fields = 0
    if re.search(r"callback[_\-]?url|webhook[_\-]?url|endpoint[_\-]?url", ch5_content, re.IGNORECASE):
        webhook_fields += 1
    if re.search(r"event[_\-]?(type|name)s?|trigger[_\-]?(type|event)", ch5_content, re.IGNORECASE):
        webhook_fields += 1
    if re.search(r"secret|signing[_\-]?key|hmac|auth[_\-]?header", ch5_content, re.IGNORECASE):
        webhook_fields += 1
    if webhook_fields >= 3:
        score += 2.0
    elif webhook_fields >= 2:
        score += 1.0
    elif webhook_fields >= 1:
        score += 0.5

    # 4. Must show HTTP status codes in response examples (201, 200, 404, 429)
    status_codes_in_responses = set(re.findall(r"\b(200|201|204|400|401|403|404|409|429|500|503)\b", ch5_content))
    if len(status_codes_in_responses) >= 5:
        score += 2.0
    elif len(status_codes_in_responses) >= 3:
        score += 1.0
    elif len(status_codes_in_responses) >= 2:
        score += 0.5

    return round(score / total, 4)


def _check_nonfunctional_requirements_tracing(content: str) -> float:
    """HIDDEN CHECK: Verify that non-functional requirements from voc.md are traced
    through the document to specific architectural/interface decisions.

    The voc.md specifies:
    - p99 < 1ms for rate check
    - p50 < 50ms for metrics query
    - 500+ concurrent tenants
    - zero-downtime migration
    - sync + async gateway modes

    A strong agent traces these NFRs into specific architecture choices and interface
    constraints. Weak models mention them in Ch1 but don't carry them through.
    """
    score = 0.0
    total = 10.0

    ch4_content = _extract_chapter(content, 4)
    ch5_content = _extract_chapter(content, 5)

    # 1. Latency requirement (< 1ms) must appear in ARCHITECTURE chapter
    #    (not just copied in Ch1) showing it influenced design
    if re.search(r"(<?\s*1\s*ms|sub.?millisecond|latency.*1\s*ms|p99.*1\s*ms)", ch4_content):
        score += 2.0
    elif re.search(r"(latency|perform|fast)", ch4_content, re.IGNORECASE):
        score += 0.5

    # 2. Concurrency requirement (500+ tenants) must drive architecture decisions
    #    (e.g., Redis cluster sizing, horizontal scaling, connection pooling)
    concurrency_in_arch = 0
    if re.search(r"500\+?\s*tenant|concurrent.*500|500.*concurrent", ch4_content):
        concurrency_in_arch += 1
    if re.search(r"horizontal\s*scal|auto.?scal|replica|shard", ch4_content, re.IGNORECASE):
        concurrency_in_arch += 1
    if re.search(r"connection\s*pool|pool\s*size|thread\s*pool", ch4_content, re.IGNORECASE):
        concurrency_in_arch += 1
    if concurrency_in_arch >= 2:
        score += 2.0
    elif concurrency_in_arch >= 1:
        score += 1.0

    # 3. Sync + async gateway modes must be addressed in architecture
    if re.search(r"(sync|async).*gateway|(synchronous|asynchronous).*mode|both.*mode|dual.*mode", ch4_content, re.IGNORECASE):
        score += 2.0
    elif re.search(r"async|synchronous|non.?blocking", ch4_content, re.IGNORECASE):
        score += 0.5

    # 4. Interface chapter must show rate-limit headers (standard practice)
    #    X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After
    ratelimit_headers = 0
    if re.search(r"X-RateLimit-Limit|x-ratelimit-limit|RateLimit-Limit", ch5_content):
        ratelimit_headers += 1
    if re.search(r"X-RateLimit-Remaining|x-ratelimit-remaining|RateLimit-Remaining", ch5_content):
        ratelimit_headers += 1
    if re.search(r"X-RateLimit-Reset|x-ratelimit-reset|RateLimit-Reset", ch5_content):
        ratelimit_headers += 1
    if re.search(r"Retry-After|retry-after|429.*Retry", ch5_content):
        ratelimit_headers += 1
    if ratelimit_headers >= 3:
        score += 2.0
    elif ratelimit_headers >= 2:
        score += 1.0
    elif ratelimit_headers >= 1:
        score += 0.5

    # 5. Zero-downtime migration strategy must be in architecture (not just mentioned)
    #    Look for specific migration patterns: blue-green, canary, feature flag, shadow mode
    migration_strategy = 0
    if re.search(r"blue.?green|canary|rolling.*deploy|shadow.*mode|feature.*flag|dual.?write", ch4_content, re.IGNORECASE):
        migration_strategy += 1
    if re.search(r"backward.*compat|fallback|graceful.*degrad", ch4_content, re.IGNORECASE):
        migration_strategy += 1
    if migration_strategy >= 2:
        score += 2.0
    elif migration_strategy >= 1:
        score += 1.0

    return round(score / total, 4)


def _check_scenario_acceptance_criteria(content: str) -> float:
    """HIDDEN CHECK: Verify that Ch3 scenarios have testable acceptance criteria.

    The template implies scenarios need to be actionable. A strong agent provides
    specific, measurable acceptance criteria for each scenario (e.g., "given tenant
    at 100 req/s limit, when 101st request arrives, then return 429 within 1ms").

    Weak models just describe scenarios without defining how to verify them.
    """
    ch3_content = _extract_chapter(content, 3)
    if not ch3_content:
        return 0.0

    score = 0.0
    total = 6.0

    # 1. Must have acceptance criteria / given-when-then / test conditions
    has_acceptance = bool(re.search(
        r"[Aa]cceptance\s*[Cc]riteria|[Gg]iven.*[Ww]hen.*[Tt]hen|[Tt]est\s*[Cc]ondition|[Vv]erification|[Ss]uccess\s*[Cc]riteria",
        ch3_content
    ))
    if has_acceptance:
        score += 2.0

    # 2. Must have specific numeric thresholds in scenario descriptions
    #    (not just "rate limit" but "100 req/s", "429 status", "2x burst")
    numeric_specifics = len(re.findall(
        r"\d+\s*(req/s|ms|requests?|seconds?|%|tps|rps)",
        ch3_content, re.IGNORECASE
    ))
    if numeric_specifics >= 6:
        score += 2.0
    elif numeric_specifics >= 3:
        score += 1.0
    elif numeric_specifics >= 1:
        score += 0.5

    # 3. Must reference edge cases / boundary conditions in scenarios
    #    (exactly at limit, burst expiry, concurrent requests, Redis failover)
    edge_cases = 0
    if re.search(r"(edge|boundary|limit|threshold)\s*(case|condition)", ch3_content, re.IGNORECASE):
        edge_cases += 1
    if re.search(r"(failover|failure|unavailable|timeout|fallback)", ch3_content, re.IGNORECASE):
        edge_cases += 1
    if re.search(r"(concurrent|simultaneous|parallel|race\s*condition)", ch3_content, re.IGNORECASE):
        edge_cases += 1
    if re.search(r"(expir|reset|window\s*roll|bucket\s*refill)", ch3_content, re.IGNORECASE):
        edge_cases += 1
    if edge_cases >= 3:
        score += 2.0
    elif edge_cases >= 2:
        score += 1.0
    elif edge_cases >= 1:
        score += 0.5

    return round(score / total, 4)


def _check_requirement_traceability(content: str) -> float:
    """HIDDEN CHECK: Verify end-to-end requirement traceability across chapters.

    A strong agent maintains traceability links throughout the document:
    - WANT/NEED/REQ IDs referenced in Ch3 scenarios (not just Ch1)
    - Scenario IDs (S1, S2...) referenced back in Ch4/Ch5
    - Interface IDs (IF-XX) linked to scenarios they serve

    Weak models treat each chapter as standalone, never linking back to prior chapters.
    This is a key professional practice that separates engineering docs from essays.
    """
    score = 0.0
    total = 10.0

    ch1_content = _extract_chapter(content, 1)
    ch3_content = _extract_chapter(content, 3)
    ch4_content = _extract_chapter(content, 4)
    ch5_content = _extract_chapter(content, 5)

    # 1. Ch3 must reference requirement IDs (WANT-20250301 or REQ-20250301)
    #    showing scenarios derive from requirements
    if re.search(r"WANT-20250301|REQ-20250301", ch3_content):
        score += 2.0
    elif re.search(r"WANT|REQ|requirement\s*#?\d+", ch3_content, re.IGNORECASE):
        score += 0.5

    # 2. Ch4 must reference scenario IDs (S1, S2, etc.) showing architecture
    #    decisions map to specific scenarios
    scenario_refs_in_ch4 = re.findall(r"\bS\d+\b", ch4_content)
    unique_scenario_refs = set(scenario_refs_in_ch4)
    if len(unique_scenario_refs) >= 3:
        score += 2.0
    elif len(unique_scenario_refs) >= 2:
        score += 1.0
    elif len(unique_scenario_refs) >= 1:
        score += 0.5

    # 3. Ch5 must link interfaces to scenarios (e.g., "supports S1", "covers S2/S3")
    scenario_refs_in_ch5 = re.findall(r"\bS\d+\b", ch5_content)
    unique_scenario_refs_ch5 = set(scenario_refs_in_ch5)
    if len(unique_scenario_refs_ch5) >= 3:
        score += 2.0
    elif len(unique_scenario_refs_ch5) >= 2:
        score += 1.0
    elif len(unique_scenario_refs_ch5) >= 1:
        score += 0.5

    # 4. Interface IDs from Ch5 must be referenced in Ch4 (showing which component
    #    exposes which interface)
    if_ids_in_ch5 = set(re.findall(r"IF-\d+", ch5_content))
    if_ids_in_ch4 = set(re.findall(r"IF-\d+", ch4_content))
    overlap = if_ids_in_ch4 & if_ids_in_ch5
    if len(overlap) >= 3:
        score += 2.0
    elif len(overlap) >= 2:
        score += 1.0
    elif len(overlap) >= 1:
        score += 0.5

    # 5. Must have an explicit traceability statement or matrix anywhere
    #    (e.g., "Traceability", "maps to", "derived from", "satisfies")
    traceability_phrases = re.findall(
        r"[Tt]raceability|[Mm]aps?\s+to|[Dd]erived\s+from|[Ss]atisfies|[Cc]overs?\s+(requirement|scenario)|[Ss]upports?\s+S\d+",
        content
    )
    if len(traceability_phrases) >= 4:
        score += 2.0
    elif len(traceability_phrases) >= 2:
        score += 1.0
    elif len(traceability_phrases) >= 1:
        score += 0.5

    return round(score / total, 4)


def _check_architecture_decision_rationale(content: str) -> float:
    """HIDDEN CHECK: Verify that architecture decisions include rationale (WHY).

    A strong agent doesn't just list components — it explains WHY specific
    technology choices were made:
    - Why token bucket over sliding window or leaky bucket?
    - Why Redis over in-memory counters?
    - Why specific data structures or patterns?

    Weak models state "we use Redis" without explaining the decision drivers.
    Architecture without rationale is just a parts list.
    """
    ch4_content = _extract_chapter(content, 4)
    if not ch4_content:
        return 0.0

    score = 0.0
    total = 10.0

    # 1. Must explain WHY token bucket was chosen (vs alternatives)
    #    Strong: "Token bucket chosen over sliding window because..."
    #    Weak: "Uses token bucket algorithm"
    token_bucket_rationale = 0
    if re.search(r"[Tt]oken.?[Bb]ucket.{0,80}(because|since|due to|advantage|benefit|chosen|select|prefer)", ch4_content):
        token_bucket_rationale += 1
    if re.search(r"(sliding\s*window|leaky\s*bucket|fixed\s*window).{0,60}(however|but|drawback|limitation|not\s*suitable|less|worse)", ch4_content, re.IGNORECASE):
        token_bucket_rationale += 1
    if re.search(r"(comparison|vs\.?|versus|alternative|trade.?off)", ch4_content, re.IGNORECASE):
        token_bucket_rationale += 1
    if token_bucket_rationale >= 2:
        score += 3.0
    elif token_bucket_rationale >= 1:
        score += 1.5

    # 2. Must explain WHY Redis (vs in-memory, Memcached, DB)
    redis_rationale = 0
    if re.search(r"[Rr]edis.{0,100}(because|atomic|Lua|script|cluster|replication|persist|fast|low.?latency)", ch4_content):
        redis_rationale += 1
    if re.search(r"(in.?memory|local\s*cache|single.?node).{0,80}(but|however|limitation|not\s*support|insufficient|cannot)", ch4_content, re.IGNORECASE):
        redis_rationale += 1
    if re.search(r"(distribut|multi.?instance|cross.?node|shared\s*state).{0,60}(require|need|necessitat)", ch4_content, re.IGNORECASE):
        redis_rationale += 1
    if redis_rationale >= 2:
        score += 3.0
    elif redis_rationale >= 1:
        score += 1.5

    # 3. Must discuss scalability/high-availability design decisions
    ha_rationale = 0
    if re.search(r"(single\s*point\s*of\s*failure|SPOF|availability).{0,80}(therefore|so|thus|hence|mitigat)", ch4_content, re.IGNORECASE):
        ha_rationale += 1
    if re.search(r"(failover|replica|sentinel|cluster).{0,60}(ensure|guarantee|provide|maintain)", ch4_content, re.IGNORECASE):
        ha_rationale += 1
    if re.search(r"(capacity|sizing|throughput).{0,60}(require|support|handle|sustain)", ch4_content, re.IGNORECASE):
        ha_rationale += 1
    if ha_rationale >= 2:
        score += 2.0
    elif ha_rationale >= 1:
        score += 1.0

    # 4. Must have explicit "Decision" or "Rationale" or "Why" sections/labels
    decision_labels = re.findall(
        r"[Dd]ecision|[Rr]ationale|[Ww]hy\s+[A-Z]|[Jj]ustification|[Rr]eason\s*:|[Tt]rade.?off",
        ch4_content
    )
    if len(decision_labels) >= 3:
        score += 2.0
    elif len(decision_labels) >= 2:
        score += 1.0
    elif len(decision_labels) >= 1:
        score += 0.5

    return round(score / total, 4)


def _check_error_handling_and_degradation(content: str) -> float:
    """HIDDEN CHECK: Verify that the design addresses failure modes and graceful degradation.

    The voc.md mentions Redis cluster, distributed counters, 500+ tenants.
    A strong agent addresses: what happens when Redis is down? when a node fails?
    when network partitions occur? This must appear in BOTH Ch4 (architecture)
    AND Ch5 (interface error responses).

    Weak models only describe the happy path. Strong models show they've thought
    about production failure scenarios.
    """
    ch4_content = _extract_chapter(content, 4)
    ch5_content = _extract_chapter(content, 5)

    score = 0.0
    total = 10.0

    # 1. Ch4 must describe Redis failure handling strategy
    #    (fallback to local cache, allow-all, reject-all, circuit breaker)
    redis_failure = 0
    if re.search(r"[Rr]edis.{0,80}(fail|unavailabl|down|disconnect|timeout|partition)", ch4_content):
        redis_failure += 1
    if re.search(r"(circuit\s*breaker|fallback|degrad|local\s*cache|allow.?all|fail.?open|fail.?close)", ch4_content, re.IGNORECASE):
        redis_failure += 1
    if re.search(r"(recovery|reconnect|retry|backoff|heal)", ch4_content, re.IGNORECASE):
        redis_failure += 1
    if redis_failure >= 3:
        score += 3.0
    elif redis_failure >= 2:
        score += 2.0
    elif redis_failure >= 1:
        score += 1.0

    # 2. Must describe rate limiter behavior under partial failure
    #    (what if only some Redis nodes are available, stale data, split brain)
    partial_failure = 0
    if re.search(r"(partial|split.?brain|network\s*partition|inconsisten)", ch4_content, re.IGNORECASE):
        partial_failure += 1
    if re.search(r"(stale|eventual|consisten|CAP|AP\s+over|CP\s+over)", ch4_content, re.IGNORECASE):
        partial_failure += 1
    if re.search(r"(quorum|majority|consensus|replication\s*lag)", ch4_content, re.IGNORECASE):
        partial_failure += 1
    if partial_failure >= 2:
        score += 2.0
    elif partial_failure >= 1:
        score += 1.0

    # 3. Ch5 interfaces must include 429 AND 503 with clear semantics
    #    429 = rate limited (expected), 503 = service degraded (failure mode)
    has_429_semantic = bool(re.search(r"429.{0,80}(rate.?limit|too\s*many|quota\s*exceed|throttl)", ch5_content, re.IGNORECASE))
    has_503_semantic = bool(re.search(r"503.{0,80}(unavailabl|overload|degrad|maintenance|circuit)", ch5_content, re.IGNORECASE))
    if has_429_semantic and has_503_semantic:
        score += 2.5
    elif has_429_semantic or has_503_semantic:
        score += 1.0

    # 4. Must describe retry semantics / idempotency for configuration APIs
    #    (what if a PUT to update config fails mid-way? is it safe to retry?)
    idempotency = 0
    if re.search(r"[Ii]dempoten", ch5_content + ch4_content):
        idempotency += 1
    if re.search(r"(retry|retries).{0,60}(safe|semantic|strateg|policy)", ch5_content + ch4_content, re.IGNORECASE):
        idempotency += 1
    if re.search(r"(ETag|If-Match|optimistic\s*lock|version\s*conflict|CAS|compare.?and.?swap)", ch5_content, re.IGNORECASE):
        idempotency += 1
    if idempotency >= 2:
        score += 2.5
    elif idempotency >= 1:
        score += 1.0

    return round(score / total, 4)


def grade_workspace(ws: Path) -> dict:
    """Grade the generated RSDD document."""
    # Look for rsdd.md in the expected location
    rsdd_path = ws / "project" / "workspace" / "REQ-20250301" / "rsdd.md"
    if not rsdd_path.exists():
        # Fallback: check alternate locations
        alt_paths = [
            ws / "workspace" / "REQ-20250301" / "rsdd.md",
            ws / "REQ-20250301" / "rsdd.md",
            ws / "rsdd.md",
        ]
        for alt in alt_paths:
            if alt.exists():
                rsdd_path = alt
                break

    content = _read(rsdd_path) if rsdd_path.exists() else ""

    if not content:
        return {
            "overall_score": 0.0,
            "components": {
                "ch1_requirements": 0.0,
                "ch2_environment": 0.0,
                "ch3_scenarios": 0.0,
                "ch4_architecture": 0.0,
                "ch5_interfaces": 0.0,
                "skill_compliance": 0.0,
                "domain_accuracy": 0.0,
                "template_subsection_fidelity": 0.0,
                "interface_detail_blocks": 0.0,
                "cross_chapter_consistency": 0.0,
                "interface_json_schemas": 0.0,
                "nfr_tracing": 0.0,
                "scenario_acceptance_criteria": 0.0,
                "requirement_traceability": 0.0,
                "architecture_decision_rationale": 0.0,
                "error_handling_degradation": 0.0,
            },
            "weights": {
                "ch1_requirements": 0.03,
                "ch2_environment": 0.03,
                "ch3_scenarios": 0.03,
                "ch4_architecture": 0.03,
                "ch5_interfaces": 0.03,
                "skill_compliance": 0.03,
                "domain_accuracy": 0.06,
                "template_subsection_fidelity": 0.08,
                "interface_detail_blocks": 0.10,
                "cross_chapter_consistency": 0.07,
                "interface_json_schemas": 0.10,
                "nfr_tracing": 0.10,
                "scenario_acceptance_criteria": 0.07,
                "requirement_traceability": 0.09,
                "architecture_decision_rationale": 0.08,
                "error_handling_degradation": 0.07,
            },
            "error": "rsdd.md not found",
        }

    chapters = _check_chapter_structure(content)
    skill_compliance = _check_skill_compliance(content)
    domain_accuracy = _check_domain_accuracy(content)
    template_fidelity = _check_template_subsection_fidelity(content)
    interface_details = _check_interface_detail_blocks(content)
    cross_consistency = _check_cross_chapter_consistency(content)
    interface_schemas = _check_interface_json_schemas(content)
    nfr_tracing = _check_nonfunctional_requirements_tracing(content)
    scenario_acceptance = _check_scenario_acceptance_criteria(content)
    req_traceability = _check_requirement_traceability(content)
    arch_rationale = _check_architecture_decision_rationale(content)
    error_degradation = _check_error_handling_and_degradation(content)

    components = {
        **chapters,
        "skill_compliance": skill_compliance,
        "domain_accuracy": domain_accuracy,
        "template_subsection_fidelity": template_fidelity,
        "interface_detail_blocks": interface_details,
        "cross_chapter_consistency": cross_consistency,
        "interface_json_schemas": interface_schemas,
        "nfr_tracing": nfr_tracing,
        "scenario_acceptance_criteria": scenario_acceptance,
        "requirement_traceability": req_traceability,
        "architecture_decision_rationale": arch_rationale,
        "error_handling_degradation": error_degradation,
    }

    # Rebalanced weights: easy checks minimal, hard hidden checks dominate
    # Easy checks (ch1-ch5 + compliance): 0.18 total
    # Medium checks (domain_accuracy): 0.06
    # Hard hidden checks: 0.76 total
    weights = {
        "ch1_requirements": 0.03,
        "ch2_environment": 0.03,
        "ch3_scenarios": 0.03,
        "ch4_architecture": 0.03,
        "ch5_interfaces": 0.03,
        "skill_compliance": 0.03,
        "domain_accuracy": 0.06,
        "template_subsection_fidelity": 0.08,
        "interface_detail_blocks": 0.10,
        "cross_chapter_consistency": 0.07,
        "interface_json_schemas": 0.10,
        "nfr_tracing": 0.10,
        "scenario_acceptance_criteria": 0.07,
        "requirement_traceability": 0.09,
        "architecture_decision_rationale": 0.08,
        "error_handling_degradation": 0.07,
    }

    overall = sum(weights[k] * components[k] for k in weights)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    # Try primary path first, then fallbacks
    ws = Path("/workspace/fixtures")
    if not (ws / "project").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
