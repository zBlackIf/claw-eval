#include "app_main.h"
#include "app_config.h"
#include "drv_key.h"

#include "ui_common.h"
#include "ui_home.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "lvgl.h"

static const char *TAG = "app_main";
static SemaphoreHandle_t s_lvgl_mutex = NULL;

SemaphoreHandle_t app_get_lvgl_mutex(void)
{
    return s_lvgl_mutex;
}

static void task_ui(void *arg)
{
    if (s_lvgl_mutex == NULL) {
        s_lvgl_mutex = xSemaphoreCreateMutex();
    }
    while (1) {
        if (xSemaphoreTake(s_lvgl_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            lv_timer_handler();
            xSemaphoreGive(s_lvgl_mutex);
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

static void task_ws_connect(void *arg)
{
    const app_config_t *cfg = app_config_get();
    ESP_LOGI(TAG, "connecting to ws: %s", cfg->ws_url);
    // websocket connect logic
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "app_main start");
    app_config_load();

    const app_config_t *cfg = app_config_get();
    ESP_LOGI(TAG, "device_id: %s, fw: %s", cfg->device_id, cfg->fw_version);

    // Initialize LVGL and display driver
    ESP_ERROR_CHECK(ui_common_init());

    // Start UI task
    xTaskCreate(task_ui, "task_ui", 8192, NULL, 5, NULL);

    // Start websocket connection task
    xTaskCreate(task_ws_connect, "task_ws", 4096, NULL, 3, NULL);

    ESP_LOGI(TAG, "all tasks started");
}
