# include/gpu/ganesh/mtl - Ganesh Metal 后端公共 API

## 概述

`include/gpu/ganesh/mtl` 目录包含 Ganesh 渲染引擎中 Apple Metal 后端的公共 API。Metal 是
Apple 自主开发的低级图形 API，在 macOS、iOS、iPadOS 和 tvOS 上提供高性能 GPU 加速。
Skia 的 Metal 后端是 Apple 平台上推荐的 GPU 加速选择。

此目录提供了 Metal 后端上下文、后端表面工厂方法、信号量封装以及 Metal 特有的类型定义。
由于 Metal API 基于 Objective-C，部分类型使用了 `CFTypeRef` 等 Core Foundation 类型来在
C++ 代码中引用 Objective-C 对象（如 `MTLDevice`、`MTLTexture`）。

`SkSurfaceMetal.h` 提供了将 `CAMetalLayer` 和 `MTKView` 直接包装为 `SkSurface` 的便利
方法，这使得在 iOS/macOS 应用中集成 Skia 渲染变得非常简单。

## 架构图

```
include/gpu/ganesh/mtl/
    |
    +-- GrMtlTypes.h               <-- Metal 类型定义
    |       |
    |       +-- GrMTLPixelFormat       (MTLPixelFormat 的 C++ 别名)
    |       +-- GrMTLTextureUsage      (MTLTextureUsage 的 C++ 别名)
    |       +-- GrMTLStorageMode       (MTLStorageMode 的 C++ 别名)
    |       +-- GrMTLHandle            (ObjC 对象的 C++ 句柄)
    |       +-- GrMtlTextureInfo       (Metal 纹理信息)
    |       +-- GrMtlSurfaceInfo       (Metal 表面信息)
    |
    +-- GrMtlBackendContext.h       <-- Metal 后端上下文
    +-- GrMtlBackendSurface.h       <-- Metal 后端纹理/渲染目标工厂
    +-- GrMtlBackendSemaphore.h     <-- Metal 后端信号量
    +-- GrMtlDirectContext.h        <-- Metal 上下文创建入口
    +-- SkSurfaceMetal.h            <-- CAMetalLayer/MTKView 包装
    |
    +-- (依赖) include/gpu/mtl/    <-- 共享 Metal 类型
            +-- MtlMemoryAllocator.h
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrMtlTypes.h` | Metal 类型定义：`GrMtlTextureInfo`、`GrMtlSurfaceInfo`、C++ 类型别名 |
| `GrMtlBackendContext.h` | Metal 后端上下文结构体（MTLDevice + MTLCommandQueue） |
| `GrMtlBackendSurface.h` | Metal 后端纹理和渲染目标的创建与查询 |
| `GrMtlBackendSemaphore.h` | Metal 后端信号量封装（`MTLEvent`） |
| `GrMtlDirectContext.h` | `GrDirectContexts::MakeMetal()` 工厂方法 |
| `SkSurfaceMetal.h` | `SkSurfaces::WrapCAMetalLayer()` 和 `WrapMTKView()` |

## 关键类与函数

### Metal 类型别名 (GrMtlTypes.h)

```cpp
using GrMTLPixelFormat = unsigned int;   // MTLPixelFormat
using GrMTLTextureUsage = unsigned int;  // MTLTextureUsage
using GrMTLStorageMode = unsigned int;   // MTLStorageMode
using GrMTLHandle = const void*;         // ObjC 对象句柄
```

### `GrMtlTextureInfo` 结构体

```cpp
struct GrMtlTextureInfo {
    sk_cfp<GrMTLHandle> fTexture;  // MTLTexture 对象
};
```

### `GrMtlBackendContext` 结构体

```cpp
struct GrMtlBackendContext {
    sk_cfp<GrMTLHandle> fDevice;         // MTLDevice
    sk_cfp<GrMTLHandle> fQueue;          // MTLCommandQueue
    sk_sp<const GrMtlMemoryAllocator> fMemoryAllocator;  // 可选
};
```

### 上下文创建 (GrMtlDirectContext.h)

```cpp
namespace GrDirectContexts {
    sk_sp<GrDirectContext> MakeMetal(const GrMtlBackendContext&, const GrContextOptions&);
    sk_sp<GrDirectContext> MakeMetal(const GrMtlBackendContext&);
}
```

### CAMetalLayer/MTKView 包装 (SkSurfaceMetal.h)

```cpp
namespace SkSurfaces {
    sk_sp<SkSurface> WrapCAMetalLayer(GrRecordingContext*, GrMTLHandle layer,
                                       GrSurfaceOrigin, int sampleCnt,
                                       SkColorType, sk_sp<SkColorSpace>,
                                       const SkSurfaceProps*, GrMTLHandle* drawable);

    sk_sp<SkSurface> WrapMTKView(GrRecordingContext*, GrMTLHandle mtkView,
                                  GrSurfaceOrigin, int sampleCnt,
                                  SkColorType, sk_sp<SkColorSpace>,
                                  const SkSurfaceProps*);
}
```

## 依赖关系

- **上游依赖**: `include/gpu/mtl/MtlMemoryAllocator.h`, `include/gpu/ganesh/GrTypes.h`
- **上游依赖**: `include/ports/SkCFObject.h` (Core Foundation 智能指针)
- **系统依赖**: Apple Metal 框架, `<TargetConditionals.h>`
- **平台**: macOS (10.11+), iOS (8.0+), tvOS (9.0+)
- **实现代码**: `src/gpu/ganesh/mtl/`

## 相关文档与参考

- `include/gpu/mtl/` - 共享 Metal 类型（Ganesh + Graphite）
- `include/gpu/ganesh/` - Ganesh 引擎主目录
- `include/gpu/graphite/mtl/` - Graphite Metal 后端
- Apple Metal 文档: https://developer.apple.com/metal/
