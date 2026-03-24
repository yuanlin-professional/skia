# include/gpu - Skia GPU 公共 API 顶层目录

## 概述

`include/gpu` 是 Skia 图形库中 GPU 相关公共 API 的顶层目录。该目录定义了所有 GPU 后端
（Ganesh 和 Graphite）共享的核心类型、枚举和抽象接口。无论应用程序使用的是 OpenGL、Vulkan、
Metal、Direct3D 还是 Dawn 后端，都需要依赖此目录中的基础类型。

此目录中的头文件数量精简，仅包含最基础、最通用的 GPU 类型定义。具体的后端实现（如 Vulkan、
Metal）位于子目录中，而 Ganesh 和 Graphite 两个渲染引擎的公共 API 则分别位于 `ganesh/` 和
`graphite/` 子目录下。这种分层设计使得不同后端和不同渲染引擎之间能够共享公共类型定义，
同时保持良好的模块化。

`skgpu` 命名空间是所有 GPU 相关公共类型的顶级命名空间。通过枚举如 `BackendApi` 来标识
不同的图形 API 后端，通过 `Mipmapped`、`Protected`、`Renderable` 等布尔枚举来描述
纹理和资源的属性。这些类型在 Ganesh (`GrDirectContext`) 和 Graphite (`skgpu::graphite::Context`)
中均被广泛使用。

`MutableTextureState` 提供了一种后端无关的方式来跟踪和通知纹理状态的变化（例如 Vulkan 中的
image layout 和 queue family index），使得 Skia 和客户端能够在修改 GPU 纹理状态时保持同步。
`ShaderErrorHandler` 则提供了着色器编译错误的统一上报机制。

## 架构图

```
include/gpu/
    |
    +-- GpuTypes.h              <-- 所有 GPU 后端共享的基础类型
    +-- MutableTextureState.h   <-- 可变纹理状态（后端无关）
    +-- ShaderErrorHandler.h    <-- 着色器编译错误处理
    |
    +-- vk/                     <-- Vulkan 公共类型（共享于 Ganesh 和 Graphite）
    +-- mtl/                    <-- Metal 公共类型（共享于 Ganesh 和 Graphite）
    |
    +-- ganesh/                 <-- Ganesh 渲染引擎公共 API
    |   +-- gl/                 <-- OpenGL 后端
    |   +-- vk/                 <-- Vulkan 后端（Ganesh 特有）
    |   +-- mtl/                <-- Metal 后端（Ganesh 特有）
    |   +-- d3d/                <-- Direct3D 12 后端
    |   +-- mock/               <-- Mock 测试后端
    |
    +-- graphite/               <-- Graphite 渲染引擎公共 API
        +-- dawn/               <-- Dawn/WebGPU 后端
        +-- vk/                 <-- Vulkan 后端（Graphite 特有）
        +-- mtl/                <-- Metal 后端（Graphite 特有）
        +-- precompile/         <-- 管线预编译 API
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GpuTypes.h` | 定义所有 GPU 后端共享的基础枚举和结构体 |
| `MutableTextureState.h` | 可变纹理状态的后端无关封装 |
| `ShaderErrorHandler.h` | 着色器编译错误的抽象处理器 |

## 关键类与函数

### `skgpu::BackendApi` 枚举 (GpuTypes.h)

标识 Graphite 支持的 3D API 后端类型：

```cpp
enum class BackendApi : unsigned {
    kDawn,      // Dawn/WebGPU 后端
    kMetal,     // Apple Metal 后端
    kVulkan,    // Vulkan 后端
    kMock,      // Mock 测试后端
    kUnsupported, // 不支持的后端（如 Direct3D 在 Graphite 中）
};
```

### 布尔枚举类型 (GpuTypes.h)

```cpp
enum class Budgeted : bool;     // 资源是否计入缓存预算
enum class CallbackResult : bool; // 回调操作的结果
enum class Mipmapped : bool;    // 纹理是否包含 mipmap
enum class Protected : bool;    // GPU 数据是否受保护（DRM）
enum class Renderable : bool;   // 纹理是否可用于渲染
enum class Origin : unsigned;   // 纹理逻辑原点（左上/左下）
```

### `skgpu::GpuStats` 结构体 (GpuTypes.h)

```cpp
struct GpuStats {
    uint64_t elapsedTime = 0;              // GPU 耗时
    uint64_t numOcclusionPassSamples = 0;  // 遮挡查询采样数
};
```

### `skgpu::MutableTextureState` 类 (MutableTextureState.h)

```cpp
class MutableTextureState : public SkRefCnt {
    BackendApi backend() const;
    bool isValid() const;
    void set(const MutableTextureState& that);
};
```

用于在 Skia 和客户端之间同步纹理可变状态的通用封装。后端特定的状态数据
（如 Vulkan 的 `VkImageLayout`）通过子类型化机制内联存储。

### `skgpu::ShaderErrorHandler` 类 (ShaderErrorHandler.h)

```cpp
class ShaderErrorHandler {
    virtual void compileError(const char* shader, const char* errors);
    virtual void compileError(const char* shader, const char* errors, bool shaderWasCached);
};
ShaderErrorHandler* DefaultShaderErrorHandler(); // 默认处理器（SkDebugf + assert）
```

着色器编译错误的抽象回调。客户端可派生此类以自定义错误处理逻辑。

## 依赖关系

- **上游依赖**: `include/core/SkTypes.h`, `include/core/SkRefCnt.h`
- **被下游引用**: `include/gpu/ganesh/` (Ganesh 引擎), `include/gpu/graphite/` (Graphite 引擎)
- **被下游引用**: `include/gpu/vk/`, `include/gpu/mtl/` (后端特定类型)
- **运行时关联**: `src/gpu/` 中的对应实现

## 相关文档与参考

- `include/gpu/ganesh/` - Ganesh 渲染引擎（传统 GPU 后端，支持 GL/VK/MTL/D3D）
- `include/gpu/graphite/` - Graphite 渲染引擎（新一代 GPU 后端，支持 Dawn/VK/MTL）
- `include/gpu/vk/` - Vulkan 共享类型定义
- `include/gpu/mtl/` - Metal 共享类型定义
- Skia 官方文档: https://skia.org/docs/dev/design/
