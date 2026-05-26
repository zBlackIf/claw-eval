"""Function exclusion check service logic."""
from .function_exclusion_enum import FunctionCode, MUTEX_GROUPS


class FunctionExclusionService:
    """Service to check mutual exclusion between function codes."""

    def check(self, function_codes: list[str]) -> dict:
        """Check if any pair of codes belongs to the same mutex group."""
        conflicts = []

        for group in MUTEX_GROUPS:
            group_set = set(group)
            matched = group_set.intersection(set(function_codes))
            if len(matched) >= 2:
                conflicts.append({
                    "group": list(group),
                    "matched": sorted(list(matched))
                })

        if conflicts:
            return {"result": "conflict", "conflicts": conflicts}
        return {"result": "pass", "conflicts": []}
