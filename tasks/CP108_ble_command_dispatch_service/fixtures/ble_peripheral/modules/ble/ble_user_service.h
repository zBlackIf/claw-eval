#ifndef __BLE_USER_SERVICE_H
#define __BLE_USER_SERVICE_H

/*
PRIMARY_SERVICE, C7E6FAE0-xxxx (custom 128-bit UUID)
CHARACTERISTIC, C7E6FAE1 (TX), NOTIFY,
  CLIENT_CHARACTERISTIC_CONFIGURATION (handle 0x000F)
CHARACTERISTIC, C7E6FAE2 (RX), WRITE | WRITE_WITHOUT_RESPONSE (handle 0x0011)
*/

void ble_user_service_init(void);
void ble_user_cmd_process(void);

// TODO: declare ble_user_1s_proc() here

#endif
