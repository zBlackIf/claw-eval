"""Service layer — request/response DTOs + exclusion check."""
from pydantic import BaseModel
from typing import List
from .function_exclusion_enum import FunctionCode, MUTEX_GROUPS


class ExclusionCheckRequest(BaseModel):
    tenant_id: str
    user_id: str
    function_codes: List[FunctionCode]


class ExclusionCheckResponse(BaseModel):
    ok: bool
    conflicting: List[List[str]] = []


def check_exclusion(req: ExclusionCheckRequest) -> ExclusionCheckResponse:
    codes = {c.value for c in req.function_codes}
    conflicts = []
    for group in MUTEX_GROUPS:
        hit = codes & group
        if len(hit) >= 2:
            conflicts.append(sorted(hit))
    return ExclusionCheckResponse(ok=not conflicts, conflicting=conflicts)
