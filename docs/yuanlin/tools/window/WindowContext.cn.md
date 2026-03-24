# WindowContext

> 源文件: tools/window/WindowContext.h, tools/window/WindowContext.cpp

## 概述

`WindowContext` 是 Skia 窗口系统中的核心抽象基类,封装了跨平台窗口渲染上下文的通用接口。该组件提供了后备缓冲区管理、缓冲区交换、GPU 上下文访问、窗口尺寸调整等核心功能,同时支持 Ganesh 和 Graphite 两套 GPU 后端。它定义了窗口渲染所需的最小接口集,由平台特定的子类(如 Metal、Vulkan、OpenGL 等)实现具体的本地窗口系统集成。

该类管理显示参数(DisplayParams),包括色彩空间、MSAA 采样数、VSync 等配置。提供了 GPU 计时器回调机制,用于性能分析和帧率监控。通过抽象工厂模式,支持运行时在不同 GPU 后端之间切换,为 Skia Viewer、示例应用和测试工具提供了统一的渲染上下文管理接口。

## 架构位置

`WindowContext` 位于 Skia 项目的 `tools/window` 目录下,是窗口系统的核心抽象:

```
WindowContext (抽象基类)
  ├─> GLWindowContext (OpenGL 后端)
  ├─> VulkanWindowContext (Vulkan 后端)
  ├─> MetalWindowContext (Metal 后端)
  ├─> GraphiteNativeVulkanWindowContext (Graphite Vulkan)
  ├─> GraphiteNativeMetalWindowContext (Graphite Metal)
  └─> GraphiteDawnWindowContext (Graphite Dawn)
```

依赖的核心模块:
- **tools/window/DisplayParams.h**: 显示参数配置
- **include/gpu/ganesh/GrDirectContext.h**: Ganesh GPU 上下文
- **include/gpu/graphite/Context.h**: Graphite GPU 上下文
- **include/core/SkSurface.h**: 表面抽象

## 主要类与结构体

### WindowContext

```cpp
namespace skwindow {

class WindowContext {
public:
    WindowContext(std::unique_ptr<const DisplayParams>);
    virtual ~WindowContext();

    // 核心接口
    virtual sk_sp<SkSurface> getBackbufferSurface() = 0;
    void swapBuffers();
    virtual bool isValid() = 0;
    virtual void resize(int w, int h) = 0;
    virtual void activate(bool isActive) {}

    // 显示参数管理
    const DisplayParams* getDisplayParams() { return fDisplayParams.get(); }
    virtual void setDisplayParams(std::unique_ptr<const DisplayParams>) = 0;

    // GPU 上下文访问
#if defined(SK_GANESH)
    GrDirectContext* directContext() const { return fContext.get(); }
#endif
#if defined(SK_GRAPHITE)
    skgpu::graphite::Context* graphiteContext() const { return fGraphiteContext.get(); }
    skgpu::graphite::Recorder* graphiteRecorder() const { return fGraphiteRecorder.get(); }
#endif

    // GPU 提交和计时
    using GpuTimerCallback = std::function<void(uint64_t ns)>;
    void submitToGpu(GpuTimerCallback = {});
    bool supportsGpuTimer() const;

    // 窗口尺寸查询
    int width() const { return fWidth; }
    int height() const { return fHeight; }
    SkISize dimensions() const { return {fWidth, fHeight}; }
    int sampleCount() const { return fSampleCount; }
    int stencilBits() const { return fStencilBits; }

protected:
    virtual bool isGpuContext() { return true; }
    virtual void onSwapBuffers() = 0;

#if defined(SK_GANESH)
    sk_sp<GrDirectContext> fContext;
#endif
#if defined(SK_GRAPHITE)
    std::unique_ptr<skgpu::graphite::Context> fGraphiteContext;
    std::unique_ptr<skgpu::graphite::Recorder> fGraphiteRecorder;
#endif

    int fWidth;
    int fHeight;
    std::unique_ptr<const DisplayParams> fDisplayParams;
    int fSampleCount = 1;
    int fStencilBits = 0;
};

}  // namespace skwindow
```

**关键成员变量**:
- `fContext`: Ganesh GPU 直接上下文,管理 GPU 资源和命令提交
- `fGraphiteContext`: Graphite GPU 上下文,新一代 GPU 后端
- `fGraphiteRecorder`: Graphite 记录器,用于记录绘制命令
- `fWidth`, `fHeight`: 窗口/表面尺寸
- `fDisplayParams`: 显示参数配置(不可变)
- `fSampleCount`: MSAA 采样数,由平台代码初始化
- `fStencilBits`: 模板缓冲区位数,由平台代码初始化

## 公共 API 函数

### 构造与析构

```cpp
WindowContext::WindowContext(std::unique_ptr<const DisplayParams> params)
    : fDisplayParams(std::move(params)) {}
```

接受 `DisplayParams` 的所有权,配置显示参数。

```cpp
virtual ~WindowContext()
```

虚析构函数,确保子类资源正确释放。

### 核心渲染接口

```cpp
virtual sk_sp<SkSurface> getBackbufferSurface() = 0
```

纯虚函数,子类必须实现。返回后备缓冲区表面,用于绘制操作。每帧调用一次,获取可绘制的表面。

```cpp
void swapBuffers()
```

交换前后缓冲区,显示渲染结果:
```cpp
void WindowContext::swapBuffers() {
    this->onSwapBuffers();
}
```

委托给虚函数 `onSwapBuffers()`,由子类实现平台特定的交换逻辑。

```cpp
virtual bool isValid() = 0
```

检查上下文是否有效(例如窗口未关闭、GPU 上下文未丢失)。

```cpp
virtual void resize(int w, int h) = 0
```

窗口尺寸变化时调用,子类重新创建表面和资源。

```cpp
virtual void activate(bool isActive)
```

窗口激活状态变化时调用(可选重写),默认空实现。用于优化非激活窗口的资源使用。

### 显示参数管理

```cpp
const DisplayParams* getDisplayParams()
```

获取当前显示参数的只读访问。

```cpp
virtual void setDisplayParams(std::unique_ptr<const DisplayParams>) = 0
```

设置新的显示参数,子类通常需要重建上下文或表面。

### GPU 上下文访问

```cpp
GrDirectContext* directContext() const  // Ganesh
skgpu::graphite::Context* graphiteContext() const  // Graphite
skgpu::graphite::Recorder* graphiteRecorder() const  // Graphite
```

返回相应 GPU 后端的上下文或记录器指针。根据编译选项(SK_GANESH/SK_GRAPHITE)条件编译。

### GPU 提交和计时

```cpp
void submitToGpu(GpuTimerCallback callback = {})
```

提交GPU命令并可选地测量执行时间:

**Graphite 路径**:
```cpp
if (fGraphiteContext) {
    std::unique_ptr<skgpu::graphite::Recording> recording = fGraphiteRecorder->snap();
    if (recording) {
        skgpu::graphite::InsertRecordingInfo info;
        if (statsCallback) {
            // 设置回调
            info.fFinishedContext = callback.release();
            info.fFinishedWithStatsProc = [](context, result, stats) {
                std::unique_ptr<GpuTimerCallback> cb{static_cast<GpuTimerCallback*>(context)};
                (*cb)(stats.elapsedTime);  // 返回纳秒
            };
            info.fGpuStatsFlags = skgpu::GpuStatsFlags::kElapsedTime;
        }
        fGraphiteContext->insertRecording(info);
        fGraphiteContext->submit(SyncToCpu::kNo);
    }
}
```

**Ganesh 路径**:
```cpp
if (auto dc = this->directContext()) {
    GrFlushInfo info;
    if (statsCallback) {
        info.fFinishedContext = callback.release();
        info.fFinishedWithStatsProc = [](context, stats) {
            std::unique_ptr<GpuTimerCallback> cb{static_cast<GpuTimerCallback*>(context)};
            (*cb)(stats.elapsedTime);
        };
        info.fGpuStatsFlags = skgpu::GpuStatsFlags::kElapsedTime;
    }
    dc->flush(info);
    dc->submit();
}
```

回调在 GPU 完成渲染后异步调用,传递经过的纳秒数。

```cpp
bool supportsGpuTimer() const
```

检查 GPU 是否支持计时统计:
```cpp
auto flags = fContext ? fContext->supportedGpuStats()
                      : fGraphiteContext->supportedGpuStats();
return static_cast<T>(flags) & static_cast<T>(skgpu::GpuStatsFlags::kElapsedTime);
```

查询 GPU 上下文支持的统计标志。

### 尺寸查询

```cpp
int width() const
int height() const
SkISize dimensions() const
int sampleCount() const
int stencilBits() const
```

查询窗口和表面参数,只读访问。

## 内部实现细节

### 模板方法模式

`swapBuffers()` 是模板方法:
```cpp
void swapBuffers() {
    this->onSwapBuffers();  // 委托给子类
}
```

定义流程,由子类实现细节。

### 双后端支持

使用条件编译支持 Ganesh 和 Graphite:
```cpp
#if defined(SK_GANESH)
    sk_sp<GrDirectContext> fContext;
#endif
#if defined(SK_GRAPHITE)
    std::unique_ptr<skgpu::graphite::Context> fGraphiteContext;
    std::unique_ptr<skgpu::graphite::Recorder> fGraphiteRecorder;
#endif
```

同一代码库可以构建不同后端的版本。

### 回调生命周期管理

GPU 计时回调使用 `std::unique_ptr` 管理:
```cpp
auto callback = std::make_unique<GpuTimerCallback>(std::move(statsCallback));
info.fFinishedContext = callback.release();  // 转移所有权到 GPU 上下文

// GPU 完成后,在回调中重新获取所有权并销毁
std::unique_ptr<GpuTimerCallback> cb{static_cast<GpuTimerCallback*>(context)};
(*cb)(stats.elapsedTime);  // 智能指针在作用域结束时自动删除
```

确保回调对象生命周期正确,避免内存泄漏。

### 不可变显示参数

`DisplayParams` 使用 `std::unique_ptr<const DisplayParams>`:
```cpp
std::unique_ptr<const DisplayParams> fDisplayParams;
```

一旦设置,参数不可修改,需要通过 `setDisplayParams()` 替换整个对象。这确保了参数一致性。

## 依赖关系

### 直接依赖

- **tools/window/DisplayParams.h**: 显示参数配置
- **include/core/SkSurface.h**: 表面抽象
- **include/core/SkRefCnt.h**: 引用计数智能指针
- **include/gpu/ganesh/GrDirectContext.h**: Ganesh 上下文
- **include/gpu/ganesh/GrTypes.h**: Ganesh 类型
- **include/gpu/graphite/Context.h**: Graphite 上下文
- **include/gpu/graphite/Recorder.h**: Graphite 记录器

## 设计模式与设计决策

### 抽象工厂模式

`WindowContext` 是抽象产品,平台特定的工厂创建具体产品:
```cpp
// 例如:
std::unique_ptr<WindowContext> MakeMetalContext(...);
std::unique_ptr<WindowContext> MakeVulkanContext(...);
```

### 策略模式

通过 `DisplayParams` 配置渲染策略(VSync、MSAA 等),运行时可切换。

### 非虚接口模式

`swapBuffers()` 是公共非虚函数,调用保护的虚函数 `onSwapBuffers()`:
```cpp
public:
    void swapBuffers() {
        this->onSwapBuffers();
    }
protected:
    virtual void onSwapBuffers() = 0;
```

基类控制接口,子类实现细节。

## 性能考量

### GPU 计时开销

计时查询有性能开销,仅在提供回调时启用:
```cpp
if (statsCallback) {
    info.fGpuStatsFlags = skgpu::GpuStatsFlags::kElapsedTime;
}
```

生产代码通常不启用计时。

### 异步提交

GPU 提交是异步的:
```cpp
fGraphiteContext->submit(SyncToCpu::kNo);  // 不等待 GPU 完成
```

避免阻塞 CPU,最大化并行性。

### 智能指针开销

使用 `std::unique_ptr` 管理 `DisplayParams`:
```cpp
std::unique_ptr<const DisplayParams> fDisplayParams;
```

零开销抽象,仅在设置参数时有一次分配/释放。

## 相关文件

### 核心抽象

- **tools/window/DisplayParams.h**: 显示参数定义
- **include/core/SkSurface.h**: 表面抽象

### 平台实现

- **tools/window/GLWindowContext.h**: OpenGL 实现
- **tools/window/VulkanWindowContext.h**: Vulkan 实现
- **tools/window/MetalWindowContext.h**: Metal 实现
- **tools/window/GraphiteNativeVulkanWindowContext.h**: Graphite Vulkan
- **tools/window/GraphiteNativeMetalWindowContext.h**: Graphite Metal
- **tools/window/GraphiteDawnWindowContext.h**: Graphite Dawn

### GPU 后端

- **include/gpu/ganesh/GrDirectContext.h**: Ganesh 上下文
- **include/gpu/graphite/Context.h**: Graphite 上下文

### 使用者

- **tools/viewer/Viewer.h**: Viewer 应用
- **tools/sk_app/Window.h**: 窗口抽象

### 使用场景

该组件在以下场景中使用:

1. **Viewer 工具**: 为 Viewer 提供跨平台渲染上下文
2. **示例应用**: 简化示例代码的窗口管理
3. **性能测试**: 通过 GPU 计时器测量渲染性能
4. **多后端支持**: 运行时切换 Ganesh/Graphite 后端
5. **平台抽象**: 隔离平台特定的窗口系统代码

典型使用流程:
```cpp
// 创建上下文
std::unique_ptr<WindowContext> ctx = MakeVulkanContext(...);

// 渲染循环
while (!quit) {
    sk_sp<SkSurface> surface = ctx->getBackbufferSurface();
    SkCanvas* canvas = surface->getCanvas();

    // 绘制内容
    canvas->clear(SK_ColorWHITE);
    canvas->drawRect(...);

    // 提交并测量时间
    ctx->submitToGpu([](uint64_t ns) {
        printf("GPU time: %llu ns\n", ns);
    });

    // 显示
    ctx->swapBuffers();
}

// 窗口尺寸变化
ctx->resize(newWidth, newHeight);

// 切换显示参数
auto newParams = std::make_unique<DisplayParams>(...);
ctx->setDisplayParams(std::move(newParams));
```

该组件是 Skia 窗口系统的基石,为跨平台渲染提供了统一、高效的抽象接口。
