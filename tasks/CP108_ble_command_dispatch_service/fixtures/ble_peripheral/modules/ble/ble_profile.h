#ifndef __BLE_PROFILE_H
#define __BLE_PROFILE_H

//
// GATT Profile Handle Map (new layout with 1812 FOTA + custom service)
//
// FOTA Service (UUID 0x1812): handles 0x0001 ~ 0x000B
#define ATT_SERVICE_1812_START_HANDLE           0x0001
#define ATT_SERVICE_1812_END_HANDLE             0x000B

// Custom User Service (UUID C7E6FAE0-...): handles 0x000C ~ 0x0011
#define ATT_SERVICE_C7E6FAE0_START_HANDLE       0x000C
#define ATT_SERVICE_C7E6FAE0_END_HANDLE         0x0011

// TX Characteristic (C7E6FAE1) - NOTIFY
#define ATT_CHARACTERISTIC_C7E6FAE1_VALUE_HANDLE        0x000E
// TX Client Characteristic Configuration
#define ATT_CHARACTERISTIC_C7E6FAE1_CLIENT_CONFIG_HANDLE 0x000F

// RX Characteristic (C7E6FAE2) - WRITE | WRITE_WITHOUT_RESPONSE
#define ATT_CHARACTERISTIC_C7E6FAE2_VALUE_HANDLE        0x0011

extern const uint8_t profile_data[];

#endif
