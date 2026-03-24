# SkCodec

> 源文件
> - include/codec/SkCodec.h
> - src/codec/SkCodec.cpp

## 概述

SkCodec 是 Skia 图形库中的核心图像解码抽象层,定义了统一的接口用于解码各种图像格式(PNG、JPEG、WebP、GIF、AVIF 等)。它提供了完整的解码功能,包括完整图像解码、增量解码、扫描线解码、多帧动画支持、YUV 解码、色彩空间管理等。SkCodec 采用可扩展的注册机制,允许运行时添加新的图像格式解码器。

## 架构位置

SkCodec 位于 codec 模块的核心位置:

```
应用层 API
    ↓
SkAndroidCodec (Android 适配层)
    ↓
SkCodec (抽象解码接口) ← 本文档
    ↓
具体格式实现:
  ├─ SkPngCodec
  ├─ SkJpegCodec
  ├─ SkWebpCodec
  ├─ SkGifCodec
  ├─ SkAvifCodec
  └─ ...
```

## 主要类与结构体

### SkCodec

**继承关系**: `SkNoncopyable` (不可复制)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fEncodedInfo` | `const SkEncodedInfo` | 编码信息(宽高、色彩类型等) |
| `fSrcXformFormat` | `XformFormat` | 源数据格式 |
| `fStream` | `std::unique_ptr<SkStream>` | 输入流 |
| `fOrigin` | `const SkEncodedOrigin` | EXIF 方向 |
| `fDstInfo` | `SkImageInfo` | 目标图像信息 |
| `fOptions` | `Options` | 解码选项 |
| `fCurrScanline` | `int` | 当前扫描线索引 |
| `fNeedsRewind` | `bool` | 是否需要重置流 |
| `fXformTime` | `XformTime` | 色彩转换时机 |
| `fDecodeBudget` | `size_t` | 内存预算 |

### Result 枚举

| 值 | 说明 |
|----|------|
| `kSuccess` | 成功 |
| `kIncompleteInput` | 输入不完整,生成了部分图像 |
| `kErrorInInput` | 输入有错误,无法继续解码 |
| `kInvalidConversion` | 无法转换到请求的格式 |
| `kInvalidScale` | 无法缩放到请求的尺寸 |
| `kInvalidParameters` | 参数无效 |
| `kInvalidInput` | 输入不包含有效图像 |
| `kCouldNotRewind` | 无法重置流 |
| `kInternalError` | 内部错误(如 OOM) |
| `kUnimplemented` | 方法未实现 |
| `kOutOfMemory` | 内存预算超出 |

### Options 结构体

| 成员变量 | 类型 | 默认值 | 说明 |
|----------|------|--------|------|
| `fZeroInitialized` | `ZeroInitialized` | `kNo_ZeroInitialized` | 内存是否零初始化 |
| `fSubset` | `const SkIRect*` | `nullptr` | 子区域 |
| `fFrameIndex` | `int` | `0` | 帧索引 |
| `fPriorFrame` | `int` | `kNoFrame` | 前序帧索引 |
| `fMaxDecodeMemory` | `size_t` | `0` | 最大解码内存 |

### FrameInfo 结构体

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fRequiredFrame` | `int` | 依赖的前序帧索引 |
| `fDuration` | `int` | 显示时长(毫秒) |
| `fFullyReceived` | `bool` | 是否完全接收 |
| `fAlphaType` | `SkAlphaType` | Alpha 类型 |
| `fHasAlphaWithinBounds` | `bool` | 边界内是否有 alpha |
| `fDisposalMethod` | `DisposalMethod` | 处置方法 |
| `fBlend` | `Blend` | 混合模式 |
| `fFrameRect` | `SkIRect` | 帧矩形区域 |

### SelectionPolicy 枚举

```cpp
enum class SelectionPolicy {
    kPreferStillImage,   // 优先静态图像
    kPreferAnimation,    // 优先动画序列
};
```

用于容器格式(如 HEIF)同时包含静止图像和动画序列时的选择策略。

### SkScanlineOrder 枚举

```cpp
enum SkScanlineOrder {
    kTopDown_SkScanlineOrder,   // 从上到下
    kBottomUp_SkScanlineOrder,  // 从下到上(倒置 BMP)
};
```

### IsAnimated 枚举

```cpp
enum class IsAnimated {
    kYes,      // 确定是动画
    kNo,       // 确定不是动画
    kUnknown,  // 未知(输入不完整)
};
```

## 公共 API 函数

### 工厂方法

#### MakeFromStream

```cpp
static std::unique_ptr<SkCodec> MakeFromStream(
    std::unique_ptr<SkStream>,
    SkSpan<const SkCodecs::Decoder> decoders,
    Result* = nullptr,
    SkPngChunkReader* = nullptr,
    SelectionPolicy selectionPolicy = SelectionPolicy::kPreferStillImage);
```

**功能**: 从输入流创建解码器

**流程**:
1. Peek 或 read MinBufferedBytesNeeded() (32字节)
2. 遍历注册的解码器,调用 `isFormat()` 识别格式
3. 调用对应解码器的 `makeFromStream()` 创建实例

**特殊处理**:
- PNG: 传递 `SkPngChunkReader`
- HEIF/GIF: 传递 `SelectionPolicy`
- RAW: 作为兜底解码器

#### MakeFromData

```cpp
static std::unique_ptr<SkCodec> MakeFromData(
    sk_sp<const SkData>,
    SkSpan<const SkCodecs::Decoder> decoders,
    SkPngChunkReader* = nullptr);
```

### 信息查询

#### getInfo

```cpp
SkImageInfo getInfo() const { return fEncodedInfo.makeImageInfo(); }
```

#### dimensions / bounds

```cpp
SkISize dimensions() const;
SkIRect bounds() const;
```

#### getOrigin

```cpp
SkEncodedOrigin getOrigin() const { return fOrigin; }
```

返回 EXIF 方向信息。

#### getICCProfile

```cpp
const skcms_ICCProfile* getICCProfile() const;
```

#### getHdrMetadata

```cpp
const skhdr::Metadata& getHdrMetadata() const;
```

返回 HDR 元数据(如 MaxCLL、MaxFALL)。

#### hasHighBitDepthEncodedData

```cpp
bool hasHighBitDepthEncodedData() const;
```

返回是否使用 16+ 位编码。

#### getEncodedFormat

```cpp
SkEncodedImageFormat getEncodedFormat() const;
```

### 缩放支持

#### getScaledDimensions

```cpp
SkISize getScaledDimensions(float desiredScale) const;
```

**功能**: 返回接近目标缩放比例的尺寸

**约束**:
- `desiredScale` > 0
- 不支持放大(≥1.0 返回原始尺寸)
- 格式相关(JPEG 支持 1/2, 1/4, 1/8)

#### getValidSubset

```cpp
bool getValidSubset(SkIRect* desiredSubset) const;
```

验证并调整子区域为解码器支持的区域。

### 完整图像解码

#### getPixels

```cpp
Result getPixels(const SkImageInfo& info, void* pixels,
                 size_t rowBytes, const Options* options = nullptr);
```

**功能**: 解码完整图像到指定内存

**参数**:
- `info`: 目标图像信息(可以与原始尺寸不同,请求缩放)
- `pixels`: 输出缓冲区
- `rowBytes`: 行字节数(≥ `info.minRowBytes()`)
- `options`: 解码选项

**返回值**: `Result` 枚举

**处理流程**:
1. 验证参数
2. 处理子区域请求
3. 调用 `handleFrameIndex()` 处理多帧依赖
4. 检查尺寸支持
5. 调用 `onGetPixels()` (子类实现)
6. 不完整解码时填充未初始化内存

#### getImage

```cpp
std::tuple<sk_sp<SkImage>, Result> getImage(
    const SkImageInfo& info, const Options* opts = nullptr);
```

**功能**: 解码为 SkImage 对象,自动处理 EXIF 方向旋转

**优势**:
- 自动内存管理
- 自动处理图像旋转
- 返回不可变对象

### 增量解码

#### startIncrementalDecode

```cpp
Result startIncrementalDecode(const SkImageInfo& dstInfo,
                              void* dst, size_t rowBytes,
                              const Options* options);
```

**功能**: 开始增量解码(用于渐进式图像)

#### incrementalDecode

```cpp
Result incrementalDecode(int* rowsDecoded = nullptr);
```

**功能**: 继续增量解码

**返回值**:
- `kSuccess`: 完成
- `kIncompleteInput`: 需要更多数据

**用途**: 网络图像流式加载,边下载边显示。

### 扫描线解码

#### startScanlineDecode

```cpp
Result startScanlineDecode(const SkImageInfo& dstInfo,
                           const Options* options = nullptr);
```

**功能**: 开始扫描线解码模式

**限制**:
- 仅支持 `fFrameIndex = 0`
- 子区域仅支持 X 方向(top=0, height=全高)

#### getScanlines

```cpp
int getScanlines(void* dst, int countLines, size_t rowBytes);
```

**功能**: 获取指定数量的扫描线

**返回值**: 实际解码的行数

#### skipScanlines

```cpp
bool skipScanlines(int countLines);
```

**功能**: 跳过扫描线(避免解码不需要的行)

#### getScanlineOrder

```cpp
SkScanlineOrder getScanlineOrder() const;
```

**功能**: 获取扫描线顺序

#### nextScanline / outputScanline

```cpp
int nextScanline() const;
int outputScanline(int inputScanline) const;
```

**功能**: 扫描线索引转换(处理倒置 BMP 等)

### YUV 解码

#### queryYUVAInfo

```cpp
bool queryYUVAInfo(
    const SkYUVAPixmapInfo::SupportedDataTypes& supportedDataTypes,
    SkYUVAPixmapInfo* yuvaPixmapInfo) const;
```

**功能**: 查询是否支持 YUV(A) 解码

#### getYUVAPlanes

```cpp
Result getYUVAPlanes(const SkYUVAPixmaps& yuvaPixmaps);
```

**功能**: 解码为 YUV 平面(用于硬件加速视频)

### 多帧动画

#### getFrameCount

```cpp
int getFrameCount();
```

**功能**: 返回帧数量

**注意**: 不完整输入可能返回临时值,后续可能增加。

#### getFrameInfo

```cpp
bool getFrameInfo(int index, FrameInfo* info) const;
std::vector<FrameInfo> getFrameInfo();
```

**功能**: 获取帧信息

#### getRepetitionCount

```cpp
int getRepetitionCount();
```

**功能**: 返回重复次数
- `kRepetitionCountInfinite` (-1): 无限循环
- `0`: 不重复(播放一次)
- `n`: 重复 n 次(总共播放 n+1 次)

#### isAnimated

```cpp
IsAnimated isAnimated();
```

**功能**: 判断是否为动画

**区别 getFrameCount**:
- 部分输入时 `getFrameCount()` 可能临时返回 1
- `isAnimated()` 可能返回 `kUnknown` 或确定的 `kYes`

### 解码器注册

#### Register

```cpp
static void Register(
    bool (*peek)(const void*, size_t),
    std::unique_ptr<SkCodec> (*make)(std::unique_ptr<SkStream>, Result*));
```

**功能**: 运行时注册新的解码器

**注意**: 非线程安全,需在首次解码前完成。

## 内部实现细节

### 解码器注册与识别

```cpp
// 全局解码器列表
static std::vector<Decoder>* get_decoders_for_editing() {
    static SkNoDestructor<std::vector<Decoder>> decoders;
    // 自动注册内置解码器(PNG, JPEG, WEBP等)
    return decoders.get();
}

// 格式识别
for (const SkCodecs::Decoder& proc : decoders) {
    if (proc.isFormat(buffer, bytesRead)) {
        return proc.makeFromStream(std::move(stream), outResult, ...);
    }
}
```

### 色彩空间转换

#### initializeColorXform

```cpp
bool initializeColorXform(const SkImageInfo& dstInfo,
                         SkEncodedInfo::Alpha encodedAlpha,
                         bool srcIsOpaque);
```

**功能**: 初始化色彩转换管线

**决策逻辑**:
1. 检查是否需要转换(源/目标 profile 不同)
2. 确定转换时机(`kPalette_XformTime` / `kDecodeRow_XformTime`)
3. 设置 alpha 预乘格式

#### applyColorXform

```cpp
void applyColorXform(void* dst, const void* src, int count) const;
```

**功能**: 执行色彩转换(使用 skcms_Transform)

### 多帧动画依赖处理

#### handleFrameIndex

```cpp
Result handleFrameIndex(const SkImageInfo&, void* pixels,
                       size_t rowBytes, const Options&,
                       GetPixelsCallback = nullptr);
```

**功能**: 处理帧依赖关系

**算法** (参考 `SkFrameHolder::setAlphaAndRequiredFrame`):

依赖帧确定的条件序列:
- **IND1**: 第一帧 → `kNoFrame`
- **IND2**: 填充整个画布且不透明或覆盖模式 → `kNoFrame`
- **IND3**: 所有前序帧都是 `kRestorePrevious` → `kNoFrame`
- **IND4**: 前一帧是 `kRestoreBGColor` 且填充整个画布 → `kNoFrame`
- **DEP5**: 当前帧有 alpha 且使用 blend 模式 → 依赖前一帧
- **IND6**: 当前帧矩形覆盖所有前序帧到最近独立帧 → `kNoFrame`
- **DEP7**: 其他情况 → 依赖前一帧

**递归解码**:
```cpp
if (requiredFrame != kNoFrame) {
    prevFrameOptions.fFrameIndex = requiredFrame;
    result = this->getPixels(info, pixels, rowBytes, &prevFrameOptions);
}
```

### 不完整输入处理

#### fillIncompleteImage

```cpp
void fillIncompleteImage(const SkImageInfo& dstInfo, void* dst,
                        size_t rowBytes, ZeroInitialized zeroInit,
                        int linesRequested, int linesDecoded);
```

**功能**: 填充未解码的行(默认值)

**策略**:
- 如果内存已零初始化(`kYes_ZeroInitialized`),跳过填充
- 使用 `SkSampler::Fill()` 填充背景色

### 内存预算控制

#### allocateFromBudget

```cpp
bool allocateFromBudget(size_t numBytes);
```

**功能**: 检查并扣除内存预算

**用途**: 防止解码超大图像导致 OOM。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkEncodedInfo | 编码信息 |
| SkImageInfo | 图像信息 |
| SkColorSpace | 色彩空间 |
| SkStream | 输入流 |
| skcms | 色彩管理(ICC profile) |
| SkFrameHolder | 多帧动画管理 |
| SkSampler | 扫描线采样 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| SkAndroidCodec | Android 适配层 |
| SkImage 工厂 | `SkImages::DeferredFromCodec` |
| Blink/Chromium | 浏览器图像解码 |
| Android Framework | BitmapFactory |
| Flutter | 图像加载 |

## 设计模式与设计决策

### 1. 模板方法模式

SkCodec 定义解码流程,具体格式实现虚函数:

```cpp
virtual Result onGetPixels(...) = 0;        // 纯虚函数
virtual bool onQueryYUVAInfo(...) { return false; }  // 可选功能
```

### 2. 策略模式

色彩转换时机策略:
- `kPalette_XformTime`: 转换调色板(索引色)
- `kDecodeRow_XformTime`: 逐行解码时转换
- `kNo_XformTime`: 无需转换

### 3. 工厂模式 + 注册表

全局解码器注册表支持运行时扩展:

```cpp
SkCodecs::Register({
    .id = "custom",
    .isFormat = MyCodec::IsFormat,
    .makeFromStream = MyCodec::Make
});
```

### 4. 资源获取即初始化 (RAII)

流和内存由 `std::unique_ptr` 管理。

### 5. 状态机模式

解码状态跟踪:
- `fNeedsRewind`: 是否需要重置
- `fCurrScanline`: 当前扫描线
- `fStartedIncrementalDecode`: 增量解码状态

### 6. 组合优于继承

SkCodec 包含 SkStream 而非继承。

## 性能考量

### 1. 延迟加载

仅在需要时读取元数据和帧信息:

```cpp
int getFrameCount() {
    return this->onGetFrameCount();  // 可能触发读取
}
```

### 2. 零拷贝优化

```cpp
sk_sp<const SkData> getEncodedData() const {
    return fStream->getData();  // 尝试零拷贝
}
```

### 3. 采样解码

JPEG 原生支持 DCT 域采样,避免完整解码:

```cpp
// JPEG 1/8 采样仅解码 1/64 的 DCT 系数
SkISize getScaledDimensions(0.125f);
```

### 4. 增量解码

适用于网络图像:
- 边下载边解码
- 渐进式显示(PNG/JPEG interlaced)

### 5. YUV 解码

直接输出 YUV 平面,避免 RGB 转换:
- 节省内存(YUV420 比 RGBA 节省 50%)
- 适合视频硬件加速

### 6. 缓存优化

```cpp
fEncodedInfo  // 缓存编码信息
fDstInfo      // 缓存目标信息
```

### 7. 扫描线解码

支持跳过不需要的行:

```cpp
startScanlineDecode(info);
skipScanlines(100);  // 跳过前100行
getScanlines(dst, 50, rowBytes);  // 仅解码50行
```

### 8. 内存预算

```cpp
Options opts;
opts.fMaxDecodeMemory = 100 * 1024 * 1024;  // 100MB 限制
```

防止超大图像 OOM。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/codec/SkAndroidCodec.h` | 使用者 | Android 适配层 |
| `src/codec/SkPngCodec.h` | 子类 | PNG 解码器 |
| `src/codec/SkJpegCodec.h` | 子类 | JPEG 解码器 |
| `src/codec/SkWebpCodec.h` | 子类 | WebP 解码器 |
| `src/codec/SkGifCodec.h` | 子类 | GIF 解码器 |
| `src/codec/SkAvifCodec.h` | 子类 | AVIF 解码器 |
| `src/codec/SkCodecPriv.h` | 依赖 | 内部工具 |
| `src/codec/SkFrameHolder.h` | 依赖 | 动画帧管理 |
| `src/codec/SkSampler.h` | 依赖 | 扫描线采样 |
| `modules/skcms/skcms.h` | 依赖 | 色彩管理 |
| `include/core/SkImageInfo.h` | 依赖 | 图像信息 |
| `include/core/SkColorSpace.h` | 依赖 | 色彩空间 |
