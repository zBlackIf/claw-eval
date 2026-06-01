# OSPF/4/NBR_DOWN

## 告警解释

OSPF邻居状态变为Down。

**告警ID**: 1.3.6.1.2.1.14.16.2.2

**告警级别**: Warning

**告警类型**: 通信告警

## 告警参数

| 参数名称 | 参数含义 |
|----------|----------|
| RouterId | 本设备的Router ID |
| NbrRouterId | 邻居的Router ID |
| NbrIpAddr | 邻居的IP地址 |
| IfIpAddress | 本端接口IP地址 |
| IfName | 接口名称 |
| Reason | 邻居Down的原因 |

## 可能原因

1. 邻居设备重启或者邻居接口Down。
2. OSPF进程被删除。
3. OSPF接口配置发生变化（如区域变化、认证类型变化等）。
4. 链路故障。
5. Hello报文超时。

## 处理步骤

1. 使用**display ospf peer**命令检查OSPF邻居状态。
2. 检查物理链路是否正常。
3. 检查接口的IP地址配置是否正确。
4. 检查OSPF区域配置是否一致。
5. 检查OSPF认证配置是否一致。
6. 如果问题仍然存在，请收集告警信息和配置信息，并联系技术支持。

## 相关告警

- OSPF/2/NBR_CHG (邻居状态变化)
