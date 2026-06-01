#ifndef __BLE_SERVICE_H
#define __BLE_SERVICE_H

#include "ble_profile.h"

#define CCCD_DFT    0

void ble_service_init(void);

// SDK API stubs (provided by libwireless.a)
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int bool;

typedef enum {
    ATT_TRANSACTION_MODE_NONE = 0,
    ATT_TRANSACTION_MODE_ACTIVE,
    ATT_TRANSACTION_MODE_EXECUTE,
} ATT_TRANSACTION_MODE;

typedef int (*att_read_callback_t)(uint16_t con_handle, uint16_t attribute_handle, uint16_t offset, uint8_t *buffer, uint16_t buffer_size);
typedef int (*att_write_callback_t)(uint16_t con_handle, uint16_t attribute_handle, ATT_TRANSACTION_MODE trans_mode, uint16_t offset, uint8_t *buffer, uint16_t buffer_size);
typedef void (*att_event_callback_t)(uint8_t event_type, uint16_t con_handle, uint16_t attribute_handle);

typedef struct {
    uint16_t start_handle;
    uint16_t end_handle;
    att_read_callback_t read_callback;
    att_write_callback_t write_callback;
    att_event_callback_t event_handler;
} att_service_handler_t;

// SDK functions (extern, provided by library)
extern void att_register_service_handler(att_service_handler_t *handler);
extern int ble_att_server_notify(uint16_t con_handle, uint16_t attribute_handle, const uint8_t *value, uint16_t value_len);
extern void ble_set_adv_param(uint16_t adv_int_min, uint16_t adv_int_max, uint8_t adv_type, uint8_t own_addr_type, uint8_t peer_addr_type, uint8_t *peer_addr, uint8_t channel_map, uint8_t filter_policy);

// Global config structure (provided by platform)
typedef struct {
    u8 le_addr[6];
    // ... other fields
} xcfg_cb_t;

extern xcfg_cb_t xcfg_cb;

#endif
