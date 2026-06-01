/* qmi_csi_common.c - QMI CSI framework implementation */
#include "qmi_csi_common.h"
#include <stdio.h>
#include <string.h>

static qmi_csi_service_t g_services[QMI_CSI_MAX_SERVICES];
static int g_service_count = 0;

int qmi_csi_register(int service_id, void *cb) {
    if (g_service_count >= QMI_CSI_MAX_SERVICES) return -1;
    g_services[g_service_count].service_id = service_id;
    g_services[g_service_count].is_registered = 1;
    g_services[g_service_count].ind_cb = cb;
    g_service_count++;
    return 0;
}

int qmi_csi_send_ind(int client_handle, int msg_id, void *data, int len) {
    (void)data; (void)len;
    printf("QMI IND: client=%d msg=%d\n", client_handle, msg_id);
    return 0;
}
