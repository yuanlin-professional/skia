# ProtectedUtils_Ganesh.cpp - Ganesh 受保护内容测试工具

> 源文件: `tools/ganesh/ProtectedUtils_Ganesh.cpp`

## 概述

`ProtectedUtils_Ganesh.cpp` 实现了 Ganesh GPU 后端中受保护内容（Protected Content）的测试工具函数。受保护内容是一种 GPU 安全机制，主要用于 DRM（数字版权管理）场景，确保视频帧等敏感内容在 GPU 内存中的安全性。

该文件提供了创建受保护 `SkSurface` 和 `SkImage` 的工具函数，以及验证图像后端纹理保护状态的检查函数。这些工具主要在 Skia 的单元测试中使用，用于验证受保护内容的正确行为。

## 架构位置

```
Skia 测试工具
├── tools/gpu/
│   ├── ProtectedUtils.h                <-- 受保护内容工具接口声明
│   ├── BackendSurfaceFactory.h         <-- 后端 Surface 工厂
│   └── BackendTextureImageFactory.h    <-- 后端纹理图像工厂
├── tools/ganesh/
│   └── ProtectedUtils_Ganesh.cpp       <-- 本文件：Ganesh 实现
└── tests/
    └── ProtectedTest.cpp               <-- 使用这些工具的测试
```

## 主要类与结构体

本文件不定义新类，所有函数在 `ProtectedUtils` 命名空间中实现。

## 公共 API 函数

### `CreateProtectedSkSurface`
```cpp
sk_sp<SkSurface> CreateProtectedSkSurface(GrDirectContext* dContext,
                                          SkISize size,
                                          bool textureable,
                                          bool isProtected,
                                          const SkSurfaceProps* surfaceProps);
```
创建受保护（或非受保护）的 GPU Surface。根据 `textureable` 参数选择不同的创建路径：
- `textureable = true`：通过后端纹理（BackendTexture）创建，可用于后续纹理采样
- `textureable = false`：通过后端渲染目标（BackendRenderTarget）创建

创建后自动将 Surface 清除为蓝色，并验证后端资源的保护状态与预期一致。

### `CreateProtectedSkImage`
```cpp
sk_sp<SkImage> CreateProtectedSkImage(GrDirectContext* dContext,
                                      SkISize size,
                                      SkColor4f color,
                                      bool isProtected);
```
创建受保护（或非受保护）的 GPU 图像。使用指定颜色填充，创建后立即验证图像后端纹理的保护状态。

### `CheckImageBEProtection`
```cpp
void CheckImageBEProtection(SkImage* image, bool expectingProtected);
```
验证图像的后端纹理保护状态是否与预期一致。通过 `SkImages::GetBackendTextureFromImage` 获取后端纹理并检查 `isProtected()` 属性。

## 内部实现细节

### Surface 创建的两种路径

```cpp
if (textureable) {
    surface = sk_gpu_test::MakeBackendTextureSurface(dContext, size,
        kTopLeft_GrSurfaceOrigin, 1, kRGBA_8888_SkColorType,
        nullptr, skgpu::Mipmapped::kNo, skgpu::Protected(isProtected), surfaceProps);
} else {
    surface = sk_gpu_test::MakeBackendRenderTargetSurface(dContext, size,
        kTopLeft_GrSurfaceOrigin, 1, kRGBA_8888_SkColorType,
        nullptr, skgpu::Protected(isProtected), surfaceProps);
}
```

两种路径对应 GPU 中两种不同的资源类型：
- **后端纹理**：同时可作为渲染目标和采样源
- **后端渲染目标**：仅能作为渲染目标使用

### 保护状态验证

创建后立即进行验证，通过断言确保后端资源的保护属性与请求一致。对于纹理类型和渲染目标类型分别进行检查：

```cpp
if (textureable) {
    GrBackendTexture backendTex = SkSurfaces::GetBackendTexture(
            surface.get(), SkSurfaces::BackendHandleAccess::kFlushRead);
    SkASSERT(backendTex.isValid());
    SkASSERT(backendTex.isProtected() == isProtected);
} else {
    GrBackendRenderTarget backendRT = SkSurfaces::GetBackendRenderTarget(
            surface.get(), SkSurfaces::BackendHandleAccess::kFlushRead);
    SkASSERT(backendRT.isValid());
    SkASSERT(backendRT.isProtected() == isProtected);
}
```

使用 `BackendHandleAccess::kFlushRead` 确保在访问后端句柄前所有待处理的 GPU 命令已刷新。

### 错误处理

如果资源创建失败，使用 `SK_ABORT` 直接终止程序并输出错误信息。这在测试工具中是合理的选择，因为创建失败意味着测试环境异常。

## 依赖关系

- **Skia GPU（Ganesh）**：`SkImageGanesh.h`, `SkSurfaceGanesh.h`, `GrDirectContextPriv.h`
- **Skia 测试工具**：`BackendSurfaceFactory.h`, `BackendTextureImageFactory.h`, `ProtectedUtils.h`
- **Skia 核心**：`SkSurface`, `SkImage`, `SkCanvas`, `SkColor`

## 设计模式与设计决策

1. **工厂函数模式**：`CreateProtectedSkSurface` 和 `CreateProtectedSkImage` 封装了复杂的 GPU 资源创建逻辑，为测试代码提供简洁的接口。

2. **创建即验证**：所有创建函数在返回前都会验证资源的保护状态，将"创建"和"验证"合为一步，减少测试代码的重复性。不可变验证（immutable verification）确保返回的资源始终处于正确状态。

3. **Fail-fast 策略**：创建失败时使用 `SK_ABORT` 而非返回 `nullptr`，在测试场景中更容易定位问题。这种策略避免了调用者遗忘空指针检查的风险。

4. **固定参数**：使用 `kRGBA_8888_SkColorType`、`kTopLeft_GrSurfaceOrigin` 等固定参数，因为受保护内容测试的重点是保护属性而非具体的像素格式。

5. **对称 API**：`CreateProtectedSkSurface` 和 `CreateProtectedSkImage` 接受相同的 `isProtected` 布尔参数，既可以创建受保护资源也可以创建非受保护资源，便于测试中进行对比验证。

6. **与 Graphite 的分离**：此文件专注于 Ganesh 后端的实现，Graphite 的受保护内容工具在其他文件中提供，保持了后端间的清晰边界。

## 性能考量

- 这些函数仅用于测试，不在生产路径中使用，性能不是主要考量。
- GPU 资源创建和保护标志设置是一次性操作，开销来自 GPU 驱动层面的内存分配。对于受保护内存，驱动可能需要从特殊的安全内存区域分配。
- `CheckImageBEProtection` 中的 `flushPendingGrContextIO` 会触发 GPU 命令刷新，确保状态同步但增加了延迟。
- `CreateProtectedSkSurface` 创建后立即执行 `canvas->clear(SkColors::kBlue)`，这会生成一个 GPU 命令验证 Surface 可写。
- 受保护的 GPU 资源在某些驱动上可能比非受保护资源的分配速度慢，因为需要额外的安全检查和专用内存池分配。
- 后端纹理和后端渲染目标的创建路径不同，前者需要纹理支持的额外 GPU 内存开销。

## 相关文件

- `tools/gpu/ProtectedUtils.h` - 函数声明和接口定义
- `tools/gpu/BackendSurfaceFactory.h` - 后端 Surface 创建工厂（`MakeBackendTextureSurface`, `MakeBackendRenderTargetSurface`）
- `tools/gpu/BackendTextureImageFactory.h` - 后端纹理图像创建工厂（`MakeBackendTextureImage`）
- `include/gpu/ganesh/SkSurfaceGanesh.h` - Ganesh Surface 操作（`GetBackendTexture`, `GetBackendRenderTarget`）
- `include/gpu/ganesh/SkImageGanesh.h` - Ganesh Image 操作（`GetBackendTextureFromImage`）
- `src/gpu/ganesh/GrDirectContextPriv.h` - 直接上下文私有 API
- `include/gpu/ganesh/GrBackendSurface.h` - 后端 Surface 类型（`GrBackendTexture`, `GrBackendRenderTarget`）
- `include/core/SkSurface.h` - Surface 基类
- `include/core/SkImage.h` - Image 基类
- `include/core/SkCanvas.h` - Canvas 绘图接口
- `include/gpu/GpuTypes.h` - GPU 类型定义（`skgpu::Protected`, `skgpu::Mipmapped`）

### 受保护内容的背景知识

受保护内容（Protected Content）是 GPU 安全特性的一部分，主要由以下标准和 API 支持：
- **Vulkan**：`VK_EXT_protected_content` 扩展
- **OpenGL ES**：`EGL_EXT_protected_content` 扩展
- **Android**：`MediaCodec` 的安全解码器配合 `SurfaceTexture` 使用

在 Skia 中，受保护标志通过 `skgpu::Protected` 枚举传递给后端资源创建函数，最终由底层图形驱动执行实际的安全内存分配和访问控制。
