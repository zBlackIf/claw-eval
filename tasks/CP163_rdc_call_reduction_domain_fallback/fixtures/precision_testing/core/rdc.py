# -*- coding: utf-8 -*-
"""RDC (Requirement Data Center) API wrapper.

Provides batch query support for work items, relations, and field retrieval.
"""
import time
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# --- Call counter for observability ---
_rdc_call_count = 0
_REQUEST_DELAY = 0.05  # 50ms between calls


def _rdc_request_delay():
    """Rate-limit RDC calls and increment counter."""
    global _rdc_call_count
    _rdc_call_count += 1
    time.sleep(_REQUEST_DELAY)


def get_rdc_call_stats() -> int:
    """Return total RDC API calls since last reset."""
    return _rdc_call_count


def reset_rdc_call_count():
    """Reset the RDC call counter."""
    global _rdc_call_count
    _rdc_call_count = 0


# --- Simulated RDC data store (represents external API) ---
_WORK_ITEMS_DB: Dict[str, Dict[str, Any]] = {
    "RAN-5620900": {
        "id": "RAN-5620900",
        "type": "MR",
        "title": "5G NR Carrier Aggregation Enhancement",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-5620901": {
        "id": "RAN-5620901",
        "type": "PR",
        "title": "CA Scheduling Optimization",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-5620902": {
        "id": "RAN-5620902",
        "type": "PR",
        "title": "CA Power Control",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-5620903": {
        "id": "RAN-5620903",
        "type": "US",
        "title": "Scheduling algorithm for CA",
        "System_AreaPath": "07-5G-SPA",
        "state": "Resolved",
    },
    "RAN-5620904": {
        "id": "RAN-5620904",
        "type": "US",
        "title": "Power headroom report handling",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-5620905": {
        "id": "RAN-5620905",
        "type": "US",
        "title": "SCell activation timer",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-5620906": {
        "id": "RAN-5620906",
        "type": "PR",
        "title": "Interference Management for CA",
        "System_AreaPath": "03-LTE-RRM",
        "state": "Active",
    },
    # Items with empty System_AreaPath but valid Area field (the bug scenario)
    # Only the ROOT MR has the empty System_AreaPath issue
    "RAN-1455434": {
        "id": "RAN-1455434",
        "type": "MR",
        "title": "UL Power Control Optimization",
        "System_AreaPath": "",  # BUG: empty in batch API for this item
        "state": "Active",
    },
    "RAN-1455435": {
        "id": "RAN-1455435",
        "type": "PR",
        "title": "PUSCH TPC Command Enhancement",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-1455436": {
        "id": "RAN-1455436",
        "type": "US",
        "title": "Closed-loop power adjustment",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-1455437": {
        "id": "RAN-1455437",
        "type": "US",
        "title": "Open-loop power estimation",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-1455438": {
        "id": "RAN-1455438",
        "type": "PR",
        "title": "SRS Power Control",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-1455439": {
        "id": "RAN-1455439",
        "type": "US",
        "title": "SRS transmission power calc",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-1455440": {
        "id": "RAN-1455440",
        "type": "US",
        "title": "Path loss compensation",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-1455441": {
        "id": "RAN-1455441",
        "type": "US",
        "title": "TPC accumulation mode",
        "System_AreaPath": "07-5G-SPA",
        "state": "Active",
    },
    "RAN-1455442": {
        "id": "RAN-1455442",
        "type": "PR",
        "title": "PUCCH Power Control",
        "System_AreaPath": "03-LTE-RRM",  # Different domain - should be filtered
        "state": "Active",
    },
}

# fetch_data returns full details including the Area field (fallback source)
_FETCH_DATA_DB: Dict[str, Dict[str, Any]] = {
    "RAN-1455434": {
        "id": "RAN-1455434",
        "fields": {
            "System.AreaPath": "",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "UL Power Control Optimization",
        },
    },
    "RAN-1455435": {
        "id": "RAN-1455435",
        "fields": {
            "System.AreaPath": "",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "PUSCH TPC Command Enhancement",
        },
    },
    "RAN-1455436": {
        "id": "RAN-1455436",
        "fields": {
            "System.AreaPath": "",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "Closed-loop power adjustment",
        },
    },
    "RAN-1455437": {
        "id": "RAN-1455437",
        "fields": {
            "System.AreaPath": "",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "Open-loop power estimation",
        },
    },
    "RAN-1455438": {
        "id": "RAN-1455438",
        "fields": {
            "System.AreaPath": "",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "SRS Power Control",
        },
    },
    "RAN-1455439": {
        "id": "RAN-1455439",
        "fields": {
            "System.AreaPath": "",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "SRS transmission power calc",
        },
    },
    "RAN-1455440": {
        "id": "RAN-1455440",
        "fields": {
            "System.AreaPath": "",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "Path loss compensation",
        },
    },
    "RAN-1455441": {
        "id": "RAN-1455441",
        "fields": {
            "System.AreaPath": "",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "TPC accumulation mode",
        },
    },
    "RAN-5620900": {
        "id": "RAN-5620900",
        "fields": {
            "System.AreaPath": "07-5G-SPA",
            "Area": {"persistentValue": {"name": "07-5G-SPA"}},
            "System.Title": "5G NR Carrier Aggregation Enhancement",
        },
    },
}

# Relations DB: parent -> children
_RELATIONS_DB: Dict[str, Dict[str, List[str]]] = {
    "RAN-5620900": {
        "PR": ["RAN-5620901", "RAN-5620902", "RAN-5620906"],
        "US": [],
        "MR": [],
    },
    "RAN-5620901": {
        "PR": [],
        "US": ["RAN-5620903", "RAN-5620904"],
        "MR": [],
    },
    "RAN-5620902": {
        "PR": [],
        "US": ["RAN-5620905"],
        "MR": [],
    },
    "RAN-1455434": {
        "PR": ["RAN-1455435", "RAN-1455438", "RAN-1455442"],
        "US": [],
        "MR": [],
    },
    "RAN-1455435": {
        "PR": [],
        "US": ["RAN-1455436", "RAN-1455437"],
        "MR": [],
    },
    "RAN-1455438": {
        "PR": [],
        "US": ["RAN-1455439", "RAN-1455440", "RAN-1455441"],
        "MR": [],
    },
    "RAN-1455442": {
        "PR": [],
        "US": [],
        "MR": [],
    },
}


def judge_pr_or_mr_or_us(ran_id: str) -> str:
    """Query RDC to determine requirement type (MR/PR/US).

    Makes one API call per invocation.
    """
    _rdc_request_delay()
    item = _WORK_ITEMS_DB.get(ran_id)
    if item:
        return item["type"]
    return "Unknown"


def batch_get_work_items(
    work_item_ids: List[str],
    select_fields: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Batch query work item fields. One API call for up to 200 items."""
    _rdc_request_delay()
    result = {}
    for wid in work_item_ids:
        item = _WORK_ITEMS_DB.get(wid)
        if item:
            if select_fields:
                result[wid] = {k: item.get(k, "") for k in select_fields}
            else:
                result[wid] = dict(item)
    return result


def fetch_data(ran_id: str) -> Optional[Dict[str, Any]]:
    """Fetch full work item data including all fields. One API call."""
    _rdc_request_delay()
    return _FETCH_DATA_DB.get(ran_id)


def batch_query_relations(
    work_item_ids: List[str],
    group_by_type: bool = False,
) -> Dict[str, Any]:
    """Batch query parent-child relations for multiple items.

    One API call. When group_by_type=True, returns:
    {wid: {"PR": [...], "US": [...], "MR": [...]}}

    When group_by_type=False, returns:
    {wid: [all_child_ids]}
    """
    _rdc_request_delay()
    result = {}
    for wid in work_item_ids:
        relations = _RELATIONS_DB.get(wid, {"PR": [], "US": [], "MR": []})
        if group_by_type:
            result[wid] = relations
        else:
            all_children = []
            for children in relations.values():
                all_children.extend(children)
            result[wid] = all_children
    return result
