"""Evening report (晚报) handler."""
from __future__ import annotations
from datetime import datetime


def handle(report_type: str | None = None, timestamp: str | None = None) -> dict:
    """Generate an evening report."""
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "status": "success",
        "report_type": "晚报",
        "timestamp": ts,
        "output_file": f"evening_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
    }
