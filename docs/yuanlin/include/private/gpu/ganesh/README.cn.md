# include/private/gpu/ganesh - Ganesh GPU 后端私有头文件

## 概述

`include/private/gpu/ganesh` 目录包含 Skia Ganesh GPU 后端的私有头文件。Ganesh 是 Skia 的传统 GPU 渲染后端，支持 OpenGL、Vulkan、Metal 和 Direct3D 等多种图形 API。本目录中的头文件定义了 Ganesh 内部使用的核心类型、上下文层次结构和纹理生成器接口。

Ganesh 采用分层的上下文架构，以支持不同级别的 GPU 访问需求。`GrContext_Base` 是最基础的上下文类，提供后端 API 查询和默认格式获取功能。`GrImageContext` 在此基础上增加了图像关联功能（主要用作 `GrDirectContext` 的向下转型通道）。这种层次结构使得 Promise Image 等延迟创建的图像可以在没有直接 GPU 访问权限的线程上被创建和管理。

本目录还包含 GPU 渲染的核心类型定义（`GrTypesPriv.h`），涵盖了几何图元类型、纹理属性、内存管理策略和资源生命周期管理等方面。`GrTextureGenerator` 为从各种来源（如硬件缓冲区、视频帧等）高效生成 GPU 纹理提供了统一接口。

`GrD3DTypesMinimal.h` 提供了 Direct3D 12 后端的最小类型定义，避免直接包含庞大的 D3D12 头文件，减少编译时间和头文件依赖。

## 目录结构

```
include/private/gpu/ganesh/
├── GrContext_Base.h         # GPU 上下文基类
├── GrD3DTypesMinimal.h      # Direct3D 12 最小类型定义
├── GrImageContext.h         # 图像上下文（上下文层次的中间层）
├── GrTextureGenerator.h     # GPU 纹理生成器基类
├── GrTypesPriv.h            # Ganesh 私有类型定义集合
└── BUILD.bazel              # Bazel 构建配置
```

## 关键类与函数

### 上下文层次结构
- **`GrContext_Base`**: Ganesh 上下文层次结构的基类，继承自 `SkRefCnt`。主要功能包括：
  - `backend()`: 获取后端图形 API 类型（OpenGL、Vulkan、Metal、D3D）
  - `defaultBackendFormat()`: 根据 `SkColorType` 获取默认后端纹理格式
  - `compressedBackendFormat()`: 获取压缩纹理格式
  - `maxSurfaceSampleCountForColorType()`: 查询给定颜色类型的最大 MSAA 采样数
  - `threadSafeProxy()`: 获取线程安全代理，用于跨线程共享上下文信息

- **`GrImageContext`**: 继承自 `GrContext_Base`，作为图像与 GPU 上下文之间的桥梁。当前的主要作用是作为 `GrDirectContext` 的向下转型通道。内部持有 `skgpu::SingleOwner` 以在调试模式下验证线程安全性。通过 `MakeForPromiseImage()` 可以创建仅用于 Promise Image 的轻量级实例。

### 纹理生成
- **`GrTextureGenerator`**: 继承自 `SkImageGenerator`，为 GPU 纹理提供专门的生成接口：
  - `generateTexture()`: 核心方法，根据 `GrRecordingContext`、图像信息和 Mipmap 状态生成 `GrSurfaceProxyView`
  - `onGenerateTexture()`: 纯虚方法，由子类（如 `GrAHardwareBufferImageGenerator`）实现实际的纹理生成逻辑
  - `origin()`: 返回纹理的表面原点（默认 `kTopLeft`），硬件缓冲区等来源可能需要覆盖此方法
  - `GrImageTexGenPolicy`: 控制纹理创建策略，决定是否必须创建新纹理或可以复用现有纹理

### 私有类型定义 (GrTypesPriv.h)
- **`GrPrimitiveType`**: 几何图元类型枚举 - `kTriangles`、`kTriangleStrip`、`kPoints`、`kLines`、`kLineStrip`
- **`GrTexturable`**: 表面是否可作为纹理使用
- **`GrWrapOwnership`**: 外部 GPU 资源的所有权模式 - `kBorrow_GrWrapOwnership`（借用）、`kAdopt_GrWrapOwnership`（接管）
- **`GrDDLProvider`**: 标识代理提供者是否为 DDL 录制器专用
- **`GrPrimitiveRestart`**: 图元重启标志
- **`GrSizeDivRoundUp()`**: 向上取整除法工具函数

### Direct3D 类型
- **`GrD3DBackendSurfaceInfo`**: D3D12 后端表面信息，封装 `GrD3DTextureResourceInfo` 和 `GrD3DResourceState`，用于跟踪 D3D12 资源的当前状态（`D3D12_RESOURCE_STATES`），支持多个使用者共享状态更新。
  - `setResourceState()`: 更新资源状态，所有引用同一资源的对象都能看到状态变更。
  - `snapTextureResourceInfo()`: 获取纹理资源信息的快照。
  - `isProtected()`: 查询资源是否受保护。
- **`GrD3DResourceState`**: 引用计数的 D3D12 资源状态跟踪器，用于在多个使用者之间共享资源状态。

### 上下文继承关系详解
Ganesh 的上下文继承链设计有明确的职责划分：
```
GrContext_Base（基础查询）
  └── GrImageContext（图像关联、上下文丢失处理）
        └── GrRecordingContext（GPU 操作录制）
              └── GrDirectContext（完整 GPU 访问、资源管理、提交刷新）
```
每一层仅暴露该级别所需的最小功能集，遵循最小权限原则。例如，Promise Image 只需要 `GrImageContext` 级别的访问权限，而实际的 GPU 渲染操作需要 `GrDirectContext`。

### 纹理生成策略
- **`GrImageTexGenPolicy`**: 控制纹理生成的策略枚举：
  - `kDraw`: 绘制操作使用，可复用生成器持有的现有纹理
  - `kNew_Uncached_Unbudgeted`: 创建新的未缓存、不计入预算的纹理
  - `kNew_Uncached_Budgeted`: 创建新的未缓存但计入预算的纹理

## 依赖关系

- **上游依赖**: `include/core/`（SkRefCnt、SkColorType、SkImageGenerator 等）、`include/gpu/ganesh/`（GrTypes、GrBackendSurface、GrRecordingContext）、`include/private/base/`（SingleOwner、SkAssert、SkDebug）
- **下游消费者**: `src/gpu/ganesh/`（Ganesh 渲染管线实现）、`include/private/chromium/`（DDL 和 Promise Image 系统）、`include/android/`（Android 硬件缓冲区集成）
- **同级目录**: `include/private/gpu/vk/`（Vulkan 私有类型）

## 相关文档与参考

- [Skia GPU 后端概述](https://skia.org/docs/user/api/skcanvas_overview/#gpu) - Ganesh GPU 后端使用指南
- [GrDirectContext 文档](https://api.skia.org/classGrDirectContext.html) - 完整 GPU 上下文的公共 API
- [Skia GPU 架构](https://skia.org/docs/dev/design/) - GPU 渲染管线设计
- `include/gpu/ganesh/` - Ganesh 公共 API 头文件
- `include/private/chromium/` - Chromium DDL 系统的消费者
- `include/private/gpu/vk/` - Vulkan 专用私有头文件
- `src/gpu/ganesh/` - Ganesh 后端实现源码

## 使用注意事项

### 上下文访问级别选择
在 Skia 内部代码中，应根据实际需要选择最低权限的上下文级别：
- 仅需查询后端格式信息 -> 使用 `GrContext_Base`
- 需要关联图像到 GPU 上下文 -> 使用 `GrImageContext`
- 需要录制 GPU 操作 -> 使用 `GrRecordingContext`
- 需要执行 GPU 操作（如刷新、资源管理） -> 使用 `GrDirectContext`

### 纹理生成器实现指南
实现 `GrTextureGenerator::onGenerateTexture()` 时需注意：
- 必须在传入的 `GrRecordingContext` 上创建纹理，不能使用其他上下文
- 如果无法生成 Mipmap 纹理，可以返回非 Mipmap 版本（Skia 会自动处理后续的 Mipmap 生成）
- `origin()` 方法应该是线程安全的，因为它可能从多个线程被调用
