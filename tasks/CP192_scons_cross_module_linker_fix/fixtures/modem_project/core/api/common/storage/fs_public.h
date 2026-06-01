/* fs_public.h - Public filesystem API for all modules */
#ifndef FS_PUBLIC_H
#define FS_PUBLIC_H

/* Standard EFS operations available to all modules */
int efs_open(const char *path, int flags);
int efs_close(int fd);
int efs_read(int fd, void *buf, unsigned int nbytes);
int efs_write(int fd, const void *buf, unsigned int nbytes);
int efs_mkdir(const char *path, int mode);

/* NOTE: fs_rmts_pm.h APIs (fs_set_sync_timer, fs_get_sync_timer)
 * are NOT exported here. They require explicit include of
 * core/storage/efs/inc/fs_rmts_pm.h and linking against efs module.
 */

#endif /* FS_PUBLIC_H */
