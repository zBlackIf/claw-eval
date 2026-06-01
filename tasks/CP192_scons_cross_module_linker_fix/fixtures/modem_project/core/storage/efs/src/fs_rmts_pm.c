/* fs_rmts_pm.c - Remote Storage Power Management Implementation
 * Part of core/storage/efs module.
 */
#include "fs_rmts_pm.h"
#include <stdio.h>
#include <string.h>

#define MAX_TIMERS 8

typedef struct {
    char path[64];
    unsigned int timeout_ms;
    int active;
} sync_timer_entry_t;

static sync_timer_entry_t g_timers[MAX_TIMERS];
static int g_timer_count = 0;

int fs_set_sync_timer(const char *path, unsigned int timeout_ms) {
    if (!path || timeout_ms == 0) {
        return -1;
    }

    /* Check if timer already exists for this path */
    for (int i = 0; i < g_timer_count; i++) {
        if (strcmp(g_timers[i].path, path) == 0) {
            g_timers[i].timeout_ms = timeout_ms;
            g_timers[i].active = 1;
            return 0;
        }
    }

    /* Add new timer */
    if (g_timer_count >= MAX_TIMERS) {
        return -1;
    }

    strncpy(g_timers[g_timer_count].path, path, 63);
    g_timers[g_timer_count].path[63] = '\0';
    g_timers[g_timer_count].timeout_ms = timeout_ms;
    g_timers[g_timer_count].active = 1;
    g_timer_count++;
    return 0;
}

unsigned int fs_get_sync_timer(const char *path) {
    if (!path) return 0;
    for (int i = 0; i < g_timer_count; i++) {
        if (strcmp(g_timers[i].path, path) == 0 && g_timers[i].active) {
            return g_timers[i].timeout_ms;
        }
    }
    return 0;
}
