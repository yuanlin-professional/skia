# SkEventTracer

> 源文件: include/utils/SkEventTracer.h, src/utils/SkEventTracer.cpp

## 概述

SkEventTracer 是 Skia 内部追踪系统与外部追踪框架之间的接口抽象。它定义了 Skia 如何报告性能追踪事件,允许外部实体(如 Chrome 浏览器)集成和消费这些事件。通过子类化 SkEventTracer 并提供实例,外部工具可以捕获 Skia 的执行细节,用于性能分析、调试和监控。

主要功能:
- 定义追踪事件接口(开始、结束、即时事件)
- 管理类别组启用状态
- 支持全局单例追踪器
- 提供默认的空操作追踪器
- 支持进程退出时的清理回调
- 与 Chrome 的追踪系统对齐

## 架构位置

SkEventTracer 位于 Skia 的 utils 模块中,作为追踪基础设施:

```
Skia Graphics Library
├── Core
│   └── SkTraceEvent.h (追踪宏,用于标记代码)
├── Utils
│   └── SkEventTracer (追踪接口抽象) ← 当前模块
│       ├── SkEventTracer (抽象基类)
│       └── SkDefaultEventTracer (默认实现)
└── External Integration
    └── Chrome Tracing System (外部消费者)
```

Skia 内部使用 SkTraceEvent.h 中的宏标记代码点,这些宏调用 SkEventTracer 实例的方法。

## 主要类与结构体

### SkEventTracer

**类型**: 抽象基类

**继承关系**:
- 基类,外部追踪器需要继承此类

**关键类型定义**:

| 类型 | 定义 | 说明 |
|-----|------|------|
| Handle | uint64_t | 追踪事件句柄 |

### CategoryGroupEnabledFlags 枚举

| 标志 | 值 | 说明 |
|-----|---|------|
| kEnabledForRecording_CategoryGroupEnabledFlags | 1 << 0 | 为记录模式启用 |
| kEnabledForMonitoring_CategoryGroupEnabledFlags | 1 << 1 | 为监控模式启用 |
| kEnabledForEventCallback_CategoryGroupEnabledFlags | 1 << 2 | 为事件回调启用 |

**用途**:
- 追踪宏将指针值作为布尔值使用
- 非零值表示该类别启用
- 具体标志用于区分启用原因

### SkDefaultEventTracer

**类型**: 默认实现类

**继承关系**:
```
SkEventTracer
  └── SkDefaultEventTracer
```

**特性**:
- 所有方法为空操作(no-op)
- 用于未设置自定义追踪器时
- 单例模式,静态分配

## 公共 API 函数

### SetInstance

```cpp
static bool SetInstance(SkEventTracer* tracer);
```

**功能**: 设置全局追踪器实例。

**参数**:
- `tracer`: 追踪器实例指针(转移所有权)

**返回值**:
- `true`: 首次调用,成功设置
- `false`: 已设置过,传入的 tracer 被删除

**重要特性**:
- **仅首次成功**: 使用原子 compare_exchange_strong 确保线程安全
- **不释放**: 成功设置的追踪器永不销毁(避免多线程竞争)
- **退出回调**: 成功时注册 atexit 回调,调用 onExit()
- **所有权转移**: 无论成功与否,tracer 所有权都转移

**内存管理**:
```cpp
SK_INTENTIONALLY_LEAKED(tracer);  // 标记为故意泄漏
atexit([]() { GetInstance()->onExit(); });
```

### GetInstance

```cpp
static SkEventTracer* GetInstance();
```

**功能**: 获取全局追踪器实例。

**返回值**:
- 如果设置过自定义追踪器,返回该实例
- 否则返回静态的 SkDefaultEventTracer 实例

**线程安全**:
- 使用 std::atomic 和 memory_order_acquire 保证可见性
- 默认追踪器使用静态局部变量(线程安全初始化)

**特性**:
- 首次调用会初始化默认追踪器
- 后续调用直接返回,无需锁

### getCategoryGroupEnabled (纯虚函数)

```cpp
virtual const uint8_t* getCategoryGroupEnabled(const char* name) = 0;
```

**功能**: 获取类别组的启用状态指针。

**参数**:
- `name`: 类别组名称(如 "skia", "gpu")

**返回值**:
- 指向 uint8_t 的指针,值为 CategoryGroupEnabledFlags 的组合
- 指针必须在整个进程生命周期内有效

**使用模式**:
```cpp
const uint8_t* enabled = tracer->getCategoryGroupEnabled("skia");
if (*enabled) {
    // 该类别启用,添加追踪事件
}
```

### getCategoryGroupName (纯虚函数)

```cpp
virtual const char* getCategoryGroupName(
    const uint8_t* categoryEnabledFlag
) = 0;
```

**功能**: 从启用标志指针反向获取类别组名称。

**参数**:
- `categoryEnabledFlag`: 由 getCategoryGroupEnabled 返回的指针

**返回值**:
- 类别组名称字符串

**用途**: 反向查找,用于日志或调试。

### addTraceEvent (纯虚函数)

```cpp
virtual SkEventTracer::Handle addTraceEvent(
    char phase,
    const uint8_t* categoryEnabledFlag,
    const char* name,
    uint64_t id,
    int32_t numArgs,
    const char** argNames,
    const uint8_t* argTypes,
    const uint64_t* argValues,
    uint8_t flags
) = 0;
```

**功能**: 添加追踪事件。

**参数**:
- `phase`: 事件阶段(B=开始, E=结束, I=即时, 等)
- `categoryEnabledFlag`: 类别启用标志指针
- `name`: 事件名称
- `id`: 事件 ID(用于关联开始/结束事件)
- `numArgs`: 参数数量
- `argNames`: 参数名称数组
- `argTypes`: 参数类型数组
- `argValues`: 参数值数组(编码为 uint64_t)
- `flags`: 追踪标志

**返回值**:
- 事件句柄,用于后续更新持续时间

**常见阶段字符**:
- `'B'`: Begin(开始)
- `'E'`: End(结束)
- `'X'`: Complete(完整事件)
- `'I'`: Instant(即时事件)
- `'C'`: Counter(计数器)

### updateTraceEventDuration (纯虚函数)

```cpp
virtual void updateTraceEventDuration(
    const uint8_t* categoryEnabledFlag,
    const char* name,
    SkEventTracer::Handle handle
) = 0;
```

**功能**: 更新追踪事件的持续时间。

**参数**:
- `categoryEnabledFlag`: 类别启用标志
- `name`: 事件名称
- `handle`: 由 addTraceEvent 返回的句柄

**用途**: 对于持续时间事件,结束时调用此方法更新时长。

### newTracingSection (可选实现)

```cpp
virtual void newTracingSection(const char* name) {}
```

**功能**: 可选方法,开始新的追踪分段。

**参数**:
- `name`: 分段名称

**默认行为**: 空操作

**用途**: 允许将追踪输出分割到不同的文件或区域。

### onExit (可选实现)

```cpp
virtual void onExit() {}
```

**功能**: 进程退出时调用的清理方法。

**上下文**: 在 atexit 回调中调用,可能与其他线程并发

**线程安全**: 必须是线程安全的实现

**用途**: 刷新缓冲区到磁盘、关闭文件等

## 内部实现细节

### 全局状态管理

#### 原子指针

```cpp
static std::atomic<SkEventTracer*> gUserTracer{nullptr};
```

**特性**:
- 使用 std::atomic 保证线程安全
- 初始化为 nullptr
- 仅写入一次(SetInstance 成功时)

#### SetInstance 实现

```cpp
bool SkEventTracer::SetInstance(SkEventTracer* tracer) {
    SkEventTracer* expected = nullptr;
    if (!gUserTracer.compare_exchange_strong(expected, tracer)) {
        delete tracer;  // 设置失败,删除
        return false;
    }
    // 成功,标记为故意泄漏
    SK_INTENTIONALLY_LEAKED(tracer);

    // 注册退出回调
    atexit([]() { GetInstance()->onExit(); });

    return true;
}
```

**原子操作解释**:
- `compare_exchange_strong(expected, tracer)`:
  - 如果 gUserTracer == expected(nullptr),则设置为 tracer 并返回 true
  - 否则将 gUserTracer 的值写入 expected,返回 false

**atexit 回调**:
- lambda 捕获为空,仅调用 GetInstance()
- 即使返回默认追踪器,onExit() 也是安全的空操作

#### GetInstance 实现

```cpp
SkEventTracer* SkEventTracer::GetInstance() {
    if (auto tracer = gUserTracer.load(std::memory_order_acquire)) {
        return tracer;
    }
    static SkDefaultEventTracer* defaultTracer = new SkDefaultEventTracer;
    return defaultTracer;
}
```

**内存顺序**:
- `memory_order_acquire`: 确保 tracer 的初始化对当前线程可见
- 配合 SetInstance 中的 `compare_exchange_strong`(隐含 release 语义)

**默认追踪器**:
- 使用静态局部变量,C++11 保证线程安全初始化
- new 分配但永不删除(进程生命周期)

### SkDefaultEventTracer 实现

所有方法都是空操作:

```cpp
class SkDefaultEventTracer : public SkEventTracer {
    Handle addTraceEvent(...) override { return 0; }

    void updateTraceEventDuration(...) override {}

    const uint8_t* getCategoryGroupEnabled(const char* name) override {
        static uint8_t no = 0;
        return &no;  // 返回指向 0 的指针(类别未启用)
    }

    const char* getCategoryGroupName(const uint8_t*) override {
        static const char* stub = "stub";
        return stub;
    }

    void newTracingSection(const char*) override {}
};
```

**设计目的**:
- 提供默认行为,避免空指针检查
- 性能开销极小(内联的空函数)
- 启用标志返回 0,使追踪宏快速跳过

### 与 Chrome 追踪系统的对齐

#### 兼容性注释

```cpp
// These values must be in sync with macro values in
// trace_event.h in chromium.
```

#### 类别组指针模式

Chrome 使用指针值作为快速启用检查:
```cpp
const uint8_t* enabled = getCategoryGroupEnabled("skia");
if (*enabled) {  // 快速检查,无函数调用
    addTraceEvent(...);
}
```

**优势**:
- 避免每次追踪都调用函数
- 启用标志更改时自动生效(所有指针都指向同一位置)

#### 事件参数编码

argValues 使用 uint64_t 编码所有类型:
- 整数: 直接存储
- 指针: reinterpret_cast
- 浮点: 通过 union 或 memcpy
- 字符串: 存储 const char* 指针

argTypes 指示如何解码:
- Chrome 定义的类型枚举
- Skia 不直接使用,由追踪宏处理

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 说明 |
|-----|------|------|
| SkTypes.h | 核心类型 | 类型定义和宏 |
| SkMacros.h | 宏工具 | SK_INTENTIONALLY_LEAKED |
| <atomic> | C++ 标准库 | 原子操作 |
| <stdlib.h> | C 标准库 | atexit |

### 被依赖的模块

| 模块 | 使用场景 | 说明 |
|-----|---------|------|
| SkTraceEvent.h | 追踪宏 | 内部使用 GetInstance() |
| Skia 核心代码 | 性能追踪 | 通过宏标记关键路径 |
| Chrome | 追踪集成 | 提供自定义 SkEventTracer 实现 |
| Android | 性能分析 | 集成到 Android 追踪系统 |

## 设计模式与设计决策

### 单例模式 (Singleton)

全局追踪器实例:
- **静态访问**: 通过 GetInstance() 获取
- **延迟初始化**: 首次调用时创建默认追踪器
- **线程安全**: 使用 std::atomic 和静态局部变量

**变体**: 允许外部设置(SetInstance),但仅一次。

### 策略模式 (Strategy)

SkEventTracer 定义接口,外部提供实现:
- **Chrome 策略**: 将事件写入 Chrome 追踪系统
- **文件策略**: 写入文件(JSON 格式)
- **空策略**: 默认的无操作实现

### 模板方法模式 (Template Method)

onExit 的可选实现:
- 基类提供默认空实现
- 子类可选择性重写
- 在 atexit 回调中统一调用

### 故意泄漏 (Intentional Leak)

SetInstance 成功后不释放:
- **原因**: 避免多线程竞争(其他线程可能正在使用)
- **标记**: SK_INTENTIONALLY_LEAKED 告知静态分析工具
- **替代**: onExit() 提供清理机会

### 快速路径优化

类别启用检查:
- 返回指针而非布尔值
- 调用者缓存指针,快速解引用
- 避免重复的函数调用开销

### 原子操作与内存顺序

精细的内存顺序控制:
- `compare_exchange_strong`: 隐含 release/acquire 语义
- `load(memory_order_acquire)`: 确保初始化可见

**性能**: 比使用互斥锁更轻量。

### 纯虚接口

SkEventTracer 是抽象类:
- 强制子类实现所有核心方法
- 仅 onExit 和 newTracingSection 有默认实现
- 清晰的契约定义

### atexit 回调

使用 lambda 而非函数指针:
- 无需捕获,避免分配
- 通过 GetInstance() 间接调用,适应默认追踪器

## 性能考量

### 快速禁用路径

启用检查的性能:
```cpp
const uint8_t* enabled = getCategoryGroupEnabled("skia");
if (*enabled) {  // 单次内存读取
    // 追踪代码
}
```

**开销**: 一次指针解引用(~1 纳秒)

### 默认追踪器开销

SkDefaultEventTracer 的性能:
- getCategoryGroupEnabled 返回静态 0
- 所有方法内联为空
- 分支预测友好(始终不执行追踪)

### 原子操作开销

GetInstance 的性能:
- `load(memory_order_acquire)`: ~10 纳秒
- 比互斥锁快 100 倍
- 无竞争(写入仅一次)

### 类别组缓存

外部实现通常缓存类别组:
```cpp
// 初始化时
static const uint8_t* g_skia_enabled =
    tracer->getCategoryGroupEnabled("skia");

// 使用时
if (*g_skia_enabled) { ... }
```

**效果**: 避免重复的字符串查找。

### 参数编码

argValues 使用 uint64_t 数组:
- 紧凑内存布局
- 避免类型擦除的虚函数开销
- 解码成本推迟到追踪后端

### atexit 回调成本

注册回调的开销:
- 仅在 SetInstance 成功时调用一次
- atexit 内部使用链表,O(1) 注册
- 退出时按注册相反顺序调用

### 内存占用

```
sizeof(SkEventTracer) ≈ 8 bytes (虚表指针)
sizeof(SkDefaultEventTracer) ≈ 8 bytes
sizeof(gUserTracer) = 8 bytes (指针)
```

极小的全局开销。

### 追踪事件开销

addTraceEvent 的性能取决于实现:
- Chrome 实现: ~100-500 纳秒(写入共享缓冲区)
- 文件实现: 可能更慢(I/O 操作)
- 默认实现: ~0 纳秒(空操作)

**建议**: 仅在关键路径使用追踪。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/utils/SkEventTracer.h | 公共接口声明 |
| src/utils/SkEventTracer.cpp | 实现代码 |
| src/core/SkTraceEvent.h | 追踪宏定义(内部) |
| include/core/SkTypes.h | 核心类型定义 |
| include/private/base/SkMacros.h | 宏工具 |

**外部集成**:
- Chromium: src/base/trace_event/trace_event.h
- Android: frameworks/base/core/jni/android_util_AssetManager.cpp
