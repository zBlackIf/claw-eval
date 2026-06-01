/* fs_rmts_pm.h - Remote Storage Power Management API
 * This header defines the sync timer API available to OEM PD modules.
 */
#ifndef FS_RMTS_PM_H
#define FS_RMTS_PM_H

/**
 * Set the filesystem sync timer for remote storage.
 * Called by OEM modules to configure periodic sync intervals.
 *
 * @param path      Mount path (e.g. "/")
 * @param timeout_ms Sync timeout in milliseconds
 * @return 0 on success, -1 on error
 */
int fs_set_sync_timer(const char *path, unsigned int timeout_ms);

/**
 * Get current sync timer value.
 * @param path Mount path
 * @return current timer value in ms, or 0 if not set
 */
unsigned int fs_get_sync_timer(const char *path);

#endif /* FS_RMTS_PM_H */
