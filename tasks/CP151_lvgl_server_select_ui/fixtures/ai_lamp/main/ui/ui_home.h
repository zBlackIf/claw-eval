#ifndef UI_HOME_H
#define UI_HOME_H

#include "lvgl.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

void ui_home_init(void);
void ui_home_show_boot_screen(void);
void ui_home_set_wifi_connected(bool connected);

#ifdef __cplusplus
}
#endif

#endif /* UI_HOME_H */
