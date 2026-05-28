"""Per-task workflow review service for Claw-Eval audit/payload tasks."""
from __future__ import annotations

import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

for candidate in [Path.cwd(), *Path(__file__).resolve().parents]:
    if (candidate / "mock_services" / "_base.py").exists():
        sys.path.insert(0, str(candidate))
        break

from mock_services._base import add_error_injection

SERVICE_NAME = os.environ.get("WORKFLOW_SERVICE_NAME", "citation_review")
DEFAULT_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "workflow_review.json"
FIXTURES_PATH = Path(os.environ.get("WORKFLOW_SERVICE_FIXTURES", str(DEFAULT_FIXTURES)))

app = FastAPI(title=f"{SERVICE_NAME} review service")
add_error_injection(app)

_initial: dict[str, Any] = {}
_state: dict[str, Any] = {}
_audit_log: list[dict[str, Any]] = []


def _load() -> None:
    global _initial, _state
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        loaded = json.load(f)
    if not isinstance(loaded, list):
        raise ValueError("workflow review fixture must be a top-level list")
    cross_checks = []
    for record in loaded:
        if isinstance(record, dict) and record.get("kind") == "cross_check":
            check = (record.get("metadata") or {}).get("check")
            if isinstance(check, dict):
                cross_checks.append(check)
    _initial = {"records": loaded, "cross_checks": cross_checks, "submissions": {}, "confirmations": []}
    _state = copy.deepcopy(_initial)


_load()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(endpoint: str, request_body: dict[str, Any], response_body: Any, status_code: int = 200) -> None:
    _audit_log.append({"endpoint": endpoint, "request_body": copy.deepcopy(request_body), "response_body": copy.deepcopy(response_body), "status_code": status_code, "timestamp": _now()})


def _record_map() -> dict[str, dict[str, Any]]:
    return {str(r.get("record_id")): r for r in _state.get("records", []) if r.get("record_id")}


def _brief(record: dict[str, Any]) -> dict[str, Any]:
    content = str(record.get("content") or "")
    return {"record_id": record.get("record_id"), "kind": record.get("kind"), "title": record.get("title"), "tags": record.get("tags", []), "metadata": record.get("metadata", {}), "snippet": content[:240]}


def _searchable(record: dict[str, Any]) -> str:
    return " ".join([str(record.get("record_id", "")), str(record.get("kind", "")), str(record.get("title", "")), str(record.get("content", "")), " ".join(map(str, record.get("tags", []))), json.dumps(record.get("metadata", {}), ensure_ascii=False)]).lower()


class ListRequest(BaseModel):
    kind: str | None = None
    tag: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class SearchRequest(BaseModel):
    query: str
    kind: str | None = None
    max_results: int = Field(default=10, ge=1, le=50)


class GetRequest(BaseModel):
    record_id: str


class CrossCheckRequest(BaseModel):
    primary_id: str | None = None
    comparison_ids: list[str] = Field(default_factory=list)
    focus: str | None = None


class SubmitRequest(BaseModel):
    report_id: str
    content: str
    source_ids: list[str] = Field(default_factory=list)
    decision: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfirmRequest(BaseModel):
    report_id: str
    source_ids: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    notes: str | None = None


@app.get(f"/{SERVICE_NAME}/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": SERVICE_NAME, "records": len(_state.get("records", []))}


@app.post(f"/{SERVICE_NAME}/list")
def list_records(req: ListRequest) -> dict[str, Any]:
    records = []
    for record in _state.get("records", []):
        if req.kind and record.get("kind") != req.kind:
            continue
        if req.tag and req.tag not in record.get("tags", []):
            continue
        records.append(_brief(record))
    resp = {"records": records[: req.limit], "total": len(records)}
    _log(f"/{SERVICE_NAME}/list", req.model_dump(), resp)
    return resp


@app.post(f"/{SERVICE_NAME}/search")
def search_records(req: SearchRequest) -> dict[str, Any]:
    terms = [t for t in req.query.lower().split() if t]
    results = []
    for record in _state.get("records", []):
        if req.kind and record.get("kind") != req.kind:
            continue
        hay = _searchable(record)
        if not terms or all(term in hay for term in terms) or req.query.lower() in hay:
            results.append(_brief(record))
    resp = {"records": results[: req.max_results], "total": len(results), "query": req.query}
    _log(f"/{SERVICE_NAME}/search", req.model_dump(), resp)
    return resp


@app.post(f"/{SERVICE_NAME}/get")
def get_record(req: GetRequest) -> dict[str, Any]:
    record = _record_map().get(req.record_id)
    if not record:
        resp = {"error": f"record {req.record_id} not found"}
        _log(f"/{SERVICE_NAME}/get", req.model_dump(), resp, status_code=404)
        return resp
    resp = copy.deepcopy(record)
    _log(f"/{SERVICE_NAME}/get", req.model_dump(), resp)
    return resp


@app.post(f"/{SERVICE_NAME}/cross_check")
def cross_check(req: CrossCheckRequest) -> dict[str, Any]:
    ids = [rid for rid in [req.primary_id, *req.comparison_ids] if rid]
    focus = (req.focus or "").lower()
    selected = [copy.deepcopy(_record_map()[rid]) for rid in ids if rid in _record_map()]
    checks = []
    for check in _state.get("cross_checks", []):
        text = json.dumps(check, ensure_ascii=False).lower()
        check_ids = set(check.get("primary_ids", [])) | set(check.get("comparison_ids", [])) | set(check.get("trap_ids", []))
        if ids and check_ids.intersection(ids):
            checks.append(check)
        elif focus and focus in text:
            checks.append(check)
    if not checks:
        checks = _state.get("cross_checks", [])[:4]
    resp = {"checks": copy.deepcopy(checks[:8]), "records": selected}
    _log(f"/{SERVICE_NAME}/cross_check", req.model_dump(), resp)
    return resp


@app.post(f"/{SERVICE_NAME}/submit")
def submit_report(req: SubmitRequest) -> dict[str, Any]:
    submission = req.model_dump()
    submission["submitted_at"] = _now()
    _state.setdefault("submissions", {})[req.report_id] = submission
    resp = {"status": "submitted", "report_id": req.report_id, "source_count": len(req.source_ids)}
    _log(f"/{SERVICE_NAME}/submit", req.model_dump(), resp)
    return resp


@app.post(f"/{SERVICE_NAME}/confirm")
def confirm_report(req: ConfirmRequest) -> dict[str, Any]:
    exists = req.report_id in _state.setdefault("submissions", {})
    confirmation = req.model_dump()
    confirmation["confirmed_at"] = _now()
    confirmation["submission_exists"] = exists
    _state.setdefault("confirmations", []).append(confirmation)
    resp = {"status": "confirmed" if exists else "missing_submission", "report_id": req.report_id, "submission_exists": exists}
    _log(f"/{SERVICE_NAME}/confirm", req.model_dump(), resp)
    return resp


@app.get(f"/{SERVICE_NAME}/audit")
def get_audit() -> dict[str, Any]:
    return {"calls": _audit_log, "submissions": copy.deepcopy(_state.get("submissions", {})), "confirmations": copy.deepcopy(_state.get("confirmations", []))}


@app.post(f"/{SERVICE_NAME}/reset")
def reset() -> dict[str, Any]:
    global _audit_log
    _audit_log = []
    _load()
    return {"status": "reset", "service": SERVICE_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "9412")))
