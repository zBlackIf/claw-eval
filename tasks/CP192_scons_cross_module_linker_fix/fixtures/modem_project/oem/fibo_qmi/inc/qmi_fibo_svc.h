/* qmi_fibo_svc.h - Fibo OEM QMI Service */
#ifndef QMI_FIBO_SVC_H
#define QMI_FIBO_SVC_H

#define FIBO_SLEEP_RMT_SYNC_TIMEOUT 5000  /* 5 seconds */

/* Power management request handler */
int qmi_dms_fibo_auto_set_pwrmgr_flag_req(int flag);

/* Service initialization */
int qmi_fibo_svc_init(void);

/* Main service loop */
void qmi_fibo_svc_main(void);

#endif /* QMI_FIBO_SVC_H */
