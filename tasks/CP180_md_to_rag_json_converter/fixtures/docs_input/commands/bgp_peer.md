# peer

# peer

## 命令功能

**peer**命令用来配置BGP对等体。

## 命令格式

**peer** _ip-address_ **as-number** _as-number_

## 参数说明

| 参数 | 参数说明 | 取值 |
|------|----------|------|
| _ip-address_ | 指定对等体的IP地址 | 点分十进制格式 |
| _as-number_ | 指定对等体的AS号 | 整数形式，取值范围是1～4294967295 |

## 视图

BGP视图

## 缺省级别

2：配置级

## 使用指南

通过peer命令可以指定BGP对等体，并通过指定对等体的AS号来确定对等体的类型（IBGP或EBGP）。

## 使用实例

配置BGP对等体10.1.1.1，AS号为100：

```
<Huawei> system-view
[Huawei] bgp 200
[Huawei-bgp] peer 10.1.1.1 as-number 100
```
