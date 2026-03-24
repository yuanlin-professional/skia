# SkImageGeneratorCG

> 源文件: include/ports/SkImageGeneratorCG.h, src/ports/SkImageGeneratorCG.cpp

## 概述

SkImageGeneratorCG 是 Skia 图形库为 macOS 和 iOS 平台提供的图像解码器实现，基于 Apple 的 CoreGraphics 和 ImageIO 框架。ImageIO 是 Apple 平台的系统级图像编解码框架，支持广泛的图像格式、EXIF 元数据、色彩空间管理和硬件加速。该模块将 ImageIO 集成到 Skia 的 SkImageGenerator 框架中，提供原生的图像解码能力，支持 JPEG、PNG、HEIF、GIF 等格式，以及 EXIF 方向变换。

## 架构位置

该模块位于 Skia 的平台适配层（ports），专门为 Apple 平台提供图像生成功能：

```
skia/
├── include/ports/
│   └── SkImageGeneratorCG.h           # 公共接口
└── src/ports/
    ├── SkImageGeneratorCG.cpp         # 实现（184 行）
    └── utils/mac/
        └── SkUniqueCFRef.h            # CF 对象 RAII 包装
```

该模块仅在定义 `SK_BUILD_FOR_MAC` 或 `SK_BUILD_FOR_IOS` 宏时可用。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `ImageGeneratorCG` | `SkImageGenerator` | 封装 ImageIO 的图像生成器 |

### 关键成员变量

**ImageGeneratorCG:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fImageSrc` | `SkUniqueCFRef<CGImageSourceRef>` | CoreGraphics 图像源（const）|
| `fData` | `sk_sp<const SkData>` | 编码图像的原始数据（const）|
| `fOrigin` | `SkEncodedOrigin` | EXIF 方向标签（const）|

注意：所有成员变量都是 const，确保线程安全。

## 公共 API 函数

### 工厂函数

```cpp
namespace SkImageGeneratorCG {
    SK_API std::unique_ptr<SkImageGenerator> MakeFromEncodedCG(sk_sp<const SkData>);
}
```

从编码的图像数据创建 CoreGraphics 图像生成器。支持 Apple 平台原生支持的所有图像格式，包括：
- **标准格式**: JPEG, PNG, GIF, BMP, TIFF
- **RAW 格式**: CR2, NEF, DNG 等（macOS）
- **现代格式**: HEIF, WebP（iOS 14+/macOS 11+）

### SkImageGenerator 接口实现

```cpp
protected:
    sk_sp<const SkData> onRefEncodedData() override;
    bool onGetPixels(const SkImageInfo& info, void* pixels,
                     size_t rowBytes, const Options&) override;
```

## 内部实现细节

### 解码器初始化

`MakeFromEncodedCG` 执行以下初始化流程：

#### 1. 创建 CGDataProvider

```cpp
static SkUniqueCFRef<CGImageSourceRef> data_to_CGImageSrc(const SkData* data) {
    // 创建数据提供者（不拷贝数据）
    SkUniqueCFRef<CGDataProviderRef> cgData(
        CGDataProviderCreateWithData(
            nullptr,              // info 参数
            data->data(),         // 数据指针
            data->size(),         // 数据大小
            nullptr               // 释放回调（由 SkData 管理生命周期）
        )
    );
    if (!cgData) {
        return nullptr;
    }

    // 从数据提供者创建图像源
    return SkUniqueCFRef<CGImageSourceRef>(
        CGImageSourceCreateWithDataProvider(cgData.get(), nullptr)
    );
}
```

**重要设计决策**: 禁用 `cgData` 的内存释放回调，因为 `fData` 字段保持数据生命周期。这实现了零拷贝数据传递。

#### 2. 查询图像属性

```cpp
SkUniqueCFRef<CGImageSourceRef> imageSrc = data_to_CGImageSrc(data.get());
if (!imageSrc) {
    return nullptr;
}

// 拷贝第一帧的属性字典
SkUniqueCFRef<CFDictionaryRef> properties(
    CGImageSourceCopyPropertiesAtIndex(imageSrc.get(), 0, nullptr)
);
if (!properties) {
    return nullptr;
}
```

#### 3. 提取宽度和高度

```cpp
CFNumberRef widthRef = static_cast<CFNumberRef>(
    CFDictionaryGetValue(properties.get(), kCGImagePropertyPixelWidth)
);
CFNumberRef heightRef = static_cast<CFNumberRef>(
    CFDictionaryGetValue(properties.get(), kCGImagePropertyPixelHeight)
);
if (nullptr == widthRef || nullptr == heightRef) {
    return nullptr;
}

int width, height;
if (!CFNumberGetValue(widthRef,  kCFNumberIntType, &width) ||
    !CFNumberGetValue(heightRef, kCFNumberIntType, &height))
{
    return nullptr;
}
```

#### 4. 确定透明度类型

```cpp
bool hasAlpha = bool(CFDictionaryGetValue(properties.get(), kCGImagePropertyHasAlpha));
SkAlphaType alphaType = hasAlpha ? kPremul_SkAlphaType : kOpaque_SkAlphaType;
SkImageInfo info = SkImageInfo::MakeS32(width, height, alphaType);
```

注意：CoreGraphics 不区分预乘和非预乘，Skia 统一使用预乘。

#### 5. 提取 EXIF 方向

```cpp
SkEncodedOrigin origin = kDefault_SkEncodedOrigin;
CFNumberRef orientationRef = static_cast<CFNumberRef>(
    CFDictionaryGetValue(properties.get(), kCGImagePropertyOrientation)
);
int originInt;
if (orientationRef && CFNumberGetValue(orientationRef, kCFNumberIntType, &originInt)) {
    origin = (SkEncodedOrigin)originInt;  // EXIF 方向值直接映射
}
```

EXIF 方向枚举（1-8）：
1. kTopLeft (0°)
2. kTopRight (水平翻转)
3. kBottomRight (180°)
4. kBottomLeft (垂直翻转)
5. kLeftTop (90° CW + 垂直翻转)
6. kRightTop (90° CW)
7. kRightBottom (90° CW + 水平翻转)
8. kLeftBottom (270° CW)

#### 6. 应用方向变换

```cpp
if (SkEncodedOriginSwapsWidthHeight(origin)) {
    info = SkPixmapUtils::SwapWidthHeight(info);  // 旋转 90/270 度时交换宽高
}
```

### 像素解码

`onGetPixels` 方法执行实际解码：

#### 1. 验证请求参数

```cpp
bool ImageGeneratorCG::onGetPixels(const SkImageInfo& info, void* pixels,
                                   size_t rowBytes, const Options&)
{
    // 仅支持 N32 格式（RGBA 或 BGRA，取决于平台字节序）
    if (kN32_SkColorType != info.colorType()) {
        return false;
    }

    // 验证透明度类型
    switch (info.alphaType()) {
        case kOpaque_SkAlphaType:
            if (kOpaque_SkAlphaType != this->getInfo().alphaType()) {
                return false;  // 不能将透明图像作为不透明处理
            }
            break;
        case kPremul_SkAlphaType:
            break;  // 总是接受预乘
        default:
            return false;  // 不支持 kUnpremul 和 kUnknown
    }
```

#### 2. 创建 CGImage

```cpp
SkUniqueCFRef<CGImageRef> image(
    CGImageSourceCreateImageAtIndex(fImageSrc.get(), 0, nullptr)
);
if (!image) {
    return false;
}
```

#### 3. 解码并应用方向

```cpp
SkPixmap dst(info, pixels, rowBytes);

auto decode = [&image](const SkPixmap& pm) {
    // 使用 Skia 提供的 CoreGraphics 像素拷贝工具
    return SkCopyPixelsFromCGImage(pm, image.get());
};

// 应用 EXIF 方向变换
return SkPixmapUtils::Orient(dst, fOrigin, decode);
```

`SkCopyPixelsFromCGImage` 执行以下操作：
1. 创建 CGBitmapContext 指向目标缓冲区
2. 使用 `CGContextDrawImage` 绘制 CGImage
3. CoreGraphics 自动处理色彩空间转换和像素格式转换

### 色彩空间处理

当前实现使用 `SkImageInfo::MakeS32`，即 sRGB 色彩空间。未来可扩展为提取图像的嵌入色彩空间：

```cpp
// FIXME 注释摘录：
// 我们有机会在此提取色彩空间信息，但等到理解如何将其传递给生成器后再实现
```

可能的实现方式：
```cpp
CGColorSpaceRef colorSpace = CGImageGetColorSpace(image.get());
sk_sp<SkColorSpace> skColorSpace = SkMakeColorSpaceFromCGColorSpace(colorSpace);
SkImageInfo info = SkImageInfo::Make(width, height, kN32_SkColorType,
                                      alphaType, skColorSpace);
```

### CoreFoundation 对象管理

使用 RAII 包装器管理 CF 对象生命周期：

```cpp
template<typename T>
class SkUniqueCFRef {
    T fRef;
public:
    SkUniqueCFRef() : fRef(nullptr) {}
    explicit SkUniqueCFRef(T ref) : fRef(ref) {}
    ~SkUniqueCFRef() {
        if (fRef) {
            CFRelease(fRef);  // 自动释放引用
        }
    }

    SkUniqueCFRef(SkUniqueCFRef&& that) : fRef(that.release()) {}
    SkUniqueCFRef& operator=(SkUniqueCFRef&& that) {
        reset(that.release());
        return *this;
    }

    T get() const { return fRef; }
    T release() {
        T ref = fRef;
        fRef = nullptr;
        return ref;
    }
    void reset(T ref) {
        if (fRef) CFRelease(fRef);
        fRef = ref;
    }
};
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| CoreGraphics (macOS/iOS) | 图像创建和渲染 |
| ImageIO (macOS/iOS) | 图像解码和元数据 |
| CoreFoundation | CF 对象管理 |
| `SkUniqueCFRef` | CF 对象 RAII 包装 |
| `SkCGUtils` | CoreGraphics 工具函数 |
| `SkPixmapUtils` | 像素操作和方向变换 |
| `SkEncodedOrigin` | EXIF 方向枚举 |

### 被依赖的模块

该模块通过 SkCodec 框架被 SkImage、SkBitmap 等高层 API 使用，作为 Apple 平台优先的图像解码路径。

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `MakeFromEncodedCG` 静态工厂方法
2. **适配器模式**: 将 ImageIO API 适配到 SkImageGenerator 接口
3. **RAII**: `SkUniqueCFRef` 自动管理 CF 对象生命周期
4. **策略模式**: 通过回调函数实现方向变换策略

### 设计决策

1. **零拷贝数据**: `CGDataProvider` 不拷贝数据，由 `fData` 保持生命周期
2. **第一帧解码**: 仅解码多帧图像的第一帧（如 GIF）
3. **格式限制**: 仅支持 N32 格式输出，简化实现
4. **透明度预乘**: 统一使用预乘 alpha，匹配 CoreGraphics 行为
5. **色彩空间延迟**: 当前使用 sRGB，未来可扩展为提取嵌入色彩空间
6. **Skia 辅助函数**: 使用 `SkCopyPixelsFromCGImage` 而非自己实现像素拷贝
7. **线程安全**: 所有成员变量为 const，支持多线程调用 `getPixels`

### 性能权衡

代码注释指出使用 `SkCopyPixelsFromCGImage` 限制了支持的色彩和透明度类型，但比自己实现像素交换更简单。未来可能的扩展：

```cpp
// FIXME 注释摘录：
// 如果自己实现像素交换，可以添加对以下格式的支持：
//     kUnpremul_SkAlphaType
//     16 位每通道 RGBA
//     kGray_8_SkColorType
// 此外，比较 SkSwizzler 与 CG 内置交换的性能会很有趣
```

## 性能考量

### 性能优势

1. **硬件加速**: ImageIO 可利用 Apple 硬件加速（如 A 系列芯片的图像解码单元）
2. **零拷贝数据**: 数据提供者直接指向 SkData，无额外拷贝
3. **系统优化**: Apple 针对自家平台深度优化的解码器
4. **懒解码**: 仅在 `getPixels` 时创建 CGImage
5. **色彩空间转换**: CoreGraphics 高效的色彩管理

### 内存优化

- **共享数据**: `fData` 引用计数共享原始数据
- **按需解码**: 不预先解码像素
- **CF 引用计数**: 自动管理对象生命周期

### 潜在瓶颈

1. **CGImage 创建**: 每次 `getPixels` 都创建新 CGImage（不缓存）
2. **格式转换**: N32 格式可能需要像素格式转换
3. **元数据查询**: 启动时查询属性字典有一定成本
4. **方向变换**: 某些方向需要旋转和翻转，增加计算

### 优化建议

- 缓存 CGImage（需考虑线程安全）
- 对于频繁解码的图像使用 Bitmap 缓存
- 支持更多原生色彩类型减少转换

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkImageGeneratorCG.h` | 公共接口定义 |
| `src/ports/SkImageGeneratorCG.cpp` | 实现文件（184 行）|
| `src/utils/mac/SkUniqueCFRef.h` | CF 对象 RAII 包装 |
| `include/utils/mac/SkCGUtils.h` | CoreGraphics 工具函数 |
| `src/codec/SkPixmapUtilsPriv.h` | 像素操作工具 |
| `include/codec/SkEncodedOrigin.h` | EXIF 方向枚举 |
| `include/core/SkImageGenerator.h` | 图像生成器抽象基类 |
| Apple CoreGraphics API | 图像渲染框架 |
| Apple ImageIO API | 图像编解码框架 |
