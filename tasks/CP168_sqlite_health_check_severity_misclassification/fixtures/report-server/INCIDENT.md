# Incident Report: Database Corruption After Deployment

## Timeline
- 2024-03-15 02:00: Deployed updated server with new `check_db_health()` function
- 2024-03-15 02:01: Server startup triggers health check
- 2024-03-15 02:01: Health check reports FAILED (database size 4724MB > 500MB threshold)
- 2024-03-15 02:01: Auto-recovery triggered via `recover_database()`
- 2024-03-15 02:01: Recovery strategy 1 (reconnect) succeeds — but reports success prematurely
- 2024-03-15 03:00: Cleanup task triggers, health check again reports FAILED (size > 500MB)
- 2024-03-15 03:00: Recovery strategy 1 succeeds again (SELECT 1 works) — but size issue persists
- 2024-03-15 03:00: Next iteration: health check FAILED again...
- (loop continues every hour due to the 3600s retry sleep)
- 2024-03-16 08:30: Under load, WAL grows to 150MB, SHM grows to 120MB
- 2024-03-16 08:30: Health check now reports 3 issues (size + WAL + SHM)
- 2024-03-16 08:30: Recovery triggered, strategy 1 (reconnect) works BUT issues still remain
- 2024-03-16 08:31: On second pass through the cleanup loop, health check still fails
- 2024-03-16 08:31: Recovery strategy 2 activates: DELETES WAL and SHM files
- 2024-03-16 08:31: WAL contained uncommitted pages -> DATABASE CORRUPTED
- 2024-03-16 08:32: All subsequent queries return "file is not a database"

## Impact
- Complete database corruption
- All audit logs from last 2 years lost (no recent backup existed)
- Service down for 6 hours until manual restore from week-old backup

## Root Cause (needs fixing)
The `check_db_health()` function treats **informational size warnings** identically to
**functional failures**. A 4.7GB database is large but completely functional. The health
check incorrectly sets `healthy=False` for non-critical size conditions, which triggers
the dangerous `recover_database()` path that eventually deletes WAL/SHM files.

## Expected Behavior After Fix
- Size/WAL/SHM thresholds should generate WARNINGS, not mark the database as unhealthy
- Only actual functional failures (can't read, can't write, wrong journal mode) should set `healthy=False`
- Recovery strategy 2 must NEVER delete WAL/SHM files (this can cause data loss)
- Health check return value should clearly separate `issues` (critical) from `warnings` (informational)
