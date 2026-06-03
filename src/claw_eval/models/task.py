"""TaskDefinition — loaded from YAML task files (v3 aligned).

v0.34.1 ark overlay: normalize known calendar_list_events task schemas.
"""

from __future__ import annotations

import copy
import re
import socket
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .tool import ToolEndpoint, ToolSpec


_ARK_CALENDAR_SCHEMA_NORMALIZATION_TASK_IDS = frozenset(
    {
        "T113zh_meeting_preparation",
        "T114_meeting_preparation",
        "T123zh_todo_calendar_conflict",
        "T124_todo_calendar_conflict",
        "T129zh_business_trip_planning",
        "T130_business_trip_planning",
        "T135zh_weekly_meeting_tracking",
        "T136_weekly_meeting_tracking",
        "T149zh_project_progress_report",
        "T150_project_progress_report",
        "T155zh_onsite_support_dispatch",
        "T156_onsite_support_dispatch",
    }
)

_CALENDAR_LIST_EVENTS_CANONICAL_SCHEMA = {
    "type": "object",
    "properties": {
        "date": {
            "type": "string",
            "description": "Query date (YYYY-MM-DD)",
        },
        "days": {
            "type": "integer",
            "description": "Number of days to query",
            "default": 1,
        },
    },
    "required": ["date"],
}


def _normalize_calendar_list_events_schema(data: dict[str, Any]) -> None:
    """Patch accidental task-side schema drift for known Claw-Eval tasks."""
    if not isinstance(data, dict):
        return

    task_id = str(data.get("task_id") or "")
    if task_id not in _ARK_CALENDAR_SCHEMA_NORMALIZATION_TASK_IDS:
        return

    tools = data.get("tools") or []
    if not isinstance(tools, list):
        return

    for tool in tools:
        if not isinstance(tool, dict) or tool.get("name") != "calendar_list_events":
            continue

        schema = tool.get("input_schema") or {}
        properties = schema.get("properties") or {}
        if "start_date" in properties or "end_date" in properties:
            tool["input_schema"] = copy.deepcopy(_CALENDAR_LIST_EVENTS_CANONICAL_SCHEMA)


def _pick_free_tcp_ports(count: int) -> list[int]:
    """Return *count* distinct free TCP ports assigned by the OS.

    All sockets are held open simultaneously while their ports are read, so the
    OS guarantees the ports are mutually distinct; they are then closed for the
    mock services to bind. Matches how services bind (IPv4 wildcard), mirroring
    ``claw_eval_ports.probe_unavailable_tcp_ports``.
    """
    socks: list[socket.socket] = []
    try:
        for _ in range(count):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("0.0.0.0", 0))
            socks.append(sock)
        return [sock.getsockname()[1] for sock in socks]
    finally:
        for sock in socks:
            sock.close()


class Prompt(BaseModel):
    text: str
    language: str = "zh"
    attachments: list[str] = Field(default_factory=list)


class DeterministicCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    field: str | None = None
    tool_name: str | None = None
    min_calls: int | None = None
    categories: list[str] | None = None
    min_length: int | None = None
    patterns: list[str] | None = None
    keywords: list[str] | None = None
    description: str | None = None
    rubric: str | None = None

    @field_validator("keywords", mode="before")
    @classmethod
    def _coerce_keywords_to_str(cls, v: Any) -> list[str] | None:
        """YAML parses unquoted numbers as ints; coerce to str."""
        if v is None:
            return v
        return [str(item) for item in v]


class ScoringComponent(BaseModel):
    name: str
    weight: float
    check: DeterministicCheck


class SafetyCheck(BaseModel):
    type: str
    tool_name: str | None = None
    patterns: list[str] | None = None
    description: str = ""


class Environment(BaseModel):
    timeout_seconds: int = 300
    max_turns: int = 20
    mock_today: str | None = None  # "YYYY-MM-DD" — disables date offset in services, injected into system prompt
    fixtures: list[str] = Field(default_factory=list)
    env_snapshot_timeout: int = 10
    # TodoWrite settings
    enable_todo: bool = False
    todo_nag_rounds: int = 3  # 0 = no reminder
    # Context Compact settings
    enable_compact: bool = False
    compact_keep_recent: int = 20         # Layer 1: keep recent N turns intact
    compact_min_chars: int = 500          # Layer 1: don't truncate short results
    compact_threshold_pct: float = 0.70   # Layer 2: trigger at this % of context window
    compact_keep_recent_on_summary: int = 4  # Layer 2: keep N messages after summary
    compact_protect_tokens: int = 40_000  # Layer 2: protect recent token budget
    compact_max_auto_compacts: int = 2    # Layer 2: max auto-compacts per task run


class ServiceDef(BaseModel):
    """A mock service that must be running for a task."""

    name: str
    command: str
    port: int
    health_check: str
    health_check_method: str = "POST"
    ready_timeout: int = 10
    reset_endpoint: str | None = None
    env: dict[str, str] = Field(default_factory=dict)


class ExpectedAction(BaseModel):
    """Describes an action the agent is expected to perform."""

    service: str  # "gmail", "calendar", etc.
    action_key: str  # key in /audit response: "drafts", "created_events", etc.
    required: bool = True


class UserAgentTaskConfig(BaseModel):
    """Per-task user agent simulation settings."""
    enabled: bool = False
    persona: str = ""
    max_rounds: int = 3
    system_prompt_suffix: str = ""


class TaskDefinition(BaseModel):
    task_id: str
    task_name: str
    version: str = "1.0"
    category: str = ""
    difficulty: str = "simple"
    prompt: Prompt
    tools: list[ToolSpec] = Field(default_factory=list)
    tool_endpoints: list[ToolEndpoint] = Field(default_factory=list)
    environment: Environment = Field(default_factory=Environment)
    scoring_components: list[ScoringComponent] = Field(default_factory=list)
    safety_checks: list[SafetyCheck] = Field(default_factory=list)
    services: list[ServiceDef] = Field(default_factory=list)
    expected_actions: list[ExpectedAction] = Field(default_factory=list)
    judge_rubric: str = ""
    reference_solution: str = ""
    primary_dimensions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    user_agent: UserAgentTaskConfig = Field(default_factory=UserAgentTaskConfig)
    sandbox_files: list[str] = Field(default_factory=list)
    sandbox_grader_files: list[str] = Field(default_factory=list)
    env_snapshot_files: list[str] = Field(default_factory=list)
    env_snapshot_commands: list[str] = Field(default_factory=list)
    local_grader_files: list[str] = Field(default_factory=list)
    task_file: str | None = Field(default=None, exclude=True)

    @classmethod
    def from_yaml(cls, path: str | Path) -> TaskDefinition:
        with open(path) as f:
            data = yaml.safe_load(f)
        _normalize_calendar_list_events_schema(data)
        data["task_file"] = str(Path(path).resolve())
        return cls.model_validate(data)

    def apply_port_offset(self, offset: int) -> None:
        """Shift all service ports and endpoint URLs by *offset*.

        This allows multiple task instances to run in parallel on
        non-overlapping port ranges.
        """
        if offset == 0:
            return

        def _shift_url(url: str) -> str:
            """Replace localhost:<port> with localhost:<port+offset>."""
            return re.sub(
                r"localhost:(\d+)",
                lambda m: f"localhost:{int(m.group(1)) + offset}",
                url,
            )

        for svc in self.services:
            svc.port += offset
            svc.health_check = _shift_url(svc.health_check)
            if svc.reset_endpoint:
                svc.reset_endpoint = _shift_url(svc.reset_endpoint)
            # Tell the subprocess which port to bind
            svc.env = {**(svc.env or {}), "PORT": str(svc.port)}

        for ep in self.tool_endpoints:
            ep.url = _shift_url(ep.url)

    def assign_dynamic_ports(self) -> None:
        """Bind每个声明端口到一个 OS 分配的空闲端口（动态端口，bind 0）。

        替代固定端口 + offset/lease 机制（见 v0.50.11 §3.3）：mock service 本就读
        ``PORT`` env，这里在起服务前把每个 distinct 的声明端口映射成一个 OS 空闲端口，
        并一致重写 svc.port / env[PORT] / health_check / reset_endpoint 及所有
        tool_endpoints.url。端口不再有 ~47 并发硬上限，瓶颈转 RAM。

        同一题内的所有端口由“同时持有多个 bind(0) socket 再统一读端口”保证互不相同
        （OS 不会把已占用的端口再分给另一个打开的 socket）。题间的极小 TOCTOU 窗口由
        ServiceManager 的 ServiceStartError + 重试兜底。
        """
        declared_ports = sorted({int(svc.port) for svc in self.services})
        if not declared_ports:
            return

        free_ports = _pick_free_tcp_ports(len(declared_ports))
        port_map = dict(zip(declared_ports, free_ports))

        def _remap_url(url: str) -> str:
            return re.sub(
                r"localhost:(\d+)",
                lambda m: f"localhost:{port_map.get(int(m.group(1)), int(m.group(1)))}",
                url,
            )

        for svc in self.services:
            new_port = port_map[int(svc.port)]
            svc.port = new_port
            svc.health_check = _remap_url(svc.health_check)
            if svc.reset_endpoint:
                svc.reset_endpoint = _remap_url(svc.reset_endpoint)
            # Tell the subprocess which port to bind
            svc.env = {**(svc.env or {}), "PORT": str(new_port)}

        for ep in self.tool_endpoints:
            ep.url = _remap_url(ep.url)

    def get_endpoint_map(self) -> dict[str, ToolEndpoint]:
        """Return {tool_name: ToolEndpoint} for dispatcher lookup."""
        return {ep.tool_name: ep for ep in self.tool_endpoints}
