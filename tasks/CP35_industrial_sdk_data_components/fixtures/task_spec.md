# Data 命名空间组件规格

## 1. CircularBuffer<T> — 环形缓冲区

命名空间: `MinqiaIndustrialComponentLibrary.Data`

### 要求
- 泛型实现，支持任意值类型
- 线程安全（使用 SemaphoreSlim 或 lock）
- 固定容量，满时覆盖最旧数据
- 提供方法: Write(T item), Read() -> T, TryRead(out T), Count, Capacity, Clear()
- 实现 IDisposable

## 2. AlarmManager — 报警管理器

命名空间: `MinqiaIndustrialComponentLibrary.Data`

### 要求
- AlarmSeverity 枚举: Info, Warning, Error, Critical
- AlarmEntry 类: Id, Timestamp, Severity, Source, Message, IsAcknowledged
- AlarmManager 类:
  - RaiseAlarm(severity, source, message) -> AlarmEntry
  - AcknowledgeAlarm(id) -> bool
  - GetActiveAlarms() -> IReadOnlyList<AlarmEntry>
  - GetAlarmHistory(count) -> IReadOnlyList<AlarmEntry>
  - event AlarmRaised / event AlarmAcknowledged
- 线程安全

## 3. LogLevel 枚举 + 扩展

命名空间: `MinqiaIndustrialComponentLibrary.Data`

### 要求
- LogLevel 枚举: Trace=0, Debug=1, Info=2, Warning=3, Error=4, Fatal=5
- LogLevelExtensions 静态类:
  - ToDisplayString(this LogLevel) -> string
  - ToColor(this LogLevel) -> ConsoleColor
  - IsEnabled(this LogLevel, LogLevel minLevel) -> bool
