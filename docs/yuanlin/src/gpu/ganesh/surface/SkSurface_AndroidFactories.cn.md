# SkSurface_AndroidFactories — Android Surface 工厂

> 源文件: `src/gpu/ganesh/surface/SkSurface_AndroidFactories.cpp`

## 概述

本文件实现了 `SkSurfaces::WrapAndroidHardwareBuffer()` 工厂函数，将 Android `AHardwareBuffer` 包装为 Skia `SkSurface`。这是 Android 平台上直接在硬件缓冲区上进行 Skia GPU 渲染的主要入口，广泛用于 Android Framework、SurfaceFlinger 和第三方应用中。文件仅在 Android 平台且 API 级别 >= 26 时编译。

## 架构位置

```
Android 应用 / Framework
    └── SkSurfaces::WrapAndroidHardwareBuffer (本文件)
        ├── AHardwareBuffer_describe() — 查询缓冲区属性
        ├── GrAHardwareBufferUtils::GetBackendFormat() — 获取后端格式
        ├── GrAHardwareBufferUtils::MakeBackendTexture() — 创建后端纹理
        └── SkSurfaces::WrapBackendTexture() — 通用后端纹理包装
            └── SkSurface_Ganesh
```

## 主要类与结构体

本文件不定义新类，实现 `SkSurfaces` 命名空间中的工厂函数。涉及的关键类型：

| 类型 | 描述 |
|------|------|
| `AHardwareBuffer` | Android 原生硬件缓冲区 |
| `AHardwareBuffer_Desc` | 硬件缓冲区描述结构体 |
| `GrDirectContext` | Ganesh 直接渲染上下文 |
| `GrBackendTexture` | Skia 后端纹理 |
| `GrBackendFormat` | Skia 后端格式 |

## 公共 API 函数

### WrapAndroidHardwareBuffer()

```cpp
sk_sp<SkSurface> WrapAndroidHardwareBuffer(GrDirectContext* dContext,
                                            AHardwareBuffer* hardwareBuffer,
                                            GrSurfaceOrigin origin,
                                            sk_sp<SkColorSpace> colorSpace,
                                            const SkSurfaceProps* surfaceProps,
                                            bool fromWindow);
```

将 Android 硬件缓冲区包装为可渲染的 Skia Surface。

**处理流程**:

1. **查询缓冲区属性**: 通过 `AHardwareBuffer_describe()` 获取缓冲区的宽度、高度、格式和用途标志。

2. **用途验证**:
   - 必须有 `AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT`（可作为渲染目标）
   - 必须有 `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE`（可采样为纹理）
   - 任一缺失则输出调试信息并返回 nullptr

3. **格式映射**: 通过 `GrAHardwareBufferUtils::GetBackendFormat()` 将 Android 格式转为 Skia 后端格式。`requireKnownFormat=true` 表示只接受已知格式。

4. **保护内容检测**: 检查 `AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT` 标志。

5. **创建后端纹理**: 通过 `MakeBackendTexture()` 创建可渲染的后端纹理，获取清理和更新回调函数。

6. **颜色类型映射**: `AHardwareBufferUtils::GetSkColorTypeFromBufferFormat()` 将缓冲区格式映射为 `SkColorType`。

7. **Surface 创建**: 委托给 `SkSurfaces::WrapBackendTexture()` 完成最终 Surface 创建，传入删除回调确保资源正确释放。

## 内部实现细节

1. **fromWindow 参数**: `fromWindow` 标志仅在 `SK_BUILD_FOR_ANDROID_FRAMEWORK` 编译时有效。在 Android Framework 中，来自窗口的缓冲区在 Vulkan 路径中可能需要特殊处理（如 swapchain 集成）。

2. **回调式资源管理**: `deleteImageProc`、`updateImageProc` 和 `deleteImageCtx` 三元组用于管理后端纹理的生命周期。当 Surface 销毁时，通过 `deleteImageProc` 清理 GPU 后端的 AHardwareBuffer 引用。

3. **格式验证链**: 多层验证确保缓冲区可用——用途标志检查 -> 格式映射检查 -> 后端纹理创建检查。每层失败都输出描述性调试信息。

4. **采样数为 0**: `WrapBackendTexture` 的 `sampleCnt` 参数传 0，表示使用后端纹理的原始采样数。

5. **错误诊断**: 每个失败点都通过 `SkDebugf` 输出包含函数名 (`__func__`) 和具体原因的诊断信息，便于问题定位。

## 依赖关系

**Android NDK**:
- `<android/hardware_buffer.h>` — AHardwareBuffer API

**Skia 公共 API**:
- `include/android/SkSurfaceAndroid.h` — 公共声明
- `include/android/AHardwareBufferUtils.h` — 格式映射工具
- `include/android/GrAHardwareBufferUtils.h` — GPU 后端格式/纹理工具

**Ganesh 内部**:
- `src/gpu/ganesh/GrCaps.h`, `GrProxyProvider.h` 等资源管理类
- `src/gpu/ganesh/surface/SkSurface_Ganesh.h` — Surface 实现
- `include/gpu/ganesh/GrDirectContext.h` — 直接上下文
- `include/gpu/ganesh/SkSurfaceGanesh.h` — `WrapBackendTexture()`

## 设计模式与设计决策

1. **管线式验证**: 采用"提前返回"模式，在每个验证步骤失败时立即返回 nullptr，避免深层嵌套。

2. **工厂方法委托**: 本函数处理 Android 特定的缓冲区验证和格式转换后，委托给通用的 `WrapBackendTexture()` 完成 Surface 创建，复用已有逻辑。

3. **回调式生命周期**: 将资源清理逻辑封装在回调中传给 Surface，确保硬件缓冲区引用在 Surface 销毁时正确释放，避免 GPU 资源泄漏。

4. **条件编译**: 整个文件由 Android 平台和 API 级别宏保护，在非 Android 平台上完全不编译。

## 性能考量

- 此函数仅在 Surface 创建时调用一次，不在渲染热路径上。
- `AHardwareBuffer_describe()` 是一个轻量级查询，几乎无开销。
- `MakeBackendTexture()` 可能涉及 GPU 驱动操作（如 Vulkan 图像导入），是主要耗时点。
- 创建后的 Surface 绘制性能与直接创建的 Surface 相同——硬件缓冲区后端不引入额外渲染开销。

## 相关文件

- `include/android/SkSurfaceAndroid.h` — 公共 API 声明
- `src/gpu/ganesh/GrAHardwareBufferUtils.cpp` — 后端格式/纹理转换
- `src/gpu/ganesh/vk/AHardwareBufferVk.cpp` — Vulkan 路径实现
- `src/gpu/ganesh/gl/AHardwareBufferGL.cpp` — OpenGL 路径实现
- `src/gpu/ganesh/image/SkImage_GaneshFactories_Android.cpp` — Android Image 工厂
- `src/gpu/ganesh/surface/SkSurface_GaneshMtl.mm` — Metal 平台类似工厂
