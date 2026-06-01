#include "include.h"
#include "ble_service.h"

static att_service_handler_t       ff20_service;
static uint16_t ff22_client_config;

#define BLE_CMD_BUF_LEN     4
#define BLE_CMD_BUF_MASK    (BLE_CMD_BUF_LEN - 1)
#define BLE_RX_BUF_LEN      20


struct ble_cmd_t {
    u8 buf[BLE_RX_BUF_LEN];
    u8 len;
};

static struct ble_cmd_t ble_cmd_fifo[BLE_CMD_BUF_LEN];
static u8 ble_cmd_wr_idx;
static u8 ble_cmd_rd_idx;

static uint16_t current_con_handle = 0;

// TODO: Implement command dispatch table (package_entry_t)
// Format: {cmd_type, cmd_id, handler_function}
// Required commands:
//   - Handshake:    0xEA, 0x01
//   - Set Time:     0xEA, 0x04
//   - Set Battery:  0xEA, 0x07


static int service_read_callback(uint16_t con_handle, uint16_t attribute_handle, uint16_t offset, uint8_t *buffer, uint16_t buffer_size)
{
    // TODO: handle read requests
    return 0;
}

static int service_write_callback(uint16_t con_handle, uint16_t attribute_handle, ATT_TRANSACTION_MODE transaction_mode, uint16_t offset, uint8_t *buffer, uint16_t buffer_size)
{
    // TODO: Implement write callback
    // 1. Check if attribute_handle == 0x0011 (RX characteristic)
    // 2. Printf hex dump of received data
    // 3. Dispatch to command handler based on cmd_type + cmd_id
    return 0;
}

void ble_user_service_init(void)
{
    printf("ble_user_service_init\n");

    // get service handle range
    uint16_t start_handle = 0x000C;
    uint16_t end_handle   = 0x0011;

    ff20_service.start_handle = start_handle;
    ff20_service.end_handle   = end_handle;
    ff20_service.read_callback  = &service_read_callback;
    ff20_service.write_callback = &service_write_callback;
    att_register_service_handler(&ff20_service);
}

// TODO: Implement ble_user_1s_proc()
// - Called every 1 second from system tick
// - If BLE is connected, send a heartbeat notify packet via handle 0x000E
// - If not connected, do nothing

void ble_user_cmd_process(void)
{
    // Process queued commands
    while (ble_cmd_rd_idx != ble_cmd_wr_idx) {
        struct ble_cmd_t *cmd = &ble_cmd_fifo[ble_cmd_rd_idx & BLE_CMD_BUF_MASK];
        // TODO: process command
        ble_cmd_rd_idx++;
    }
}
