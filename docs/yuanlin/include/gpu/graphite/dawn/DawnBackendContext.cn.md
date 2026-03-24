# DawnBackendContext

> 源文件: `include/gpu/graphite/dawn/DawnBackendContext.h`

## 概述

DawnBackendContext.h 定义了创建 Dawn/WebGPU 后端 Graphite Context 所需的结构体和工厂函数。它封装了 WebGPU 实例、设备、队列和 tick 函数,是初始化 Graphite Dawn 后端的入口点,同时处理了 WebGPU 特有的事件处理机制。

## 架构位置

该文件位于 Skia Graphite GPU 后端的 Dawn/WebGPU 平台特定接口层,属于 `skgpu::graphite` 命名空间。Dawn 是 Chrome 开发的跨平台 WebGPU 实现,支持 Desktop 和 WebAssembly/Emscripten 环境。

## 主要类型定义

### DawnTickFunction

```cpp
using DawnTickFunction = void(const wgpu::Instance& device);
```

**用途**: 允许主线程事件循环运行以检测 GPU 进度的回调函数类型。

**背景**: WebGPU 需要让主线程事件循环运行才能检测 GPU 进度:
- **Dawn Native**: 有 `wgpu::Instance::ProcessEvents` 函数
- **Web WebGPU**: 没有该函数,需要其他机制

### DawnNativeProcessEventsFunction (Desktop)

```cpp
#if !defined(__EMSCRIPTEN__)
SK_API inline void DawnNativeProcessEventsFunction(const wgpu::Instance& instance) {
    instance.ProcessEvents();
}
#endif
```

- **功能**: Desktop 平台的默认 tick 函数实现
- **机制**: 直接调用 Dawn Native 的 ProcessEvents
- **可用性**: 仅在非 Emscripten 环境

## 主要结构体

### DawnBackendContext

```cpp
struct SK_API DawnBackendContext {
    wgpu::Instance fInstance;
    wgpu::Device fDevice;
    wgpu::Queue fQueue;
    DawnTickFunction* fTick =
#if defined(__EMSCRIPTEN__)
        nullptr;
#else
        DawnNativeProcessEventsFunction;
#endif
};
```

**职责**: 封装创建 Graphite Dawn Context 所需的 WebGPU 对象和配置。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fInstance` | `wgpu::Instance` | WebGPU 实例对象 |
| `fDevice` | `wgpu::Device` | WebGPU 设备对象 |
| `fQueue` | `wgpu::Queue` | WebGPU 命令队列 |
| `fTick` | `DawnTickFunction*` | 事件处理函数指针 |

### fTick 的平台默认值

- **Desktop (Dawn Native)**: 默认为 `DawnNativeProcessEventsFunction`
- **WebAssembly/Emscripten**: 默认为 `nullptr` (non-yielding Context)

## Non-Yielding Context 概念

当 `fTick` 为 `nullptr` 时,Context 为"non-yielding"模式,有以下限制:

### 限制 1: 禁用 SyncToCpu::kYes

```cpp
// 禁止
SubmitInfo info;
info.fSync = SyncToCpu::kYes;
context->submit(info);  // 将失败或断言
```

**原因**: 无法主动等待 GPU 完成,因为没有 tick 函数驱动事件循环。

### 限制 2: Context 销毁前的责任

```cpp
// 客户端必须确保 GPU 工作完成
while (context->hasUnfinishedGpuWork()) {
    // 等待或处理其他事件
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
}
// 现在可以安全销毁
context.reset();
```

**原因**: Context 析构函数无法等待 GPU 完成(没有 tick 函数)。

### hasUnfinishedGpuWork API

```cpp
bool hasUnfinishedGpuWork() const;
```

- **功能**: 检查是否有未完成的 GPU 工作
- **用途**: non-yielding Context 销毁前必须检查
- **返回值**: true 表示仍有工作进行中

## 公共 API 函数

### ContextFactory::MakeDawn

```cpp
namespace ContextFactory {
SK_API std::unique_ptr<Context> MakeDawn(const DawnBackendContext&, const ContextOptions&);
}
```

- **功能**: 创建 Dawn 后端的 Graphite Context
- **参数**:
  - `DawnBackendContext&`: 包含 WebGPU 对象的后端上下文
  - `ContextOptions&`: Context 配置选项
- **返回值**: 成功返回 Context 智能指针,失败返回 nullptr
- **验证**: 检查 fInstance, fDevice, fQueue 的有效性

## 内部实现细节

### WebGPU 事件处理机制

#### Desktop (Dawn Native)

```cpp
DawnBackendContext ctx;
ctx.fInstance = ...;
ctx.fDevice = ...;
ctx.fQueue = ...;
ctx.fTick = DawnNativeProcessEventsFunction;  // 默认值

// Context 内部调用
ctx.fTick(ctx.fInstance);  // 处理 GPU 事件
```

#### WebAssembly/Emscripten

```cpp
// Emscripten with -s ASYNCIFY
EM_ASYNC_JS(void, asyncSleep, (), {
    await new Promise((resolve, _) => {
        setTimeout(resolve, 0);
    })
});

void WebGPUTickFunction(const wgpu::Instance& instance) {
    asyncSleep();  // 让出控制权,允许事件循环运行
}

DawnBackendContext ctx;
// ...
ctx.fTick = WebGPUTickFunction;
```

**注意**: 需要 Emscripten 的 `-s ASYNCIFY` 编译选项。

#### 不使用 ASYNCIFY

```cpp
DawnBackendContext ctx;
// ...
ctx.fTick = nullptr;  // non-yielding Context
// 必须遵守 non-yielding 限制
```

**优势**: 无需 ASYNCIFY,减小 WASM 体积和编译开销。

### Context 创建流程

1. **验证**: 检查 fInstance, fDevice, fQueue 有效性
2. **Tick 函数**: 根据 fTick 决定 yielding/non-yielding 模式
3. **能力查询**: 查询 WebGPU 设备支持的特性和限制
4. **资源初始化**: 创建内部资源池、缓存
5. **着色器编译**: 加载或编译 WebGPU 着色器模块
6. **返回**: 返回初始化完成的 Context

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkTypes.h` | 基础类型定义 |
| `webgpu/webgpu_cpp.h` | WebGPU C++ 绑定 |
| `include/gpu/graphite/Context.h` | Context 类定义 |
| `include/gpu/graphite/ContextOptions.h` | 配置选项 |

### 被依赖的模块

- 应用程序初始化代码
- Graphite Dawn 后端实现
- 跨平台渲染抽象层

## 设计模式与设计决策

### 策略模式 - Tick 函数

通过函数指针注入事件处理策略:
- **Desktop**: Dawn Native 的 ProcessEvents
- **Web (ASYNCIFY)**: 自定义异步睡眠
- **Web (non-yielding)**: nullptr

### 平台抽象

通过条件编译提供平台特定默认值:
```cpp
#if defined(__EMSCRIPTEN__)
    nullptr;
#else
    DawnNativeProcessEventsFunction;
#endif
```

**优势**: 客户端在大多数情况下无需手动设置。

### 明确限制而非运行时失败

non-yielding Context 的限制在文档中明确说明:
- **优势**: 开发者提前知晓限制
- **权衡**: 牺牲部分功能换取简化和性能

## 性能考量

### Tick 函数开销

- **Desktop**: ProcessEvents 调用很轻量(< 1ms)
- **Web ASYNCIFY**: yield 开销较高(数十 ms)
- **Non-yielding**: 零开销

### ASYNCIFY 的影响

启用 `-s ASYNCIFY`:
- **WASM 大小**: 增加 20-50%
- **启动时间**: 增加 10-30%
- **运行时**: 轻微开销

### 推荐配置

| 场景 | 配置 | 原因 |
|------|------|------|
| Desktop 应用 | 使用默认 tick 函数 | 最佳体验,低开销 |
| Web 高性能 | Non-yielding + 手动同步 | 最小 WASM 体积 |
| Web 简化开发 | ASYNCIFY + 自定义 tick | 功能完整 |

## 使用示例

### Desktop (Dawn Native)

```cpp
#include "include/gpu/graphite/dawn/DawnBackendContext.h"
#include <dawn/native/DawnNative.h>

using namespace skgpu::graphite;

// 创建 Dawn 实例和设备
dawn::native::Instance dawnInstance;
dawnInstance.DiscoverDefaultAdapters();

std::vector<dawn::native::Adapter> adapters = dawnInstance.GetAdapters();
wgpu::Adapter adapter = adapters[0].Get();

wgpu::Device device = adapter.CreateDevice();
wgpu::Queue queue = device.GetQueue();

// 构造后端上下文(使用默认 tick 函数)
DawnBackendContext backendContext;
backendContext.fInstance = dawnInstance.Get();
backendContext.fDevice = device;
backendContext.fQueue = queue;
// fTick 自动设置为 DawnNativeProcessEventsFunction

// 创建 Context
ContextOptions options;
auto context = ContextFactory::MakeDawn(backendContext, options);
```

### WebAssembly (ASYNCIFY)

```cpp
// 需要 emcc -s ASYNCIFY

#include <emscripten.h>

EM_ASYNC_JS(void, yieldToEventLoop, (), {
    await new Promise(resolve => setTimeout(resolve, 0));
});

void webGpuTick(const wgpu::Instance& instance) {
    yieldToEventLoop();
}

// 初始化
DawnBackendContext backendContext;
backendContext.fInstance = instance;
backendContext.fDevice = device;
backendContext.fQueue = queue;
backendContext.fTick = webGpuTick;

auto context = ContextFactory::MakeDawn(backendContext, options);
```

### WebAssembly (Non-Yielding)

```cpp
DawnBackendContext backendContext;
backendContext.fInstance = instance;
backendContext.fDevice = device;
backendContext.fQueue = queue;
backendContext.fTick = nullptr;  // non-yielding

auto context = ContextFactory::MakeDawn(backendContext, options);

// 使用限制:
// 1. 不能使用 SyncToCpu::kYes
context->submit(SubmitInfo{SyncToCpu::kNo});  // 必须使用 kNo

// 2. 销毁前检查
while (context->hasUnfinishedGpuWork()) {
    emscripten_sleep(1);  // 或处理其他事件
}
context.reset();
```

### 完整 Web 应用

```cpp
class WebGraphiteApp {
public:
    void initialize(wgpu::Instance instance, wgpu::Device device) {
        DawnBackendContext backendContext;
        backendContext.fInstance = instance;
        backendContext.fDevice = device;
        backendContext.fQueue = device.GetQueue();

        // 根据是否有 ASYNCIFY 决定
#ifdef USE_ASYNCIFY
        backendContext.fTick = yieldToEventLoop;
#else
        backendContext.fTick = nullptr;
        fNonYielding = true;
#endif

        ContextOptions options;
        fContext = ContextFactory::MakeDawn(backendContext, options);
    }

    void render() {
        // 渲染代码...

        if (fNonYielding) {
            fContext->submit(SubmitInfo{SyncToCpu::kNo});
        } else {
            fContext->submit(SubmitInfo{SyncToCpu::kYes});  // 可选
        }
    }

    ~WebGraphiteApp() {
        if (fNonYielding) {
            // 必须等待 GPU 完成
            while (fContext->hasUnfinishedGpuWork()) {
                emscripten_sleep(1);
            }
        }
        fContext.reset();
    }

private:
    std::unique_ptr<Context> fContext;
    bool fNonYielding = false;
};
```

## 平台相关说明

### Desktop (Windows/Linux/macOS)

- 使用 Dawn Native
- 完整的 WebGPU 功能
- 默认 tick 函数工作良好
- 支持所有 Graphite 特性

### Web (Emscripten + ASYNCIFY)

- 使用浏览器的 WebGPU 实现
- 需要自定义 tick 函数
- 功能完整但 WASM 体积大
- 编译选项: `-s ASYNCIFY=1`

### Web (Emscripten 不用 ASYNCIFY)

- 使用 non-yielding Context
- WASM 体积最小
- 部分功能受限
- 最适合高性能要求场景

### 移动平台

Dawn 当前主要用于 Desktop 和 Web,移动平台通常使用:
- iOS/macOS: Metal 后端
- Android: Vulkan 后端

## 错误处理

### 设备创建失败

```cpp
wgpu::Device device = adapter.CreateDevice();
if (!device) {
    // WebGPU 不可用
}
```

### Context 创建失败

```cpp
auto context = ContextFactory::MakeDawn(backendContext, options);
if (!context) {
    // 可能原因:
    // - fInstance/fDevice/fQueue 为空
    // - 设备不支持必需特性
}
```

### Non-Yielding 同步失败

```cpp
// 设置超时避免无限等待
int timeout = 5000;  // 5秒
while (context->hasUnfinishedGpuWork() && timeout-- > 0) {
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
}
if (timeout <= 0) {
    // GPU 工作超时未完成,可能是死锁或驱动问题
}
```

## 最佳实践

1. **Desktop**: 使用默认配置,最简单
2. **Web**: 根据需求选择 ASYNCIFY 或 non-yielding
3. **错误检查**: 总是检查 Context 创建结果
4. **生命周期**: Context 销毁前确保 GPU 工作完成
5. **性能测试**: 在目标平台测试 ASYNCIFY 影响
6. **文档化**: 明确标注 non-yielding 限制

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/Context.h` | Context 基类 |
| `include/gpu/graphite/ContextOptions.h` | 配置选项 |
| `include/gpu/graphite/dawn/DawnTypes.h` | Dawn 类型定义(已弃用) |
| `include/gpu/graphite/dawn/DawnGraphiteTypes.h` | Dawn 类型定义 |
| `webgpu/webgpu_cpp.h` | WebGPU C++ API |
| `src/gpu/graphite/dawn/DawnGraphiteContext.cpp` | Dawn Context 实现 |

## 未来方向

- 简化 Web 平台的事件处理
- 改进 non-yielding Context 的用户体验
- 可能的 API 简化(自动检测平台)
