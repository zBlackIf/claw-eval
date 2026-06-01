#include "app_config.h"
#include <string.h>

static app_config_t g_cfg = {
    .device_id = "H1-00001234",
    .fw_version = "1.2.0",
    .hw_version = "H1-REV2",
    .ws_url = "ws://20.tcp.vip.cpolar.cn:10244",
    .token = "",
};

esp_err_t app_config_load(void)
{
    // load from NVS in real implementation
    return ESP_OK;
}

const app_config_t *app_config_get(void)
{
    return &g_cfg;
}
