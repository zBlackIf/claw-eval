"""Hidden verifier for CP150 — Clash proxy split routing configuration."""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _load_yaml(text: str) -> dict | None:
    """Try to parse YAML content."""
    if yaml:
        try:
            return yaml.safe_load(text)
        except Exception:
            pass
    # Fallback: basic field extraction without pyyaml
    return None


def grade_workspace(ws: Path) -> dict:
    # Try multiple paths for the config
    config_dir = ws / "fixtures" / "clash-config"
    if not config_dir.exists():
        config_dir = ws / "clash-config"

    config_file = config_dir / "config.yaml"
    if not config_file.exists():
        # Try alternate name
        config_file = config_dir / "config.yml"

    components = {k: 0.0 for k in [
        "dns_china_nameservers",
        "dns_fallback_configured",
        "proxy_groups_structured",
        "china_direct_rules",
        "foreign_proxy_rules",
        "final_rule_configured",
        "redir_port_or_tproxy",
        "dns_leak_prevention",
        "iptables_script_quality",
        "rule_ordering_correctness",
        "proxy_group_health_params",
        "docker_network_awareness",
        "ipv6_leak_prevention",
        "fake_ip_range_validity",
    ]}

    config_text = _read(config_file)
    if not config_text:
        return {
            "overall_score": 0.0,
            "components": components,
            "weights": _weights(),
        }

    config_lower = config_text.lower()

    # 1. DNS: Must have Chinese DNS nameservers (114.114.114.114, 223.5.5.5, 119.29.29.29, etc.)
    china_dns = ["114.114.114.114", "223.5.5.5", "223.6.6.6", "119.29.29.29"]
    dns_china_count = sum(1 for d in china_dns if d in config_text)
    components["dns_china_nameservers"] = min(1.0, dns_china_count / 2.0)

    # 2. DNS: Must have fallback DNS configured (for anti-pollution)
    has_fallback = "fallback:" in config_lower or "fallback-filter:" in config_lower
    has_enhanced = "enhanced-mode" in config_lower
    # Check for fake-ip or redir-host mode
    has_mode = "fake-ip" in config_lower or "redir-host" in config_lower
    components["dns_fallback_configured"] = (
        (0.4 if has_fallback else 0.0) +
        (0.3 if has_enhanced else 0.0) +
        (0.3 if has_mode else 0.0)
    )

    # 3. Proxy groups: Must have structured groups (not just one "Proxy" selector)
    # Good config has: auto/url-test group, direct group, selector group, fallback group
    proxy_group_patterns = [
        (r"type:\s*url-test", 0.3),      # Auto-test group
        (r"type:\s*select", 0.2),          # Manual select group
        (r"type:\s*fallback", 0.2),        # Fallback group
        (r"name:.*(?:direct|cn|china|domestic)", 0.15, re.IGNORECASE),  # China/direct group
        (r"name:.*(?:proxy|foreign|global|international)", 0.15, re.IGNORECASE),  # Foreign group
    ]
    pg_score = 0.0
    for pattern_info in proxy_group_patterns:
        if len(pattern_info) == 3:
            pat, w, flags = pattern_info
            if re.search(pat, config_text, flags):
                pg_score += w
        else:
            pat, w = pattern_info
            if re.search(pat, config_text):
                pg_score += w
    components["proxy_groups_structured"] = min(1.0, pg_score)

    # 4. Rules: Must have China direct rules (GEOIP,CN,DIRECT or domain-suffix for cn sites)
    china_rules = [
        r"geoip\s*,\s*cn\s*,\s*direct",
        r"domain-suffix\s*,\s*cn\s*,\s*direct",
        r"domain-suffix\s*,\s*baidu\.com",
        r"domain-suffix\s*,\s*qq\.com",
        r"domain-suffix\s*,\s*taobao\.com",
        r"domain-suffix\s*,\s*163\.com",
        r"domain-suffix\s*,\s*bilibili\.com",
    ]
    china_hits = sum(1 for pat in china_rules if re.search(pat, config_lower))
    # GEOIP,CN is the key one
    has_geoip_cn = bool(re.search(r"geoip\s*,\s*cn\s*,\s*direct", config_lower))
    components["china_direct_rules"] = (0.5 if has_geoip_cn else 0.0) + min(0.5, (china_hits - (1 if has_geoip_cn else 0)) * 0.1)

    # 5. Rules: Must have foreign/proxy rules (google, youtube, twitter, etc.)
    foreign_rules = [
        r"domain-(?:suffix|keyword)\s*,\s*google",
        r"domain-(?:suffix|keyword)\s*,\s*youtube",
        r"domain-(?:suffix|keyword)\s*,\s*twitter",
        r"domain-(?:suffix|keyword)\s*,\s*facebook",
        r"domain-(?:suffix|keyword)\s*,\s*github",
        r"domain-(?:suffix|keyword)\s*,\s*telegram",
        r"geoip\s*,\s*(?!cn)",
    ]
    foreign_hits = sum(1 for pat in foreign_rules if re.search(pat, config_lower))
    components["foreign_proxy_rules"] = min(1.0, foreign_hits / 3.0)

    # 6. Final rule: MATCH should route to proxy (not DIRECT) for proper split routing
    # The fallback behavior for unknown traffic should go through proxy
    match_lines = re.findall(r"^\s*-\s*MATCH\s*,\s*(\S+)", config_text, re.MULTILINE | re.IGNORECASE)
    if match_lines:
        last_match = match_lines[-1].lower()
        # MATCH should go to a proxy group, not DIRECT (otherwise foreign sites without explicit rules fail)
        if last_match != "direct" and last_match != "reject":
            components["final_rule_configured"] = 1.0
        elif last_match == "direct":
            # DIRECT is acceptable only if there are enough foreign rules
            components["final_rule_configured"] = 0.3
    else:
        components["final_rule_configured"] = 0.0

    # 7. Transparent proxy support: redir-port or tproxy-port for router-level redirection
    has_redir = "redir-port:" in config_lower
    has_tproxy = "tproxy-port:" in config_lower
    has_tun = "tun:" in config_lower
    # Check setup script for iptables rules
    setup_script = _read(config_dir / "setup-tproxy.sh")
    setup_lower = setup_script.lower()
    has_iptables_redirect = bool(re.search(r"iptables.*redirect|iptables.*tproxy|ip\s+rule", setup_lower))
    components["redir_port_or_tproxy"] = (
        (0.4 if (has_redir or has_tproxy or has_tun) else 0.0) +
        (0.3 if has_iptables_redirect else 0.0) +
        (0.3 if ("nat" in setup_lower or "mangle" in setup_lower) else 0.0)
    )

    # --- HIDDEN ADVANCED CHECKS ---

    # 8. DNS leak prevention: proper separation of CN vs foreign DNS resolution
    # Strong models should configure nameserver-policy or fallback-filter with geoip+ipcidr
    dns_leak_score = 0.0
    # Check for fallback-filter with geoip enabled (prevents DNS pollution)
    if re.search(r"fallback-filter\s*:", config_lower):
        dns_leak_score += 0.2
        # Check geoip: true inside fallback-filter context
        if re.search(r"geoip\s*:\s*true", config_lower):
            dns_leak_score += 0.2
        # Check for ipcidr ranges in fallback-filter (240.0.0.0/4 is known polluted range)
        if re.search(r"ipcidr\s*:", config_lower) and re.search(r"240\.0\.0\.0", config_text):
            dns_leak_score += 0.2
    # Check for nameserver-policy (domain-specific DNS routing)
    if re.search(r"nameserver-policy\s*:", config_lower):
        dns_leak_score += 0.2
    # Check for fake-ip-filter (excludes CN domains from fake-ip to prevent issues)
    if re.search(r"fake-ip-filter\s*:", config_lower):
        dns_leak_score += 0.2
    components["dns_leak_prevention"] = min(1.0, dns_leak_score)

    # 9. iptables script quality: proper chain management, local bypass, loop prevention
    ipt_quality_score = 0.0
    # Must create a dedicated chain (proper practice, not inline rules)
    if re.search(r"iptables\s+-t\s+nat\s+-N\s+\w+", setup_script):
        ipt_quality_score += 0.15
    # Must have local/private network bypass rules (at least 3 of: 127.0.0.0/8, 10.0.0.0/8,
    # 172.16.0.0/12, 192.168.0.0/16, 0.0.0.0/8, 169.254.0.0/16, 224.0.0.0/4)
    private_nets = [
        r"127\.0\.0\.0/8", r"10\.0\.0\.0/8", r"172\.16\.0\.0/12",
        r"192\.168\.0\.0/16", r"0\.0\.0\.0/8", r"169\.254\.0\.0/16", r"224\.0\.0\.0/4",
    ]
    private_bypass_count = sum(1 for net in private_nets if re.search(net, setup_script))
    if private_bypass_count >= 4:
        ipt_quality_score += 0.25
    elif private_bypass_count >= 2:
        ipt_quality_score += 0.1
    # Must redirect DNS (port 53) to Clash DNS port for transparent DNS
    if re.search(r"(dport\s+53|--dport\s+53).*redirect", setup_lower) or \
       re.search(r"redirect.*--to-port.*(53|1053|5353)", setup_lower):
        ipt_quality_score += 0.2
    # Must have loop prevention (exclude Clash process/user from being redirected back)
    # Either via -m owner --uid-owner or by excluding the Clash container's traffic
    if re.search(r"owner\s+--uid-owner|owner\s+--gid-owner|-m\s+owner", setup_lower):
        ipt_quality_score += 0.2
    elif re.search(r"cgroup|mark\s+--set-mark|RETURN.*clash", setup_script, re.IGNORECASE):
        ipt_quality_score += 0.15
    # Should flush/cleanup existing rules before applying (idempotent script)
    if re.search(r"iptables\s+-t\s+nat\s+-F\s+\w+|iptables\s+-t\s+nat\s+-X\s+\w+", setup_script):
        ipt_quality_score += 0.2
    components["iptables_script_quality"] = min(1.0, ipt_quality_score)

    # 10. Rule ordering correctness: domain rules > IP rules > GEOIP > MATCH
    # In Clash, the order matters: more specific rules must come first.
    rule_order_score = 0.0
    # Extract all rule lines
    rule_lines = re.findall(r"^\s*-\s*(DOMAIN[^,]*|IP-CIDR[^,]*|GEOIP[^,]*|MATCH|SRC-[^,]*|DST-[^,]*|PROCESS-[^,]*|RULE-SET[^,]*)",
                            config_text, re.MULTILINE | re.IGNORECASE)
    if rule_lines:
        # Find positions of different rule types
        domain_positions = [i for i, r in enumerate(rule_lines) if r.upper().startswith("DOMAIN")]
        ipcidr_positions = [i for i, r in enumerate(rule_lines) if r.upper().startswith("IP-CIDR")]
        geoip_positions = [i for i, r in enumerate(rule_lines) if r.upper().startswith("GEOIP")]
        match_positions = [i for i, r in enumerate(rule_lines) if r.upper().startswith("MATCH")]

        # Domain rules should come before GEOIP rules
        if domain_positions and geoip_positions:
            if max(domain_positions) < min(geoip_positions):
                rule_order_score += 0.35
            elif sum(1 for d in domain_positions if d < min(geoip_positions)) > len(domain_positions) * 0.8:
                rule_order_score += 0.2

        # GEOIP should come before MATCH
        if geoip_positions and match_positions:
            if max(geoip_positions) < min(match_positions):
                rule_order_score += 0.25

        # IP-CIDR rules (if any) should come after domain but before/with GEOIP
        if ipcidr_positions and domain_positions and geoip_positions:
            if min(ipcidr_positions) > max(domain_positions):
                rule_order_score += 0.15

        # Must have sufficient rule count (at least 8 rules for proper coverage)
        if len(rule_lines) >= 15:
            rule_order_score += 0.25
        elif len(rule_lines) >= 8:
            rule_order_score += 0.15
    components["rule_ordering_correctness"] = min(1.0, rule_order_score)

    # 11. Proxy-group health check parameters: url-test groups need proper config
    health_score = 0.0
    # Find url-test groups and check for required parameters
    url_test_blocks = re.findall(
        r"type:\s*url-test.*?(?=(?:^\s*-\s*name:|\Z))",
        config_text, re.MULTILINE | re.DOTALL
    )
    # Alternative: just check for presence of these params near url-test
    has_url_test = bool(re.search(r"type:\s*url-test", config_text))
    if has_url_test:
        # Must have health check URL (typically http://www.gstatic.com/generate_204)
        if re.search(r"url\s*:\s*['\"]?http", config_text):
            health_score += 0.3
        # Must have interval parameter (check frequency)
        if re.search(r"interval\s*:\s*\d+", config_text):
            health_score += 0.25
        # Should have tolerance parameter (latency difference threshold for switching)
        if re.search(r"tolerance\s*:\s*\d+", config_text):
            health_score += 0.25
        # Should have lazy parameter or reasonable interval (not too aggressive)
        interval_match = re.search(r"interval\s*:\s*(\d+)", config_text)
        if interval_match:
            interval_val = int(interval_match.group(1))
            # Good interval: 60-600 seconds (not too aggressive, not too slow)
            if 60 <= interval_val <= 600:
                health_score += 0.2
            elif 30 <= interval_val < 60 or 600 < interval_val <= 900:
                health_score += 0.1
    components["proxy_group_health_params"] = min(1.0, health_score)

    # --- HIDDEN CHECK 12: Docker network awareness ---
    # When running Clash in Docker on a router, the iptables script must handle
    # Docker networking correctly: exclude Docker bridge subnet, handle container
    # traffic properly, and reference the correct interface/port from docker-compose.
    docker_score = 0.0
    # Check docker-compose.yml for network_mode or port mapping consistency
    compose_file = config_dir / "docker-compose.yml"
    compose_text = _read(compose_file)
    compose_lower = compose_text.lower()
    # network_mode: host is the recommended approach for transparent proxy in Docker
    if re.search(r"network_mode\s*:\s*['\"]?host", compose_text):
        docker_score += 0.35
    elif re.search(r"network_mode\s*:", compose_text):
        docker_score += 0.1
    # If not host mode, must map redir-port AND dns port in docker-compose
    if not re.search(r"network_mode\s*:\s*['\"]?host", compose_text):
        redir_port_mapped = bool(re.search(r"7892\s*:\s*7892|7893\s*:\s*7893", compose_text))
        dns_port_mapped = bool(re.search(r"53\s*:\s*53|1053\s*:\s*1053", compose_text))
        if redir_port_mapped:
            docker_score += 0.15
        if dns_port_mapped:
            docker_score += 0.15
    # iptables script should exclude Docker's bridge subnet (172.17.0.0/16 or custom)
    if re.search(r"172\.17\.0\.0|docker0|br-", setup_script):
        docker_score += 0.15
    # Should handle DOCKER chain interaction (avoid inserting rules that conflict)
    if re.search(r"DOCKER|docker", setup_script) or \
       re.search(r"-I\s+PREROUTING|PREROUTING.*-j\s+\w+CLASH", setup_script, re.IGNORECASE):
        docker_score += 0.2
    # cap_add NET_ADMIN is needed for tproxy/tun in container
    if re.search(r"cap_add|NET_ADMIN|net_admin|privileged", compose_text, re.IGNORECASE):
        docker_score += 0.15
    components["docker_network_awareness"] = min(1.0, docker_score)

    # --- HIDDEN CHECK 13: IPv6 leak prevention ---
    # A proper transparent proxy must handle IPv6; otherwise traffic leaks around the proxy.
    # Either disable IPv6 entirely via sysctl/ip6tables, or configure Clash for IPv6.
    ipv6_score = 0.0
    all_script_text = setup_script + compose_text + config_text
    all_script_lower = all_script_text.lower()
    # Option A: Disable IPv6 via sysctl (net.ipv6.conf.all.disable_ipv6 = 1)
    if re.search(r"disable_ipv6\s*=\s*1|disable_ipv6.*1", all_script_text):
        ipv6_score += 0.4
    # Option B: Add ip6tables rules to block/redirect IPv6 traffic
    if re.search(r"ip6tables", all_script_lower):
        ipv6_score += 0.35
    # Option C: Clash config has ipv6: true/false explicitly set (awareness of the issue)
    if re.search(r"^\s*ipv6\s*:\s*(true|false)", config_text, re.MULTILINE | re.IGNORECASE):
        ipv6_score += 0.25
    # DNS should explicitly handle IPv6: either disable AAAA or configure IPv6 nameservers
    if re.search(r"ipv6\s*:\s*false", config_lower) or \
       re.search(r"prefer-h3|use-hosts", config_lower):
        ipv6_score += 0.15
    # If enhanced-mode is fake-ip, fake-ip-range should cover IPv6 or IPv6 be disabled
    if re.search(r"fake-ip-range.*:", config_text) and re.search(r"ipv6", config_lower):
        ipv6_score += 0.1
    components["ipv6_leak_prevention"] = min(1.0, ipv6_score)

    # --- HIDDEN CHECK 14: fake-ip-range validity and DNS architecture ---
    # Strong models know: fake-ip-range must be in a reserved CIDR (198.18.0.0/15 is standard),
    # DNS listen address must match iptables redirect target, and fake-ip-filter should
    # exclude domains that break with fake IPs (e.g., NTP servers, local services).
    fakeip_score = 0.0
    # Check for proper fake-ip-range in reserved CIDR
    fakeip_range_match = re.search(r"fake-ip-range\s*:\s*([^\s#]+)", config_text)
    if fakeip_range_match:
        fakeip_range = fakeip_range_match.group(1)
        # 198.18.0.0/15 (or subnet like 198.18.0.1/16) is the standard Clash fake-ip range
        if re.search(r"198\.18\.", fakeip_range):
            fakeip_score += 0.35
        # 28.0.0.0/8 or other RFC-reserved ranges are also acceptable
        elif re.search(r"28\.0\.0|240\.0\.0|100\.64\.", fakeip_range):
            fakeip_score += 0.2
        else:
            # Using non-standard range shows awareness but may cause issues
            fakeip_score += 0.1
    # fake-ip-filter should exclude problematic domains
    if re.search(r"fake-ip-filter\s*:", config_lower):
        fakeip_score += 0.15
        # Should exclude common problematic patterns (NTP, LAN discovery, Microsoft connect test)
        filter_patterns = [
            r"\+\.lan",
            r"ntp|time\.",
            r"msftconnecttest|msftncsi|captive",
            r"localhost|local",
            r"\*\.local",
        ]
        filter_hits = sum(1 for p in filter_patterns if re.search(p, config_lower))
        fakeip_score += min(0.2, filter_hits * 0.05)
    # DNS listen port in config must be consistent with iptables redirect target
    dns_listen_match = re.search(r"listen\s*:\s*\S*:(\d+)", config_text)
    if dns_listen_match:
        dns_port = dns_listen_match.group(1)
        # Check if iptables redirects to the same port
        if dns_port in setup_script:
            fakeip_score += 0.2
        elif dns_port == "53" and re.search(r"--to-port", setup_lower):
            # Port 53 is default, some scripts redirect to it implicitly
            fakeip_score += 0.1
    # enhanced-mode should be explicitly set (fake-ip preferred for transparent proxy)
    if re.search(r"enhanced-mode\s*:\s*fake-ip", config_lower):
        fakeip_score += 0.15
    elif re.search(r"enhanced-mode\s*:\s*redir-host", config_lower):
        fakeip_score += 0.08
    components["fake_ip_range_validity"] = min(1.0, fakeip_score)

    return {
        "overall_score": round(_compute_overall(components), 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": _weights(),
    }


def _weights() -> dict:
    return {
        # Basic checks (0.30 total — easy for any model)
        "dns_china_nameservers": 0.05,
        "dns_fallback_configured": 0.05,
        "proxy_groups_structured": 0.05,
        "china_direct_rules": 0.05,
        "foreign_proxy_rules": 0.05,
        "final_rule_configured": 0.02,
        "redir_port_or_tproxy": 0.03,
        # Advanced hidden checks (0.70 total — separates strong from weak)
        "dns_leak_prevention": 0.12,
        "iptables_script_quality": 0.12,
        "rule_ordering_correctness": 0.10,
        "proxy_group_health_params": 0.09,
        "docker_network_awareness": 0.10,
        "ipv6_leak_prevention": 0.09,
        "fake_ip_range_validity": 0.08,
    }


def _compute_overall(components: dict) -> float:
    w = _weights()
    return sum(w[k] * components[k] for k in w)


def main():
    ws = Path("/workspace/fixtures")
    if not (ws / "clash-config").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
