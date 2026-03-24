# MtlTestContext

> 源文件：tools/ganesh/mtl/MtlTestContext.h, tools/ganesh/mtl/MtlTestContext.mm

## 概述

MtlTestContext 是 Skia Ganesh 测试框架中用于 Metal 后端的测试上下文实现。Metal 是 Apple 的现代图形和计算 API，用于 macOS、iOS、iPadOS 和 tvOS 平台。该类封装了 Metal 设备和命令队列的创建，为 Metal GPU 测试提供统一接口。

主要特性：
- 自动选择最佳 Metal 设备（优先选择独立 GPU）
- 支持上下文共享（共享 Metal 设备和命令队列）
- 创建 Ganesh Metal 直接上下文
- 支持栅栏同步

该模块使用 Objective-C++（.mm 文件），以便使用 Metal 的 Objective-C API。

## 架构位置

- **基类**：TestContext
- **同级实现**：OpenGL、Vulkan、Direct3D、Mock 实现
- **平台**：仅 Apple 平台（macOS、iOS）
- **依赖**：Metal 框架、GrMtlBackendContext

## 主要类与结构体

### MtlTestContext（抽象类）

```cpp
class MtlTestContext : public TestContext {
public:
    GrBackendApi backend() override { return GrBackendApi::kMetal; }
    const GrMtlBackendContext& getMtlBackendContext() const;

protected:
    MtlTestContext(const GrMtlBackendContext& mtl);
    GrMtlBackendContext fMtl;
};
```

### CreatePlatformMtlTestContext（工厂函数）

```cpp
MtlTestContext* CreatePlatformMtlTestContext(MtlTestContext* sharedContext);
```

创建 Metal 测试上下文。如果提供共享上下文，将重用其 Metal 设备和命令队列。

## 内部实现细节

### 设备选择（macOS）

在 macOS 上，代码智能选择最佳 GPU：

```cpp
#ifdef SK_BUILD_FOR_MAC
sk_cfp<NSArray<id <MTLDevice>>*> availableDevices(MTLCopyAllDevices());
for (id<MTLDevice> dev in availableDevices.get()) {
    if (!dev.isLowPower) {        // 优先选择非低功耗设备（独立 GPU）
        device.retain(dev);
        break;
    }
    if (dev.isRemovable) {         // 其次选择可移除设备（外置 GPU）
        device.retain(dev);
        break;
    }
}
if (!device) {
    device.reset(MTLCreateSystemDefaultDevice());  // 回退到默认设备
}
#else
device.reset(MTLCreateSystemDefaultDevice());      // iOS 直接使用默认设备
#endif
```

这确保测试在最快的 GPU 上运行，提高测试性能和准确性。

### 上下文创建

```cpp
backendContext.fDevice.retain((GrMTLHandle)device.get());
sk_cfp<id<MTLCommandQueue>> queue([*device newCommandQueue]);
backendContext.fQueue.retain((GrMTLHandle)queue.get());
```

创建 Metal 命令队列并包装在 GrMtlBackendContext 中。

### Ganesh 上下文创建

```cpp
sk_sp<GrDirectContext> makeContext(const GrContextOptions& options) override {
    return GrDirectContexts::MakeMetal(fMtl, options);
}
```

### 栅栏支持

```cpp
fFenceSupport = true;
```

Metal 始终支持栅栏同步（`MTLFence`）。

### 上下文切换

```cpp
void onPlatformMakeNotCurrent() const override {}
void onPlatformMakeCurrent() const override {}
std::function<void()> onPlatformGetAutoContextRestore() const override { return nullptr; }
```

Metal 没有"当前上下文"概念（类似 Vulkan），因此这些操作为空。

## 依赖关系

- **Metal 框架**：`<Metal/Metal.h>`
- **GrMtlBackendContext**：Metal 后端上下文
- **GrDirectContexts::MakeMetal**：Metal 上下文工厂
- **sk_cfp**：Core Foundation 智能指针包装器

## 设计模式与设计决策

### 设备选择策略
优先选择高性能 GPU 确保测试结果代表性，同时支持回退到集成 GPU。

### 资源管理
使用 `sk_cfp` 智能指针自动管理 Objective-C 对象的引用计数。

### 条件编译
使用 `#ifdef SK_METAL` 保护整个模块，允许在非 Apple 平台编译。

## 性能考量

- 选择独立 GPU 提高测试性能
- 命令队列可被多个 Ganesh 上下文共享
- Metal 的低开销 API 特性
- 无上下文切换开销

## 相关文件

- `tools/ganesh/TestContext.h/cpp` - 基类
- `include/gpu/ganesh/mtl/GrMtlBackendContext.h` - Metal 后端上下文
- `include/gpu/ganesh/mtl/GrMtlDirectContext.h` - Metal 直接上下文
- `src/gpu/ganesh/mtl/GrMtlUtil.h` - Metal 工具函数
