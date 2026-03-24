# ProtectedUtils.h - GPU 受保护内容工具函数

> 源文件: [tools/gpu/ProtectedUtils.h](../../tools/gpu/ProtectedUtils.h)

## 概述

此头文件声明了一组工具函数，用于创建具有明确保护状态（protected/unprotected）的 GPU Surface 和 Image。受保护内容（Protected Content）是一种 GPU 安全机制，用于防止受 DRM 保护的视频内容被未授权复制。这些函数同时支持 Ganesh 和 Graphite 两种 GPU 后端，主要用于 Skia 的 GPU 保护内容功能的测试。

## 架构位置

该头文件属于 Skia 工具层的 GPU 测试辅助模块（`tools/gpu/`），在 `ProtectedUtils` 命名空间下。它为 Skia 的 GPU 保护内容测试提供了工厂函数，桥接了测试代码与底层 GPU 后端的保护内容 API。

## 主要类与结构体

本文件仅声明函数（无类定义）。依赖的关键类型：

- **`GrDirectContext`**：Ganesh 直接上下文（前向声明）
- **`SkImage`**、**`SkSurface`**：Skia 核心类型（前向声明）
- **`SkSurfaceProps`**：Surface 属性（前向声明）
- **`skgpu::Protected`**：Graphite 保护状态枚举
- **`skgpu::graphite::Recorder`**：Graphite 录制器

## 公共 API 函数

### Ganesh 后端（`#ifdef SK_GANESH`）

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `CreateProtectedSkSurface(ctx, size, textureable, isProtected, props)` | GrDirectContext*, SkISize, bool, bool, SkSurfaceProps* | `sk_sp<SkSurface>` | 创建指定保护状态的 Surface |
| `CheckImageBEProtection(image, expectingProtected)` | SkImage*, bool | void | 验证图像的后端保护状态 |
| `CreateProtectedSkImage(ctx, size, color, isProtected)` | GrDirectContext*, SkISize, SkColor4f, bool | `sk_sp<SkImage>` | 创建指定保护状态的纯色图像 |

### Graphite 后端（`#ifdef SK_GRAPHITE`）

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `CreateProtectedSkSurface(recorder, size, protection)` | Recorder*, SkISize, skgpu::Protected | `sk_sp<SkSurface>` | 创建指定保护状态的 Surface |
| `CreateProtectedSkImage(recorder, size, color, protection)` | Recorder*, SkISize, SkColor4f, skgpu::Protected | `sk_sp<SkImage>` | 创建指定保护状态的纯色图像 |

## 内部实现细节

- 头文件仅包含函数声明，实现位于对应的 `.cpp` 文件中。
- 如果无法以指定的保护状态创建 Surface/Image，函数返回 `nullptr`，而非抛出异常或断言。这允许测试优雅地处理硬件不支持的情况。
- Ganesh 和 Graphite 版本的参数风格略有不同：Ganesh 使用 `bool isProtected`，Graphite 使用强类型 `skgpu::Protected` 枚举。

## 依赖关系

- **Skia 核心**：`SkColor`、`SkRefCnt`
- **Ganesh**（条件）：`GrDirectContext`
- **Graphite**（条件）：`skgpu::graphite::Recorder`、`skgpu::Protected`
- 前向声明了 `SkImage`、`SkSurface`、`SkSurfaceProps`、`SkISize` 以减少头文件依赖

## 设计模式与设计决策

- **条件编译分离**：Ganesh 和 Graphite 的 API 通过 `#ifdef` 分离，允许在仅启用一个后端时编译。
- **工厂函数模式**：使用命名空间级别的工厂函数而非类方法，保持了工具代码的简洁性。
- **nullptr 返回约定**：函数在无法满足保护要求时返回 nullptr，让调用者（通常是测试）决定是跳过测试还是报错。
- **最小头文件依赖**：大量使用前向声明而非 `#include`，减少编译时依赖和编译时间。
- **API 一致性**：Surface 和 Image 创建函数在两个后端间保持相似的签名结构。

## 性能考量

- 受保护的 Surface/Image 创建可能比普通资源更慢，因为 GPU 驱动需要额外的安全设置。
- 作为测试工具，性能不是主要关注点。
- 前向声明策略有助于减少编译时间。

## 相关文件

- `tools/gpu/ProtectedUtils.cpp`：函数实现
- `include/gpu/ganesh/GrDirectContext.h`：Ganesh 上下文
- `include/gpu/graphite/Recorder.h`：Graphite 录制器
- Skia GPU 保护内容相关测试用例

### 补充说明

- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
