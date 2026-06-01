"""Database utilities for report generation system.

Uses SQLite in WAL mode for concurrent read access.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

DATABASE_DIR = os.getenv("DB_DIR", "/app/data")
DATABASE_PATH = os.path.join(DATABASE_DIR, "data.db")


def get_connection() -> sqlite3.Connection:
    """Get a database connection with WAL mode enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_db_size() -> float:
    """Get database file size in MB."""
    if os.path.exists(DATABASE_PATH):
        return os.path.getsize(DATABASE_PATH) / (1024 * 1024)
    return 0.0


def check_db_health() -> dict:
    """Database health check.

    Checks:
    1. Database file exists
    2. Database is readable (can run SELECT)
    3. Database is writable (can create/write/delete temp table)
    4. WAL mode is active
    5. Database file size is not abnormal (>500MB considered abnormal)
    6. WAL/SHM file sizes are not excessive (>100MB considered abnormal)

    Returns:
        dict with keys: healthy (bool), issues (list), size_mb (float)
    """
    issues = []
    db_path = DATABASE_PATH

    # Check 1: File exists
    if not os.path.exists(db_path):
        return {"healthy": False, "issues": ["database file does not exist"], "size_mb": 0.0}

    # Check 2: Readable
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
    except Exception as e:
        issues.append(f"database read failed: {e}")
        return {"healthy": False, "issues": issues, "size_mb": get_db_size()}

    # Check 3: Writable
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS _health_check_tmp (id INTEGER)")
        conn.execute("INSERT INTO _health_check_tmp VALUES (1)")
        conn.execute("DROP TABLE _health_check_tmp")
        conn.commit()
    except Exception as e:
        issues.append(f"database write failed: {e}")

    # Check 4: WAL mode
    try:
        result = conn.execute("PRAGMA journal_mode").fetchone()
        if result and result[0].lower() != "wal":
            issues.append(f"journal mode is {result[0]}, expected WAL")
    except Exception as e:
        issues.append(f"failed to check journal mode: {e}")

    # Check 5: Database file size
    size_mb = get_db_size()
    if size_mb > 500:
        issues.append(f"database file too large: {size_mb:.1f}MB (threshold: 500MB)")

    # Check 6: WAL/SHM file sizes
    wal_path = db_path + "-wal"
    shm_path = db_path + "-shm"
    if os.path.exists(wal_path):
        wal_size = os.path.getsize(wal_path) / (1024 * 1024)
        if wal_size > 100:
            issues.append(f"WAL file too large: {wal_size:.1f}MB (threshold: 100MB)")
    if os.path.exists(shm_path):
        shm_size = os.path.getsize(shm_path) / (1024 * 1024)
        if shm_size > 100:
            issues.append(f"SHM file too large: {shm_size:.1f}MB (threshold: 100MB)")

    conn.close()
    return {"healthy": len(issues) == 0, "issues": issues, "size_mb": size_mb}


def recover_database() -> dict:
    """Attempt to recover a database that failed health check.

    Recovery strategies (tried in order):
    1. Dispose connections and reconnect
    2. Remove stale lock files (WAL and SHM) and reconnect
    3. Restore from backup

    Returns:
        dict with keys: success (bool), method (str), error (str or None)
    """
    db_path = DATABASE_PATH
    error_msg = ""

    # Strategy 1: Simple reconnect
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
        return {"success": True, "method": "reconnect", "error": None}
    except Exception as e:
        error_msg = f"reconnect failed: {e}"

    # Strategy 2: Remove WAL and SHM files, then reconnect
    try:
        wal_path = db_path + "-wal"
        shm_path = db_path + "-shm"
        if os.path.exists(wal_path):
            os.remove(wal_path)
        if os.path.exists(shm_path):
            os.remove(shm_path)

        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
        return {"success": True, "method": "remove_lock_files", "error": None}
    except Exception as e:
        error_msg = f"lock file cleanup failed: {e}"

    # Strategy 3: Restore from backup
    try:
        backup_dir = os.path.join(os.path.dirname(db_path), "..", "backup")
        if os.path.exists(backup_dir):
            backups = sorted(Path(backup_dir).glob("data_*.db"), reverse=True)
            if backups:
                shutil.copy2(str(backups[0]), db_path)
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1")
                conn.close()
                return {"success": True, "method": "restore_backup", "error": None}
        error_msg = "no backup available"
    except Exception as e:
        error_msg = f"backup restore failed: {e}"

    return {"success": False, "method": "none", "error": error_msg}


def cleanup_old_records(retention_days: int = 180) -> int:
    """Delete audit log records older than retention_days. Returns count deleted."""
    try:
        conn = get_connection()
        cursor = conn.execute(
            "DELETE FROM audit_logs WHERE created_at < datetime('now', ?)",
            (f"-{retention_days} days",)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
    except Exception:
        return 0


def execute_vacuum() -> bool:
    """Run VACUUM to reclaim space. Returns success."""
    try:
        conn = get_connection()
        conn.execute("VACUUM")
        conn.close()
        return True
    except Exception:
        return False
