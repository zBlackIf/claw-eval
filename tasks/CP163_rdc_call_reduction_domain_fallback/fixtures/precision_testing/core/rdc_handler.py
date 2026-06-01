# -*- coding: utf-8 -*-
"""RDC handler — higher-level functions built on core.rdc."""
from typing import Dict, List, Any

from core.rdc import (
    batch_query_relations,
    batch_get_work_items,
    judge_pr_or_mr_or_us,
)


def batch_get_children_by_type(work_item_ids: List[str]) -> Dict[str, Dict[str, List[str]]]:
    """Get all children grouped by type for multiple work items.

    Uses a single batch_query_relations call with group_by_type=True.
    Returns: {parent_id: {"PR": [...], "US": [...], "MR": [...]}}
    """
    return batch_query_relations(work_item_ids, group_by_type=True)


def batch_get_child_prs_from_mr(mr_numbers: List[str]) -> Dict[str, List[str]]:
    """Get child PRs for each MR. Uses batch_query_relations."""
    relations = batch_query_relations(mr_numbers, group_by_type=True)
    return {mid: rels.get("PR", []) for mid, rels in relations.items()}


def batch_get_child_uss_from_pr(pr_numbers: List[str]) -> Dict[str, List[str]]:
    """Get child USs for each PR. Uses batch_query_relations."""
    relations = batch_query_relations(pr_numbers, group_by_type=True)
    return {pid: rels.get("US", []) for pid, rels in relations.items()}


def batch_get_child_mrs_from_mr(mr_numbers: List[str]) -> Dict[str, List[str]]:
    """Get child MRs for each MR. Uses batch_query_relations."""
    relations = batch_query_relations(mr_numbers, group_by_type=True)
    return {mid: rels.get("MR", []) for mid, rels in relations.items()}
