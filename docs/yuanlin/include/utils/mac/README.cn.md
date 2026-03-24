# utils/mac - macOS/iOS 平台工具 API

## 概述

`include/utils/mac` 目录提供了 Skia 在 Apple 平台（macOS 和 iOS）上的平台特定
工具函数。这些工具实现了 Skia 像素数据与 Apple Core Graphics（CG）框架对象之间
的双向转换，使得 Skia 可以无缝集成到 Apple 的原生图形系统中。

该目录仅包含一个头文件 `SkCGUtils.h`，提供了一组对称的转换函数。一方面，可以
将 `CGImage` 转换为 Skia 的 `SkBitmap` 或 `SkImage`，也可以直接将 `CGImage`
的像素复制到 Skia 的像素缓冲区中。另一方面，可以将 Skia 的 `SkBitmap` 转换为
`CGImageRef`，或者从 `SkPixmap` 创建 `CGContextRef` 以便使用 Core Graphics
直接绘制到 Skia 管理的像素缓冲区中。

颜色空间转换也是该模块的重要功能。`SkMakeColorSpaceFromCGColorSpace` 将 Apple
的 `CGColorSpace` 转换为 Skia 的 `SkColorSpace`，`SkCreateCGColorSpace` 则执行
反向转换。此外还提供了 `CGDataProvider` 的创建函数，用于将 `SkData` 包装为
Core Graphics 可以使用的数据提供者。

这些工具函数对于在 Apple 平台上进行 Skia 与 UIKit/AppKit 混合渲染、使用
CoreGraphics 进行屏幕截图或图像处理等场景至关重要。所有函数仅在
`SK_BUILD_FOR_MAC` 或 `SK_BUILD_FOR_IOS` 宏定义时可用。

## 架构图

```
+------------------------------------------------------------------+
|                  Apple 应用层                                      |
|  UIKit / AppKit / SwiftUI                                        |
+------------------------------------------------------------------+
         |                              |
         v                              v
+-------------------+          +-------------------+
| Core Graphics     |          |     Skia          |
| CGImage           |<-------->| SkBitmap / SkImage|
| CGContext         |          | SkPixmap          |
| CGColorSpace      |<-------->| SkColorSpace      |
| CGDataProvider    |          | SkData            |
+-------------------+          +-------------------+
         |         ^            ^         |
         |         |            |         |
         v         |            |         v
+------------------------------------------------------------------+
|                   SkCGUtils 转换函数                                |
+------------------------------------------------------------------+
| CGImage --> Skia:                                                 |
|   SkCreateBitmapFromCGImage()   CGImage -> SkBitmap               |
|   SkMakeImageFromCGImage()      CGImage -> SkImage                |
|   SkCopyPixelsFromCGImage()     CGImage -> 像素缓冲区              |
+------------------------------------------------------------------+
| Skia --> CGImage:                                                 |
|   SkCreateCGImageRef()          SkBitmap -> CGImageRef            |
|   SkCreateCGImageRefWithCS()    SkBitmap + 色彩空间 -> CGImageRef  |
+------------------------------------------------------------------+
| 上下文与色彩空间:                                                   |
|   SkCreateCGContext()           SkPixmap -> CGContextRef           |
|   SkCreateCGColorSpace()        SkColorSpace -> CGColorSpaceRef   |
|   SkMakeColorSpaceFromCG..()   CGColorSpaceRef -> SkColorSpace    |
|   SkCreateCGDataProvider()      SkData -> CGDataProviderRef       |
+------------------------------------------------------------------+
| 绘制工具:                                                          |
|   SkCGDrawBitmap()             在 CGContext 中绘制 SkBitmap        |
+------------------------------------------------------------------+
```

## 目录结构

```
include/utils/mac/
  BUILD.bazel       # Bazel 构建配置
  SkCGUtils.h       # Core Graphics 互操作工具函数集
```

## 关键类与函数

### CGImage 到 Skia 的转换

**SkCreateBitmapFromCGImage - CGImage 到 SkBitmap：**
```cpp
bool SkCreateBitmapFromCGImage(SkBitmap* dst, CGImageRef src);
```
将 CGImage 的像素复制到 SkBitmap 中。失败时返回 false，SkBitmap 保持不变。

**SkMakeImageFromCGImage - CGImage 到 SkImage：**
```cpp
sk_sp<SkImage> SkMakeImageFromCGImage(CGImageRef);
```
从 CGImage 创建不可变的 SkImage 对象。

**SkCopyPixelsFromCGImage - CGImage 像素复制：**
```cpp
bool SkCopyPixelsFromCGImage(const SkImageInfo& info, size_t rowBytes,
                              void* dstPixels, CGImageRef src);
bool SkCopyPixelsFromCGImage(const SkPixmap& dst, CGImageRef src);
```
将 CGImage 的像素数据复制到指定的内存区域。可以指定目标格式和行字节数。

### Skia 到 CGImage 的转换

**SkCreateCGImageRef - SkBitmap 到 CGImage：**
```cpp
CGImageRef SkCreateCGImageRef(const SkBitmap& bm);
```
从 SkBitmap 创建 CGImageRef。调用者负责释放（CGImageRelease）。

**SkCreateCGImageRefWithColorspace - 带色彩空间的转换：**
```cpp
CGImageRef SkCreateCGImageRefWithColorspace(const SkBitmap& bm, CGColorSpaceRef space);
```
从 SkBitmap 创建带有指定色彩空间的 CGImageRef。

### CG 上下文创建

**SkCreateCGContext - 创建 CG 绘图上下文：**
```cpp
CGContextRef SkCreateCGContext(const SkPixmap&);
```
从 SkPixmap 创建 CGContextRef，允许使用 Core Graphics API 直接绘制到
Skia 管理的像素缓冲区中。

### 颜色空间转换

**SkCreateCGColorSpace - Skia 到 CG 色彩空间：**
```cpp
CGColorSpaceRef SkCreateCGColorSpace(const SkColorSpace*);
```
将 SkColorSpace 转换为 CGColorSpaceRef。如果输入为 nullptr 或转换失败，
返回 sRGB 色彩空间。

**SkMakeColorSpaceFromCGColorSpace - CG 到 Skia 色彩空间：**
```cpp
sk_sp<SkColorSpace> SkMakeColorSpaceFromCGColorSpace(CGColorSpaceRef);
```
将 CGColorSpaceRef 转换为 SkColorSpace。无法转换或输入为 nullptr 时返回 nullptr。

### 数据提供者

**SkCreateCGDataProvider - 创建 CG 数据提供者：**
```cpp
CGDataProviderRef SkCreateCGDataProvider(sk_sp<SkData>);
```
将 SkData 封装为 CGDataProviderRef，并保持对 SkData 的引用，确保数据生命周期。

### 绘制工具

**SkCGDrawBitmap - 在 CG 上下文中绘制位图：**
```cpp
void SkCGDrawBitmap(CGContextRef, const SkBitmap&, float x, float y);
```
在指定的 CG 上下文中绘制 SkBitmap，(x, y) 指定位图左上角的位置。

## 依赖关系

- **内部依赖**：`include/core`（SkBitmap、SkImage、SkPixmap、SkColorSpace、SkData、SkImageInfo）
- **平台依赖**：
  - macOS：ApplicationServices.framework（包含 CoreGraphics）
  - iOS：CoreGraphics.framework
- **编译条件**：`SK_BUILD_FOR_MAC` 或 `SK_BUILD_FOR_IOS`

## 相关文档与参考

- Apple Core Graphics 文档：https://developer.apple.com/documentation/coregraphics
- Apple CGImage 文档：https://developer.apple.com/documentation/coregraphics/cgimage
- Apple CGColorSpace 文档：https://developer.apple.com/documentation/coregraphics/cgcolorspace
- 源码实现位于 `src/utils/mac/` 目录
