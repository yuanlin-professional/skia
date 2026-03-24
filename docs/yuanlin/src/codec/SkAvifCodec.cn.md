# SkAvifCodec

> 源文件: src/codec/SkAvifCodec.h, src/codec/SkAvifCodec.cpp

## 概述

`SkAvifCodec` 是 Skia 中用于解码 AVIF (AV1 Image File Format) 图片格式的解码器。AVIF 是基于 AV1 视频编码的现代图片格式，支持高效压缩、HDR、广色域和动画。该解码器通过集成 libavif 库实现 AVIF 图片的解码功能。

该类继承自 `SkScalingCodec`，支持缩放解码和动画帧管理。它能够处理静态 AVIF 图片和 AVIF 动画序列，提供帧信息查询和逐帧解码能力。

## 架构位置

在 Skia 解码器体系中的位置：

```
SkCodec (基类)
    ↓
SkScalingCodec (支持缩放的解码器)
    ↓
SkAvifCodec (AVIF 解码器)
```

**主要职责**:
- 识别 AVIF 文件格式（通过 ftyp box）
- 解析 AVIF 容器结构
- 管理 libavif 解码器生命周期
- 支持动画帧管理和解码
- 处理 YUV 到 RGB 颜色空间转换
- 支持多种颜色类型（RGBA_8888、BGRA_8888、RGBA_F16）

**格式支持**:
- 静态 AVIF 图片
- AVIF 动画序列（AVIS）
- 8 位和 10+ 位颜色深度
- 有/无 Alpha 通道
- 图片缩放（通过 libavif）

## 主要类与结构体

### SkAvifCodec 类

**继承关系**: `SkAvifCodec → SkScalingCodec → SkCodec → SkRefCnt`

**主要成员变量**:
- `sk_sp<const SkData> fData`: 图片数据（必须在解码器之前声明，确保生命周期）
- `AvifDecoder fAvifDecoder`: libavif 解码器（智能指针包装）
- `bool fUseAnimation`: 是否启用动画支持
- `FrameHolder fFrameHolder`: 帧信息管理器

**自定义删除器**:
```cpp
struct AvifDecoderDeleter {
    void operator()(avifDecoder* decoder) const;
};
using AvifDecoder = std::unique_ptr<avifDecoder, AvifDecoderDeleter>;
```
确保 libavif 解码器正确释放。

### Frame 嵌套类

扩展 `SkFrame`，添加 Alpha 信息：
```cpp
class Frame : public SkFrame {
    Frame(int i, SkEncodedInfo::Alpha alpha);
protected:
    SkEncodedInfo::Alpha onReportedAlpha() const override;
private:
    const SkEncodedInfo::Alpha fReportedAlpha;
};
```

### FrameHolder 嵌套类

管理动画帧集合：
```cpp
class FrameHolder : public SkFrameHolder {
    void setScreenSize(int w, int h);
    Frame* appendNewFrame(bool hasAlpha);
    const Frame* frame(int i) const;
    int size() const;
    void reserve(int size);
private:
    std::vector<Frame> fFrames;
};
```

## 公共 API 函数

### 格式识别

**IsAvif**
```cpp
static bool IsAvif(const void* buffer, size_t bytesRead)
```
检查数据是否为 AVIF 格式：
1. 调用 libavif 的 `avifPeekCompatibleFileType`
2. 如果失败，手动检查文件签名（ftyp box 中的 "avif" 或 "avis"）

**双重检查原因**: libavif 的 peek 功能在 ftyp box 较大时可能失败。

### 解码器创建

**MakeFromStream**
```cpp
static std::unique_ptr<SkCodec> MakeFromStream(std::unique_ptr<SkStream>, Result*)
```
创建 AVIF 解码器的主要流程：

1. **创建 libavif 解码器**
```cpp
AvifDecoder avifDecoder(avifDecoderCreate());
```

2. **配置解码器选项**
```cpp
avifDecoder->ignoreXMP = AVIF_TRUE;           // 忽略 XMP 元数据
avifDecoder->ignoreExif = AVIF_TRUE;          // 忽略 EXIF 元数据
avifDecoder->allowProgressive = AVIF_FALSE;   // 禁用渐进式解码
avifDecoder->allowIncremental = AVIF_FALSE;   // 禁用增量解码
avifDecoder->strictFlags = AVIF_STRICT_DISABLED;  // 宽松模式
avifDecoder->maxThreads = 1;                  // 单线程（TODO: 多线程优化）
```

3. **准备连续内存数据**
- 如果流有内存基址，使用 `SkData::MakeWithoutCopy`
- 否则复制流数据到 `SkData`

4. **解析 AVIF 容器**
```cpp
avifDecoderSetIOMemory(avifDecoder.get(), data->bytes(), data->size());
avifDecoderParse(avifDecoder.get());
```

5. **提取编码信息**
- 颜色类型：根据 `alphaPresent` 确定 RGB 或 RGBA
- 位深度：根据 `image->depth` 确定 8 位或 16 位
- 动画检测：`imageCount > 1` 表示动画

6. **创建编解码器对象**
```cpp
return std::unique_ptr<SkCodec>(new SkAvifCodec(...));
```

## 重写的基类方法

### 格式信息

**onGetEncodedFormat**
```cpp
SkEncodedImageFormat onGetEncodedFormat() const override
```
返回 `SkEncodedImageFormat::kAVIF`。

### 动画支持

**onGetFrameCount**
```cpp
int onGetFrameCount() override
```
返回帧数：
- 非动画模式返回 1
- 首次调用时初始化 `fFrameHolder`，为每一帧创建 `Frame` 对象并填充时序信息

**onGetFrameInfo**
```cpp
bool onGetFrameInfo(int i, FrameInfo* frameInfo) const override
```
获取指定帧的信息（尺寸、持续时间、Alpha、处置方法等）。

**onGetRepetitionCount**
```cpp
int onGetRepetitionCount() override
```
返回 `kRepetitionCountInfinite`（无限循环）。

**onIsAnimated**
```cpp
IsAnimated onIsAnimated() override
```
根据 `fUseAnimation` 和 `imageCount` 判断是否为动画。

### 像素解码

**onGetPixels**
```cpp
Result onGetPixels(const SkImageInfo& dstInfo, void* dst, size_t dstRowBytes,
                   const Options& options, int* rowsDecoded) override
```

解码流程：

1. **验证参数**
- 不支持子区域解码（返回 `kUnimplemented`）
- 仅支持 RGBA_8888、BGRA_8888、RGBA_F16 颜色类型

2. **解码指定帧**
```cpp
avifDecoderNthImage(fAvifDecoder.get(), options.fFrameIndex);
```

3. **缩放图片（如需要）**
```cpp
if (this->dimensions() != dstInfo.dimensions()) {
    avifImageScale(fAvifDecoder->image, dstInfo.width(), dstInfo.height(), ...);
}
```

4. **配置 RGB 输出格式**
```cpp
avifRGBImage rgbImage;
avifRGBImageSetDefaults(&rgbImage, fAvifDecoder->image);
rgbImage.pixels = static_cast<uint8_t*>(dst);
rgbImage.rowBytes = dstRowBytes;
```

根据目标颜色类型设置：
- `kRGBA_8888_SkColorType`: 8 位 RGBA
- `kBGRA_8888_SkColorType`: 8 位 BGRA（设置 `AVIF_RGB_FORMAT_BGRA`）
- `kRGBA_F16_SkColorType`: 16 位浮点 RGBA（设置 `isFloat = AVIF_TRUE`）

5. **YUV 到 RGB 转换**
```cpp
avifImageYUVToRGB(fAvifDecoder->image, &rgbImage);
```

AVIF 内部使用 YUV 色彩空间，需要转换为 RGB。使用 `AVIF_CHROMA_UPSAMPLING_FASTEST` 模式以提高性能。

## 内部实现细节

### 内存管理策略

**数据生命周期顺序至关重要**:
```cpp
sk_sp<const SkData> fData;  // 必须在解码器之前声明
AvifDecoder fAvifDecoder;   // 依赖 fData
```

libavif 解码器持有 `fData` 的指针，必须确保 `fData` 在解码器之后销毁。C++ 成员变量按声明顺序析构（逆序），因此先声明的 `fData` 后析构。

### 帧信息初始化

首次调用 `onGetFrameCount` 时延迟初始化帧信息：
```cpp
for (int i = 0; i < fAvifDecoder->imageCount; i++) {
    Frame* frame = fFrameHolder.appendNewFrame(alphaPresent);
    frame->setXYWH(0, 0, width, height);
    frame->setDisposalMethod(SkCodecAnimation::DisposalMethod::kKeep);
    avifImageTiming timing;
    avifDecoderNthImageTiming(fAvifDecoder.get(), i, &timing);
    frame->setDuration(timing.duration * 1000);  // 转换为毫秒
    frame->setRequiredFrame(SkCodec::kNoFrame);
    frame->setHasAlpha(alphaPresent);
}
```

**设计特点**:
- 延迟初始化：避免不需要动画信息时的开销
- 完整遍历：一次性初始化所有帧
- 独立帧：每帧都标记为不依赖其他帧（`kNoFrame`）

### 色度上采样策略

使用 `AVIF_CHROMA_UPSAMPLING_FASTEST`：
- AVIF 通常使用 4:2:0 或 4:2:2 色度子采样
- 需要上采样到 4:4:4 以转换为 RGB
- "FASTEST" 模式使用简单的双线性插值，牺牲一些质量换取速度

## 依赖关系

### 直接依赖
- **SkScalingCodec**: 父类，提供缩放功能
- **libavif**: 第三方库，AVIF 解码核心
- **SkFrameHolder**: 动画帧管理基类
- **SkData**: 数据容器
- **SkStream**: 数据流接口
- **skcms**: 颜色管理（像素格式定义）

### 被依赖
- **SkAvifDecoder**: 公共 API 命名空间
- **SkCodec**: 通过工厂方法注册
- **Skia 解码器系统**: 自动识别和使用

## 设计模式与设计决策

### RAII 与自定义删除器

使用自定义删除器管理 C 库资源：
```cpp
void AvifDecoderDeleter::operator()(avifDecoder* decoder) const {
    if (decoder != nullptr) {
        avifDecoderDestroy(decoder);
    }
}
```

确保异常安全和资源正确释放。

### 适配器模式

将 libavif C API 适配为 Skia C++ 接口：
- 封装 libavif 的复杂性
- 提供 Skia 风格的 API
- 隔离第三方库依赖

### 延迟初始化

动画帧信息延迟到首次访问时初始化：
- 静态图片无开销
- 减少解码器创建时间
- 按需分配内存

### 配置策略

解码器配置采用保守策略：
- 禁用渐进式和增量解码（简化实现）
- 单线程模式（TODO: 后续优化）
- 忽略元数据（减少内存和处理时间）
- 宽松模式（提高兼容性）

## 性能考量

### 内存效率

**连续内存需求**: libavif 要求连续内存块
- 优先使用零拷贝（`MakeWithoutCopy`）
- 必要时才复制（流不支持内存基址）

**帧信息缓存**: 一次性解析所有帧信息
- 避免重复调用 libavif API
- 预分配 `std::vector` 减少动态分配

### 解码性能

**色度上采样**: 使用最快模式
- 对于大多数用途足够
- 可在未来添加质量选项

**单线程限制**: 当前强制单线程
- TODO 注释表明计划支持多线程
- 应根据 CPU 核心数动态调整

**缩放优化**: 利用 libavif 的内置缩放
- 在解码前缩放，减少解码开销
- 比先解码再缩放更高效

### 颜色转换

YUV 到 RGB 转换性能：
- libavif 内部使用 SIMD 优化
- 支持多种输出格式减少后续转换
- F16 支持允许 HDR 工作流

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/codec/SkScalingCodec.h` | 父类 | 支持缩放的解码器基类 |
| `src/codec/SkFrameHolder.h` | 基类 | 动画帧管理基类 |
| `include/codec/SkAvifDecoder.h` | 公共 API | 公开的 AVIF 解码器接口 |
| `include/codec/SkCodec.h` | 基类 | 所有解码器的基类 |
| `avif/avif.h` | 依赖 | libavif 第三方库 |
| `include/core/SkData.h` | 依赖 | 数据容器 |
| `include/core/SkStream.h` | 依赖 | 数据流接口 |
| `src/codec/SkCodecPriv.h` | 工具 | 内部工具函数 |
