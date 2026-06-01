/* qmi_csi_common.h - QMI Common Service Interface */
#ifndef QMI_CSI_COMMON_H
#define QMI_CSI_COMMON_H

#define QMI_CSI_MAX_SERVICES 32

typedef struct {
    int service_id;
    int is_registered;
    void (*ind_cb)(int client_handle, int msg_id, void *data);
} qmi_csi_service_t;

int qmi_csi_register(int service_id, void *cb);
int qmi_csi_send_ind(int client_handle, int msg_id, void *data, int len);

#endif /* QMI_CSI_COMMON_H */
