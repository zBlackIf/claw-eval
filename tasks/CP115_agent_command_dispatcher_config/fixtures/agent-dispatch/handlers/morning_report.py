"""Morning report (早报) handler."""
from __future__ import annotations
from datetime import datetime


def handle(report_type: str | None = None, timestamp: str | None = None) -> dict:
    """Generate a morning report."""
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "status": "success",
        "report_type": "早报",
        "timestamp": ts,
        "output_file": f"morning_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
    }
