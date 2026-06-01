"""Flash report (快报) handler."""
from __future__ import annotations
from datetime import datetime


def handle(report_type: str | None = None, timestamp: str | None = None) -> dict:
    """Generate a flash report."""
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "status": "success",
        "report_type": "快报",
        "timestamp": ts,
        "output_file": f"flash_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
    }
