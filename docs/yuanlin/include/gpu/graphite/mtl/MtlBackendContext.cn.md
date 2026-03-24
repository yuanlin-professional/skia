# MtlBackendContext

> 源文件: `include/gpu/graphite/mtl/MtlBackendContext.h`

## 概述

MtlBackendContext.h 定义了创建 Metal 后端 Graphite Context 所需的结构体和工厂函数。它封装了 Metal 设备和命令队列对象,是初始化 Graphite Metal 后端的入口点。

## 架构位置

该文件位于 Skia Graphite GPU 后端的 Metal 平台特定接口层,属于 `skgpu::graphite` 命名空间。它是应用程序与 Graphite Metal 后端交互的首要接口,负责建立渲染上下文。

## 主要结构体与函数

### MtlBackendContext

```cpp
struct SK_API MtlBackendContext {
    sk_cfp<CFTypeRef> fDevice;
    sk_cfp<CFTypeRef> fQueue;
};
```

**职责**: 封装创建 Graphite Metal Context 所需的基础 Metal 对象。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fDevice` | `sk_cfp<CFTypeRef>` | Metal 设备对象 (id<MTLDevice>) |
| `fQueue` | `sk_cfp<CFTypeRef>` | Metal 命令队列 (id<MTLCommandQueue>) |

**设计特点**:
- 使用 `sk_cfp` 智能指针自动管理引用计数
- 通过 CFTypeRef 类型擦除,支持 C++ 和 Objective-C++
- 客户端负责创建和配置 Metal 对象
- Graphite 不会修改这些对象的配置

## 公共 API 函数

### ContextFactory::MakeMetal

```cpp
namespace ContextFactory {
SK_API std::unique_ptr<Context> MakeMetal(const MtlBackendContext&, const ContextOptions&);
}
```

- **功能**: 创建 Metal 后端的 Graphite Context
- **参数**:
  - `MtlBackendContext&`: 包含 Metal 设备和队列的后端上下文
  - `ContextOptions&`: Context 配置选项
- **返回值**: 成功返回 Context 智能指针,失败返回 nullptr
- **生命周期**:
  - Context 持有 fDevice 和 fQueue 的引用
  - MtlBackendContext 本身在调用后可释放
- **失败情况**:
  - Metal 设备或队列无效
  - 设备不支持必需的特性
  - 内存分配失败

## 内部实现细节

### sk_cfp 智能指针

```cpp
sk_cfp<CFTypeRef> fDevice;
```

**特性**:
- 自动调用 CFRetain/CFRelease
- 支持移动语义
- 线程安全的引用计数
- 零开销抽象(编译后与手动管理相同)

### CFTypeRef 桥接

#### 从 Objective-C 对象创建

```cpp
id<MTLDevice> device = MTLCreateSystemDefaultDevice();
id<MTLCommandQueue> queue = [device newCommandQueue];

MtlBackendContext backendContext;
backendContext.fDevice.reset((__bridge_retained CFTypeRef)device);
backendContext.fQueue.reset((__bridge_retained CFTypeRef)queue);
```

#### 访问底层对象

```cpp
// 从 Context 内部访问
id<MTLDevice> device = (__bridge id<MTLDevice>)backendContext.fDevice.get();
id<MTLCommandQueue> queue = (__bridge id<MTLCommandQueue>)backendContext.fQueue.get();
```

### Context 创建流程

1. **验证**: 检查 fDevice 和 fQueue 有效性
2. **能力查询**: 查询 Metal 设备支持的特性
3. **资源初始化**: 创建内部资源池、缓存等
4. **管线编译**: 加载或编译基础 Pipeline
5. **返回**: 返回完全初始化的 Context

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/gpu/graphite/Context.h` | Context 类定义 |
| `include/ports/SkCFObject.h` | sk_cfp 智能指针 |
| `include/private/base/SkAPI.h` | SK_API 宏 |
| `CoreFoundation/CoreFoundation.h` | CFTypeRef 定义 |

### 被依赖的模块

- 应用程序初始化代码
- Graphite Metal 后端实现
- 跨平台抽象层

## 设计模式与设计决策

### 工厂方法模式

```cpp
namespace ContextFactory {
    std::unique_ptr<Context> MakeMetal(...);
}
```

**优势**:
- 隐藏具体 Context 实现类
- 统一的创建接口
- 易于扩展其他后端(MakeDawn, MakeVulkan)

### 分离配置与创建

MtlBackendContext 负责 Metal 特定配置,ContextOptions 负责通用配置:
- **职责分离**: 平台特定 vs 通用
- **复用**: ContextOptions 可用于所有后端
- **灵活性**: 独立配置各自领域

### 智能指针所有权

使用 `sk_cfp` 而非原始指针:
- **安全性**: 自动管理引用计数
- **异常安全**: RAII 保证资源释放
- **移动语义**: 高效转移所有权

## 性能考量

### 设备选择

```cpp
// 获取默认设备(通常是集成GPU)
id<MTLDevice> device = MTLCreateSystemDefaultDevice();

// 或选择高性能设备
NSArray<id<MTLDevice>>* devices = MTLCopyAllDevices();
for (id<MTLDevice> d in devices) {
    if (!d.isLowPower) {
        device = d;  // 选择独立GPU
        break;
    }
}
```

### 命令队列配置

```cpp
// 基础配置
id<MTLCommandQueue> queue = [device newCommandQueue];

// 或指定优先级(macOS)
id<MTLCommandQueue> queue = [device newCommandQueueWithMaxCommandBufferCount:64];
```

### Context 创建开销

- **典型耗时**: 10-100ms
- **主要开销**: Pipeline 编译、资源预分配
- **优化**: 使用 PersistentPipelineStorage 缓存

## 使用示例

### 基础初始化

```cpp
#include "include/gpu/graphite/mtl/MtlBackendContext.h"
#include "include/gpu/graphite/ContextOptions.h"

using namespace skgpu::graphite;

// 创建 Metal 对象
id<MTLDevice> device = MTLCreateSystemDefaultDevice();
id<MTLCommandQueue> queue = [device newCommandQueue];

// 构造后端上下文
MtlBackendContext backendContext;
backendContext.fDevice.reset((__bridge_retained CFTypeRef)device);
backendContext.fQueue.reset((__bridge_retained CFTypeRef)queue);

// 配置选项
ContextOptions options;
options.fGpuBudgetInBytes = 256 * 1024 * 1024;  // 256 MB

// 创建 Context
std::unique_ptr<Context> context = ContextFactory::MakeMetal(backendContext, options);
if (!context) {
    // 处理错误
}
```

### 使用 Pipeline 缓存

```cpp
// 持久化存储
FilePipelineStorage storage("/path/to/cache.bin");

MtlBackendContext backendContext;
// ... 初始化 fDevice 和 fQueue ...

ContextOptions options;
options.fPersistentPipelineStorage = &storage;

auto context = ContextFactory::MakeMetal(backendContext, options);
```

### 多线程编译

```cpp
SkTaskExecutor executor(4);  // 4 worker threads

ContextOptions options;
options.fExecutor = &executor;

auto context = ContextFactory::MakeMetal(backendContext, options);
```

### 完整应用示例

```cpp
class GraphiteApp {
public:
    bool initialize() {
        // 创建 Metal 设备
        fDevice = MTLCreateSystemDefaultDevice();
        if (!fDevice) return false;

        // 创建命令队列
        fQueue = [fDevice newCommandQueue];
        if (!fQueue) return false;

        // 构造后端上下文
        MtlBackendContext backendContext;
        backendContext.fDevice.reset((__bridge_retained CFTypeRef)fDevice);
        backendContext.fQueue.reset((__bridge_retained CFTypeRef)fQueue);

        // 配置
        ContextOptions options;
        options.fGpuBudgetInBytes = 512 * 1024 * 1024;
        options.fSetBackendLabels = true;

        // 创建 Context
        fContext = ContextFactory::MakeMetal(backendContext, options);
        return fContext != nullptr;
    }

    void shutdown() {
        fContext.reset();
        [fQueue release];
        [fDevice release];
    }

private:
    id<MTLDevice> fDevice;
    id<MTLCommandQueue> fQueue;
    std::unique_ptr<Context> fContext;
};
```

## 平台相关说明

### iOS

- **设备**: 只有一个设备,使用 `MTLCreateSystemDefaultDevice()`
- **队列**: 通常创建一个全局队列
- **内存**: 注意内存限制,调整 `fGpuBudgetInBytes`

### macOS

- **设备**: 可能有多个(集成+独立GPU)
- **选择策略**:
  - 交互式应用: 集成GPU(省电)
  - 高性能应用: 独立GPU
- **eGPU**: 支持外接 GPU

### tvOS

- 与 iOS 类似
- 性能介于 iOS 和 macOS 之间

### Mac Catalyst

- 在 iPad 上运行的 macOS 应用
- Metal 行为与 iOS 相同

## 错误处理

### 设备创建失败

```cpp
id<MTLDevice> device = MTLCreateSystemDefaultDevice();
if (!device) {
    // Metal 不可用
    // 可能原因:
    // - 系统过旧(macOS < 10.11, iOS < 8.0)
    // - 虚拟机环境
    // - GPU 驱动问题
}
```

### Context 创建失败

```cpp
auto context = ContextFactory::MakeMetal(backendContext, options);
if (!context) {
    // 可能原因:
    // - fDevice 或 fQueue 为空
    // - 设备不支持必需特性
    // - 内存不足
}
```

### 资源限制

```cpp
// 监听内存警告(iOS)
[[NSNotificationCenter defaultCenter]
    addObserver:self
    selector:@selector(handleMemoryWarning:)
    name:UIApplicationDidReceiveMemoryWarningNotification
    object:nil];

- (void)handleMemoryWarning:(NSNotification*)notification {
    // 调用 Context::freeGpuResources()
    context->freeGpuResources();
}
```

## 最佳实践

1. **设备选择**: 根据应用需求选择合适的 GPU
2. **队列数量**: 通常一个全局队列足够,多队列仅用于特殊优化
3. **错误处理**: 总是检查 Context 创建是否成功
4. **生命周期**: Context 应在 Metal 对象之前销毁
5. **内存预算**: 根据平台调整 `fGpuBudgetInBytes`
6. **Pipeline 缓存**: 生产环境应启用持久化缓存

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/Context.h` | Context 基类 |
| `include/gpu/graphite/ContextOptions.h` | 配置选项 |
| `include/ports/SkCFObject.h` | sk_cfp 定义 |
| `src/gpu/graphite/mtl/MtlGraphiteContext.cpp` | Metal Context 实现 |

## 注意事项

### 引用计数

- `__bridge`: 不改变引用计数
- `__bridge_retained`: +1 引用计数(传递所有权给 C++)
- `__bridge_transfer`: 转移所有权(C++ 到 Objective-C)

### 线程安全

- MTLDevice: 线程安全
- MTLCommandQueue: 线程安全
- Context 创建: 应在主线程
- 后续使用: 参考 Context 文档

### ARC 兼容

在 ARC 环境下:
```cpp
// ARC 管理 Objective-C 对象
id<MTLDevice> device = MTLCreateSystemDefaultDevice();
// 无需手动 release

// 传递给 C++ 时需要 bridge_retained
backendContext.fDevice.reset((__bridge_retained CFTypeRef)device);
```
