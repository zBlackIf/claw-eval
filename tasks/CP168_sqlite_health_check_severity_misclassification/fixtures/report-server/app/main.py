"""Main application entry point with scheduled tasks."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from app.database import (
    check_db_health,
    cleanup_old_records,
    execute_vacuum,
    recover_database,
)


async def audit_log_cleanup_task():
    """Background task: clean up old audit logs daily at 3:00 AM."""
    while True:
        try:
            now = datetime.now()
            # Calculate next 3:00 AM
            target = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)

            wait_seconds = (target - now).total_seconds()
            print(f"[Cleanup] Next run at {target}, waiting {wait_seconds:.0f}s")
            await asyncio.sleep(wait_seconds)

            # Health check before cleanup
            health = check_db_health()
            if not health["healthy"]:
                print(f"[Cleanup] DB health check failed: {health.get('issues', [])}, attempting recovery...")
                recovery = recover_database()
                if not recovery["success"]:
                    print(f"[Cleanup] Recovery failed: {recovery.get('error')}, skipping cleanup")
                    await asyncio.sleep(3600)
                    continue
                print(f"[Cleanup] Recovery succeeded via: {recovery['method']}")

            # Run cleanup
            retention_months = int(os.getenv("AUDIT_RETENTION_MONTHS", "6"))
            deleted = cleanup_old_records(retention_days=retention_months * 30)
            print(f"[Cleanup] Deleted {deleted} old records")

            # Vacuum if significant records deleted
            if deleted > 1000:
                execute_vacuum()
                print("[Cleanup] VACUUM completed")

        except Exception as e:
            print(f"[Cleanup] Error: {e}")
            await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan: start background tasks."""
    # Startup: check DB health
    health = check_db_health()
    if health["healthy"]:
        print(f"[System] DB health check passed (size: {health.get('size_mb', 0):.2f}MB)")
    else:
        print(f"[System] DB health check FAILED: {health.get('issues', [])}")
        recovery = recover_database()
        if recovery["success"]:
            print(f"[System] Auto-recovery succeeded: {recovery['method']}")
        else:
            print(f"[System] Auto-recovery FAILED: {recovery.get('error')}")

    # Start background cleanup
    cleanup_handle = asyncio.create_task(audit_log_cleanup_task())
    yield
    cleanup_handle.cancel()


# Application would be created here with lifespan
# app = FastAPI(lifespan=lifespan)
