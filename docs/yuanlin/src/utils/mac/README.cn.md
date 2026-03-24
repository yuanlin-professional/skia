# src/utils/mac - macOS/iOS 平台专用工具库

## 概述

`src/utils/mac` 目录包含了 Skia 在 macOS 和 iOS 平台上与 Apple 系统框架交互的工具代码。这些代码主要负责 Skia 内部数据类型与 Apple Core Graphics（CG）和 Core Text（CT）框架数据类型之间的桥接与转换，是 Skia 在 Apple 平台上进行字体渲染和图像处理的关键基础设施。

该目录中所有代码均通过条件编译宏 `SK_BUILD_FOR_MAC` 和 `SK_BUILD_FOR_IOS` 进行平台隔离，确保这些代码仅在 Apple 平台上编译和链接。macOS 平台通过 `ApplicationServices` 框架获取 CoreGraphics 和 CoreText 功能，而 iOS 平台则直接包含 `CoreGraphics/CoreGraphics.h` 和 `CoreText/CoreText.h` 头文件。

从功能维度划分，该目录的代码涵盖三大领域：首先是 Core Graphics 集成，包括 CGFloat 与 SkScalar 之间的类型转换、CGRect 几何辅助函数、SkBitmap 与 CGImage 的双向转换、以及 SkColorSpace 与 CGColorSpace 的互相转换；其次是 Core Text 集成，包括 CTFont 的字体平滑行为检测、CSS 字重到 CTFont 权重的映射关系、以及 CTFont 精确复制（在保持光学尺寸等属性不变的前提下调整字号）；最后是资源管理工具，即 `SkUniqueCFRef` 智能指针模板，用于自动管理 CoreFoundation 对象的引用计数。

这些工具在 Skia 的 macOS/iOS 字体端口（`src/ports/SkTypeface_mac_ct.h`）和系统集成层中被广泛使用，是 Skia 能够在 Apple 平台上实现高质量文本渲染和图像处理的重要支撑。

## 架构图

```
+------------------------------------------------------------------------+
|                    src/utils/mac 平台工具库                              |
+------------------------------------------------------------------------+
|                                                                          |
|  +--------------------------+     +-------------------------------+     |
|  | Core Graphics 集成层      |     | Core Text 集成层              |     |
|  |                          |     |                               |     |
|  | SkCGBase.h               |     | SkCTFont.h / .cpp             |     |
|  |   SkScalarToCGFloat()    |     |   SkCTFontSmoothBehavior      |     |
|  |   SkScalarFromCGFloat()  |     |   SkCTFontGetSmoothBehavior() |     |
|  |   SkFloatFromCGFloat()   |     |   SkCTFontGetNSFontWeight-    |     |
|  |                          |     |     Mapping()                 |     |
|  | SkCGGeometry.h           |     |   SkCTFontGetDataFont-        |     |
|  |   SkCGRectIsEmpty()      |     |     WeightMapping()           |     |
|  |   SkCGRectGetMinX/MaxX() |     |                               |     |
|  |   SkCGRectGetMinY/MaxY() |     | SkCTFontCreateExactCopy.h/.cpp|     |
|  |   SkCGRectGetWidth()     |     |   SkCTFontCreateExactCopy()   |     |
|  |                          |     |   add_opsz_attr()             |     |
|  | SkCreateCGImageRef.cpp   |     |   add_notrak_attr()           |     |
|  |   SkCreateCGImageRef()   |     |                               |     |
|  |   SkCGDrawBitmap()       |     +-------------------------------+     |
|  |   SkCreateCGContext()    |                                           |
|  |   SkCopyPixelsFromCG-    |     +-------------------------------+     |
|  |     Image()              |     | 资源管理                       |     |
|  |   SkCreateBitmapFromCG-  |     |                               |     |
|  |     Image()              |     | SkUniqueCFRef.h               |     |
|  |   SkMakeImageFromCGImage(|     |   template<CFRef>             |     |
|  |   SkCreateCGDataProvider(|     |   SkUniqueCFRef =             |     |
|  |   SkMakeColorSpaceFrom-  |     |     unique_ptr<CFRef,         |     |
|  |     CGColorSpace()       |     |       CFRelease>              |     |
|  |   SkCreateCGColorSpace() |     |                               |     |
|  +--------------------------+     +-------------------------------+     |
|                                                                          |
+------------------------------------------------------------------------+
         |                                    |
         v                                    v
+-------------------+              +---------------------+
| Apple 系统框架     |              | Skia 核心模块        |
|                   |              |                     |
| CoreGraphics      |              | include/core/       |
|   CGImage         |              |   SkBitmap          |
|   CGContext       |              |   SkColorSpace      |
|   CGColorSpace    |              |   SkPixmap          |
|   CGDataProvider  |              |   SkImageInfo       |
|                   |              |   SkScalar          |
| CoreText          |              |                     |
|   CTFont          |              | src/ports/          |
|   CTFontDescriptor|              |   SkTypeface_mac_ct |
|                   |              |                     |
| CoreFoundation    |              | include/encode/     |
|   CFRelease       |              |   SkICC             |
|   CFData          |              |                     |
+-------------------+              +---------------------+
```

## 目录结构

```
src/utils/mac/
├── BUILD.bazel                       # Bazel 构建配置
├── SkCGBase.h                        # CG 基础类型转换（SkScalar <-> CGFloat）
├── SkCGGeometry.h                    # CG 几何类型辅助内联函数
├── SkCreateCGImageRef.cpp            # CG 图像创建与 Bitmap/Image 双向转换
├── SkCTFont.cpp                      # CT 字体平滑行为检测与权重映射
├── SkCTFont.h                        # CT 字体工具头文件
├── SkCTFontCreateExactCopy.cpp       # CTFont 精确复制实现
├── SkCTFontCreateExactCopy.h         # CTFont 精确复制头文件
└── SkUniqueCFRef.h                   # CoreFoundation 智能指针模板
```

## 关键类与函数

### SkCGBase.h - Core Graphics 基础类型转换

```cpp
// src/utils/mac/SkCGBase.h
static inline CGFloat SkScalarToCGFloat(SkScalar scalar) {
    return CGFLOAT_IS_DOUBLE ? SkScalarToDouble(scalar) : scalar;
}

static inline SkScalar SkScalarFromCGFloat(CGFloat cgFloat) {
    return CGFLOAT_IS_DOUBLE ? SkDoubleToScalar(cgFloat) : cgFloat;
}

static inline float SkFloatFromCGFloat(CGFloat cgFloat) {
    return CGFLOAT_IS_DOUBLE ? static_cast<float>(cgFloat) : cgFloat;
}
```
这三个内联函数处理 Skia 的 `SkScalar`（float）与 Apple 的 `CGFloat` 之间的类型转换。在 64 位系统中 `CGFloat` 是 `double`，因此需要进行精度转换；在 32 位系统中两者类型相同，编译器会优化掉转换开销。`CGFLOAT_IS_DOUBLE` 宏由系统头文件定义，根据当前架构自动选择正确的转换路径。

### SkCGGeometry.h - Core Graphics 几何辅助函数

```cpp
// src/utils/mac/SkCGGeometry.h
static inline bool SkCGRectIsEmpty(const CGRect& rect);
static inline CGFloat SkCGRectGetMinX(const CGRect& rect);
static inline CGFloat SkCGRectGetMaxX(const CGRect& rect);
static inline CGFloat SkCGRectGetMinY(const CGRect& rect);
static inline CGFloat SkCGRectGetMaxY(const CGRect& rect);
static inline CGFloat SkCGRectGetWidth(const CGRect& rect);
```
这些内联函数是 Apple `CGRectGetMinX()` 等系统函数的高性能替代品。系统版本的 CGRect 辅助函数需要进行函数调用并在栈上复制 CGRect 结构体，而 Skia 的内联版本直接通过引用访问字段成员，消除了函数调用和内存拷贝的开销。在频繁进行几何计算的渲染路径中，这种优化可以带来显著的性能提升。

### SkCreateCGImageRef.cpp - 图像转换核心

```cpp
// src/utils/mac/SkCreateCGImageRef.cpp

// SkBitmap -> CGImageRef（Skia 到系统方向）
CGImageRef SkCreateCGImageRef(const SkBitmap& bm);

// 在 CGContext 上绘制 SkBitmap
void SkCGDrawBitmap(CGContextRef cg, const SkBitmap& bm, float x, float y);

// 从 SkPixmap 创建 CGContext
CGContextRef SkCreateCGContext(const SkPixmap& pmap);

// CGImageRef -> SkBitmap（系统到 Skia 方向）
bool SkCopyPixelsFromCGImage(const SkImageInfo& info, size_t rowBytes,
                              void* pixels, CGImageRef image);
bool SkCreateBitmapFromCGImage(SkBitmap* dst, CGImageRef image);
sk_sp<SkImage> SkMakeImageFromCGImage(CGImageRef src);

// 颜色空间双向转换
sk_sp<SkColorSpace> SkMakeColorSpaceFromCGColorSpace(CGColorSpaceRef cgColorSpace);
CGColorSpaceRef SkCreateCGColorSpace(const SkColorSpace* space);

// 数据提供者创建
CGDataProviderRef SkCreateCGDataProvider(sk_sp<SkData> data);
```

这是该目录中最核心的文件，实现了 Skia 与 Core Graphics 之间的完整图像数据桥接。关键设计要点包括：

- **像素格式适配**：支持 RGBA_8888、BGRA_8888、ARGB_4444 和 RGB_565 等格式。对于 CG 不直接支持的 RGB_565 格式，会自动上转为 RGBA_8888。
- **Alpha 类型映射**：正确处理 Opaque、Premultiplied 和 Unpremultiplied 三种 Alpha 类型到 CGBitmapInfo 标志的映射。
- **颜色空间转换**：支持 sRGB 快速路径和通过 ICC Profile 解析的通用路径。使用 `skcms_Parse` 解析 ICC 数据，使用 `SkWriteICCProfile` 生成 ICC 数据。
- **内存管理**：通过 `CGDataProviderCreateWithData` 的回调机制实现零拷贝数据共享，在 CGDataProvider 释放时自动释放 Skia 端的数据。

### SkCTFont - Core Text 字体工具

```cpp
// src/utils/mac/SkCTFont.h
enum class SkCTFontSmoothBehavior {
    none,      // SmoothFonts 无效果
    some,      // SmoothFonts 有效果但无亚像素覆盖
    subpixel,  // SmoothFonts 有效果且提供亚像素覆盖
};

SkCTFontSmoothBehavior SkCTFontGetSmoothBehavior();

using SkCTFontWeightMapping = const CGFloat[11];
SkCTFontWeightMapping& SkCTFontGetNSFontWeightMapping();   // 系统字体权重映射
SkCTFontWeightMapping& SkCTFontGetDataFontWeightMapping();  // 数据字体权重映射
```

字体平滑行为检测函数 `SkCTFontGetSmoothBehavior()` 通过实际渲染一个测试字形（蜘蛛符号）来检测当前系统的字体渲染模式。内部嵌入了一个完整的 TrueType 字体文件数据用于测试。

字重映射函数提供了 CSS 标准字重值（0-1000，步长 100）到 CTFontDescriptor 权重值（-1.0 到 1.0）的映射表。系统字体（`NSFont`）和数据字体使用不同的映射关系，因此分别提供了两套映射。

### SkCTFontCreateExactCopy - CTFont 精确复制

```cpp
// src/utils/mac/SkCTFontCreateExactCopy.h
struct OpszVariation;

SkUniqueCFRef<CTFontRef> SkCTFontCreateExactCopy(
    CTFontRef baseFont, CGFloat textSize, OpszVariation opsz);
```

这是一个精心设计的函数，用于在调整 CTFont 字号的同时保持其他属性不变。在 macOS 的字体系统中，简单地调用 `CTFontCreateCopyWithAttributes` 可能会导致光学尺寸（optical size）、相对字形度量以及底层字体数据发生意外变化。

该函数处理了多个 macOS 版本中的复杂行为：
- **macOS 10.12+**：CGFont 上默认轴值的变化会在创建 CTFont 时被丢弃
- **macOS 10.15**：光学尺寸设置的优先级链（CTFontDescriptor 属性 > 默认值 > CGFont 变化 > 请求大小）
- **`add_opsz_attr()`**：通过未文档化的 `NSCTFontOpticalSizeAttribute` 属性精确控制光学尺寸
- **`add_notrak_attr()`**：通过 `NSCTFontUnscaledTrackingAttribute` 关闭 `trak` 表对字距的影响

### SkUniqueCFRef - CoreFoundation 智能指针

```cpp
// src/utils/mac/SkUniqueCFRef.h
template <typename CFRef>
using SkUniqueCFRef =
    std::unique_ptr<std::remove_pointer_t<CFRef>, SkFunctionObject<CFRelease>>;
```

这是一个轻量级的类型别名模板，将 `std::unique_ptr` 与 `CFRelease` 组合，为所有 CoreFoundation 引用类型（如 `CGImageRef`、`CTFontRef`、`CFStringRef` 等）提供自动引用计数管理。使用 `SkFunctionObject<CFRelease>` 作为删除器，确保在智能指针析构时自动调用 `CFRelease()`。

典型用法：
```cpp
SkUniqueCFRef<CGImageRef> img(SkCreateCGImageRef(bm));
SkUniqueCFRef<CGColorSpaceRef> cs(SkCreateCGColorSpace(colorSpace));
SkUniqueCFRef<CTFontRef> font(SkCTFontCreateExactCopy(base, size, opsz));
```

## 依赖关系

```
src/utils/mac/ 的依赖关系图:

Apple 系统框架依赖:
  macOS:  ApplicationServices.framework (包含 CG 和 CT)
  iOS:    CoreGraphics.framework + CoreText.framework + CoreFoundation.framework

Skia 内部依赖:
  include/core/SkBitmap.h          -> SkBitmap 类（图像转换）
  include/core/SkColorSpace.h      -> SkColorSpace 类（颜色空间转换）
  include/core/SkData.h            -> SkData 类（数据管理）
  include/core/SkImage.h           -> SkImage 类（图像转换）
  include/core/SkScalar.h          -> SkScalar 类型定义
  include/core/SkTypes.h           -> 平台编译宏
  include/encode/SkICC.h           -> ICC Profile 编码
  include/private/base/SkTemplates.h -> SkFunctionObject
  include/utils/mac/SkCGUtils.h    -> 公开 API 头文件
  src/core/SkColorData.h           -> 颜色数据处理
  src/sfnt/SkOTTable_OS_2.h        -> OpenType 字体表
  src/sfnt/SkSFNTHeader.h          -> SFNT 字体头
  src/ports/SkTypeface_mac_ct.h    -> macOS 字体端口

被以下模块使用:
  src/ports/SkTypeface_mac_ct.cpp  -> 使用 SkCTFont*, SkCTFontCreateExactCopy
  src/ports/SkFontMgr_mac_ct.cpp   -> 使用 SkCTFontGetNSFontWeightMapping
  include/utils/mac/SkCGUtils.h    -> 声明 SkCreateCGImageRef 等公开 API
```

## 设计模式分析

### 1. 桥接模式（Bridge Pattern）
整个 `src/utils/mac` 目录本质上是一个桥接层，将 Skia 的平台无关抽象与 Apple 平台的具体实现连接起来。例如 `SkCreateCGImageRef()` 将 Skia 的 `SkBitmap` 桥接为 Apple 的 `CGImageRef`，`SkMakeColorSpaceFromCGColorSpace()` 将 Apple 的 `CGColorSpaceRef` 桥接为 Skia 的 `SkColorSpace`。

### 2. 适配器模式（Adapter Pattern）
`SkCGBase.h` 中的类型转换函数充当适配器角色，适配 Skia 的 `SkScalar`（始终为 float）与 Apple 的 `CGFloat`（在 64 位系统上为 double）之间的类型差异。`SkCGGeometry.h` 则适配了 CGRect 的访问方式，提供了内联的高性能替代。

### 3. RAII 与智能指针模式
`SkUniqueCFRef<T>` 是 RAII 模式的典型应用，它基于 `std::unique_ptr` 实现，确保 CoreFoundation 对象在作用域结束时自动释放。整个目录中的函数返回值大量使用此智能指针，避免了手动 `CFRelease()` 可能导致的资源泄漏。

### 4. 零拷贝数据共享（Zero-Copy Sharing）
`SkCreateCGImageRef()` 和 `SkCreateCGDataProvider()` 的实现展示了零拷贝数据共享模式。通过 `CGDataProviderCreateWithData` 的回调机制，CG 直接引用 Skia 管理的内存块，避免了不必要的数据复制。回调在 CG 端释放数据提供者时负责释放 Skia 端的数据。

### 5. 条件编译隔离
所有源文件使用 `#if defined(SK_BUILD_FOR_MAC) || defined(SK_BUILD_FOR_IOS)` 进行平台隔离，同时在不同平台上包含不同的系统头文件。这种设计确保了代码在非 Apple 平台上的编译安全性，并允许 macOS 和 iOS 共享大部分实现代码。

## 数据流

### SkBitmap 到 CGImage 转换流程
```
SkBitmap (Skia 位图)
    |
    v
prepare_for_image_ref()
    |-- 检测颜色类型 (RGBA_8888 / BGRA_8888 / ARGB_4444 / RGB_565)
    |-- RGB_565 需要上转为 RGBA_8888 (深拷贝像素)
    |-- 计算 bitsPerComponent 和 CGBitmapInfo
    |
    v
CGDataProviderCreateWithData()
    |-- 零拷贝：CG 直接引用 SkBitmap 的像素数据
    |-- 注册释放回调：delete SkBitmap*
    |
    v
SkCreateCGColorSpace()
    |-- sRGB 快速路径：直接创建 kCGColorSpaceSRGB
    |-- 其他颜色空间：通过 ICC Profile 创建
    |
    v
CGImageCreate() -> CGImageRef (Apple 图像对象)
```

### CGImage 到 SkBitmap 转换流程
```
CGImageRef (Apple 图像对象)
    |
    v
SkCreateBitmapFromCGImage()
    |-- 获取宽高: CGImageGetWidth/Height()
    |-- 获取颜色空间: CGImageGetColorSpace()
    |     |
    |     v
    |   SkMakeColorSpaceFromCGColorSpace()
    |     |-- 尝试按名称匹配 sRGB
    |     |-- 尝试解析 ICC Profile: CGColorSpaceCopyICCData() + skcms_Parse()
    |
    v
SkBitmap::tryAllocPixels(SkImageInfo::MakeN32Premul(...))
    |
    v
SkCopyPixelsFromCGImage()
    |-- 创建 CGBitmapContext 指向 SkBitmap 像素
    |-- CGContextSetBlendMode(kCGBlendModeCopy) -- 避免混合
    |-- CGContextDrawImage() -- 将 CGImage 绘制到上下文中
    |
    v
检测 Alpha 不透明性 -> 设置正确的 SkAlphaType
    |
    v
SkBitmap (Skia 位图输出)
```

### CTFont 精确复制流程
```
CTFontRef (原始字体) + textSize + OpszVariation
    |
    v
创建 CFMutableDictionary (属性字典)
    |
    +-- opszVariation.isSet == true
    |     |
    |     v
    |   add_opsz_attr() -> 设置 NSCTFontOpticalSizeAttribute
    |
    +-- opszVariation.isSet == false
    |     |
    |     v
    |   保留原始字体的光学尺寸（兼容 10.10-10.14 的 SFNSText/SFNSDisplay 切换）
    |
    v
add_notrak_attr() -> 设置 NSCTFontUnscaledTrackingAttribute = 0
    |
    v
CTFontCreateCopyWithAttributes(baseFont, textSize, NULL, descriptor)
    |
    v
SkUniqueCFRef<CTFontRef> (精确复制的字体，仅字号不同)
```

## 相关文档与参考

| 参考项 | 路径/链接 |
|-------|----------|
| 公开 macOS 工具 API | `include/utils/mac/SkCGUtils.h` |
| macOS 字体端口实现 | `src/ports/SkTypeface_mac_ct.h`, `src/ports/SkTypeface_mac_ct.cpp` |
| macOS 字体管理器 | `src/ports/SkFontMgr_mac_ct.cpp` |
| ICC Profile 编码 | `include/encode/SkICC.h` |
| 颜色空间核心类 | `include/core/SkColorSpace.h` |
| SFNT/OpenType 字体表 | `src/sfnt/SkOTTable_OS_2.h`, `src/sfnt/SkSFNTHeader.h` |
| 父目录工具库 | `src/utils/README.md` |
| Apple CoreGraphics 文档 | https://developer.apple.com/documentation/coregraphics |
| Apple CoreText 文档 | https://developer.apple.com/documentation/coretext |
| Apple CoreFoundation 文档 | https://developer.apple.com/documentation/corefoundation |
| skcms 颜色管理系统 | `third_party/skcms/` |
| Skia 官方文档 | https://skia.org/docs/ |
