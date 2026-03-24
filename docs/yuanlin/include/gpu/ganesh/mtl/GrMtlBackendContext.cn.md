# GrMtlBackendContext - Metal 后端上下文

> 源文件: `include/gpu/ganesh/mtl/GrMtlBackendContext.h`

## 概述

GrMtlBackendContext.h 定义了初始化 Skia Ganesh Metal 后端所需的核心上下文结构体。该文件提供了一个简洁的数据容器，封装了 Metal 设备和命令队列的引用，是创建 GrDirectContext 的必要参数，充当应用层与 Skia Metal GPU 实现之间的桥梁。

## 架构位置

- **所属子系统**: GPU/Ganesh 渲染后端 - Metal 分支
- **层级**: 公共 API 接口层
- **作用域**: Metal 后端初始化专用

该结构体位于 Metal 后端的顶层接口，是所有 Metal GPU 操作的起点。

## 主要类与结构体

### GrMtlBackendContext

封装 Metal 后端初始化所需的基础 Metal 对象的轻量级结构体。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fDevice | sk_cfp\<GrMTLHandle\> | Metal 设备对象（对应 id\<MTLDevice\>） |
| fQueue | sk_cfp\<GrMTLHandle\> | Metal 命令队列对象（对应 id\<MTLCommandQueue\>） |

**设计特点**:
- **纯数据结构**: 无成员函数，仅作为参数传递容器
- **智能指针管理**: 使用 `sk_cfp` 自动管理 Metal 对象的引用计数
- **最小化依赖**: 仅包含创建 GPU 上下文的必要信息

## 公共 API 函数

该结构体没有成员函数，使用默认的编译器生成的构造、析构和赋值函数。

## 内部实现细节

### Metal 设备与队列的角色

**fDevice (MTLDevice)**:
- **作用**: 代表物理 GPU 设备
- **生命周期**: 通常在应用启动时创建，贯穿整个应用生命周期
- **职责**:
  - 创建所有 Metal 资源（纹理、缓冲区、管线状态等）
  - 查询设备能力和特性
  - 管理内存分配

**fQueue (MTLCommandQueue)**:
- **作用**: 提交命令缓冲区到 GPU 执行
- **生命周期**: 通常与设备一起创建，长期持有
- **职责**:
  - 创建命令缓冲区（MTLCommandBuffer）
  - 按顺序执行提交的命令
  - 管理 GPU 工作调度

### 智能指针 sk_cfp 的作用

`sk_cfp` 是 Skia 提供的 Core Foundation 智能指针模板：

**引用计数管理**:
```cpp
// 创建上下文
id<MTLDevice> device = MTLCreateSystemDefaultDevice();
id<MTLCommandQueue> queue = [device newCommandQueue];

GrMtlBackendContext backendContext;
// retain() 增加引用计数
backendContext.fDevice.retain((__bridge GrMTLHandle)device);
backendContext.fQueue.retain((__bridge GrMTLHandle)queue);

// 当 backendContext 销毁时，自动释放引用
```

**ARC 兼容性**:
- 即使在 ARC (Automatic Reference Counting) 环境中，仍需要手动管理 C++ 对象中的 Objective-C 引用
- `sk_cfp` 确保在 C++ 对象销毁时正确释放 Metal 对象
- 避免循环引用和内存泄漏

### 与 GrDirectContext 的集成

GrMtlBackendContext 作为参数传递给 `GrDirectContext::MakeMetal()`：

```cpp
// 伪代码展示内部流程
sk_sp<GrDirectContext> GrDirectContext::MakeMetal(
    const GrMtlBackendContext& backendContext,
    const GrContextOptions& options) {

    // 验证参数
    if (!backendContext.fDevice || !backendContext.fQueue) {
        return nullptr;
    }

    // 创建 GrMtlGpu 对象
    auto gpu = GrMtlGpu::Make(backendContext, options);
    if (!gpu) {
        return nullptr;
    }

    // 创建 GrDirectContext
    auto context = GrDirectContext::MakeFromGpu(std::move(gpu));
    return context;
}
```

### 设备能力查询

在创建上下文后，Skia 会查询设备能力：

**常见查询**:
- 支持的像素格式
- 最大纹理尺寸
- 多重采样支持
- 特性集（Feature Set）
- 内存资源限制

这些信息用于：
- 优化资源创建策略
- 选择最佳渲染路径
- 避免使用不支持的特性

### 命令队列的使用模式

GrMtlGpu 内部使用命令队列：

1. **创建命令缓冲区**: `[queue commandBuffer]`
2. **编码渲染命令**: 通过 render/blit/compute encoder
3. **提交执行**: `[commandBuffer commit]`
4. **等待完成**: 可选的同步点

Skia 优化命令提交频率以平衡延迟和吞吐量。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/gpu/ganesh/mtl/GrMtlTypes.h | GrMTLHandle 类型定义 |
| include/ports/SkCFObject.h | sk_cfp 智能指针模板 |

### 被依赖的模块

- **GrDirectContext**: 使用此结构体创建 Metal 上下文
- **应用层初始化代码**: 在启动时创建并填充此结构体
- **GrMtlGpu**: 内部存储和使用设备与队列

### 系统依赖

- **Metal.framework**: 提供 MTLDevice 和 MTLCommandQueue 接口

## 设计模式与设计决策

### 1. 最小化接口原则

仅包含绝对必要的字段：
- **优点**:
  - 简化 API 使用
  - 减少配置复杂度
  - 降低错误可能性
- **权衡**: 高级配置需要在创建后通过其他 API 设置

### 2. 值语义设计

使用结构体而非类：
- **复制语义**: 可直接复制（虽然通常不需要）
- **无虚函数**: 无运行时开销
- **POD-like**: 除了智能指针，行为类似 Plain Old Data

### 3. 智能指针封装

使用 `sk_cfp` 而非裸指针：
- **自动管理**: 避免手动 retain/release
- **异常安全**: RAII 保证资源释放
- **跨 ARC/MRC**: 在两种内存管理模式下都正确工作

### 4. 分离初始化与使用

上下文结构体仅负责传递参数：
- **职责单一**: 不负责创建 Metal 对象
- **灵活性**: 客户端完全控制设备和队列的创建
- **共享资源**: 支持多个 GrContext 共享同一设备

## 性能考量

### 设备选择策略

在有多个 GPU 的系统（如 Mac 带独显）：
```objc
// 选择默认设备（通常是集成 GPU）
id<MTLDevice> device = MTLCreateSystemDefaultDevice();

// 或选择高性能设备
NSArray<id<MTLDevice>>* devices = MTLCopyAllDevices();
for (id<MTLDevice> device in devices) {
    if (!device.isLowPower) {
        // 使用独立 GPU
        break;
    }
}
```

**权衡**:
- **集成 GPU**: 省电，适合移动设备
- **独立 GPU**: 高性能，适合桌面渲染

### 命令队列配置

Metal 允许创建多个命令队列：
```objc
// 默认队列（推荐）
id<MTLCommandQueue> queue = [device newCommandQueue];

// 带优先级的队列（macOS 10.15+）
id<MTLCommandQueue> highPriorityQueue = [device newCommandQueueWithMaxCommandBufferCount:64];
```

**Skia 的选择**:
- 通常使用单个队列
- 简化同步逻辑
- 减少上下文切换开销

### 生命周期管理开销

`sk_cfp` 的引用计数操作：
- **retain/release**: 原子操作，有一定开销
- **缓解**: 引用计数操作仅在对象创建和销毁时发生
- **影响**: 相比渲染开销可忽略不计

## 平台相关说明

### iOS/iPadOS

**设备创建**:
```objc
// iOS 只有一个 GPU
id<MTLDevice> device = MTLCreateSystemDefaultDevice();
if (!device) {
    // Metal 不支持（A7 芯片之前的设备）
}
```

**内存限制**:
- iOS 设备内存有限，需要注意纹理和缓冲区大小
- 使用 `MTLResourceOptions` 优化内存使用

### macOS

**多 GPU 支持**:
```objc
NSArray<id<MTLDevice>>* devices = MTLCopyAllDevices();
for (id<MTLDevice> device in devices) {
    NSLog(@"Device: %@, Low Power: %d", device.name, device.isLowPower);
}
```

**外接 eGPU**:
- macOS 支持外接 GPU
- 可以在运行时检测 eGPU 连接/断开
- 需要处理设备丢失场景

### tvOS

与 iOS 类似，但有特定考虑：
- Apple TV 性能介于 iPhone 和 iPad 之间
- 固定分辨率（1080p 或 4K）
- 无移动性，可以更激进地使用 GPU

### Apple Silicon (M1/M2/M3)

**统一内存架构**:
- CPU 和 GPU 共享内存
- `MTLStorageModeShared` 性能优秀
- 减少数据复制开销

**高性能核心**:
- GPU 性能强劲，可处理复杂渲染
- 支持所有 Metal 特性集

## 使用示例

### 基本初始化

```cpp
// C++: 创建 Skia Metal 上下文
sk_sp<GrDirectContext> createSkiaMetalContext() {
    @autoreleasepool {
        // 创建 Metal 对象
        id<MTLDevice> device = MTLCreateSystemDefaultDevice();
        if (!device) {
            return nullptr;
        }

        id<MTLCommandQueue> queue = [device newCommandQueue];
        if (!queue) {
            return nullptr;
        }

        // 填充 backend context
        GrMtlBackendContext backendContext;
        backendContext.fDevice.retain((__bridge GrMTLHandle)device);
        backendContext.fQueue.retain((__bridge GrMTLHandle)queue);

        // 创建 Skia 上下文
        sk_sp<GrDirectContext> context = GrDirectContext::MakeMetal(backendContext);

        return context;
    }
}
```

### 带选项的初始化

```cpp
sk_sp<GrDirectContext> createSkiaMetalContextWithOptions() {
    @autoreleasepool {
        id<MTLDevice> device = MTLCreateSystemDefaultDevice();
        id<MTLCommandQueue> queue = [device newCommandQueue];

        GrMtlBackendContext backendContext;
        backendContext.fDevice.retain((__bridge GrMTLHandle)device);
        backendContext.fQueue.retain((__bridge GrMTLHandle)queue);

        // 配置 Skia 上下文选项
        GrContextOptions options;
        options.fDisableCoverageCountingPaths = false;
        options.fAllowPathMaskCaching = true;
        options.fGpuPathRenderers = GpuPathRenderers::kAll;

        sk_sp<GrDirectContext> context = GrDirectContext::MakeMetal(
            backendContext, options);

        return context;
    }
}
```

### 选择高性能 GPU (macOS)

```objc
id<MTLDevice> selectBestDevice() {
    NSArray<id<MTLDevice>>* devices = MTLCopyAllDevices();

    // 优先选择独立 GPU
    for (id<MTLDevice> device in devices) {
        if (!device.isLowPower && !device.isRemovable) {
            return device;
        }
    }

    // 其次选择外接 GPU
    for (id<MTLDevice> device in devices) {
        if (device.isRemovable) {
            return device;
        }
    }

    // 最后使用集成 GPU
    return MTLCreateSystemDefaultDevice();
}

// 使用自定义设备
id<MTLDevice> device = selectBestDevice();
id<MTLCommandQueue> queue = [device newCommandQueue];

GrMtlBackendContext backendContext;
backendContext.fDevice.retain((__bridge GrMTLHandle)device);
backendContext.fQueue.retain((__bridge GrMTLHandle)queue);
```

### 共享 Metal 设备

```cpp
// 在多个 Skia 上下文间共享 Metal 设备
class MetalDeviceManager {
public:
    static MetalDeviceManager& instance() {
        static MetalDeviceManager instance;
        return instance;
    }

    sk_sp<GrDirectContext> createContext() {
        GrMtlBackendContext backendContext;
        backendContext.fDevice = fDevice;
        backendContext.fQueue = fQueue;

        return GrDirectContext::MakeMetal(backendContext);
    }

private:
    MetalDeviceManager() {
        @autoreleasepool {
            id<MTLDevice> device = MTLCreateSystemDefaultDevice();
            id<MTLCommandQueue> queue = [device newCommandQueue];

            fDevice.retain((__bridge GrMTLHandle)device);
            fQueue.retain((__bridge GrMTLHandle)queue);
        }
    }

    sk_cfp<GrMTLHandle> fDevice;
    sk_cfp<GrMTLHandle> fQueue;
};

// 使用
sk_sp<GrDirectContext> context1 = MetalDeviceManager::instance().createContext();
sk_sp<GrDirectContext> context2 = MetalDeviceManager::instance().createContext();
// context1 和 context2 共享同一 Metal 设备
```

## 相关文件

| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/mtl/GrMtlTypes.h | 定义 GrMTLHandle 类型 |
| include/ports/SkCFObject.h | 定义 sk_cfp 智能指针 |
| include/gpu/GrDirectContext.h | 使用此结构体创建上下文（`MakeMetal()` 方法） |
| src/gpu/ganesh/mtl/GrMtlGpu.h | 内部存储和使用设备与队列 |
| include/gpu/ganesh/mtl/SkSurfaceMetal.h | 创建表面时需要已初始化的上下文 |

## 最佳实践

### 单例设备管理

**推荐**: 在应用中使用单例管理 Metal 设备：
```cpp
// 避免重复创建设备（昂贵操作）
static id<MTLDevice> g_sharedDevice = nil;

id<MTLDevice> getSharedMetalDevice() {
    if (!g_sharedDevice) {
        g_sharedDevice = MTLCreateSystemDefaultDevice();
    }
    return g_sharedDevice;
}
```

### 命令队列重用

**推荐**: 重用命令队列而非频繁创建：
```cpp
// 好的做法
static id<MTLCommandQueue> g_sharedQueue = nil;

// 不好的做法
id<MTLCommandQueue> queue = [device newCommandQueue];  // 每次都创建
```

### 错误处理

**推荐**: 检查 Metal 对象创建是否成功：
```cpp
id<MTLDevice> device = MTLCreateSystemDefaultDevice();
if (!device) {
    // 处理 Metal 不可用的情况（旧设备或模拟器）
    return nullptr;
}

id<MTLCommandQueue> queue = [device newCommandQueue];
if (!queue) {
    // 队列创建失败（内存不足？）
    return nullptr;
}
```

### 多上下文场景

**推荐**: 为不同用途创建独立上下文：
```cpp
// UI 渲染上下文（高优先级）
sk_sp<GrDirectContext> uiContext = createUIContext();

// 离屏渲染上下文（低优先级）
sk_sp<GrDirectContext> offscreenContext = createOffscreenContext();
```

**注意**: 所有上下文共享同一设备，但可有独立的命令队列和资源缓存。

### 生命周期管理

**推荐**: 确保正确的清理顺序：
```cpp
// 1. 释放 Skia 上下文
context.reset();

// 2. 刷新所有待处理的 GPU 工作
// 3. 释放 Metal 对象（由 sk_cfp 自动完成）
```

**避免**: 在 Metal 对象销毁后继续使用 Skia 上下文。
