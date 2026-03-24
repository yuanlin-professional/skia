# GpuTimer.h - GPU 计时器抽象接口

> 源文件: `tools/ganesh/GpuTimer.h`

## 概述

`GpuTimer.h` 定义了一个平台无关的 GPU 计时器抽象接口 `GpuTimer`，用于测量 GPU 命令流中操作的执行时间。该接口属于 Skia 的基准测试工具链（benchmarking infrastructure），为不同图形 API（OpenGL、Vulkan 等）的 GPU 时间查询提供了统一的抽象。

GPU 计时与 CPU 计时不同，它需要将"开始计时"和"停止计时"命令插入到 GPU 命令流中，等待 GPU 异步执行完成后才能读取结果。

## 架构位置

```
Skia 基准测试工具
├── tools/ganesh/
│   ├── GpuTimer.h              <-- 本文件：GPU 计时器抽象接口
│   ├── gl/GLTestContext.h      <-- OpenGL 测试上下文（可包含 GL 计时器实现）
│   └── vk/VkTestContext.h      <-- Vulkan 测试上下文（可包含 Vk 计时器实现）
└── bench/
    └── nanobench 相关文件       <-- 使用 GpuTimer 的基准测试程序
```

## 主要类与结构体

### `GpuTimer`
GPU 计时器的抽象基类，定义了计时器的完整生命周期接口。

```cpp
class GpuTimer {
public:
    explicit GpuTimer(bool disjointSupport);
    virtual ~GpuTimer();

    bool disjointSupport() const;
    void queueStart();
    [[nodiscard]] PlatformTimerQuery queueStop();

    enum class QueryStatus {
        kInvalid,   // 查询无效
        kPending,   // GPU 仍在执行
        kDisjoint,  // 查询完成，但因不连续 GPU 操作结果不可靠
        kAccurate   // 查询完成且结果可靠
    };

    virtual QueryStatus checkQueryStatus(PlatformTimerQuery) = 0;
    virtual std::chrono::nanoseconds getTimeElapsed(PlatformTimerQuery) = 0;
    virtual void deleteQuery(PlatformTimerQuery) = 0;

private:
    virtual PlatformTimerQuery onQueueTimerStart() const = 0;
    virtual void onQueueTimerStop(PlatformTimerQuery) const = 0;

    bool const         fDisjointSupport;
    PlatformTimerQuery fActiveTimer;
};
```

### `PlatformTimerQuery`
平台计时器查询的类型别名，实际为 `uint64_t`，用于存储各平台的查询句柄或 ID。

```cpp
using PlatformTimerQuery = uint64_t;
static constexpr PlatformTimerQuery kInvalidTimerQuery = 0;
```

### `QueryStatus` 枚举
描述计时器查询的四种状态，反映了 GPU 异步计算的特性。

## 公共 API 函数

### `GpuTimer(bool disjointSupport)`
构造函数。`disjointSupport` 参数指示该计时器是否能检测不连续的 GPU 操作（如 GPU 频率变化、上下文切换等），这会影响计时结果的可靠性。

### `queueStart()`
在 GPU 命令流中插入"开始计时"命令。调用前必须没有活动的计时器（通过 `SkASSERT` 检查）。

### `queueStop() -> PlatformTimerQuery`
在 GPU 命令流中插入"停止计时"命令。返回一个查询对象，可用于后续检查结果。标记为 `[[nodiscard]]`，编译器会在丢弃返回值时发出警告。

### `checkQueryStatus(PlatformTimerQuery) -> QueryStatus`
检查查询的当前状态。纯虚函数，需要平台具体实现。

### `getTimeElapsed(PlatformTimerQuery) -> std::chrono::nanoseconds`
获取计时器测量到的经过时间（纳秒精度）。仅在状态为 `kAccurate` 或 `kDisjoint` 时调用有意义。

### `deleteQuery(PlatformTimerQuery)`
释放查询相关的平台资源。

## 内部实现细节

### 模板方法模式

`queueStart()` 和 `queueStop()` 是模板方法，它们管理内部状态（`fActiveTimer`）并委托给子类的 `onQueueTimerStart()` 和 `onQueueTimerStop()` 虚函数：

```cpp
void queueStart() {
    SkASSERT(!fActiveTimer);
    fActiveTimer = this->onQueueTimerStart();
}

PlatformTimerQuery queueStop() {
    SkASSERT(fActiveTimer);
    this->onQueueTimerStop(fActiveTimer);
    return std::exchange(fActiveTimer, kInvalidTimerQuery);
}
```

### Disjoint 支持

GPU 在测量期间可能发生不连续事件（如频率调整、上下文切换），导致计时结果不准确。支持 disjoint 检测的 API（如 OpenGL 的 `GL_EXT_disjoint_timer_query`）可以标记这类查询为 `kDisjoint`，让调用者知道结果可能不可靠。

### 析构安全检查

```cpp
virtual ~GpuTimer() { SkASSERT(!fActiveTimer); }
```

析构时断言没有活动的计时器，确保调用者正确地停止了所有计时操作。

## 依赖关系

- **Skia 核心**：`include/core/SkTypes.h`（SkASSERT 等基础宏）
- **C++ 标准库**：`<chrono>`（时间类型）

## 设计模式与设计决策

1. **模板方法模式**：公共的 `queueStart()`/`queueStop()` 方法管理通用状态，将平台特定的实现委托给 `onQueueTimerStart()`/`onQueueTimerStop()` 虚函数。

2. **NVI（Non-Virtual Interface）模式**：虚函数被放在 private 部分，公共接口是非虚的，确保基类能够在调用前后执行断言检查。

3. **句柄式 API**：`PlatformTimerQuery` 使用 `uint64_t` 作为不透明句柄，既可以存储指针也可以存储整数 ID，适应不同平台的实现需求。

4. **四态查询模型**：`QueryStatus` 的四种状态完整地描述了 GPU 异步查询的生命周期，让调用者能够正确处理各种情况。

## 性能考量

- **零开销抽象**：虚函数调用的开销相对于 GPU 操作可忽略不计。
- **异步查询模型**：查询结果通过轮询获取（`checkQueryStatus`），避免了同步等待 GPU 的开销。调用者可以在等待 GPU 完成时执行其他工作。
- **纳秒精度**：使用 `std::chrono::nanoseconds` 提供高精度时间测量，满足 GPU 微基准测试的需求。
- **`[[nodiscard]]` 注解**：防止调用者忘记处理查询对象导致资源泄漏。

## 相关文件

- `tools/ganesh/gl/GLTestContext.h` - OpenGL 测试上下文，可能包含 GL 版本的计时器实现
- `tools/ganesh/vk/VkTestContext.h` - Vulkan 测试上下文，可能包含 Vulkan 版本的计时器实现
- `include/core/SkTypes.h` - Skia 基础类型和断言宏
