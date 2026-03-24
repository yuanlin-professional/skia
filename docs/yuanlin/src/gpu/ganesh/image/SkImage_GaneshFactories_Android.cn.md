# SkImage_GaneshFactories_Android — Android Image GPU 工厂

> 源文件: `src/gpu/ganesh/image/SkImage_GaneshFactories_Android.cpp`

## 概述

本文件实现了 `SkImages` 命名空间中用于 Android 平台的三个图像创建工厂函数，将 Android `AHardwareBuffer` 转换为 Skia GPU 图像 (`SkImage`)。提供延迟创建和立即创建（带数据上传）两种模式。延迟创建使用图像生成器 (ImageGenerator)，直到实际需要纹理时才执行 GPU 操作；立即创建则直接包装硬件缓冲区并上传像素数据。

## 架构位置

```
Android 应用 / Framework
    └── SkImages 命名空间 (本文件)
        ├── DeferredFromAHardwareBuffer() × 2
        │   └── GrAHardwareBufferImageGenerator
        │       └── DeferredFromTextureGenerator()
        └── TextureFromAHardwareBufferWithData()
            ├── GrAHardwareBufferUtils::MakeBackendTexture()
            ├── proxyProvider->wrapBackendTexture()
            ├── SurfaceContext::writePixels()
            └── SkImage_Ganesh
```

## 主要类与结构体

本文件不定义新类。涉及的关键类型：

| 类型 | 描述 |
|------|------|
| `AHardwareBuffer` | Android 原生硬件缓冲区 |
| `GrAHardwareBufferImageGenerator` | 从 AHardwareBuffer 延迟生成纹理的生成器 |
| `SkImage_Ganesh` | Ganesh GPU 图像实现类 |
| `skgpu::RefCntedCallback` | 引用计数的释放回调封装 |
| `SurfaceContext` | Surface 上下文，用于像素写入 |

## 公共 API 函数

### DeferredFromAHardwareBuffer() (简化版)

```cpp
sk_sp<SkImage> DeferredFromAHardwareBuffer(AHardwareBuffer* graphicBuffer, SkAlphaType at);
```

从 AHardwareBuffer 创建延迟图像。使用默认色彩空间 (nullptr) 和 `kTopLeft` 表面原点。内部创建 `GrAHardwareBufferImageGenerator` 并委托给 `DeferredFromTextureGenerator()`。

### DeferredFromAHardwareBuffer() (完整版)

```cpp
sk_sp<SkImage> DeferredFromAHardwareBuffer(AHardwareBuffer* graphicBuffer,
                                            SkAlphaType at,
                                            sk_sp<SkColorSpace> cs,
                                            GrSurfaceOrigin surfaceOrigin);
```

完整版本，允许指定色彩空间和表面原点。

### TextureFromAHardwareBufferWithData()

```cpp
sk_sp<SkImage> TextureFromAHardwareBufferWithData(GrDirectContext* dContext,
                                                   const SkPixmap& pixmap,
                                                   AHardwareBuffer* hardwareBuffer,
                                                   GrSurfaceOrigin surfaceOrigin);
```

创建 GPU 纹理图像并立即从 `SkPixmap` 上传像素数据。处理流程：

1. 验证缓冲区支持 GPU 采样
2. 获取后端格式
3. 创建后端纹理（检查是否可渲染）
4. 通过 `proxyProvider->wrapBackendTexture()` 包装为代理
5. 创建 `SkImage_Ganesh` 图像
6. 通过 `SurfaceContext::writePixels()` 上传像素数据
7. 刷新绘制管理器确保数据传输完成

## 内部实现细节

1. **延迟 vs 立即**: 两个 `DeferredFromAHardwareBuffer` 函数使用图像生成器模式，纹理创建被推迟到首次使用时。`TextureFromAHardwareBufferWithData` 则立即创建纹理并上传数据。

2. **RefCntedCallback 资源管理**: `TextureFromAHardwareBufferWithData` 将 `deleteImageProc` 包装为 `RefCntedCallback`，通过引用计数自动管理清理。当代理和所有引用释放时，自动调用删除回调释放 AHardwareBuffer。

3. **即时刷新**: 像素写入后通过 `drawingManager->flush()` 立即提交 GPU 操作，确保数据在函数返回前已传输到纹理。使用 `BackendSurfaceAccess::kNoAccess` 表示不需要后端表面访问同步。

4. **颜色类型转换**: 使用 `AHardwareBufferUtils::GetSkColorTypeFromBufferFormat()` 将 Android 格式映射为 Skia 颜色类型，然后再映射为 Gr 颜色类型用于 swizzle 计算。

5. **可渲染检测**: `TextureFromAHardwareBufferWithData` 检查 `AHARDWAREBUFFER_USAGE_GPU_FRAMEBUFFER` 标志决定是否将纹理标记为可渲染。

6. **所有权借用**: `wrapBackendTexture` 使用 `kBorrow_GrWrapOwnership`，表示 Skia 不拥有底层纹理资源的所有权（由 AHardwareBuffer 管理）。

## 依赖关系

**Android NDK**:
- `<android/hardware_buffer.h>` — AHardwareBuffer API

**图像生成**:
- `src/gpu/ganesh/GrAHardwareBufferImageGenerator.h` — 延迟纹理生成器
- `include/gpu/ganesh/GrExternalTextureGenerator.h` — 外部纹理生成器基类

**GPU 资源管理**:
- `src/gpu/ganesh/GrProxyProvider.h` — 代理创建和包装
- `src/gpu/ganesh/GrDrawingManager.h` — 绘制管理器（flush）
- `src/gpu/ganesh/SurfaceContext.h` — writePixels 数据上传
- `src/gpu/RefCntedCallback.h` — 释放回调封装

**Android 工具**:
- `include/android/AHardwareBufferUtils.h` — 格式映射
- `include/android/GrAHardwareBufferUtils.h` — GPU 后端操作

## 设计模式与设计决策

1. **延迟创建策略**: `DeferredFromAHardwareBuffer` 通过图像生成器实现按需纹理创建，适合不确定图像是否真正需要 GPU 渲染的场景，避免过早的 GPU 资源分配。

2. **立即创建 + 数据上传**: `TextureFromAHardwareBufferWithData` 提供一步完成纹理创建和数据填充的便利接口，适合需要立即可用的纹理场景。

3. **函数重载**: 两个 `DeferredFromAHardwareBuffer` 重载提供简洁和完整两种调用方式，简化版使用合理默认值。

4. **引用计数回调**: 使用 `RefCntedCallback` 而非裸函数指针，确保多个持有者场景下的正确资源释放。

## 性能考量

- **延迟创建**: `DeferredFromAHardwareBuffer` 在创建时几乎零开销，GPU 操作推迟到首次绘制。
- **立即上传**: `TextureFromAHardwareBufferWithData` 涉及 GPU 数据传输和 flush，是同步操作。
- **kBorrow 所有权**: 避免了不必要的 AHardwareBuffer 引用计数操作。
- **flush 同步**: `TextureFromAHardwareBufferWithData` 中的 flush 确保数据一致性，但会引入 GPU 管线停顿。
- **GrWrapCacheable::kNo**: 包装的纹理不进入缓存，因为 AHardwareBuffer 的生命周期由外部管理。

## 相关文件

- `include/android/SkImageAndroid.h` — 公共 API 声明
- `src/gpu/ganesh/GrAHardwareBufferImageGenerator.h` — AHB 图像生成器
- `src/gpu/ganesh/surface/SkSurface_AndroidFactories.cpp` — Android Surface 工厂
- `src/gpu/ganesh/image/SkImage_GaneshFactories.cpp` — 通用 Image 工厂
- `src/gpu/ganesh/GrAHardwareBufferUtils.cpp` — AHB 工具函数
- `src/gpu/ganesh/image/SkImage_Ganesh.h` — Ganesh Image 实现
