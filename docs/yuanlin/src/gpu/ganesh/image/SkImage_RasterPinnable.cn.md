# SkImage_RasterPinnable - 可钉住的光栅图像

> 源文件: `src/gpu/ganesh/image/SkImage_RasterPinnable.h`, `src/gpu/ganesh/image/SkImage_RasterPinnable.cpp`

## 概述

`SkImage_RasterPinnable` 是 `SkImage_Raster` 的子类，支持将光栅图像数据"钉住"（pin）到 GPU 纹理中。当光栅图像被频繁用于 GPU 绘制时，钉住机制将其上传为 GPU 纹理并缓存，避免每帧重复上传。引用计数追踪钉住状态，当所有 GPU 使用完毕后可释放纹理。

## 架构位置

```
SkImage (公共 API)
    |
SkImage_Base
    |
SkImage_Raster
    |
SkImage_RasterPinnable (本文件)
    |
PinnedData -> GrSurfaceProxyView (GPU 纹理缓存)
```

该类桥接了 CPU 光栅数据和 GPU 纹理缓存，是 Ganesh 后端对 `SkBitmap` 的 GPU 加速入口。

## 主要类与结构体

### `PinnedData`

```cpp
struct PinnedData {
    GrSurfaceProxyView fPinnedView;
    int32_t fPinnedCount = 0;
    uint32_t fPinnedUniqueID = SK_InvalidUniqueID;
    uint32_t fPinnedContextID = SK_InvalidUniqueID;
    GrColorType fPinnedColorType = GrColorType::kUnknown;
};
```

追踪钉住状态：GPU 纹理视图、引用计数、关联的上下文 ID 和颜色类型。

### `SkImage_RasterPinnable`

继承自 `SkImage_Raster`，标记为 `final`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fPinnedData` | `unique_ptr<PinnedData>` | 钉住数据（可为空） |

## 公共 API 函数

### 构造函数

```cpp
SkImage_RasterPinnable(const SkBitmap& bm);
```

从位图创建，允许位图可变（`bitmapMayBeMutable = true`）。

### `asView()`

```cpp
std::tuple<GrSurfaceProxyView, GrColorType> asView(GrRecordingContext*,
                                                     skgpu::Mipmapped,
                                                     GrImageTexGenPolicy) const;
```

返回 GPU 纹理视图。若已钉住则返回缓存的视图，否则创建新的上传。

### `type()`

返回 `SkImage_Base::Type::kRasterPinnable`。

## 内部实现细节

钉住计数为零时释放 GPU 纹理。上下文 ID 确保纹理与正确的 GPU 上下文关联，防止跨上下文使用过期纹理。

## 依赖关系

- **上游依赖**: `SkImage_Raster`、`GrSurfaceProxyView`。
- **被依赖**: Ganesh 图像渲染管线。

## 设计模式与设计决策

1. **延迟上传**: GPU 纹理仅在首次需要时创建。
2. **引用计数钉住**: 允许多个 GPU 操作共享同一纹理，最后一个释放时清理。
3. **上下文绑定**: `fPinnedContextID` 防止纹理在上下文销毁后被使用。

## 性能考量

- 钉住机制避免了频繁的 CPU->GPU 纹理上传。
- `fPinnedUniqueID` 检测位图内容变化，内容变更时重新上传。

## 相关文件

- `src/image/SkImage_Raster.h` - 光栅图像基类
- `src/gpu/ganesh/GrSurfaceProxyView.h` - GPU 纹理代理视图
- `src/gpu/ganesh/image/GrImageUtils.h` - GPU 图像工具
