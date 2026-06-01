/* efs_core.c - Core EFS operations */
#include "fs_public.h"
#include <stdio.h>

/* Minimal stubs for core efs operations */
int efs_open(const char *path, int flags) {
    (void)path; (void)flags;
    return 3; /* fake fd */
}

int efs_close(int fd) {
    (void)fd;
    return 0;
}

int efs_read(int fd, void *buf, unsigned int nbytes) {
    (void)fd; (void)buf; (void)nbytes;
    return 0;
}

int efs_write(int fd, const void *buf, unsigned int nbytes) {
    (void)fd; (void)buf; (void)nbytes;
    return (int)nbytes;
}

int efs_mkdir(const char *path, int mode) {
    (void)path; (void)mode;
    return 0;
}
