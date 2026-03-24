# SkJpegxlDecoder

> 源文件: `include/codec/SkJpegxlDecoder.h`

## 概述

SkJpegxlDecoder 命名空间提供了 JPEG XL 图像格式的解码功能。JPEG XL 是新一代图像格式,由 JPEG 委员会开发,旨在取代传统 JPEG,提供更好的压缩效率、更高的图像质量、支持 HDR 和透明度,同时保持与 JPEG 的无损转码能力。该模块是 Skia 支持下一代图像格式的重要组成部分。

## 架构位置

SkJpegxlDecoder 位于 Skia 图像编解码子系统的格式特定层,属于 JPEG XL 解码模块。它依赖 libjxl(JPEG XL 参考实现库)进行实际的图像解析和解码。该模块实现了 SkCodec 的工厂接口,通过标准的解码器注册机制与 Skia 核心集成,是 Skia 适配现代图像格式的前沿实现。

## 主要函数

### 格式检测

#### `SK_API bool IsJpegxl(const void*, size_t)`

**功能**: 检查给定的字节序列是否为 JPEG XL 图像

**参数**:
- 第一个参数: 指向数据缓冲区的指针
- 第二个参数: 缓冲区大小(字节)

**返回值**:
- `true`: 数据符合 JPEG XL 文件头特征
- `false`: 不是有效的 JPEG XL 数据

**检测机制**:
JPEG XL 有两种容器格式:

**裸码流(Naked codestream)**:
```
字节 0-1: 0xFF 0x0A
```

**ISOBMFF 容器(基于 ISO Base Media File Format)**:
```
字节 0-11: 标准 ISOBMFF box 结构
字节 4-7:  "JXL " (0x4A 0x58 0x4C 0x20)
```

**最小检测大小**: 至少 2-12 字节(取决于格式)

**使用场景**:
- 识别下一代图像格式
- 自动格式检测
- 未来格式迁移

### 解码器创建

#### `SK_API std::unique_ptr<SkCodec> Decode(std::unique_ptr<SkStream>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从流中解码 JPEG XL 图像

**参数**:
- `stream`: 唯一指针,指向包含 JPEG XL 数据的输入流
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 被忽略(JPEG XL 解码不使用上下文)

**返回值**:
- 成功: 返回 SkCodec 智能指针
- 失败: 返回 nullptr,同时设置 result 参数

**result 可能的值**:
- `SkCodec::kSuccess`: 成功创建解码器
- `SkCodec::kInvalidInput`: 不是有效的 JPEG XL
- `SkCodec::kUnimplemented`: 不支持的 JPEG XL 特性
- `SkCodec::kInternalError`: libjxl 内部错误

**JPEG XL 支持的特性**:
- **有损和无损压缩**: 统一的编解码器
- **高动态范围(HDR)**: 浮点像素值
- **广色域**: 支持任意色彩空间
- **Alpha 透明度**: 独立 Alpha 通道
- **动画**: 多帧图像
- **渐进式解码**: 逐步提高质量
- **无损 JPEG 转码**: 比原 JPEG 小 20%

#### `SK_API std::unique_ptr<SkCodec> Decode(sk_sp<const SkData>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从内存数据中解码 JPEG XL 图像

**参数**:
- `data`: 智能指针,指向包含 JPEG XL 数据的内存块
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 被忽略

**返回值**: 同流版本

**使用场景**:
- 网络下载的完整图像
- 内存中的图像资源
- 批量处理场景

**性能**: 内存版本支持更高效的随机访问

### 解码器描述符

#### `inline constexpr SkCodecs::Decoder Decoder()`

**功能**: 返回 JPEG XL 解码器的描述符,用于注册到解码器系统

**返回值**: SkCodecs::Decoder 结构体,包含:
- `name`: "jpegxl"(格式名称)
- `probe`: IsJpegxl(格式检测函数)
- `decode`: Decode(解码函数)

**使用场景**:
```cpp
// 注册 JPEG XL 解码器
SkCodecs::Register(SkJpegxlDecoder::Decoder());

// 之后可以通过通用接口解码 JPEG XL
std::unique_ptr<SkCodec> codec = SkCodecs::Decode(stream, &result);
```

## JPEG XL 格式详解

### 核心特性

**1. 统一的有损/无损压缩**:
- 同一编解码器处理两种模式
- 无损模式: 可逆变换
- 有损模式: 基于 VarDCT 和 Modular 编码

**2. 高级色彩管理**:
- 支持任意 ICC 配置文件
- 内置 sRGB、Display P3、Rec.2100 PQ/HLG
- 浮点和整数像素值

**3. 渐进式解码**:
- 多个质量层
- 早期帧快速预览
- 逐步细化到完整质量

**4. 响应式图像**:
- 内置缩略图和下采样版本
- 无需重新编码即可提取不同分辨率

**5. 元数据支持**:
- EXIF、XMP、JUMBF
- 保留原始 JPEG 元数据

### 文件结构

**裸码流格式**:
```
Signature: 0xFF 0x0A
Headers:   编码参数、图像尺寸、色彩空间
Frames:    一个或多个图像帧
```

**ISOBMFF 容器格式**:
```
ftyp box: 文件类型标识 "jxl "
jxlc box: JPEG XL 码流
jxlp box: 部分码流(用于流式传输)
Exif box: EXIF 元数据
xml  box: XMP 元数据
```

### 压缩技术

**VarDCT (Variable DCT)**:
- 可变块大小 DCT
- 自适应量化
- 更好的感知质量

**Modular 编码**:
- 基于预测的无损/近无损编码
- 适用于文本、图标
- 低延迟解码

**高级特性**:
- 自适应量化矩阵
- 边缘保持滤波
- 感知优化

## 使用示例

### 示例 1: 基础解码

```cpp
#include "include/codec/SkJpegxlDecoder.h"
#include "include/core/SkBitmap.h"
#include "include/core/SkStream.h"

bool decodeJpegxlFile(const char* path, SkBitmap* bitmap) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkJpegxlDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        printf("Failed to decode JPEG XL: %d\n", result);
        return false;
    }

    SkImageInfo info = codec->getInfo();
    printf("JPEG XL: %dx%d, colorType=%d, alphaType=%d\n",
           info.width(), info.height(),
           info.colorType(), info.alphaType());

    if (!bitmap->tryAllocPixels(info)) {
        return false;
    }

    result = codec->getPixels(info, bitmap->getPixels(),
                              bitmap->rowBytes());
    return result == SkCodec::kSuccess;
}
```

### 示例 2: HDR 图像解码

```cpp
bool decodeJpegxlHDR(const char* path, SkBitmap* bitmap) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkJpegxlDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        return false;
    }

    // 检查是否为 HDR
    SkImageInfo srcInfo = codec->getInfo();
    if (srcInfo.colorType() == kRGBA_F16_SkColorType ||
        srcInfo.colorType() == kRGBA_F32_SkColorType) {
        printf("HDR JPEG XL detected\n");
    }

    // 解码为浮点格式以保留 HDR
    SkImageInfo dstInfo = srcInfo.makeColorType(kRGBA_F16_SkColorType);
    if (!bitmap->tryAllocPixels(dstInfo)) {
        return false;
    }

    result = codec->getPixels(dstInfo, bitmap->getPixels(),
                              bitmap->rowBytes());
    return result == SkCodec::kSuccess;
}
```

### 示例 3: 渐进式解码

```cpp
bool decodeJpegxlProgressive(const char* path,
                             std::vector<SkBitmap>* levels) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkJpegxlDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        return false;
    }

    SkImageInfo fullInfo = codec->getInfo();

    // 解码不同质量级别(如果支持)
    // 注: 实际实现取决于 SkCodec 的渐进式 API
    for (int level = 0; level < 3; level++) {
        SkBitmap bitmap;
        SkImageInfo info = fullInfo;

        if (!bitmap.tryAllocPixels(info)) {
            break;
        }

        // 设置解码选项以获取特定质量级别
        SkCodec::Options options;
        result = codec->getPixels(info, bitmap.getPixels(),
                                  bitmap.rowBytes(), &options);

        if (result == SkCodec::kSuccess) {
            levels->push_back(std::move(bitmap));
        }
    }

    return !levels->empty();
}
```

### 示例 4: 格式转换

```cpp
bool convertJpegToJpegxl(const char* jpegPath,
                        const char* jxlPath) {
    // 加载 JPEG
    std::unique_ptr<SkFILEStream> jpegStream =
        SkFILEStream::Make(jpegPath);
    if (!jpegStream) {
        return false;
    }

    // 解码 JPEG
    SkCodec::Result result;
    std::unique_ptr<SkCodec> jpegCodec =
        SkCodecs::Decode(std::move(jpegStream), &result);
    if (!jpegCodec) {
        return false;
    }

    SkBitmap bitmap;
    if (!bitmap.tryAllocPixels(jpegCodec->getInfo())) {
        return false;
    }

    if (jpegCodec->getPixels(bitmap.info(), bitmap.getPixels(),
                            bitmap.rowBytes()) != SkCodec::kSuccess) {
        return false;
    }

    // 编码为 JPEG XL
    // 注: Skia 不直接提供 JPEG XL 编码,需要使用 libjxl
    // 这里仅展示概念

    return true;
}
```

## 内部实现细节

### libjxl 集成

SkJpegxlDecoder 依赖 libjxl:
- **JxlDecoder**: 主解码器对象
- **JxlDecoderSubscribeEvents**: 事件订阅
- **JxlDecoderProcessInput**: 处理输入数据
- **JxlDecoderGetFrameHeader**: 获取帧信息
- **JxlDecoderGetColorAsEncodedProfile**: 颜色空间信息
- **JxlDecoderSetImageOutBuffer**: 设置输出缓冲区

Skia 的职责:
- 提供统一的 SkCodec 接口
- 管理解码器生命周期
- 颜色空间转换和管理
- 错误处理和资源清理

### 颜色空间处理

JPEG XL 支持复杂的颜色管理:
- 内置色彩空间: sRGB、Display P3、Rec.2100
- 自定义 ICC 配置文件
- HDR 传输函数: PQ、HLG

Skia 转换策略:
1. 读取编码的色彩空间
2. 转换为 Skia 的 SkColorSpace
3. 应用到 SkImageInfo
4. 解码时进行必要的色彩空间转换

### 像素格式映射

JPEG XL → Skia 像素格式映射:

| JPEG XL 格式 | Skia SkColorType |
|--------------|------------------|
| 8-bit RGB | kRGBA_8888_SkColorType |
| 8-bit Gray | kGray_8_SkColorType |
| 16-bit RGB | kR16G16B16A16_unorm_SkColorType |
| 16-bit Float | kRGBA_F16_SkColorType |
| 32-bit Float | kRGBA_F32_SkColorType |

### 渐进式解码支持

JPEG XL 的渐进式解码:
- 多个 DC 帧
- 逐步细化的 AC 系数
- 早期退出机制

Skia 实现:
- 订阅 JxlDecoder 的渐进式事件
- 提供中间质量的图像
- 支持取消和继续

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkCodec.h | 解码器基类和接口 |
| SkRefCnt.h | 智能指针和引用计数 |
| SkAPI.h | API 导出宏 |
| libjxl | JPEG XL 参考实现(外部) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkCodecs | 解码器注册和查找系统 |
| SkImage | 从 JPEG XL 创建图像 |
| 下一代 Web | 现代 Web 图像格式 |
| HDR 应用 | 高动态范围内容 |

## 设计模式与设计决策

### 前瞻性设计

支持 JPEG XL 体现了 Skia 的前瞻性:
- 为未来图像格式做准备
- 支持更好的压缩和质量
- HDR 和广色域支持

### 可选依赖

JPEG XL 作为可选模块:
- libjxl 较大(~1 MB)
- 格式尚未广泛部署
- 允许按需编译

### 统一接口

遵循 SkCodec 接口:
- 与其他格式一致的 API
- 简化用户代码
- 易于切换格式

## 性能考量

### 压缩效率

JPEG XL vs 其他格式(相同质量):
- **vs JPEG**: 小 20-60%
- **vs PNG**(无损): 小 35-50%
- **vs WebP**: 小 10-30%

### 解码性能

影响因素:
- **图像复杂度**: 纹理多的图像慢
- **质量设置**: 高质量解码慢
- **HDR**: 浮点运算开销
- **硬件加速**: 部分平台支持

典型性能:
- SDR 图像: 与 JPEG 相当或稍慢
- HDR 图像: 比 PNG 快 2-3x
- 渐进式: 早期帧非常快

### 内存使用

内存需求:
- 解码器对象: ~10-50 KB
- 输入缓冲: 文件大小
- 输出位图: 宽 × 高 × BPP
- 临时缓冲: libjxl 内部,可能较大

优化建议:
- 使用流式解码
- 对于大图像,解码为目标尺寸
- 限制并发解码器数量

## 浏览器和工具支持

### 浏览器支持(截至 2024)

- **Chrome**: 实验性支持(需要启用标志)
- **Firefox**: 开发中
- **Safari**: 未公开
- **Edge**: 跟随 Chromium

### 工具支持

- **ImageMagick**: 完全支持
- **GIMP**: 通过插件支持
- **XnView**: 支持查看
- **cjxl/djxl**: 官方命令行工具

## 未来展望

### JPEG XL 的优势

1. **取代 JPEG**: 无损转码 + 更小文件
2. **统一格式**: 替代 JPEG、PNG、WebP
3. **未来技术**: HDR、广色域、高效压缩

### 挑战

1. **生态系统**: 需要广泛的工具支持
2. **硬件加速**: 需要时间部署
3. **市场接受度**: 与现有格式竞争

## 相关文件

| 文件 | 关系 |
|------|------|
| include/codec/SkCodec.h | 解码器基类 |
| src/codec/SkJpegxlCodec.h | JPEG XL 解码器实现类 |
| src/codec/SkJpegxlCodec.cpp | JPEG XL 解码器实现 |
| third_party/libjxl | libjxl 库 |
| include/core/SkColorSpace.h | 颜色空间管理 |
| include/core/SkData.h | 内存数据容器 |
| include/core/SkStream.h | 流接口 |
