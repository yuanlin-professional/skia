# GraphiteMtlTestContext - Graphite Metal 测试上下文

> 源文件:
> - `tools/graphite/mtl/GraphiteMtlTestContext.h`
> - `tools/graphite/mtl/GraphiteMtlTestContext.mm`

## 概述

GraphiteMtlTestContext 提供了基于 Apple Metal 后端的 Graphite 测试上下文实现。它负责创建和管理 Metal 设备（MTLDevice）及命令队列（MTLCommandQueue），为 Skia 的 Graphite 渲染引擎提供 Metal 后端测试环境。实现文件使用 Objective-C++ (.mm) 以便直接调用 Metal API。

## 架构位置

```
skiatest::graphite::GraphiteTestContext (基类)
    └── skiatest::graphite::MtlTestContext (Metal 后端实现)
```

与 `VulkanTestContext` 和 `DawnTestContext` 并列，共同构成 Graphite 多后端测试基础设施的一部分。仅在 macOS/iOS 平台上可用。

## 主要类与结构体

### `MtlTestContext`

- **继承**: `GraphiteTestContext`
- **命名空间**: `skiatest::graphite`
- **成员变量**:
  - `fMtl` (`skgpu::graphite::MtlBackendContext`): Metal 后端上下文，包含设备和命令队列

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `Make()` | 静态工厂方法，创建并返回 `MtlTestContext` 实例 |
| `backend()` | 返回 `skgpu::BackendApi::kMetal` |
| `contextType()` | 返回 `skgpu::ContextType::kMetal` |
| `makeContext(const TestOptions&)` | 创建 Graphite Metal 上下文用于测试 |
| `getBackendContext()` | 返回底层 `MtlBackendContext` 的常量引用 |

## 内部实现细节

### Metal 设备选择策略（macOS）

在 macOS 平台（`SK_BUILD_FOR_MAC`）下，`Make()` 方法实现了智能设备选择：

1. 调用 `MTLCopyAllDevices()` 枚举所有可用 Metal 设备
2. 优先选择非低功耗（`!isLowPower`）的 GPU（即独立显卡）
3. 其次选择可拔出（`isRemovable`）的外部 GPU
4. 如果以上都不满足，回退到 `MTLCreateSystemDefaultDevice()`

在非 macOS 平台（如 iOS）上，直接使用 `MTLCreateSystemDefaultDevice()`。

### 上下文创建

选择设备后，创建 `MtlBackendContext`：
- `fDevice`: 通过 `retain` 保持对 Metal 设备的强引用
- `fQueue`: 通过 `[device newCommandQueue]` 创建命令队列

### makeContext 配置

设置 `fStoreContextRefInRecorder = true` 以支持同步 `readPixels` 操作。然后通过 `ContextFactory::MakeMetal` 创建 Graphite Context。

## 依赖关系

- **内部依赖**: `GraphiteTestContext`（基类）、`TestOptions`、`ContextOptionsPriv`
- **Metal 框架**: `<Metal/Metal.h>`（通过 Objective-C++ 引入）
- **Graphite 核心**: `Context`、`ContextOptions`、`MtlBackendContext`
- **平台工具**: `ContextType`（上下文类型枚举）

## 设计模式与设计决策

- **工厂方法模式**: `Make()` 封装平台相关的 Metal 设备选择逻辑
- **受保护构造函数**: 使用 `protected` 而非 `private`（与 Vulkan 版本不同），允许子类化
- **平台条件编译**: 使用 `SK_BUILD_FOR_MAC` 区分 macOS 和 iOS 的设备选择逻辑
- **Objective-C++ 桥接**: 使用 `.mm` 文件扩展名以便混合 C++ 和 Objective-C 代码调用 Metal API
- **`sk_cfp` 智能指针**: 使用 Core Foundation 智能指针管理 Objective-C 对象的生命周期

## 性能考量

- 优先选择独立显卡（非低功耗设备），确保测试使用最高性能的 GPU
- Metal 命令队列在初始化时一次性创建，避免重复创建的开销
- 析构函数为空 (`{}`)，依赖成员变量的自动析构完成 Metal 资源释放

## 相关文件

- `tools/graphite/GraphiteTestContext.h` - 测试上下文基类
- `tools/graphite/vk/GraphiteVulkanTestContext.h` - Vulkan 后端对应实现
- `tools/graphite/dawn/GraphiteDawnTestContext.h` - Dawn 后端对应实现
- `include/gpu/graphite/mtl/MtlBackendContext.h` - Metal 后端上下文定义
- `tools/graphite/TestOptions.h` - 测试选项定义
