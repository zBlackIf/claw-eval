#ifndef __DRV_KEY_H__
#define __DRV_KEY_H__

#include "esp_err.h"

typedef enum {
    DRV_KEY_NONE = 0,
    DRV_KEY_UP,
    DRV_KEY_DOWN,
    DRV_KEY_LEFT,
    DRV_KEY_RIGHT,
    DRV_KEY_MIDDLE,
} drv_key_t;

esp_err_t drv_key_init(void);
esp_err_t drv_key_read(drv_key_t *key);

#endif /* __DRV_KEY_H__ */
