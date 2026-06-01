# display ip routing-table

## 命令功能

**display ip routing-table**命令用来查看IPv4路由表的摘要信息。

## 命令格式

**display ip routing-table** [ _vpn-instance_ _vpn-instance-name_ ] [ _ip-address_ [ _mask_ | _mask-length_ ] [ longer-match ] ]

## 参数说明

| 参数 | 参数说明 | 取值 |
|------|----------|------|
| _vpn-instance-name_ | 指定VPN实例的名称 | 字符串形式，不支持空格，区分大小写，长度范围是1～31 |
| _ip-address_ | 指定目的IP地址 | 点分十进制格式 |
| _mask_ | 指定掩码 | 点分十进制格式 |
| _mask-length_ | 指定掩码长度 | 整数形式，取值范围是0～32 |

## 视图

所有视图

## 缺省级别

1：监控级

## 使用指南

使用display ip routing-table命令可以查看路由表中各路由协议路由的摘要信息，包括路由的目的地址/掩码长度、协议类型、优先级、开销值、下一跳和出接口。

## 使用实例

查看IPv4路由表的摘要信息：

```
<Huawei> display ip routing-table
Route Flags: R - relay, D - download to fib
------------------------------------------------------------------------------
Routing Tables: Public
         Destinations : 12        Routes : 12

Destination/Mask    Proto   Pre  Cost      Flags NextHop         Interface
127.0.0.0/8         Direct  0    0           D   127.0.0.1       InLoopBack0
127.0.0.1/32        Direct  0    0           D   127.0.0.1       InLoopBack0
192.168.1.0/24      Direct  0    0           D   192.168.1.1     GE0/0/1
192.168.1.1/32      Direct  0    0           D   127.0.0.1       GE0/0/1
```

## 相关主题

- [ip route-static](../ip_route-static/ip_route-static.md)
- [display ip routing-table statistics](../display_ip_routing-table_statistics/display_ip_routing-table_statistics.md)
