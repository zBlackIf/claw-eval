/* qmi_fibo_svc.c - Fibo OEM QMI Service Implementation
 *
 * This module provides OEM-specific QMI services for power management.
 * It needs to call fs_set_sync_timer() from the EFS module to configure
 * filesystem sync before entering low-power mode.
 */
#include "qmi_fibo_svc.h"
#include "qmi_csi_common.h"
#include "fs_public.h"
/* BUG: Missing include for fs_rmts_pm.h - causes implicit declaration warning
 * Also: even if included, the linker cannot find fs_set_sync_timer because
 * efs.scons does not compile fs_rmts_pm.c
 */
#include <stdio.h>

static int g_pwrmgr_flag = 0;

int qmi_dms_fibo_auto_set_pwrmgr_flag_req(int flag) {
    g_pwrmgr_flag = flag;

    if (flag == 1) {
        /* Before entering low power mode, trigger FS sync */
        printf("Setting FS sync timer before LPM entry\n");
        /* This call causes the linker error:
         * undefined reference to `fs_set_sync_timer'
         */
        fs_set_sync_timer("/", FIBO_SLEEP_RMT_SYNC_TIMEOUT);
    }

    return 0;
}

int qmi_fibo_svc_init(void) {
    printf("Fibo QMI service initialized\n");
    return qmi_csi_register(0x1234, NULL);
}

void qmi_fibo_svc_main(void) {
    qmi_fibo_svc_init();
    printf("Fibo QMI service running\n");
}

int main(void) {
    qmi_fibo_svc_main();
    qmi_dms_fibo_auto_set_pwrmgr_flag_req(1);
    return 0;
}
