# SkAndroidCodec

> 源文件
> - include/codec/SkAndroidCodec.h
> - src/codec/SkAndroidCodec.cpp

## 概述

SkAndroidCodec 是 Skia 为 Android 平台定制的图像解码抽象层,提供了缩放解码、子区域解码和色彩空间管理等专门针对移动设备优化的功能。它封装了 SkCodec,提供更适合 Android 应用场景的 API,包括高效的采样(sampling)和部分解码能力,以降低内存占用和提升解码性能。

## 架构位置

SkAndroidCodec 位于 codec 模块 (`include/codec` 和 `src/codec`),处于 SkCodec 之上的适配层:

```
SkAndroidCodec (Android API 适配层)
      ↓
SkCodec (通用解码抽象)
      ↓
具体格式解码器 (PNG, JPEG, WEBP等)
```

它通过 `SkSampledCodec` 和 `SkAndroidCodecAdapter` 两种实现策略,为不同图像格式提供统一的 Android 接口。

## 主要类与结构体

### SkAndroidCodec

**继承关系**: `SkNoncopyable` (不可复制)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fInfo` | `const SkImageInfo` | 缓存的图像信息 |
| `fCodec` | `std::unique_ptr<SkCodec>` | 底层解码器 |

### AndroidOptions

**继承关系**: `public SkCodec::Options`

**关键成员变量**:

| 成员变量 | 类型 默认值 | 说明 |
|----------|------------|------|
| `fSampleSize` | `int` (1) | 下采样因子,必须 > 0 |
| `fSubset` | `const SkIRect*` (继承) | 要解码的子区域 |
| `fFrameIndex` | `int` (继承) | 多帧图像的帧索引 |
| `fZeroInitialized` | `ZeroInitialized` (继承) | 内存是否零初始化 |

### ExifOrientationBehavior (已弃用)

```cpp
enum class ExifOrientationBehavior {
    kIgnore,   // 忽略方向信息
    kRespect,  // 遵守方向信息
};
```

**注意**: 该枚举已弃用,SkAndroidCodec 现在忽略 EXIF 方向,由客户端处理。

## 公共 API 函数

### 工厂方法

#### MakeFromCodec

```cpp
static std::unique_ptr<SkAndroidCodec> MakeFromCodec(std::unique_ptr<SkCodec>);
```

**功能**: 从 SkCodec 创建 SkAndroidCodec

**策略选择**:
- PNG, JPEG, ICO, BMP, WBMP → `SkSampledCodec` (支持高效采样)
- GIF, WEBP, DNG, AVIF, HEIF → `SkAndroidCodecAdapter` (内部缩放)

#### MakeFromStream / MakeFromData

```cpp
static std::unique_ptr<SkAndroidCodec> MakeFromStream(
    std::unique_ptr<SkStream>, SkPngChunkReader* = nullptr);

static std::unique_ptr<SkAndroidCodec> MakeFromData(
    sk_sp<const SkData>, SkPngChunkReader* = nullptr);
```

### 信息查询

#### getInfo

```cpp
const SkImageInfo& getInfo() const { return fInfo; }
```

#### getEncodedFormat

```cpp
SkEncodedImageFormat getEncodedFormat() const;
```

#### getICCProfile

```cpp
const skcms_ICCProfile* getICCProfile() const;
```

### 输出参数计算

#### computeOutputColorType

```cpp
SkColorType computeOutputColorType(SkColorType requestedColorType);
```

**功能**: 根据请求的颜色类型和图像特性,计算实际输出的颜色类型

**处理逻辑**:
- 高精度图像(bitsPerComponent > 8)默认使用 `kRGBA_F16_SkColorType`
- 10 位深度图像使用 `kRGBA_1010102_SkColorType`
- 灰度图像保持 `kGray_8_SkColorType`
- 不透明图像支持 `kRGB_565_SkColorType`

#### computeOutputAlphaType

```cpp
SkAlphaType computeOutputAlphaType(bool requestedUnpremul);
```

**功能**: 根据图像是否包含 alpha 通道,确定输出 alpha 类型

#### computeOutputColorSpace

```cpp
sk_sp<SkColorSpace> computeOutputColorSpace(
    SkColorType outputColorType,
    sk_sp<SkColorSpace> prefColorSpace = nullptr);
```

**功能**: 计算输出色彩空间,支持 ICC 配置文件

### 采样与缩放

#### computeSampleSize

```cpp
int computeSampleSize(SkISize* desiredSize) const;
```

**功能**: 计算达到目标尺寸所需的采样大小

**算法**:
1. 如果原始尺寸 ≤ 期望尺寸,返回 1(无缩放)
2. 计算 `sampleX = width/desiredWidth`, `sampleY = height/desiredHeight`
3. 返回 `min(sampleX, sampleY)`
4. 调整 `desiredSize` 为实际能达到的最接近尺寸

**特殊情况**:
- WebP 动画不支持下采样,返回 1
- 搜索最紧密匹配的采样大小

#### getSampledDimensions

```cpp
SkISize getSampledDimensions(int sampleSize) const;
```

**功能**: 返回指定采样大小下的输出尺寸

**计算**:
- 一般情况: `(width/sampleSize, height/sampleSize)`
- 特殊格式可能向上或向下取整

#### getSampledSubsetDimensions

```cpp
SkISize getSampledSubsetDimensions(int sampleSize, const SkIRect& subset) const;
```

**功能**: 计算采样后的子区域尺寸

### 子区域支持

#### getSupportedSubset

```cpp
bool getSupportedSubset(SkIRect* desiredSubset) const;
```

**功能**: 验证并调整子区域为解码器支持的子区域

**约束**:
- 子区域必须在图像边界内
- WebP 要求 top 和 left 为偶数

### 解码

#### getAndroidPixels

```cpp
SkCodec::Result getAndroidPixels(const SkImageInfo& info,
                                 void* pixels,
                                 size_t rowBytes,
                                 const AndroidOptions* options);
```

**功能**: 执行解码,支持采样和子区域

**参数验证**:
- `pixels` 非空
- `rowBytes` ≥ `info.minRowBytes()`
- 子区域有效性检查

**特性**:
- 支持多帧动画的依赖帧处理
- 自动处理 `fRequiredFrame` 递归解码
- 通过 `fPriorFrame` 优化避免重复解码

### Gainmap 支持

#### getGainmapAndroidCodec

```cpp
bool getGainmapAndroidCodec(SkGainmapInfo* outInfo,
                            std::unique_ptr<SkAndroidCodec>* outCodec);
```

**功能**: 提取 HDR gainmap 图像及其参数(用于 Ultra HDR)

## 内部实现细节

### 解码策略分派

```cpp
switch (codec->getEncodedFormat()) {
    case SkEncodedImageFormat::kPNG:
    case SkEncodedImageFormat::kJPEG:
    case SkEncodedImageFormat::kICO:
    case SkEncodedImageFormat::kBMP:
    case SkEncodedImageFormat::kWBMP:
        return std::make_unique<SkSampledCodec>(codec.release());

    case SkEncodedImageFormat::kGIF:
    case SkEncodedImageFormat::kWEBP:
    case SkEncodedImageFormat::kAVIF:
    case SkEncodedImageFormat::kHEIF:
        return std::make_unique<SkAndroidCodecAdapter>(codec.release());

    default:
        return nullptr;  // 不支持的格式
}
```

### 采样大小计算算法

```cpp
// 处理严格大于期望尺寸的情况
if (strictly_bigger_than(computedSize, *desiredSize)) {
    while (true) {
        auto smaller = this->getSampledDimensions(sampleSize + 1);
        if (smaller == *desiredSize) {
            return sampleSize + 1;
        }
        if (smaller == computedSize || smaller_than(smaller, *desiredSize)) {
            *desiredSize = computedSize;
            return sampleSize;
        }
        sampleSize++;
        computedSize = smaller;
    }
}
```

### 多帧动画处理

`getAndroidPixels` 使用 lambda 回调处理依赖帧:

```cpp
auto getPixelsFn = [&](const SkImageInfo& info, void* pixels,
                       size_t rowBytes, const SkCodec::Options& opts,
                       int requiredFrame) -> SkCodec::Result {
    SkAndroidCodec::AndroidOptions prevFrameOptions(
        reinterpret_cast<const SkAndroidCodec::AndroidOptions&>(opts));
    prevFrameOptions.fFrameIndex = requiredFrame;
    return this->getAndroidPixels(info, pixels, rowBytes, &prevFrameOptions);
};
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkCodec | 底层解码抽象 |
| SkSampledCodec | 采样解码实现 |
| SkAndroidCodecAdapter | 适配器实现 |
| SkCodecPriv | 内部工具函数 |
| skcms | 色彩管理 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| Android Framework | 通过 JNI 调用图像解码 |
| BitmapFactory | Android 位图创建 |
| ImageDecoder | Android 10+ 图像解码 API |

## 设计模式与设计决策

### 1. 适配器模式

SkAndroidCodec 是 SkCodec 的适配器,提供 Android 专用接口:
- 简化 API(隐藏不常用功能)
- 增加 Android 特定功能(采样、部分解码)
- 优化内存使用

### 2. 策略模式

根据图像格式选择不同的实现策略:
- `SkSampledCodec`: 解码时采样
- `SkAndroidCodecAdapter`: 后处理缩放

### 3. 工厂方法

静态工厂方法 `MakeFromCodec/Stream/Data` 封装复杂的创建逻辑和策略选择。

### 4. 不可复制设计

继承 `SkNoncopyable` 防止意外复制大型解码器对象。

### 5. RAII 资源管理

使用 `std::unique_ptr` 管理 SkCodec 生命周期。

## 性能考量

### 1. 内存优化

**采样解码**:
- JPEG 支持 1/2, 1/4, 1/8 原生采样
- 避免解码完整图像后再缩放
- 缩略图场景可节省 75%-93% 内存

**部分解码**:
- 仅解码可见区域
- 适用于大图平铺显示

### 2. 缓存策略

```cpp
const SkImageInfo fInfo;  // 缓存图像信息,避免重复查询
```

### 3. 动画优化

通过 `fPriorFrame` 机制避免重复解码:
- 客户端可指定已解码的前序帧
- 跳过不必要的依赖帧解码

### 4. 色彩空间优化

```cpp
if (const auto* colorProfile = fCodec->getEncodedInfo().colorProfile()) {
    return colorProfile->getAndroidOutputColorSpace();
}
return SkColorSpace::MakeSRGB();  // 默认 sRGB
```

避免不必要的色彩空间转换。

### 5. WebP 特殊处理

```cpp
if (is_webp(fCodec.get())) {
    if (fCodec->getFrameCount() > 1) {
        *desiredSize = origDims;  // 动画 WebP 不支持采样
    }
    return 1;
}
```

识别并处理格式限制。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/codec/SkSampledCodec.h` | 实现 | 采样解码实现 |
| `src/codec/SkAndroidCodecAdapter.h` | 实现 | 适配器实现 |
| `include/codec/SkCodec.h` | 依赖 | 底层解码抽象 |
| `src/codec/SkCodecPriv.h` | 依赖 | 内部工具函数 |
| `android/BitmapFactory.cpp` | 使用者 | Android 位图工厂 |
| `android/ImageDecoder.cpp` | 使用者 | Android 图像解码器 |
