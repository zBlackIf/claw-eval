# Data模块组件开发任务

## 背景
参考现有 Communication/Modbus/ModbusTcpClient.cs 的代码风格，为项目新增 Data 命名空间下的组件。

## 要求创建以下文件：

### 1. Data/Buffer/CircularBuffer.cs
- 泛型环形缓冲区 CircularBuffer<T>
- 线程安全（使用 SemaphoreSlim 或 lock）
- 支持操作：Write(T item), Read() -> T, Peek() -> T, Clear()
- 属性：Count, Capacity, IsEmpty, IsFull
- 构造函数接受 capacity 参数
- 缓冲区满时Write应覆盖最旧数据
- 缓冲区空时Read应抛出 InvalidOperationException

### 2. Data/Alarm/AlarmManager.cs
- 报警管理器，管理工业报警事件
- AlarmEntry 类：Id, Message, Severity(enum), Timestamp, IsAcknowledged
- AlarmSeverity 枚举：Info, Warning, Error, Critical
- AlarmManager 类方法：RaiseAlarm, AcknowledgeAlarm, GetActiveAlarms, GetAlarmHistory, ClearAll
- 线程安全
- 支持报警回调 OnAlarmRaised event

### 3. Data/Log/LogLevel.cs
- 日志级别枚举：Trace, Debug, Info, Warning, Error, Fatal
- 使用 [Flags] attribute 如果适用
- 包含扩展方法类 LogLevelExtensions：ToDisplayString(), IsHigherThan(LogLevel other)

## 代码风格要求
- 命名空间格式：MinqiaIndustrialComponentLibrary.Data.XXX
- XML注释文档
- 使用 nullable reference types
- 遵循现有项目中的 async/await 模式
