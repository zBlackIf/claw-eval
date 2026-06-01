# hwEntityTemperatureThresholdNotification

## MIB节点信息

**OID**: 1.3.6.1.4.1.2011.5.25.31.2.1

**节点名称**: hwEntityTemperatureThresholdNotification

**所属MIB**: HUAWEI-ENTITY-EXTENT-MIB

**状态**: current

## 告警描述

设备温度超过告警阈值时产生此告警。当温度恢复到正常范围内时，产生恢复告警。

## 绑定变量

| 变量名 | OID | 说明 |
|--------|-----|------|
| hwEntityTemperature | 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.11 | 当前温度值 |
| hwEntityTemperatureThreshold | 1.3.6.1.4.1.2011.5.25.31.1.1.1.1.12 | 温度告警阈值 |
| entPhysicalName | 1.3.6.1.2.1.47.1.1.1.1.7 | 物理实体名称 |

## 触发条件

当实体温度（hwEntityTemperature）大于或等于温度告警阈值（hwEntityTemperatureThreshold）时触发。

## 恢复条件

当实体温度低于（温度告警阈值 - 温度恢复差值）时恢复。

## 对系统的影响

设备温度过高可能导致芯片工作异常或设备自动保护性关机。
