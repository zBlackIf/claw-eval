# -*- coding: utf-8 -*-
"""Requirement Impact Analyzer.

Analyzes requirement hierarchies:
- MR input: analyze MR + child PRs + grandchild USs (filter by same domain)
- PR input: analyze PR + child USs (filter by same domain)
- MR with child MRs: error "请输入子需求，不要输入父需求"

BUG 1: _resolve_domain_from_rdc does NOT have fetch_data fallback.
        When System_AreaPath is empty, domain returns [] even though
        the Area field has data accessible via fetch_data().

BUG 2: _analyze_single calls judge_pr_or_mr_or_us for EVERY entity
        in the entities list, even though the type is already known from
        batch_query_relations. This causes ~N extra RDC API calls.

BUG 3: _analyze_single calls batch_get_child_prs_from_mr and
        batch_get_child_uss_from_pr SEPARATELY instead of using
        batch_get_children_by_type once. This doubles the relation queries.
"""
import logging
from typing import Dict, List, Optional, Tuple

from core.rdc import (
    batch_get_work_items,
    judge_pr_or_mr_or_us,
    get_rdc_call_stats,
    reset_rdc_call_count,
)
from core.rdc_handler import (
    batch_get_child_prs_from_mr,
    batch_get_child_uss_from_pr,
    batch_get_child_mrs_from_mr,
    batch_get_children_by_type,
)

logger = logging.getLogger(__name__)


class RequirementImpactAnalyzer:
    """需求波及分析器"""

    def __init__(self, domain: Optional[str] = None):
        self.domain = domain
        self.results: List[Dict] = []

    def analyze(self, req_id: str) -> Dict:
        """Main entry point. Analyzes requirement and returns results.

        Returns:
            {
                "req_id": str,
                "entities": [...],
                "domain": str,
                "rdc_call_count": int,
                "error": str or None,
            }
        """
        reset_rdc_call_count()
        logger.info(f"开始分析需求: {req_id}")

        try:
            result = self._analyze_single(req_id)
            rdc_calls = get_rdc_call_stats()
            logger.info(f"本次分析共发起 {rdc_calls} 次 RDC 调用")
            result["rdc_call_count"] = rdc_calls
            return result
        except ValueError as e:
            return {
                "req_id": req_id,
                "entities": [],
                "domain": "",
                "rdc_call_count": get_rdc_call_stats(),
                "error": str(e),
            }

    def _analyze_single(self, req_id: str) -> Dict:
        """Analyze a single requirement ID.

        Expand logic:
        - MR: self + child PRs + grandchild USs
        - PR: self + child USs
        - MR with child MRs: raise error

        BUG: calls judge_pr_or_mr_or_us for each entity even when type is known.
        BUG: uses separate batch_get_child_prs_from_mr + batch_get_child_uss_from_pr
             instead of single batch_get_children_by_type call.
        """
        # Step 1: Determine type of the root requirement
        req_type = judge_pr_or_mr_or_us(req_id)

        if req_type == "Unknown":
            raise ValueError(f"无法识别需求类型: {req_id}")

        # Resolve domain for the root requirement
        domain = self._resolve_domain_from_rdc(req_id)
        domain_str = domain[0] if domain else ""

        # Build entity list: (id, type)
        entities: List[Tuple[str, str]] = [(req_id, req_type)]

        if req_type == "MR":
            # Check for child MRs first (error case)
            child_mrs = batch_get_child_mrs_from_mr([req_id])
            if child_mrs.get(req_id):
                raise ValueError("请输入子需求，不要输入父需求")

            # BUG: Uses separate calls instead of batch_get_children_by_type
            child_prs_map = batch_get_child_prs_from_mr([req_id])
            child_prs = child_prs_map.get(req_id, [])

            # Filter PRs by domain
            filtered_prs = self._filter_by_domain(child_prs, domain_str)
            for pr_id in filtered_prs:
                entities.append((pr_id, "PR"))

            # Get grandchild USs from each PR
            if filtered_prs:
                child_uss_map = batch_get_child_uss_from_pr(filtered_prs)
                for pr_id in filtered_prs:
                    uss = child_uss_map.get(pr_id, [])
                    filtered_uss = self._filter_by_domain(uss, domain_str)
                    for us_id in filtered_uss:
                        entities.append((us_id, "US"))

        elif req_type == "PR":
            # BUG: Uses separate call instead of batch_get_children_by_type
            child_uss_map = batch_get_child_uss_from_pr([req_id])
            child_uss = child_uss_map.get(req_id, [])

            filtered_uss = self._filter_by_domain(child_uss, domain_str)
            for us_id in filtered_uss:
                entities.append((us_id, "US"))

        # Step 2: Resolve functions for each entity
        # BUG: calls judge_pr_or_mr_or_us again for each entity
        all_functions = {}
        for entity_id, entity_type in entities:
            func_info = self._step1_resolve_functions(entity_id)
            all_functions[entity_id] = func_info

        return {
            "req_id": req_id,
            "entities": entities,
            "domain": domain_str,
            "functions": all_functions,
            "error": None,
        }

    def _step1_resolve_functions(self, req_id: str, known_type: str = "") -> Dict:
        """Resolve function paths for a requirement.

        BUG: Does NOT use the known_type parameter — always calls
        judge_pr_or_mr_or_us regardless, wasting an API call per entity.
        """
        # BUG: ignores known_type, always queries type
        req_type = judge_pr_or_mr_or_us(req_id)

        # Simulate function resolution based on type
        if req_type == "MR":
            return {"type": "MR", "functions": ["module_init", "module_config"]}
        elif req_type == "PR":
            return {"type": "PR", "functions": ["feature_impl", "feature_test"]}
        elif req_type == "US":
            return {"type": "US", "functions": ["story_acceptance"]}
        return {"type": "Unknown", "functions": []}

    def _resolve_domain_from_rdc(self, req_id: str) -> List[str]:
        """Resolve domain (area path) for a requirement from RDC.

        BUG: Only checks batch_get_work_items System_AreaPath.
        When it's empty, returns [] without trying fetch_data fallback.
        The fetch_data API returns the Area.persistentValue.name field
        which always has the correct domain value.
        """
        try:
            info = batch_get_work_items(
                [req_id], select_fields=["System_AreaPath"]
            )
            area_path = info.get(req_id, {}).get("System_AreaPath", "")
            if area_path:
                # Extract domain from area path (e.g., "07-5G-SPA" -> "07-5G-SPA")
                return [area_path]
            # BUG: Should fallback to fetch_data here but doesn't
            return []
        except Exception as e:
            logger.error(f"解析领域失败 {req_id}: {e}")
            return []

    def _filter_by_domain(
        self, req_ids: List[str], domain: str
    ) -> List[str]:
        """Filter requirement IDs to only those matching the given domain.

        If domain is empty, returns all IDs (no filtering).
        """
        if not domain:
            return req_ids

        try:
            info = batch_get_work_items(
                req_ids, select_fields=["System_AreaPath"]
            )
            result = []
            for rid in req_ids:
                item_domain = info.get(rid, {}).get("System_AreaPath", "")
                if item_domain == domain:
                    result.append(rid)
            return result
        except Exception:
            return req_ids
