"""Controller layer — POST /ac-common-service/function/exclusion/check."""
from fastapi import APIRouter, HTTPException
from .function_exclusion_check_svc import (
    ExclusionCheckRequest, ExclusionCheckResponse, check_exclusion,
)

router = APIRouter(prefix="/ac-common-service")


@router.post("/function/exclusion/check", response_model=ExclusionCheckResponse)
def check(req: ExclusionCheckRequest):
    if not req.function_codes:
        raise HTTPException(status_code=400, detail="function_codes must not be empty")
    return check_exclusion(req)
