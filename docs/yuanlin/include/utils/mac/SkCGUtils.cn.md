# SkCGUtils Core Graphics 工具集

> 源文件: `include/utils/mac/SkCGUtils.h`

## 概述

`SkCGUtils` 提供了 Skia 与 Apple 的 Core Graphics (CG) 框架之间的互操作工具函数集。该模块允许在 Skia 数据类型(如 `SkBitmap`、`SkImage`、`SkColorSpace`)和 Core Graphics 类型(如 `CGImageRef`、`CGContextRef`、`CGColorSpaceRef`)之间进行转换,是 Skia 在 macOS 和 iOS 平台上集成的关键桥梁。

## 架构位置

本模块位于 Skia 的平台特定工具(utils/mac)子系统中,属于平台抽象层。它专门用于 macOS 和 iOS 平台,提供与 Apple 原生图形 API 的双向数据转换能力,使得 Skia 可以与 Cocoa/UIKit 框架无缝集成。

## 平台限定

该文件仅在以下平台编译和使用:
- **macOS**: 通过 `SK_BUILD_FOR_MAC` 宏控制
- **iOS**: 通过 `SK_BUILD_FOR_IOS` 宏控制

在其他平台上,这些函数不可用。

## 公共 API 函数

### 上下文创建

#### `SK_API CGContextRef SkCreateCGContext(const SkPixmap&)`

- **功能**: 从 Skia 的 `SkPixmap` 创建 Core Graphics 绘图上下文
- **参数**: `SkPixmap` 对象,包含像素数据和格式信息
- **返回值**: 新创建的 `CGContextRef`,调用者负责释放
- **用途**: 允许使用 Core Graphics API 在 Skia 像素缓冲区上绘制
- **注意**: 返回的上下文与 SkPixmap 共享像素缓冲区,修改会影响原数据

### 从 Core Graphics 导入到 Skia

#### `SK_API bool SkCreateBitmapFromCGImage(SkBitmap* dst, CGImageRef src)`

- **功能**: 从 Core Graphics 图像创建 Skia 位图
- **参数**:
  - `dst`: 指向目标 `SkBitmap` 的指针
  - `src`: 源 Core Graphics 图像
- **返回值**: 成功返回 `true`,失败返回 `false`
- **失败情况**: 图像格式不兼容或内存分配失败
- **行为**: 会复制像素数据,分配新内存

#### `SK_API sk_sp<SkImage> SkMakeImageFromCGImage(CGImageRef)`

- **功能**: 从 Core Graphics 图像创建 Skia 图像
- **参数**: Core Graphics 图像引用
- **返回值**: Skia 图像的智能指针,失败返回 `nullptr`
- **优势**: 使用智能指针自动管理内存,更现代的 API
- **用途**: 在 Skia 中使用 macOS/iOS 加载或处理的图像

#### `SK_API bool SkCopyPixelsFromCGImage(const SkImageInfo& info, size_t rowBytes, void* dstPixels, CGImageRef src)`

- **功能**: 从 Core Graphics 图像复制像素数据到指定内存区域
- **参数**:
  - `info`: 目标像素格式信息
  - `rowBytes`: 每行字节数(步幅)
  - `dstPixels`: 目标内存地址
  - `src`: 源 Core Graphics 图像
- **返回值**: 成功返回 `true`,失败返回 `false`
- **用途**: 提供更底层的控制,可以复制到预分配的内存

#### `static inline bool SkCopyPixelsFromCGImage(const SkPixmap& dst, CGImageRef src)`

- **功能**: `SkCopyPixelsFromCGImage` 的便捷重载版本
- **参数**:
  - `dst`: 目标 `SkPixmap` 对象
  - `src`: 源 Core Graphics 图像
- **返回值**: 成功返回 `true`,失败返回 `false`
- **优势**: 自动从 SkPixmap 提取格式和内存信息

### 从 Skia 导出到 Core Graphics

#### `SK_API CGImageRef SkCreateCGImageRef(const SkBitmap& bm)`

- **功能**: 从 Skia 位图创建 Core Graphics 图像
- **参数**: Skia 位图引用
- **返回值**: 新创建的 `CGImageRef`,调用者负责释放
- **用途**: 将 Skia 渲染结果显示在 macOS/iOS UI 中
- **行为**: 使用位图的色彩空间信息

#### `SK_API CGImageRef SkCreateCGImageRefWithColorspace(const SkBitmap& bm, CGColorSpaceRef space)`

- **功能**: 从 Skia 位图创建 Core Graphics 图像,指定色彩空间
- **参数**:
  - `bm`: Skia 位图
  - `space`: Core Graphics 色彩空间(当前被忽略)
- **返回值**: 新创建的 `CGImageRef`
- **注意**: 文档说明色彩空间参数被忽略,实际使用位图自身的色彩空间

### 色彩空间转换

#### `SK_API sk_sp<SkColorSpace> SkMakeColorSpaceFromCGColorSpace(CGColorSpaceRef)`

- **功能**: 从 Core Graphics 色彩空间创建 Skia 色彩空间
- **参数**: Core Graphics 色彩空间引用
- **返回值**: Skia 色彩空间智能指针,失败或输入为 `nullptr` 时返回 `nullptr`
- **用途**: 保持色彩管理的一致性,确保正确的色彩空间转换

#### `SK_API CGColorSpaceRef SkCreateCGColorSpace(const SkColorSpace*)`

- **功能**: 从 Skia 色彩空间创建 Core Graphics 色彩空间
- **参数**: Skia 色彩空间指针,可以为 `nullptr`
- **返回值**: Core Graphics 色彩空间引用,失败或输入为 `nullptr` 时返回 sRGB
- **默认行为**: 失败时返回 sRGB 色彩空间作为安全默认值
- **注意**: 不会保留(retain)输入的 SkColorSpace

### 数据提供者

#### `SK_API CGDataProviderRef SkCreateCGDataProvider(sk_sp<SkData>)`

- **功能**: 从 Skia 数据对象创建 Core Graphics 数据提供者
- **参数**: Skia 数据智能指针
- **返回值**: Core Graphics 数据提供者引用
- **行为**: 保留(retain) SkData 对象,确保数据生命周期
- **用途**: 在创建 CGImage 时提供像素数据源

### 绘制函数

#### `void SkCGDrawBitmap(CGContextRef, const SkBitmap&, float x, float y)`

- **功能**: 将 Skia 位图绘制到 Core Graphics 上下文
- **参数**:
  - 第1个: Core Graphics 绘图上下文
  - 第2个: 要绘制的 Skia 位图
  - `x`, `y`: 位图左上角的位置坐标
- **用途**: 在 macOS/iOS 的视图中显示 Skia 渲染的内容
- **注意**: 此函数没有 `SK_API` 标记,可能是内部使用或向后兼容

## 内部实现细节

### 像素格式转换

Skia 和 Core Graphics 使用不同的像素格式约定:

- **字节序差异**: 需要处理大小端和通道顺序
- **预乘 Alpha**: Core Graphics 通常使用预乘 Alpha,需要正确转换
- **色彩空间**: 确保两种系统的色彩空间一致

### 内存管理策略

1. **CGImage 创建**: 通常会复制像素数据,或使用 `CGDataProvider` 延迟复制
2. **引用计数**: Core Graphics 使用引用计数,需要正确的 retain/release
3. **智能指针**: Skia 侧使用 `sk_sp<>`,需要正确的跨边界内存管理

### 性能考量

- **零拷贝优化**: 某些情况下可以共享内存而不是复制
- **延迟转换**: 只在实际需要时进行格式转换
- **缓存**: 重复使用的图像可以缓存转换结果

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkImage.h` | Skia 图像类型 |
| `include/core/SkImageInfo.h` | 图像格式信息 |
| `include/core/SkPixmap.h` | 像素映射接口 |
| `include/core/SkSize.h` | 尺寸定义 |
| `ApplicationServices/ApplicationServices.h` (macOS) | Core Graphics 框架 |
| `CoreGraphics/CoreGraphics.h` (iOS) | Core Graphics 框架 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `src/ports/SkFontHost_mac.cpp` | macOS 字体渲染 |
| `src/ports/SkImageGenerator_mac.cpp` | 从 macOS 图像源生成 Skia 图像 |
| `src/utils/mac/` | macOS 平台特定工具 |
| 应用层代码 | 在 macOS/iOS 应用中集成 Skia |

## 设计模式与设计决策

### 工厂模式

所有创建 Core Graphics 对象的函数(`SkCreateCGImageRef`, `SkCreateCGContext` 等)都遵循工厂模式,返回新创建的对象。

### 适配器模式

整个模块本质上是一个适配器,连接 Skia 和 Core Graphics 两个不同的图形系统:
- 提供双向转换
- 隐藏内部复杂性
- 统一接口风格

### 函数重载

提供了多个版本的转换函数(如 `SkCopyPixelsFromCGImage`),适应不同的使用场景:
- 底层版本: 最大灵活性
- 便捷版本: 更易使用

## 使用场景

### 场景 1: 在 macOS/iOS 视图中显示 Skia 内容

```cpp
// Skia 渲染
SkBitmap bitmap;
// ... 使用 Skia 渲染到 bitmap ...

// 转换为 Core Graphics 并显示
CGImageRef cgImage = SkCreateCGImageRef(bitmap);
// 在 NSImageView 或 UIImageView 中显示
CGImageRelease(cgImage);  // 记得释放
```

### 场景 2: 加载系统图像到 Skia

```cpp
// 从文件加载 Core Graphics 图像
CGImageRef cgImage = /* 从 NSImage 或 UIImage 获取 */;

// 转换为 Skia 图像
sk_sp<SkImage> skImage = SkMakeImageFromCGImage(cgImage);

// 在 Skia 中使用
canvas->drawImage(skImage, 0, 0);
```

### 场景 3: 色彩空间管理

```cpp
// 获取系统色彩空间
CGColorSpaceRef cgSpace = CGColorSpaceCreateWithName(kCGColorSpaceDisplayP3);

// 转换为 Skia 色彩空间
sk_sp<SkColorSpace> skSpace = SkMakeColorSpaceFromCGColorSpace(cgSpace);

// 创建带正确色彩空间的图像
SkImageInfo info = SkImageInfo::Make(width, height, colorType, alphaType, skSpace);

CGColorSpaceRelease(cgSpace);
```

### 场景 4: 混合渲染

```cpp
// 创建 Skia 像素缓冲区
SkBitmap bitmap;
bitmap.allocN32Pixels(width, height);

// 使用 Core Graphics 绘制
CGContextRef ctx = SkCreateCGContext(bitmap.pixmap());
// ... 使用 CG 函数绘制 ...
CGContextRelease(ctx);

// 然后使用 Skia 继续绘制
SkCanvas canvas(bitmap);
// ... 使用 Skia 继续渲染 ...
```

## 平台相关说明

### macOS 特定

- 包含 `ApplicationServices/ApplicationServices.h`
- 通常用于 AppKit (NSView) 集成
- 支持高 DPI (Retina) 显示

### iOS 特定

- 包含 `CoreGraphics/CoreGraphics.h`
- 用于 UIKit (UIView) 集成
- 考虑设备像素比 (scale factor)

### 性能建议

1. **macOS**: 在 Metal 或 OpenGL 后端优先使用 Skia 原生渲染
2. **iOS**: 考虑使用 Metal 后端以获得最佳性能
3. **转换开销**: 频繁转换会影响性能,尽量减少跨边界调用

## 常见陷阱

### 内存管理

```cpp
// ❌ 错误: 忘记释放 Core Graphics 对象
CGImageRef img = SkCreateCGImageRef(bitmap);
// ... 使用 img ...
// 内存泄漏!

// ✅ 正确: 使用后释放
CGImageRef img = SkCreateCGImageRef(bitmap);
// ... 使用 img ...
CGImageRelease(img);
```

### 色彩空间不匹配

```cpp
// ❌ 错误: 忽略色彩空间可能导致颜色不准确
sk_sp<SkImage> img = SkMakeImageFromCGImage(cgImage);
// 可能丢失 Display P3 等宽色域信息

// ✅ 正确: 显式处理色彩空间
CGColorSpaceRef cgSpace = CGImageGetColorSpace(cgImage);
sk_sp<SkColorSpace> skSpace = SkMakeColorSpaceFromCGColorSpace(cgSpace);
// 使用 skSpace 创建正确的 SkImageInfo
```

### 像素格式假设

```cpp
// ❌ 错误: 假设特定的像素格式
// Core Graphics 可能返回各种格式

// ✅ 正确: 检查并处理不同格式
if (!SkCopyPixelsFromCGImage(pixmap, cgImage)) {
    // 处理不兼容的格式
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkBitmap.h` | Skia 位图类定义 |
| `include/core/SkImage.h` | Skia 图像类定义 |
| `include/core/SkColorSpace.h` | Skia 色彩空间类 |
| `src/utils/mac/SkCGUtils.cpp` | 本头文件的实现 |
| `src/ports/SkImageGenerator_mac.cpp` | 使用这些工具的图像生成器 |
| `tools/sk_app/mac/` | macOS 应用框架,使用这些工具 |

## 总结

`SkCGUtils` 是 Skia 在 Apple 平台上的关键桥梁,提供了全面的 Skia 与 Core Graphics 互操作能力。其设计充分考虑了两个图形系统的差异,包括像素格式、色彩空间、内存管理等方面。通过提供丰富的双向转换函数,它使得开发者可以灵活地在 Skia 和原生 macOS/iOS 图形 API 之间切换,充分利用两者的优势。对于在 Apple 平台上使用 Skia 的开发者来说,掌握这些工具函数是必不可少的。
