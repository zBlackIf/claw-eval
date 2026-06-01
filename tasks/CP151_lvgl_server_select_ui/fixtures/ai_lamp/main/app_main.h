#pragma once

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#ifdef __cplusplus
extern "C" {
#endif

void app_main(void);
SemaphoreHandle_t app_get_lvgl_mutex(void);

#ifdef __cplusplus
}
#endif
