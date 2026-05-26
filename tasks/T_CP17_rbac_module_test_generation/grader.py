"""T_CP17_rbac_module_test_generation grader — Pattern D.

Source: Themis taskset-260427-121234:task_60_rbac_test_gen.

Agent reads 3 RBAC modules from /workspace/fixtures/code/ and produces
a markdown report with 3 pytest code blocks (one per module).
"""

from __future__ import annotations

from claw_eval.graders.pinbench_common import PinbenchAdaptedGrader


class RbacModuleTestGenerationGrader(PinbenchAdaptedGrader):

    REQUIRED_TOOLS = {}  # no mock service

    REQUIRED_KEYWORDS = [
        "pytest",
        "assert",
        "tenant",
        # Module-specific anchors
        "role_service",
        "user_role_binding",
        "access_check",
    ]

    OPTIONAL_KEYWORDS = [
        "def test_",
        "cyclic", "循环",
        "expired", "expires_at", "过期",
        "deny_overrides",
        "stale binding",
        "fixture", "@pytest.fixture",
        "raises", "pytest.raises",
        "ValueError",
        "KeyError",
        "parametrize",
    ]

    # Must contain at least one ```python code block (markdown fence)
    REQUIRED_PATTERNS = [
        r"```python",
        r"^def test_",
    ]

    MIN_FINAL_LENGTH = 800
