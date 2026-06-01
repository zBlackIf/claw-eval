#include "include.h"

const uint8_t adv_data_const[] = {
    // Flags general discoverable, BR/EDR not supported
    0x02, 0x01, 0x06,
    // Manufacturer Specific Data: length=9, type=0xFF, company_id=0x0642
    // followed by 6 bytes placeholder for MAC address
    0x09, 0xff, 0x42, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

const uint8_t scan_data_const[] = {
};

u32 ble_get_scan_data(u8 *scan_buf, u32 buf_size)
{
    memset(scan_buf, 0, buf_size);
    u32 data_len = sizeof(scan_data_const);
    memcpy(scan_buf, scan_data_const, data_len);
    return data_len;
}

u32 ble_get_adv_data(u8 *adv_buf, u32 buf_size)
{
    memset(adv_buf, 0, buf_size);
    u32 data_len = sizeof(adv_data_const);
    memcpy(adv_buf, adv_data_const, data_len);

    // TODO: Fill MAC address from xcfg_cb.le_addr[0..5] into the
    // manufacturer specific data section (bytes after company ID).
    // This allows iOS apps to identify the device since iOS hides
    // the actual BLE MAC address from applications.

    return data_len;
}

void ble_adv_param_init(void)
{
    // Set advertising parameters
    uint8_t adv_type = 0;   // ADV_IND
    uint8_t own_addr_type = 0;
    uint8_t peer_addr_type = 0;
    uint8_t peer_addr[6] = {0};
    uint8_t channel_map = 0x07; // all 3 channels
    uint8_t filter_policy = 0;

    ble_set_adv_param(160, 160, adv_type, own_addr_type,
                      peer_addr_type, peer_addr, channel_map, filter_policy);
}
