# SkWebpDecoder

> 源文件: `include/codec/SkWebpDecoder.h`

## 概述

SkWebpDecoder 命名空间提供了 WebP 图像格式的解码功能。WebP 是 Google 开发的现代图像格式,在相同质量下比 JPEG 和 PNG 文件更小,支持有损和无损压缩、透明度和动画。该模块是 Skia 模块化图像解码架构的一部分,将 WebP 特定的解码逻辑封装在独立的命名空间中。

## 架构位置

SkWebpDecoder 位于 Skia 图像编解码子系统的格式特定层,属于 WebP 解码模块。它依赖 Google 的 libwebp 库进行实际的 WebP 解析和解码。该模块实现了 SkCodec 的工厂接口,通过标准的解码器注册机制与 Skia 核心集成,是连接 Skia 和 libwebp 的适配层。

## 主要函数

### 格式检测

#### `SK_API bool IsWebp(const void*, size_t)`

**功能**: 检查给定的字节序列是否为 WebP 图像

**参数**:
- 第一个参数: 指向数据缓冲区的指针
- 第二个参数: 缓冲区大小(字节)

**返回值**:
- `true`: 数据符合 WebP 文件头特征
- `false`: 不是有效的 WebP 数据

**检测机制**:
WebP 文件使用 RIFF 容器格式,具有特定的魔数:
```
偏移 0-3:  "RIFF" (0x52 0x49 0x46 0x46)
偏移 4-7:  文件大小 - 8
偏移 8-11: "WEBP" (0x57 0x45 0x42 0x50)
```

**最小检测大小**: 至少需要 12 字节才能可靠检测

**使用场景**:
- 快速格式验证
- 多格式自动识别
- 避免无效解码尝试

**性能**: 非常快,仅检查前 12 字节

### 解码器创建

#### `SK_API std::unique_ptr<SkCodec> Decode(std::unique_ptr<SkStream>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从流中解码 WebP 图像

**参数**:
- `stream`: 唯一指针,指向包含 WebP 数据的输入流
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 被忽略(WebP 解码不使用上下文)

**返回值**:
- 成功: 返回 SkCodec 智能指针
- 失败: 返回 nullptr,同时设置 result 参数

**result 可能的值**:
- `SkCodec::kSuccess`: 成功创建解码器
- `SkCodec::kInvalidInput`: 不是有效的 WebP
- `SkCodec::kUnimplemented`: 不支持的 WebP 特性
- `SkCodec::kInternalError`: libwebp 内部错误

**支持的 WebP 特性**:
- 有损压缩(VP8 编码)
- 无损压缩(VP8L 编码)
- Alpha 透明通道
- 简单动画(部分支持,取决于 SkCodec 配置)
- EXIF/XMP 元数据

#### `SK_API std::unique_ptr<SkCodec> Decode(sk_sp<const SkData>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从内存数据中解码 WebP 图像

**参数**:
- `data`: 智能指针,指向包含 WebP 数据的内存块
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 被忽略

**返回值**: 同流版本

**使用场景**:
- 数据已完全加载到内存
- 网络请求响应数据
- 嵌入式资源

**性能**: 比流版本稍快,因为数据连续且可随机访问

#### `inline std::unique_ptr<SkCodec> Decode(sk_sp<SkData>, SkCodec::Result*, SkCodecs::DecodeContext)` (待移除)

**功能**: 兼容旧 API 的重载版本

**状态**: 标记为 "TODO: remove after client migration"

**说明**: 接受非 const SkData,内部转换为 const 版本

### 解码器描述符

#### `inline constexpr SkCodecs::Decoder Decoder()`

**功能**: 返回 WebP 解码器的描述符,用于注册到解码器系统

**返回值**: SkCodecs::Decoder 结构体,包含:
- `name`: "webp"(格式名称)
- `probe`: IsWebp(格式检测函数)
- `decode`: Decode(解码函数)

**使用场景**:
```cpp
// 注册 WebP 解码器
SkCodecs::Register(SkWebpDecoder::Decoder());

// 之后可以通过通用接口解码 WebP
std::unique_ptr<SkCodec> codec = SkCodecs::Decode(stream, &result);
```

## 使用示例

### 示例 1: 基础解码

```cpp
#include "include/codec/SkWebpDecoder.h"
#include "include/core/SkBitmap.h"
#include "include/core/SkStream.h"

bool decodeWebpFile(const char* path, SkBitmap* bitmap) {
    // 打开文件流
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    // 创建解码器
    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkWebpDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        printf("Failed to decode WebP: %d\n", result);
        return false;
    }

    // 分配位图
    SkImageInfo info = codec->getInfo();
    if (!bitmap->tryAllocPixels(info)) {
        return false;
    }

    // 解码像素
    result = codec->getPixels(info, bitmap->getPixels(),
                              bitmap->rowBytes());
    return result == SkCodec::kSuccess;
}
```

### 示例 2: 检测和解码

```cpp
bool loadImageSmart(const char* path, SkBitmap* bitmap) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    // 读取文件头进行检测
    uint8_t header[12];
    if (stream->peek(header, 12) < 12) {
        return false;
    }

    // 检查是否为 WebP
    if (SkWebpDecoder::IsWebp(header, 12)) {
        printf("Detected WebP format\n");
        SkCodec::Result result;
        auto codec = SkWebpDecoder::Decode(std::move(stream), &result);
        if (codec) {
            return codec->getPixels(codec->getInfo(),
                                   bitmap->getPixels(),
                                   bitmap->rowBytes()) == SkCodec::kSuccess;
        }
    }

    // 尝试其他格式...
    return false;
}
```

### 示例 3: 获取图像信息

```cpp
struct WebpInfo {
    int width;
    int height;
    bool hasAlpha;
    SkColorType colorType;
    size_t fileSize;
};

bool getWebpInfo(const char* path, WebpInfo* info) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    // 获取文件大小
    info->fileSize = stream->getLength();

    // 创建解码器
    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkWebpDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        return false;
    }

    // 提取信息
    SkImageInfo imageInfo = codec->getInfo();
    info->width = imageInfo.width();
    info->height = imageInfo.height();
    info->hasAlpha = imageInfo.alphaType() != kOpaque_SkAlphaType;
    info->colorType = imageInfo.colorType();

    return true;
}
```

### 示例 4: 缩放解码

```cpp
bool decodeWebpScaled(const char* path, SkBitmap* bitmap,
                      int maxDimension) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkWebpDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        return false;
    }

    // 计算缩放比例
    SkImageInfo fullInfo = codec->getInfo();
    float scale = std::min(
        (float)maxDimension / fullInfo.width(),
        (float)maxDimension / fullInfo.height()
    );

    if (scale >= 1.0f) {
        scale = 1.0f; // 不放大
    }

    // 计算目标尺寸
    int dstWidth = (int)(fullInfo.width() * scale);
    int dstHeight = (int)(fullInfo.height() * scale);
    SkImageInfo dstInfo = fullInfo.makeWH(dstWidth, dstHeight);

    // 分配和解码
    if (!bitmap->tryAllocPixels(dstInfo)) {
        return false;
    }

    result = codec->getPixels(dstInfo, bitmap->getPixels(),
                              bitmap->rowBytes());
    return result == SkCodec::kSuccess;
}
```

### 示例 5: 内存数据解码

```cpp
bool decodeWebpFromMemory(const std::vector<uint8_t>& data,
                         SkBitmap* bitmap) {
    // 创建 SkData
    sk_sp<SkData> skData = SkData::MakeWithCopy(
        data.data(), data.size());

    // 解码
    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkWebpDecoder::Decode(skData, &result);
    if (!codec) {
        return false;
    }

    SkImageInfo info = codec->getInfo();
    if (!bitmap->tryAllocPixels(info)) {
        return false;
    }

    result = codec->getPixels(info, bitmap->getPixels(),
                              bitmap->rowBytes());
    return result == SkCodec::kSuccess;
}
```

## 内部实现细节

### WebP 格式结构

**RIFF 容器**:
```
"RIFF" [文件大小] "WEBP"
  [块1] [块2] [块3] ...
```

**主要块类型**:
- **VP8**: 有损图像数据
- **VP8L**: 无损图像数据
- **VP8X**: 扩展特性(Alpha、动画、EXIF 等)
- **ALPH**: Alpha 通道数据
- **ANIM**: 动画参数
- **ANMF**: 动画帧
- **ICCP**: ICC 颜色配置文件
- **EXIF**: EXIF 元数据
- **XMP**: XMP 元数据

### libwebp 集成

SkWebpDecoder 依赖 libwebp:
- **WebPGetInfo**: 获取图像尺寸
- **WebPDecode**: 解码到 RGBA/BGRA
- **WebPDecodeYUV**: 解码到 YUV(可选)
- **WebPGetFeatures**: 查询图像特性

Skia 的职责:
- 提供统一的 SkCodec 接口
- 管理内存和错误处理
- 颜色空间转换
- 像素格式适配

### 颜色格式支持

libwebp 输出格式:
- RGB/BGR
- RGBA/BGRA
- ARGB/ABGR
- YUV(高级用法)

Skia 转换:
- 根据 SkImageInfo 选择最佳输出格式
- 自动处理字节序差异
- 支持预乘/非预乘 Alpha

### 性能优化

**渐进式解码**:
WebP 不原生支持渐进式,但 Skia 可以:
- 使用逐行解码接口
- 实现增量渲染

**硬件加速**:
某些平台提供 WebP 硬件解码:
- Android: MediaCodec
- iOS: 第三方库
- 桌面: libwebp 优化版本

**SIMD 优化**:
libwebp 内置 SIMD 优化:
- SSE2/AVX2(x86)
- NEON(ARM)
- 自动检测和启用

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkCodec.h | 解码器基类和接口 |
| SkRefCnt.h | 智能指针和引用计数 |
| SkAPI.h | API 导出宏 |
| libwebp | 底层 WebP 解析和解码(外部) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkCodecs | 解码器注册和查找系统 |
| SkImage | 从 WebP 数据创建图像 |
| SkBitmap | 解码到位图 |
| Web 浏览器 | 网页图像渲染 |

## 设计模式与设计决策

### 命名空间封装

使用命名空间而非类:
- 避免不必要的类层次
- 清晰的模块边界
- 便于条件编译

### 忽略 DecodeContext

WebP 不使用 DecodeContext:
- 无需元数据回调(不同于 PNG)
- 简化接口
- 保持与其他解码器一致

### 向后兼容性

提供旧 API 重载:
- 平滑迁移路径
- 避免破坏现有代码
- 清晰的弃用标记

## 性能考量

### 文件大小比较

相同质量下的典型文件大小:
- **WebP 有损**: 基准(1x)
- **JPEG**: 1.2-1.5x
- **WebP 无损**: 1.5-2x
- **PNG**: 2-3x

### 解码性能

影响因素:
- **压缩类型**: 有损 vs 无损
- **图像尺寸**: 线性复杂度
- **颜色转换**: 额外开销
- **Alpha 通道**: 略微增加时间

典型性能(相对):
- WebP 有损: 比 JPEG 慢 10-30%
- WebP 无损: 比 PNG 快 20-50%

### 内存使用

内存需求:
- 解码器对象: ~1-2 KB
- 输入缓冲: 文件大小
- 输出位图: 宽 × 高 × 4 字节
- 临时缓冲: libwebp 内部使用,通常 < 1 MB

### 优化建议

1. **缓存解码结果**: WebP 解码相对耗时
2. **使用缩放解码**: 避免解码大图后再缩小
3. **预加载**: 异步解码网络图像
4. **硬件加速**: 在支持的平台使用

## 平台相关说明

### libwebp 依赖

不同平台的 libwebp:
- **Linux**: 系统 libwebp 或静态链接
- **macOS**: Homebrew 或系统版本
- **Windows**: 通常静态链接
- **Android**: 系统 libwebp(Android 4.0+)
- **iOS**: 静态链接或第三方库

### 编译选项

可选编译:
```gn
# BUILD.gn
skia_enable_webp_codec = true
```

条件编译:
```cpp
#if defined(SK_CODEC_DECODES_WEBP)
    // WebP 解码代码
#endif
```

### 浏览器支持

WebP 浏览器支持:
- Chrome: 完全支持(Google 开发)
- Firefox: 完全支持(65+)
- Safari: 支持(14+)
- Edge: 支持(基于 Chromium)

## WebP vs 其他格式

### WebP vs JPEG

优势:
- 文件更小(20-30%)
- 支持透明度
- 更好的细节保留

劣势:
- 解码稍慢
- 浏览器支持较新
- 编辑软件支持有限

### WebP vs PNG

优势:
- 文件显著更小(50-70%)
- 更快的解码(无损模式)

劣势:
- 不支持所有 PNG 特性(如 16 位通道)
- 某些工具链不支持

## 相关文件

| 文件 | 关系 |
|------|------|
| include/codec/SkCodec.h | 解码器基类 |
| src/codec/SkWebpCodec.h | WebP 解码器实现类 |
| src/codec/SkWebpCodec.cpp | WebP 解码器实现 |
| third_party/libwebp | libwebp 库 |
| include/core/SkData.h | 内存数据容器 |
| include/core/SkStream.h | 流接口 |
