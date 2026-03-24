# SkTraceMemoryDump

> 源文件: `include/core/SkTraceMemoryDump.h`

## 概述
SkTraceMemoryDump 是 Skia 提供的内存跟踪接口,用于将 Skia 对象的内存使用情况导出到外部跟踪系统。该接口作为参数传递给 Skia 对象的内存转储方法,由嵌入器(embedder)实现具体的数据收集逻辑,支持不同粒度的内存统计和跟踪。

## 架构位置
SkTraceMemoryDump 位于 Skia 的核心(core)模块中,是内存诊断和性能分析子系统的核心接口。它不依赖于任何特定的图形后端,是一个纯抽象的跟踪协议层,连接 Skia 内部的内存管理和外部监控系统(如 Chrome 的 tracing 基础设施)。

## 主要类与结构体

### SkTraceMemoryDump
内存跟踪的抽象接口,定义了统一的内存数据导出协议。

**继承关系**: 无父类(纯抽象基类)

**关键成员变量**:
无公共成员变量(纯抽象接口)

**关键枚举类型**:

#### LevelOfDetail
定义内存转储的详细程度级别:
- `kLight_LevelOfDetail`: 轻量级转储,仅获取总内存使用量(通常只包含汇总数据)
- `kObjectsBreakdowns_LevelOfDetail`: 详细转储,包含缓存中对象的详细分解信息

## 公共 API 函数

### `dumpNumericValue()`
```cpp
virtual void dumpNumericValue(const char* dumpName,
                              const char* valueName,
                              const char* units,
                              uint64_t value) = 0;
```
- **功能**: 向跟踪基础设施追加一条新的内存转储记录(一行数据)
- **参数**:
  - `dumpName`: 被转储项的绝对路径名称(使用斜杠分隔),例如 "skia/CacheX/EntryY"
  - `valueName`: 列名,表示值的类型,例如 "size"、"active_size"、"number_of_objects"(长生命周期字符串,不会被复制)
  - `units`: 值的单位,例如 "bytes"、"objects"(长生命周期字符串,不会被复制)
  - `value`: 实际的数值数据
- **返回值**: 无
- **说明**: 如果 dumpName 不存在则创建新条目,否则向已有条目追加新列

### `dumpStringValue()`
```cpp
virtual void dumpStringValue(const char* dumpName,
                             const char* valueName,
                             const char* value)
```
- **功能**: 转储字符串类型的值
- **参数**: 与 `dumpNumericValue()` 类似,但值为字符串类型
- **返回值**: 无
- **说明**: 默认实现为空,嵌入器可选择性实现

### `setMemoryBacking()`
```cpp
virtual void setMemoryBacking(const char* dumpName,
                              const char* backingType,
                              const char* backingObjectId) = 0;
```
- **功能**: 为已存在的转储条目设置内存支持信息
- **参数**:
  - `dumpName`: 转储条目名称
  - `backingType`: 支持内存的类型
  - `backingObjectId`: 支持对象的 ID
- **返回值**: 无
- **说明**: 由嵌入器使用,将通过 `dumpNumericValue()` 转储的内存与相应的支持转储关联

### `setDiscardableMemoryBacking()`
```cpp
virtual void setDiscardableMemoryBacking(
    const char* dumpName,
    const SkDiscardableMemory& discardableMemoryObject) = 0;
```
- **功能**: 设置可丢弃内存的支持信息(专用特化版本)
- **参数**:
  - `dumpName`: 转储条目名称
  - `discardableMemoryObject`: 可丢弃内存对象引用
- **返回值**: 无

### `getRequestedDetails()`
```cpp
virtual LevelOfDetail getRequestedDetails() const = 0;
```
- **功能**: 返回请求的转储详细程度级别
- **返回值**: LevelOfDetail 枚举值
- **说明**: 转储的粒度应与此参数匹配,但不应影响报告的总大小,只影响子条目的粒度

### `shouldDumpWrappedObjects()`
```cpp
virtual bool shouldDumpWrappedObjects() const
```
- **功能**: 查询是否应转储包装对象
- **返回值**: 默认返回 true
- **说明**: 包装对象来自 Skia 外部,可能在外部独立跟踪

### `dumpWrappedState()`
```cpp
virtual void dumpWrappedState(const char* dumpName, bool isWrappedObject)
```
- **功能**: 当 `shouldDumpWrappedObjects()` 返回 true 时,填充被转储项是否为包装对象的信息
- **参数**:
  - `dumpName`: 转储条目名称
  - `isWrappedObject`: 是否为包装对象
- **返回值**: 无
- **说明**: 默认实现为空

### `shouldDumpUnbudgetedObjects()`
```cpp
virtual bool shouldDumpUnbudgetedObjects() const
```
- **功能**: 查询是否应转储非预算对象
- **返回值**: 默认返回 true
- **说明**: 仅在转储 Graphite 内存统计时使用,非预算对象可能来自客户端的包装对象或 Skia 创建但由客户端持有的对象

### `dumpBudgetedState()`
```cpp
virtual void dumpBudgetedState(const char* dumpName, bool isBudgeted)
```
- **功能**: 转储对象的预算状态信息
- **参数**:
  - `dumpName`: 转储条目名称
  - `isBudgeted`: 是否为预算内对象
- **返回值**: 无
- **说明**: 仅在转储 Graphite 内存统计时使用,默认实现为空

### `shouldDumpSizelessObjects()`
```cpp
virtual bool shouldDumpSizelessObjects() const
```
- **功能**: 查询是否应转储无大小的非纹理对象(如 Sampler、pipeline 等)
- **返回值**: 默认返回 false
- **说明**: 无内存的纹理始终会被转储,仅在转储 Graphite 内存统计时使用

## 内部实现细节

### 抽象接口设计
SkTraceMemoryDump 采用纯虚函数设计,所有核心方法都必须由嵌入器实现。这种设计允许不同的嵌入环境(如 Chrome、Android、自定义应用)实现各自的跟踪后端,而无需修改 Skia 代码。

### 内存转储层次结构
通过 `dumpName` 的斜杠分隔路径(例如 "skia/GpuCache/Texture/12345"),系统支持构建层次化的内存视图。这允许在跟踪工具中以树形结构展示内存使用情况。

### 生命周期管理
接口禁止拷贝构造和赋值操作,确保跟踪对象的唯一性。虚析构函数设为 protected,防止通过基类指针删除对象,生命周期由嵌入器控制。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkTypes.h | 基础类型定义和 SK_API 宏 |
| SkDiscardableMemory | 可丢弃内存的抽象(前向声明) |

### 被依赖的模块
该接口被以下模块依赖:
- **GrContext**: GPU 上下文的内存统计
- **SkResourceCache**: 资源缓存的内存跟踪
- **Graphite 后端**: 新图形后端的内存诊断
- **各类 Skia 对象**: 实现 `dumpMemoryStatistics()` 方法的对象

## 设计模式与设计决策

### 策略模式(Strategy Pattern)
SkTraceMemoryDump 是典型的策略模式应用:将内存跟踪的"算法"(如何收集和报告数据)与使用它的对象分离。Skia 对象通过此接口导出数据,但不关心数据如何存储或传输。

### 依赖倒置原则(DIP)
高层模块(Skia 对象)依赖于抽象(SkTraceMemoryDump 接口),而非具体实现。这使得 Skia 可以在不同环境中使用,无需修改核心代码。

### 接口隔离原则(ISP)
提供了多个可选实现的虚函数(如 `dumpStringValue()`、`shouldDumpWrappedObjects()`),允许嵌入器根据需求选择性实现功能。

## 性能考量

### 字符串生命周期
`valueName` 和 `units` 参数要求为长生命周期字符串,不会被复制。这是一个关键的性能优化:避免在每次转储时进行字符串分配和复制,因为这些字符串通常是编译期常量(如 "bytes"、"size")。

### 条件转储
通过 `LevelOfDetail` 枚举,调用者可以控制转储的详细程度。在生产环境中可使用轻量级转储减少开销,而在调试时使用详细转储获取完整信息。

### 可选功能
`shouldDumpWrappedObjects()` 和 `shouldDumpUnbudgetedObjects()` 等查询函数允许在运行时跳过不需要的数据收集,避免不必要的性能损耗。

## 平台相关说明

### Chrome 集成
在 Chrome 浏览器中,该接口的实现连接到 Chrome 的 tracing 基础设施(chrome://tracing),允许开发者在性能分析工具中查看 Skia 的内存使用。

### Android 集成
Android 系统可能使用该接口与系统级内存跟踪工具(如 memtrack HAL)集成,提供全系统的图形内存视图。

### 独立应用
独立应用可以实现简单的日志记录版本,将内存统计输出到文件或控制台,用于离线分析。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkDiscardableMemory.h | 定义可丢弃内存抽象 |
| src/core/SkResourceCache.h | 实现内存转储的资源缓存 |
| src/gpu/GrContext.cpp | GPU 上下文的内存统计实现 |
| include/core/SkTypes.h | 提供基础类型定义 |
