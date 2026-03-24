# include/private/gpu - GPU 后端私有头文件

## 概述

`include/private/gpu` 目录是 Skia GPU 后端私有头文件的组织目录。该目录本身不直接包含头文件（仅有 `BUILD.bazel` 构建配置），而是作为 GPU 相关私有头文件子目录的父容器。其下包含两个重要子目录：`ganesh/`（Ganesh 渲染引擎私有类型）和 `vk/`（Vulkan 后端私有头文件）。

Skia 当前拥有两个 GPU 渲染引擎：Ganesh（传统引擎）和 Graphite（新一代引擎）。Ganesh 是成熟稳定的 GPU 后端，支持 OpenGL、OpenGL ES、Vulkan、Metal 和 Direct3D 12 等多种图形 API。Graphite 是 Skia 正在开发的下一代 GPU 渲染引擎，旨在更好地利用现代图形 API 的特性。本目录中的私有头文件主要服务于 Ganesh 引擎的内部实现。

这些私有头文件定义了 GPU 上下文层次结构（`GrContext_Base` -> `GrImageContext` -> `GrRecordingContext` -> `GrDirectContext`）的内部接口、GPU 纹理生成器、渲染图元类型以及图形 API 特定的类型封装。它们被 Skia 内部的 GPU 渲染管线和特权嵌入者（如 Chromium）所使用。

本目录的组织结构清晰地反映了 Skia GPU 后端的架构：通用 GPU 类型位于 `ganesh/` 子目录，而图形 API 特定的类型（如 Vulkan）则位于对应的子目录中。

## 目录结构

```
include/private/gpu/
├── ganesh/                      # Ganesh GPU 后端私有头文件
│   ├── GrContext_Base.h         # GPU 上下文基类
│   ├── GrD3DTypesMinimal.h      # Direct3D 12 最小类型定义
│   ├── GrImageContext.h         # 图像上下文
│   ├── GrTextureGenerator.h     # GPU 纹理生成器
│   ├── GrTypesPriv.h            # 私有类型定义（图元、纹理属性等）
│   └── BUILD.bazel              # 构建配置
├── vk/                          # Vulkan 私有头文件
│   ├── SkiaVulkan.h             # Vulkan 头文件统一入口
│   └── BUILD.bazel              # 构建配置
└── BUILD.bazel                  # 本目录构建配置
```

## 关键类与函数

### Ganesh 上下文层次结构
Ganesh 采用分层上下文设计，每一层提供不同级别的 GPU 访问能力：

- **`GrContext_Base`** (`ganesh/GrContext_Base.h`): 最基础的上下文层，提供后端 API 查询（`backend()`）、默认格式获取（`defaultBackendFormat()`）和线程安全代理访问（`threadSafeProxy()`）。
- **`GrImageContext`** (`ganesh/GrImageContext.h`): 中间层上下文，继承自 `GrContext_Base`，为 SkImage 提供 GPU 上下文关联。包含 `abandonContext()` 和 `abandoned()` 用于处理 GPU 上下文丢失。
- `GrRecordingContext`（在 `include/gpu/ganesh/` 中定义）: 支持 GPU 操作录制的上下文层。
- `GrDirectContext`（在 `include/gpu/ganesh/` 中定义）: 具有完整 GPU 访问权限的上下文。

### GPU 纹理生成
- **`GrTextureGenerator`** (`ganesh/GrTextureGenerator.h`): 抽象基类，允许从非标准来源生成 GPU 纹理，通过 `generateTexture()` 方法返回 `GrSurfaceProxyView`。

### 核心 GPU 类型
- **`GrPrimitiveType`** (`ganesh/GrTypesPriv.h`): 渲染图元类型 - 三角形、三角形带、点、线段、线带。
- **`GrWrapOwnership`**: 外部 GPU 资源导入时的所有权语义。
- **`GrD3DBackendSurfaceInfo`** (`ganesh/GrD3DTypesMinimal.h`): Direct3D 12 后端表面信息封装。

### Vulkan 集成
- **`SkiaVulkan.h`** (`vk/SkiaVulkan.h`): Vulkan API 头文件的统一引入点，根据平台和构建配置选择正确的 Vulkan 头文件路径。在 Android 平台上额外引入 `vulkan_android.h` 以支持 AHardwareBuffer 等 Android 扩展。

### 目录设计理念
本目录采用两级组织结构的设计理由如下：
- **按渲染引擎划分**: `ganesh/` 子目录包含 Ganesh 引擎的私有类型。当前 Graphite 引擎的私有类型分布在其他位置（如 `src/gpu/graphite/`），但未来可能在此目录下增加 `graphite/` 子目录。
- **按图形 API 划分**: `vk/` 子目录包含 Vulkan 特定的头文件。其他图形 API（OpenGL、Metal、D3D）的特定头文件主要位于 `src/` 目录中或直接在 `ganesh/` 子目录的通用头文件里处理。
- **最小暴露原则**: 仅将确实需要在头文件级别跨模块共享的类型放在此目录，其余实现细节保留在 `src/` 中。

### 公共与私有 API 的边界
GPU 相关头文件的公共/私有划分遵循以下规则：
- `include/gpu/`（公共）: 面向所有 Skia 用户的 GPU API，如 `GrDirectContext`、`GrBackendTexture`
- `include/private/gpu/`（私有）: 面向 Skia 内部和特权嵌入者的 GPU 类型，如 `GrContext_Base`、`GrTypesPriv`
- `src/gpu/`（内部）: 纯内部实现，不对外暴露任何头文件

## 依赖关系

- **上游依赖**: `include/core/`（SkRefCnt、SkColorType 等）、`include/gpu/`（GpuTypes）、`include/gpu/ganesh/`（GrTypes、GrBackendSurface）、`include/private/base/`（基础设施）
- **下游消费者**: `include/private/chromium/`（DDL、Promise Image）、`include/android/`（Android 集成）、`src/gpu/ganesh/`（Ganesh 实现）、`src/gpu/vk/`（Vulkan 实现）
- **子目录关系**: `ganesh/` 定义通用 GPU 类型，`vk/` 定义 Vulkan 特定类型

## 相关文档与参考

- [Skia GPU 概述](https://skia.org/docs/user/api/skcanvas_overview/#gpu) - GPU 渲染后端使用指南
- [Ganesh 架构](https://skia.org/docs/dev/design/) - Ganesh 渲染引擎的设计文档
- [Graphite 概述](https://skia.org/docs/user/api/graphite/) - 新一代 GPU 渲染引擎
- `include/gpu/` - GPU 公共 API
- `include/gpu/ganesh/` - Ganesh 公共 API
- `include/gpu/vk/` - Vulkan 公共 API
- `include/private/gpu/ganesh/` - Ganesh 私有类型详细文档
- `include/private/gpu/vk/` - Vulkan 私有类型详细文档

## 使用注意事项

### Ganesh 与 Graphite 的迁移
Skia 正在逐步从 Ganesh 迁移到 Graphite 渲染引擎。在这个过程中：
- 本目录中的 Ganesh 私有类型将继续被维护，直到 Ganesh 被完全弃用
- 新功能开发优先在 Graphite 引擎中进行
- 如果需要使用 GPU 私有类型，应先评估是否有 Graphite 等效接口

### 头文件包含建议
- 优先包含 `include/gpu/` 中的公共头文件
- 只有在确实需要内部功能时才包含 `include/private/gpu/` 中的头文件
- 避免在公共 API 头文件中包含私有 GPU 头文件（会导致私有类型泄漏到公共接口）

### GPU 后端选择指南
Skia 的 GPU 后端选择取决于目标平台和性能需求：
- **Android**: 推荐 Vulkan（通过 `include/private/gpu/vk/SkiaVulkan.h`），回退到 OpenGL ES
- **iOS/macOS**: 推荐 Metal
- **Windows**: 推荐 Direct3D 12 或 Vulkan
- **Web**: 通过 Dawn 使用 WebGPU
- **Linux**: Vulkan 或 OpenGL

### 目录未来发展
随着 Skia 架构的演进，本目录可能会发生以下变化：
- 增加 `graphite/` 子目录存放 Graphite 引擎的私有 GPU 类型
- Ganesh 相关头文件可能在 Ganesh 引擎正式弃用后被移除
- 新的图形 API 后端（如 WebGPU 原生支持）可能带来新的子目录
