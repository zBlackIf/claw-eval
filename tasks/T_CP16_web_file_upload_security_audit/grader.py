"""T_CP16_web_file_upload_security_audit grader — Pattern D (Sandbox-Adapted).

Source: Themis taskset-260408-163403:task_04_security_audit_file_upload.

Pattern D: PinbenchAdaptedGrader with class attributes.
Agent reads PHP + nginx config from sandbox, outputs markdown security audit.
"""

from __future__ import annotations

from claw_eval.graders.pinbench_common import PinbenchAdaptedGrader


class WebFileUploadSecurityAuditGrader(PinbenchAdaptedGrader):
    """Grade web file upload security audit report."""

    REQUIRED_TOOLS = {}  # no mock service; reads sandbox_files directly

    REQUIRED_KEYWORDS = [
        # Must have these structural anchors
        "Critical",
        "High",
        "扩展名",     # extension whitelist
        "MIME",       # MIME / content sniffing
        ".htaccess",  # apache directive coverage
    ]

    OPTIONAL_KEYWORDS = [
        # Vulnerability category anchors (bonus)
        "path traversal", "Path Traversal", "路径穿越",
        "TOCTOU", "race condition", "竞态",
        "RCE", "代码执行",
        "double extension", "双扩展", "双扩展名",
        "finfo", "mime_content_type",
        "CSRF", "csrf",
        "XSS",
        "GDPR",
        "DoS", "拒绝服务",
        "CVSS",
        "client_max_body_size",
        "upload_max_filesize",
        "move_uploaded_file",
        "REMOTE_ADDR",
        "htmlspecialchars",
    ]

    # Must use markdown headings / lists / code blocks
    REQUIRED_PATTERNS = [
        r"^#+\s+|^\d+\.\s|^[-*]\s",
    ]

    MIN_FINAL_LENGTH = 600
