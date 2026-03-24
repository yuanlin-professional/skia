# TestContext

> 源文件：tools/ganesh/TestContext.h, tools/ganesh/TestContext.cpp

## 概述

TestContext 是 Skia Ganesh 测试框架中的核心抽象类，用于管理离屏 3D 渲染上下文。该类专门为 Skia 的内部测试需求设计，提供了跨平台的 GPU 上下文管理、同步控制和性能测量功能。

TestContext 的主要职责包括：
- 封装平台特定的 GPU 上下文管理（如 OpenGL、Metal、Vulkan、Direct3D）
- 提供统一的上下文切换接口
- 管理 GPU 同步和刷新操作
- 支持 GPU 性能计时
- 控制帧延迟（frame lag）以优化测试性能

该类采用抽象基类设计，由平台特定的子类（如 GLTestContext、VkTestContext、MtlTestContext）实现具体的上下文操作。这种设计使测试代码能够以平台无关的方式操作 GPU 上下文，极大地简化了跨平台测试的编写和维护。

## 架构位置

TestContext 位于 Skia 测试工具层级的顶层抽象位置，处于架构的关键层次：

- **上层调用者**：
  - 各种 Ganesh GPU 单元测试和集成测试
  - 性能基准测试（benchmarks）
  - GPU 功能验证测试

- **子类实现**：
  - `tools/ganesh/gl/GLTestContext` - OpenGL 实现
  - `tools/ganesh/vk/VkTestContext` - Vulkan 实现
  - `tools/ganesh/mtl/MtlTestContext` - Metal 实现
  - `tools/ganesh/d3d/D3DTestContext` - Direct3D 实现
  - `tools/ganesh/mock/MockTestContext` - 模拟实现（用于不需要真实 GPU 的测试）

- **同级组件**：
  - TestOps - 测试用绘制操作
  - ProxyUtils - 代理工具函数
  - MemoryCache - 内存缓存测试工具

- **下层依赖**：
  - `include/gpu/ganesh/GrDirectContext.h` - Ganesh 直接上下文
  - `tools/ganesh/GpuTimer.h` - GPU 性能计时器
  - `tools/gpu/FlushFinishTracker.h` - 刷新完成追踪器

## 主要类与结构体

### TestContext

```cpp
class TestContext : public SkNoncopyable {
public:
    virtual ~TestContext();

    // 能力查询
    bool fenceSyncSupport() const;
    bool gpuTimingSupport() const;
    GpuTimer* gpuTimer() const;
    bool getMaxGpuFrameLag(int *maxFrameLag) const;

    // 上下文切换
    void makeNotCurrent() const;
    void makeCurrent() const;
    [[nodiscard]] SkScopeExit makeCurrentAndAutoRestore() const;

    // 后端信息
    virtual GrBackendApi backend() = 0;

    // 上下文创建
    virtual sk_sp<GrDirectContext> makeContext(const GrContextOptions&);

    // 同步操作
    void flushAndWaitOnSync(GrDirectContext* context);
    void flushAndSyncCpu(GrDirectContext*);

    // 测试支持
    virtual void testAbandon();

protected:
    bool fFenceSupport = false;
    std::unique_ptr<GpuTimer> fGpuTimer;

    TestContext();
    virtual void teardown();

    // 平台特定接口（子类实现）
    virtual void onPlatformMakeNotCurrent() const = 0;
    virtual void onPlatformMakeCurrent() const = 0;
    virtual std::function<void()> onPlatformGetAutoContextRestore() const = 0;

private:
    enum { kMaxFrameLag = 3 };
    sk_sp<FlushFinishTracker> fFinishTrackers[kMaxFrameLag - 1];
    int fCurrentFlushIdx = 0;
};
```

TestContext 继承自 `SkNoncopyable`，明确禁止拷贝操作，确保上下文对象的唯一性。

### 关键成员变量

- **fFenceSupport**：标识是否支持栅栏同步（fence sync），用于异步 GPU 操作的同步
- **fGpuTimer**：GPU 性能计时器，用于测量 GPU 操作的执行时间
- **fFinishTrackers**：刷新完成追踪器数组，管理异步刷新操作的完成状态
- **fCurrentFlushIdx**：当前刷新索引，用于循环管理多个并发刷新操作
- **kMaxFrameLag**：最大帧延迟常量（值为 3），限制 GPU 上未完成的刷新操作数量

## 公共 API 函数

### 能力查询

```cpp
bool fenceSyncSupport() const { return fFenceSupport; }
bool gpuTimingSupport() const { return fGpuTimer != nullptr; }
GpuTimer* gpuTimer() const { SkASSERT(fGpuTimer); return fGpuTimer.get(); }
```

这些函数允许测试代码查询当前上下文的能力，以决定是否使用高级功能如性能计时或异步同步。

### 上下文切换

```cpp
void makeNotCurrent() const;
void makeCurrent() const;
```

这两个函数控制 GPU 上下文的当前状态。许多 GPU API（如 OpenGL）要求在执行 GPU 操作前将上下文设为当前。这些函数封装了平台特定的上下文切换操作。

### 自动恢复上下文

```cpp
[[nodiscard]] SkScopeExit makeCurrentAndAutoRestore() const;
```

这是一个 RAII 风格的函数，返回一个作用域退出对象。该对象在构造时将此上下文设为当前，在析构时恢复之前的上下文。使用示例：

```cpp
{
    auto restore = testContext->makeCurrentAndAutoRestore();
    // 在此作用域内，testContext 是当前上下文
    // 执行 GPU 操作...
} // restore 析构，恢复之前的上下文
```

`[[nodiscard]]` 属性确保调用者必须捕获返回值，避免立即销毁导致的上下文提前恢复。

### 上下文创建

```cpp
virtual sk_sp<GrDirectContext> makeContext(const GrContextOptions&);
```

从此测试上下文创建 Ganesh 直接上下文。基类实现返回 `nullptr`，子类应重写此方法以创建平台特定的上下文。

### 刷新和同步

```cpp
void flushAndWaitOnSync(GrDirectContext* context);
void flushAndSyncCpu(GrDirectContext* context);
```

**flushAndWaitOnSync**：
- 刷新 GPU 工作到设备
- 如果支持栅栏同步，添加完成回调
- 管理帧延迟，确保不超过 `kMaxFrameLag` 个未完成的刷新
- 如果达到限制，在 CPU 上等待直到有刷新完成

**flushAndSyncCpu**：
- 刷新并立即同步 CPU
- 阻塞等待所有 GPU 工作完成
- 用于需要严格同步的测试场景

### 测试支持

```cpp
virtual void testAbandon();
```

通知上下文即将被故意放弃（abandon）。这对于测试资源清理和错误处理路径很有用。默认实现为空，子类可以重写以执行清理操作。

## 内部实现细节

### 帧延迟管理

`flushAndWaitOnSync` 实现了帧延迟管理机制：

```cpp
void TestContext::flushAndWaitOnSync(GrDirectContext* context) {
    TRACE_EVENT0("skia.gpu", TRACE_FUNC);
    SkASSERT(context);

    if (fFinishTrackers[fCurrentFlushIdx]) {
        fFinishTrackers[fCurrentFlushIdx]->waitTillFinished();
    }

    fFinishTrackers[fCurrentFlushIdx].reset(new FlushFinishTracker(context));
    fFinishTrackers[fCurrentFlushIdx]->ref();

    GrFlushInfo flushInfo;
    flushInfo.fFinishedProc = FlushFinishTracker::FlushFinished;
    flushInfo.fFinishedContext = fFinishTrackers[fCurrentFlushIdx].get();

    context->flush(flushInfo);
    context->submit();

    fCurrentFlushIdx = (fCurrentFlushIdx + 1) % std::size(fFinishTrackers);
}
```

**工作原理**：
1. 检查当前索引位置的追踪器是否有未完成的刷新，如有则等待
2. 创建新的 FlushFinishTracker 并增加引用计数
3. 设置刷新信息，包含完成回调
4. 执行刷新和提交
5. 循环递增索引，实现循环队列

这种设计允许最多 `kMaxFrameLag - 1` = 2 个刷新并发执行，平衡了性能和内存使用。

### 追踪器引用管理

追踪器使用手动引用计数管理：
- 一个引用由 `fFinishTrackers` 数组持有
- 另一个引用传递给 GPU 完成回调
- 回调执行时解除第二个引用
- 当新刷新覆盖数组位置时，旧追踪器的第一个引用被释放

这种双引用机制确保追踪器在需要时保持活跃。

### 上下文切换委托

基类将上下文切换委托给纯虚函数：

```cpp
void TestContext::makeNotCurrent() const { this->onPlatformMakeNotCurrent(); }
void TestContext::makeCurrent() const { this->onPlatformMakeCurrent(); }
```

子类必须实现这些平台特定的操作，如：
- **OpenGL**：`glMakeCurrent` 或 `eglMakeCurrent`
- **Vulkan**：通常无操作（Vulkan 没有当前上下文概念）
- **Metal**：设置当前命令队列

### 自动恢复机制

`makeCurrentAndAutoRestore` 使用 `SkScopeExit` 实现 RAII：

```cpp
SkScopeExit TestContext::makeCurrentAndAutoRestore() const {
    auto asr = SkScopeExit(this->onPlatformGetAutoContextRestore());
    this->makeCurrent();
    return asr;
}
```

子类的 `onPlatformGetAutoContextRestore` 返回一个函数对象，该对象捕获当前上下文状态，并在调用时恢复该状态。

### CPU 同步实现

`flushAndSyncCpu` 使用 `GrSyncCpu::kYes` 参数：

```cpp
void TestContext::flushAndSyncCpu(GrDirectContext* context) {
    SkASSERT(context);
    context->flush();
    context->submit(GrSyncCpu::kYes);
}
```

这会阻塞 CPU 直到所有提交的 GPU 工作完成，适用于需要严格顺序执行的测试。

### 析构器验证

析构器断言 `fGpuTimer` 已被清理：

```cpp
TestContext::~TestContext() {
    SkASSERT(!fGpuTimer);
}
```

这确保子类在销毁前调用了 `teardown()`，遵循了正确的清理顺序。

## 依赖关系

### 核心依赖

- **GrDirectContext**：Ganesh 的主要 GPU 上下文接口
- **SkNoncopyable**：禁止拷贝的基类
- **SkRefCnt**：引用计数基础设施

### 测试工具依赖

- **GpuTimer**：GPU 性能计时抽象
- **FlushFinishTracker**：追踪异步刷新完成状态
- **SkScopeExit**：RAII 作用域退出工具

### 平台特定依赖（由子类引入）

- **OpenGL**：EGL、GLX、CGL、WGL 等平台绑定
- **Vulkan**：Vulkan API
- **Metal**：Metal 框架
- **Direct3D**：D3D12 API

## 设计模式与设计决策

### 模板方法模式

TestContext 使用模板方法模式定义操作的骨架，子类实现具体步骤：

```cpp
// 公共接口（模板方法）
void makeCurrent() const;

// 平台特定实现（由子类提供）
virtual void onPlatformMakeCurrent() const = 0;
```

这种设计：
- **统一接口**：测试代码使用一致的 API
- **平台多态**：每个平台提供特定实现
- **易于扩展**：添加新平台只需实现纯虚函数

### RAII 资源管理

`makeCurrentAndAutoRestore` 使用 RAII 确保上下文恢复：

```cpp
auto restore = testContext->makeCurrentAndAutoRestore();
// 自动在作用域结束时恢复
```

这比手动调用 `makeCurrent` 和 `makeNotCurrent` 更安全，防止异常或提前返回导致的上下文泄漏。

### 不可拷贝设计

继承 `SkNoncopyable` 明确禁止拷贝：

```cpp
class TestContext : public SkNoncopyable { ... };
```

这防止了上下文的意外复制，因为：
- GPU 上下文通常是不可拷贝的资源
- 拷贝会导致多个对象管理同一资源
- 使用智能指针共享是更好的选择

### 循环缓冲区模式

帧延迟管理使用循环缓冲区：

```cpp
fFinishTrackers[kMaxFrameLag - 1];  // 固定大小数组
fCurrentFlushIdx = (fCurrentFlushIdx + 1) % std::size(fFinishTrackers);
```

这种设计：
- **固定内存**：避免动态分配
- **高效复用**：循环使用追踪器槽位
- **简单实现**：使用模运算实现循环

### 虚函数最小化

只有必须由子类实现的函数才声明为虚函数：

```cpp
virtual GrBackendApi backend() = 0;  // 纯虚函数
virtual sk_sp<GrDirectContext> makeContext(...);  // 虚函数（有默认实现）
virtual void testAbandon();  // 虚函数（有默认实现）
```

非虚函数（如 `makeCurrent`）实现通用逻辑并委托给虚函数，减少虚函数调用开销。

### 能力标志设计

使用布尔标志表示可选能力：

```cpp
bool fFenceSupport = false;
std::unique_ptr<GpuTimer> fGpuTimer;
```

测试代码可以查询这些能力并相应调整行为，支持不同硬件能力的优雅降级。

## 性能考量

### 帧延迟优化

`kMaxFrameLag = 3` 的设计平衡了性能和延迟：
- **太小**（如 1）：GPU 等待 CPU，利用率低
- **太大**（如 10）：内存占用高，延迟大
- **3**：通常足够保持 GPU 忙碌，同时限制内存使用

### 异步同步

`flushAndWaitOnSync` 使用异步回调避免阻塞：
- GPU 工作异步执行
- CPU 可以继续准备下一帧
- 只有在达到帧延迟限制时才阻塞

这比每帧同步 CPU（`flushAndSyncCpu`）快得多。

### 最小化上下文切换

TestContext 鼓励批量操作而非频繁切换：
- `makeCurrentAndAutoRestore` 支持作用域内的多个操作
- 子类可以缓存上下文状态避免不必要的切换

### 性能计时开销

GPU 计时器是可选的：
```cpp
bool gpuTimingSupport() const { return fGpuTimer != nullptr; }
```

如果不需要性能测量，可以不创建计时器，避免开销。

### 追踪事件

使用 `TRACE_EVENT0` 支持性能分析：
```cpp
TRACE_EVENT0("skia.gpu", TRACE_FUNC);
```

这允许在 Chrome 追踪工具中可视化 GPU 操作，对性能优化至关重要。

## 相关文件

### 子类实现
- `tools/ganesh/gl/GLTestContext.h/cpp` - OpenGL 实现
- `tools/ganesh/vk/VkTestContext.h/cpp` - Vulkan 实现
- `tools/ganesh/mtl/MtlTestContext.h/.mm` - Metal 实现
- `tools/ganesh/d3d/D3DTestContext.h/cpp` - Direct3D 实现
- `tools/ganesh/mock/MockTestContext.h/cpp` - 模拟实现

### 同目录工具
- `tools/ganesh/TestOps.h/cpp` - 测试用绘制操作
- `tools/ganesh/ProxyUtils.h/cpp` - 代理工具函数
- `tools/ganesh/MemoryCache.h/cpp` - 内存缓存工具
- `tools/ganesh/GpuTimer.h` - GPU 性能计时器抽象

### Ganesh 核心
- `include/gpu/ganesh/GrDirectContext.h` - 直接上下文接口
- `include/gpu/ganesh/GrTypes.h` - Ganesh 类型定义
- `src/gpu/ganesh/GrContextOptions.h` - 上下文配置选项

### 工具基础设施
- `tools/gpu/FlushFinishTracker.h` - 刷新完成追踪
- `src/base/SkScopeExit.h` - RAII 作用域退出
- `src/core/SkTraceEvent.h` - 性能追踪事件
- `include/private/base/SkNoncopyable.h` - 不可拷贝基类
