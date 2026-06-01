# interface vlanif

## 命令功能

**interface vlanif**命令用来创建VLANIF接口并进入VLANIF接口视图，或者进入已创建的VLANIF接口视图。

**undo interface vlanif**命令用来删除VLANIF接口。

## 命令格式

**interface vlanif** _vlan-id_

**undo interface vlanif** _vlan-id_

## 参数说明

| 参数 | 参数说明 | 取值 |
|------|----------|------|
| _vlan-id_ | 指定VLAN编号 | 整数形式，取值范围是1～4094 |

## 视图

系统视图

## 缺省级别

2：配置级

## 使用指南

VLANIF接口是一种三层逻辑接口，可以实现不同VLAN之间的三层互通。创建VLANIF接口之前，需要先创建对应的VLAN。

### 注意事项

- 一个VLAN只能创建一个VLANIF接口
- 删除VLANIF接口前需确认已无业务使用该接口

## 使用实例

创建VLANIF100接口：

```
<Huawei> system-view
[Huawei] interface vlanif 100
[Huawei-Vlanif100]
```
