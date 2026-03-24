# include/android/graphite - Android Graphite 渲染引擎接口

## 概述

`include/android/graphite` 目录包含 Skia Graphite 渲染引擎在 Android 平台上的专用接口。Graphite 是 Skia 的新一代 GPU 渲染引擎，旨在取代传统的 Ganesh 后端，更好地利用现代图形 API（如 Vulkan、Metal 和 Dawn）的特性。本目录提供了 Graphite 引擎与 Android 硬件缓冲区（AHardwareBuffer）系统的集成接口。

当前该目录仅包含 `SurfaceAndroid.h` 一个头文件，提供了从 Android 硬件缓冲区创建 Graphite 渲染表面（SkSurface）的功能。与 Ganesh 版本（位于 `include/android/SkSurfaceAndroid.h`）类似，此接口允许 Android Framework 将 AHardwareBuffer 包装为 Skia 可渲染的 Surface，但使用的是 Graphite 渲染引擎而非 Ganesh。

该接口被标记为 Android Framework 私有，仅供 Android 系统框架层内部使用。与 Ganesh 版本的主要区别在于：Graphite 版本使用 `skgpu::graphite::Recorder` 而非 `GrDirectContext`，并提供了显式的缓冲区释放回调机制（`BufferReleaseProc`），使得资源生命周期管理更加灵活和精确。

随着 Android 系统逐步从 Ganesh 迁移到 Graphite，本目录中的 API 将变得更加重要，未来可能会增加更多 Graphite 特化的 Android 集成接口。

## 目录结构

```
include/android/graphite/
└── SurfaceAndroid.h     # Graphite 引擎的 AHardwareBuffer Surface 创建
```

## 关键类与函数

### Surface 创建
- **`SkSurfaces::WrapAndroidHardwareBuffer()`** (`SurfaceAndroid.h`):
  从 Android 硬件缓冲区创建 Graphite 渲染引擎支持的 SkSurface。

  **参数说明**:
  - `recorder` (`skgpu::graphite::Recorder*`): Graphite 录制器，用于记录渲染命令
  - `hardwareBuffer` (`AHardwareBuffer*`): Android 硬件缓冲区指针
  - `colorSpace` (`sk_sp<SkColorSpace>`): 色彩空间，可为 nullptr
  - `surfaceProps` (`const SkSurfaceProps*`): 表面属性（LCD 条纹方向等），可为 nullptr
  - `bufferReleaseProc` (`BufferReleaseProc`): 缓冲区安全释放回调，默认为 nullptr
  - `releaseContext` (`ReleaseContext`): 传递给释放回调的上下文参数
  - `fromWindow` (`bool`): 是否来自 Android Window，目前仅影响 Vulkan 后端行为

  **返回值**: 成功返回 `sk_sp<SkSurface>`，失败返回 nullptr。

  **使用要求**:
  - 硬件缓冲区必须同时具有 `AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT` 和 `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE` 使用标志
  - 当 Surface 创建失败时，`bufferReleaseProc` 会在函数返回前被调用
  - 创建成功后，`bufferReleaseProc` 在后端 API 中缓冲区不再被使用时调用

### 类型别名
- **`SkSurfaces::ReleaseContext`**: `void*` 类型，作为释放回调的不透明上下文参数
- **`SkSurfaces::BufferReleaseProc`**: `void (*)(ReleaseContext)` 函数指针类型，缓冲区释放时的回调

### Ganesh 版本对比
| 特性 | Ganesh 版本 | Graphite 版本 |
|------|------------|--------------|
| 上下文 | `GrDirectContext*` | `skgpu::graphite::Recorder*` |
| 表面原点 | 显式 `GrSurfaceOrigin` 参数 | 无（Graphite 自动处理） |
| 释放回调 | 无（引用计数管理） | `BufferReleaseProc` 回调 |
| 所在文件 | `SkSurfaceAndroid.h` | `graphite/SurfaceAndroid.h` |
| 命名空间 | `SkSurfaces::` | `SkSurfaces::` |
| Window 标识 | `fromWindow` 参数 | `fromWindow` 参数 |

### Graphite 渲染引擎简介
Graphite 是 Skia 的下一代 GPU 渲染引擎，与 Ganesh 相比有以下设计改进：
- **录制/回放分离**: 通过 `Recorder` 录制绘制命令，然后通过 `Context` 提交到 GPU。这种分离使得多线程录制成为一等公民。
- **现代图形 API 优先**: 设计上优先考虑 Vulkan、Metal 和 Dawn 等现代图形 API，充分利用显式内存管理和命令缓冲区模型。
- **更好的批处理**: 通过更智能的绘制排序和合并策略减少 GPU 状态切换和绘制调用数量。

### 缓冲区释放回调机制
Graphite 版本引入的 `BufferReleaseProc` 回调机制是与 Ganesh 版本的重要区别：
- **回调时机**: 当 Skia 的后端 API 不再使用该缓冲区时调用（仅计算此 Surface 对缓冲区的使用）
- **失败处理**: 如果 Surface 创建失败，回调在 `WrapAndroidHardwareBuffer()` 返回前立即调用
- **线程安全**: 回调可能在任何执行 Skia 命令提交的线程上被调用
- **用途**: 允许 Android Framework 在不再需要缓冲区时及时释放对 AHardwareBuffer 的引用，避免内存泄漏

### fromWindow 参数说明
`fromWindow` 参数标识 AHardwareBuffer 是否来自 Android Window（如 SurfaceFlinger 管理的显示缓冲区）。当前此参数仅影响 Vulkan 后端的行为，因为 Vulkan 在处理窗口关联的缓冲区时可能需要不同的交换链配置和内存属性。

## 依赖关系

- **上游依赖**: `include/core/SkRefCnt.h`、`include/core/SkSurface.h`（SkSurface 基类定义）
- **Graphite 依赖**: `skgpu::graphite::Recorder`（Graphite 渲染录制器）
- **平台依赖**: Android NDK `AHardwareBuffer`（需要 `__ANDROID_API__ >= 26`）
- **下游消费者**: Android Framework 的 `hwui`（在 Graphite 模式下运行时）
- **对应 Ganesh 版本**: `include/android/SkSurfaceAndroid.h`

## 相关文档与参考

- [Skia Graphite 概述](https://skia.org/docs/user/api/graphite/) - Graphite 渲染引擎文档
- [Android AHardwareBuffer](https://developer.android.com/ndk/reference/group/a-hardware-buffer) - Android 硬件缓冲区 API
- [Android 图形架构](https://source.android.com/docs/core/graphics/) - Android 系统图形栈
- `include/android/SkSurfaceAndroid.h` - Ganesh 版本的 AHardwareBuffer Surface
- `include/android/` - Android 平台 API 总目录
- `include/gpu/graphite/` - Graphite 公共 API
- `src/gpu/graphite/` - Graphite 引擎实现源码

## 使用注意事项

### 迁移指南
从 Ganesh 版本（`SkSurfaceAndroid.h`）迁移到 Graphite 版本时，主要变更包括：
1. 将 `GrDirectContext*` 参数替换为 `skgpu::graphite::Recorder*`
2. 移除显式的 `GrSurfaceOrigin` 参数（Graphite 自动处理表面原点）
3. 添加 `BufferReleaseProc` 和 `ReleaseContext` 参数以管理缓冲区释放（可选）
4. 确保 Recorder 在 Surface 使用期间保持有效

### 错误处理
`WrapAndroidHardwareBuffer()` 在以下情况下返回 nullptr：
- 传入的 `AHardwareBuffer` 不支持所需的 GPU 使用标志
- 后端 GPU 不支持该缓冲区的格式
- `Recorder` 无效或已失效
- 系统内存不足无法创建所需的 GPU 资源

在函数返回 nullptr 时，如果提供了 `BufferReleaseProc`，该回调会在返回前被调用以确保资源清理。
