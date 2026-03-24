# SkCreateCGImageRef — Skia 与 Core Graphics 的图像互操作

> 源文件: `src/utils/mac/SkCreateCGImageRef.cpp`

## 概述

`SkCreateCGImageRef.cpp` 是 Skia 在 macOS 和 iOS 平台上与 Apple Core Graphics (CG) 框架进行图像互操作的桥梁模块。该文件实现了 Skia 位图/图像与 `CGImageRef`/`CGContextRef` 之间的双向转换，以及 Skia 色彩空间与 `CGColorSpaceRef` 之间的转换。

主要功能包括：
- **Skia -> CG**: 将 `SkBitmap` 转换为 `CGImageRef`，将 `SkPixmap` 转换为 `CGContextRef`
- **CG -> Skia**: 将 `CGImageRef` 转换为 `SkBitmap` 或 `SkImage`
- **色彩空间转换**: `SkColorSpace` 与 `CGColorSpaceRef` 之间的双向转换（通过 ICC 配置文件）
- **绘制辅助**: 在 `CGContextRef` 上绘制 `SkBitmap`

该文件仅在 `SK_BUILD_FOR_MAC` 或 `SK_BUILD_FOR_IOS` 编译宏定义时编译。

## 架构位置

```
Skia
├── include/
│   ├── core/
│   │   ├── SkBitmap.h           // 位图定义
│   │   └── SkColorSpace.h       // 色彩空间
│   ├── utils/mac/
│   │   └── SkCGUtils.h          // 公共 API 声明
│   └── encode/SkICC.h           // ICC 配置文件写入
└── src/utils/mac/
    ├── SkCreateCGImageRef.cpp   // 本文件
    ├── SkUniqueCFRef.h          // CF 对象智能指针
    └── SkCGBase.h               // CG 基础定义
```

本模块是 Skia 平台抽象层（PAL）的一部分，允许在 Apple 平台上将 Skia 渲染结果无缝集成到原生 UI 框架中。

## 主要类与结构体

本文件不定义独立的类，主要由静态辅助函数和公共 API 函数组成。

### 内部辅助函数

| 函数 | 功能 |
|------|------|
| `compute_cgalpha_info_rgba()` | 计算 RGBA 格式的 CGBitmapInfo |
| `compute_cgalpha_info_bgra()` | 计算 BGRA 格式的 CGBitmapInfo |
| `compute_cgalpha_info_4444()` | 计算 ARGB4444 格式的 CGBitmapInfo |
| `get_bitmap_info()` | 将 Skia 颜色类型映射到 CG 位图信息 |
| `prepare_for_image_ref()` | 准备位图数据（必要时转换格式） |

## 公共 API 函数

### `CGImageRef SkCreateCGImageRef(const SkBitmap& bm)`

- **功能**: 将 `SkBitmap` 转换为 `CGImageRef`
- **支持的颜色类型**: `kRGB_565`（自动升级为 RGBA8888）、`kRGBA_8888`、`kBGRA_8888`、`kARGB_4444`
- **内存管理**: 创建的 `CGImageRef` 拥有位图数据的副本（通过 `CGDataProvider` 的释放回调管理生命周期）
- **返回值**: 调用者拥有返回的 `CGImageRef`，需负责释放

### `CGImageRef SkCreateCGImageRefWithColorspace(const SkBitmap& bm, CGColorSpaceRef colorSpace)`

- **功能**: 带自定义色彩空间的版本（当前实现忽略 `colorSpace` 参数，直接调用 `SkCreateCGImageRef`）

### `void SkCGDrawBitmap(CGContextRef cg, const SkBitmap& bm, float x, float y)`

- **功能**: 在 `CGContextRef` 上绘制 `SkBitmap`
- **坐标变换**: 处理 CG 的 Y 轴翻转（CG 使用左下角为原点的坐标系）

### `CGContextRef SkCreateCGContext(const SkPixmap& pmap)`

- **功能**: 基于 `SkPixmap` 创建 `CGContextRef`（用于 CG 直接渲染到 Skia 像素缓冲区）
- **支持格式**: `kRGBA_8888` 和 `kBGRA_8888`

### `bool SkCopyPixelsFromCGImage(const SkImageInfo& info, size_t rowBytes, void* pixels, CGImageRef image)`

- **功能**: 将 `CGImageRef` 的像素数据复制到内存缓冲区
- **混合模式**: 使用 `kCGBlendModeCopy` 避免不必要的混合运算

### `bool SkCreateBitmapFromCGImage(SkBitmap* dst, CGImageRef image)`

- **功能**: 从 `CGImageRef` 创建 `SkBitmap`
- **Alpha 处理**: 根据 CG 图像的 alpha 信息自动设置 `SkAlphaType`，并为完全不透明的图像进行优化标记

### `sk_sp<SkImage> SkMakeImageFromCGImage(CGImageRef src)`

- **功能**: 从 `CGImageRef` 创建不可变的 `SkImage`

### `CGColorSpaceRef SkCreateCGColorSpace(const SkColorSpace* space)`

- **功能**: 将 `SkColorSpace` 转换为 `CGColorSpaceRef`
- **策略**: 先尝试匹配 sRGB，否则通过生成 ICC 配置文件创建自定义色彩空间
- **回退**: 失败时返回 sRGB 色彩空间

### `sk_sp<SkColorSpace> SkMakeColorSpaceFromCGColorSpace(CGColorSpaceRef cgColorSpace)`

- **功能**: 将 `CGColorSpaceRef` 转换为 `SkColorSpace`
- **策略**: 先尝试名称匹配（sRGB），否则解析 ICC 配置文件数据

### `CGDataProviderRef SkCreateCGDataProvider(sk_sp<SkData> data)`

- **功能**: 将 `SkData` 包装为 `CGDataProviderRef`
- **内存管理**: 通过引用计数管理 `SkData` 的生命周期

## 内部实现细节

### 颜色格式映射

Skia 和 Core Graphics 使用不同的字节序和 alpha 预乘约定。映射关系：

| Skia 格式 | CG 字节序 | CG Alpha |
|-----------|-----------|----------|
| RGBA_8888 Premul | Big Endian (32) | PremultipliedLast |
| BGRA_8888 Premul | Little Endian (32) | PremultipliedFirst |
| RGBA_8888 Opaque | Big Endian (32) | NoneSkipLast |
| BGRA_8888 Opaque | Little Endian (32) | NoneSkipFirst |
| RGB_565 | 升级为 RGBA_8888 后处理 | — |

### 内存所有权

`SkCreateCGImageRef` 中的一个关键设计是像素数据的生命周期管理：
1. `prepare_for_image_ref` 返回一个堆分配的 `SkBitmap` 指针
2. 该指针通过 `bitmap.release()` 转移给 `CGDataProvider`
3. 当 `CGDataProvider` 被释放时，通过 lambda 回调 `delete` 该 `SkBitmap`

### Y 轴翻转

`SkCGDrawBitmap` 使用 `CGContextTranslateCTM` + `CGContextScaleCTM(cg, 1, -1)` 处理 Skia（Y 轴向下）与 CG（Y 轴向上）之间的坐标系差异。

### 色彩空间转换

色彩空间转换采用两级策略：
1. **快速路径**: 对 sRGB 进行名称匹配，避免 ICC 解析开销
2. **通用路径**: 通过 ICC 配置文件数据进行转换，支持任意色彩空间

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkBitmap.h` | Skia 位图类 |
| `SkColorSpace.h` | Skia 色彩空间 |
| `SkData.h` | 不可变数据缓冲区 |
| `SkICC.h` | ICC 配置文件写入（`SkWriteICCProfile`） |
| `SkCGUtils.h` | 公共 API 声明 |
| `SkUniqueCFRef.h` | Core Foundation 对象的 RAII 包装 |
| `SkColorData.h` | 颜色数据操作 |
| Core Graphics 框架 | `CGImageCreate`、`CGBitmapContextCreate` 等 |

## 设计模式与设计决策

1. **平台条件编译**: 整个文件包裹在 `#if defined(SK_BUILD_FOR_MAC) || defined(SK_BUILD_FOR_IOS)` 中
2. **RAII 资源管理**: 使用 `SkUniqueCFRef` 自动管理 CG 对象的生命周期，防止资源泄漏
3. **回调式内存管理**: `CGDataProvider` 通过释放回调（lambda）在数据不再需要时自动释放 Skia 对象
4. **格式升级**: 不受 CG 支持的格式（如 RGB_565）会自动升级到兼容格式（RGBA_8888）
5. **sRGB 快速路径**: 色彩空间转换优先检测 sRGB，这是最常见的情况
6. **安全回退**: 色彩空间创建失败时回退到 sRGB，确保始终有可用结果

## 性能考量

- **格式升级开销**: RGB_565 到 RGBA_8888 的转换需要完整的像素拷贝和转换
- **sRGB 快速路径**: 最常见的色彩空间无需 ICC 解析
- **kCGBlendModeCopy**: 从 CG 图像复制像素时使用复制混合模式，避免 alpha 混合的计算开销
- **零拷贝（部分）**: 对于 CG 支持的格式（RGBA_8888、BGRA_8888），`SkBitmap` 数据直接传给 CG，无需像素转换
- **ICC 解析**: 非 sRGB 色彩空间的转换涉及 ICC 配置文件的生成/解析，有一定开销

## 相关文件

- `include/utils/mac/SkCGUtils.h` — 公共 API 声明
- `src/utils/mac/SkUniqueCFRef.h` — CF 对象 RAII 包装
- `src/utils/mac/SkCGBase.h` — CG 基础定义
- `src/utils/mac/SkCGGeometry.h` — CG 几何类型转换
- `include/core/SkBitmap.h` — Skia 位图
- `include/core/SkColorSpace.h` — Skia 色彩空间
- `include/encode/SkICC.h` — ICC 配置文件操作
