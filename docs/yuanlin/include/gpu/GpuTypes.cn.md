# GpuTypes

> 源文件: `include/gpu/GpuTypes.h`

## 概述

`GpuTypes.h` 是 Skia GPU 模块的基础类型定义头文件，定义了所有 GPU 后端共用的公共枚举类型和数据结构。该文件位于 `skgpu` 命名空间下，为 Skia 的两大 GPU 引擎 -- Ganesh（旧版）和 Graphite（新版）-- 提供统一的底层类型抽象。

这些类型涵盖了 GPU 编程中的核心概念，包括后端 API 标识、资源预算控制、纹理属性描述、数据保护标志以及 GPU 性能统计等。通过将这些基础类型集中定义，Skia 确保了不同后端之间的类型一致性和代码复用。

## 架构位置

```
Skia GPU 架构
├── include/gpu/GpuTypes.h          <-- 本文件：所有 GPU 后端共享的基础类型
│
├── Ganesh 引擎 (旧版 GPU 后端)
│   ├── include/gpu/ganesh/GrTypes.h     (Ganesh 专用类型，引用 GpuTypes.h)
│   ├── include/gpu/ganesh/GrDirectContext.h
│   └── ...
│
├── Graphite 引擎 (新版 GPU 后端)
│   ├── include/gpu/graphite/...
│   └── ...
│
└── 具体后端实现
    ├── Dawn (WebGPU)
    ├── Metal (Apple)
    ├── Vulkan
    └── Mock (测试用)
```

`GpuTypes.h` 处于 GPU 模块的最底层，被 Ganesh 和 Graphite 两套引擎共同依赖。它只依赖 `include/core/SkTypes.h`（Skia 核心类型），不引入任何后端特定的头文件，从而保持了良好的层次隔离。

## 主要类与结构体

### 枚举类型

| 枚举名 | 底层类型 | 说明 |
|--------|---------|------|
| `BackendApi` | `unsigned` | 标识可用的 3D 图形 API 后端 |
| `Budgeted` | `bool` | 资源是否计入缓存预算 |
| `CallbackResult` | `bool` | 异步回调的结果状态 |
| `Mipmapped` | `bool` | 纹理是否包含 mipmap 层级 |
| `Protected` | `bool` | GPU 数据是否受 DRM 保护 |
| `Renderable` | `bool` | 纹理是否可作为渲染目标 |
| `Origin` | `unsigned` | 后端纹理的逻辑坐标原点 |
| `GpuStatsFlags` | `uint32_t` | 控制需要收集哪些 GPU 统计信息的位掩码 |

### 结构体

| 结构体名 | 说明 |
|----------|------|
| `GpuStats` | 存储 GPU 性能统计数据，包含执行时间和遮挡查询采样数 |

## 公共 API 函数

本文件不包含函数定义，仅提供类型声明。以下是各类型的详细说明及使用方式。

### BackendApi

```cpp
enum class BackendApi : unsigned {
    kDawn,          // WebGPU 的 Dawn 实现
    kMetal,         // Apple Metal API
    kVulkan,        // Vulkan API
    kMock,          // 模拟后端，用于测试
    kUnsupported,   // 不受支持的后端类型
};
```

标识 Graphite 引擎所支持的 3D 图形 API。需要注意的是，这与 Ganesh 引擎中的 `GrBackendApi` 是不同的枚举。Ganesh 支持 OpenGL 和 Direct3D，而 Graphite 不支持这两个 API，因此会返回 `kUnsupported`。

### Budgeted

```cpp
enum class Budgeted : bool {
    kNo = false,    // 不计入缓存预算
    kYes = true,    // 计入缓存预算
};
```

控制 GPU 资源分配是否受缓存预算的限制。当设为 `kYes` 时，该资源的内存占用将计入 Skia 的 GPU 资源缓存上限。超出上限时，缓存系统会清理旧的受预算管理的资源。设为 `kNo` 的资源（如客户端直接管理的纹理）不受缓存清理策略影响。

### CallbackResult

```cpp
enum class CallbackResult : bool {
    kFailed = false,   // 操作失败
    kSuccess = true,   // 操作成功
};
```

用于各种异步回调函数中，通知客户端操作的执行结果。具体含义取决于关联的回调类型，例如纹理读回（readback）完成回调或 GPU 提交完成回调。

### Mipmapped

```cpp
enum class Mipmapped : bool {
    kNo = false,    // 不生成 mipmap
    kYes = true,    // 生成 mipmap
};
```

指示纹理是否包含 mipmap 纹理链。Mipmap 是一组逐级缩小的纹理副本，用于在缩小渲染时提高视觉质量并减少锯齿。启用 mipmap 会增加约 33% 的显存占用。

### Protected

```cpp
enum class Protected : bool {
    kNo = false,    // 不使用保护内存
    kYes = true,    // 使用保护内存
};
```

标识数据是否存储在 GPU 的受保护内存区域中。受保护内存通常用于 DRM（数字版权管理）内容的渲染，防止未授权的内存读取或截屏操作。该功能需要硬件和驱动的支持（如 Vulkan 的 Protected Memory 扩展）。

### Renderable

```cpp
enum class Renderable : bool {
    kNo = false,    // 仅用作采样纹理
    kYes = true,    // 可作为渲染目标（FBO/RenderPass attachment）
};
```

指示纹理是否可以作为渲染目标。可渲染纹理可以绑定为帧缓冲区的颜色附件，支持 GPU 向其中绘制内容。非可渲染纹理仅能用于采样（读取）操作。

### Origin

```cpp
enum class Origin : unsigned {
    kTopLeft,       // 原点在左上角（常规屏幕坐标）
    kBottomLeft,    // 原点在左下角（OpenGL 风格坐标）
};
```

描述后端纹理的像素数据在内存中的逻辑起始位置。OpenGL 传统上将原点放在左下角，而大多数其他 API（Metal、Vulkan、Direct3D）以及屏幕坐标系使用左上角为原点。Skia 在内部处理这种差异，但当客户端传入已有的后端纹理时，需要正确标注其原点方向。

### GpuStatsFlags 与 GpuStats

```cpp
enum class GpuStatsFlags : uint32_t {
    kNone                = 0b00,   // 不收集统计信息
    kElapsedTime         = 0b01,   // 收集 GPU 执行时间
    kOcclusionPassSamples = 0b10,  // 收集遮挡查询采样数
};

struct GpuStats {
    uint64_t elapsedTime = 0;              // GPU 执行耗时
    uint64_t numOcclusionPassSamples = 0;  // 遮挡通道采样数
};
```

`GpuStatsFlags` 是一个位掩码枚举，用于指定需要收集的 GPU 性能统计类别。`GpuStats` 结构体存储实际的统计数据。这些机制主要用于性能分析和调试，允许开发者度量 GPU 端的执行耗时以及遮挡剔除通道中通过测试的片元数量。

## 内部实现细节

本文件采用了多个 C++ 现代特性来增强类型安全：

1. **强类型枚举（enum class）**：所有枚举均使用 `enum class` 而非传统 `enum`，避免枚举值的隐式类型转换和命名空间污染。

2. **布尔底层类型**：`Budgeted`、`CallbackResult`、`Mipmapped`、`Protected`、`Renderable` 均以 `bool` 为底层类型。这使得这些枚举可以自然地参与布尔逻辑运算，同时保持类型安全（例如 `Budgeted` 和 `Mipmapped` 不能混用）。

3. **位掩码设计**：`GpuStatsFlags` 使用 `uint32_t` 底层类型并以二进制字面量定义值，支持通过位运算组合多个标志。

4. **默认初始化**：`GpuStats` 的所有成员均有默认初始值 0，确保在未收集数据时返回安全的零值。

## 依赖关系

```
GpuTypes.h
└── include/core/SkTypes.h   (Skia 核心基础类型，提供 uint32_t 等)
```

该文件的依赖极其简洁，仅依赖 Skia 的核心类型头文件。反向依赖方面，该文件被大量 GPU 相关文件引用，包括：

- `include/gpu/ganesh/GrTypes.h` -- Ganesh 引擎类型定义
- `include/gpu/ganesh/GrDirectContext.h` -- Ganesh 直接上下文
- 各种 Graphite 引擎组件
- 测试文件和工具代码

## 设计模式与设计决策

### 统一类型层的设计理念

Skia 有两套 GPU 引擎（Ganesh 和 Graphite），它们使用不同的后端 API 集合但共享许多基础概念。将这些公共类型提取到一个独立文件中是一种**分层架构**（Layered Architecture）的体现，避免了两套引擎之间的循环依赖。

### 强类型布尔枚举

使用 `enum class` 包装布尔值而非直接使用 `bool` 参数，是为了解决 C++ 中的**布尔参数可读性问题**。例如：

```cpp
// 难以理解各个 bool 的含义
createTexture(true, false, true);

// 使用强类型枚举后，语义清晰
createTexture(Mipmapped::kYes, Protected::kNo, Renderable::kYes);
```

这种模式在 Skia 代码库中广泛使用，显著提升了 API 的可读性和安全性。

### 命名空间隔离

所有类型位于 `skgpu` 命名空间中，与 Ganesh 的 `Gr` 前缀命名风格和 Graphite 的命名空间风格均兼容，充当两者的公共基础。

## 性能考量

- 所有枚举类型均使用最小的底层类型（`bool` 或 `unsigned`），在作为函数参数或结构体成员时占用最少的存储空间。
- `GpuStats` 结构体仅包含两个 `uint64_t` 成员（共 16 字节），可以高效地按值传递或复制。
- 这些类型仅用于描述和配置，本身不涉及任何运行时计算开销。
- `GpuStatsFlags` 的位掩码设计允许通过单个整数传递多种统计需求，避免了多参数传递的开销。

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/core/SkTypes.h` | Skia 核心基础类型，`GpuTypes.h` 的唯一依赖 |
| `include/gpu/ganesh/GrTypes.h` | Ganesh 引擎的类型定义，包含 `GrBackendApi` 等 Ganesh 专用类型 |
| `include/gpu/ganesh/GrDirectContext.h` | Ganesh 直接上下文，使用本文件中的多种类型 |
| `include/gpu/graphite/GraphiteTypes.h` | Graphite 引擎类型，同样引用 `GpuTypes.h` |
| `include/gpu/ShaderErrorHandler.h` | 着色器错误处理接口 |
