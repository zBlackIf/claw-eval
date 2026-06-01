#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    char device_id[32];
    char fw_version[16];
    char hw_version[16];
    char ws_url[128];
    char token[96];
} app_config_t;

esp_err_t app_config_load(void);
const app_config_t *app_config_get(void);

#ifdef __cplusplus
}
#endif
