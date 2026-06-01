#include "include.h"
#include "func.h"

#if FUNC_BT_EN

AT(.text.app.proc.bt)
void func_bt_sub_process(void)
{
    ble_app_proc();
}

AT(.text.app.proc.bt)
void func_bt_process(void)
{
    func_process();
    func_bt_sub_process();
}

AT(.text.app.proc.bt)
void func_bt_enter(void)
{
    printf("func_bt_enter\n");
    ble_setup();
}

AT(.text.app.proc.bt)
void func_bt_exit(void)
{
    printf("func_bt_exit\n");
}

AT(.text.app.proc.bt)
void func_bt_init(void)
{
    printf("func_bt_init\n");
}

#endif
