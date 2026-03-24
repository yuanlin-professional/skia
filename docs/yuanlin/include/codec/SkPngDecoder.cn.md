# SkPngDecoder

> 源文件: `include/codec/SkPngDecoder.h`

## 概述

SkPngDecoder 命名空间提供了 PNG 图像格式的解码功能,包括格式检测、解码器创建和与 Skia 编解码系统的集成。它是 Skia 模块化图像解码架构的一部分,将 PNG 特定的解码逻辑封装在独立的命名空间中,支持可选编译和动态注册。

## 架构位置

SkPngDecoder 位于 Skia 图像编解码子系统的格式特定层,属于 PNG 解码模块。它实现了 SkCodec 的工厂接口,通过标准的解码器注册机制与 Skia 核心集成。该模块依赖 libpng 库进行实际的 PNG 解析和解压缩,是连接 Skia 和 libpng 的适配层。

## 主要函数

### 格式检测

#### `SK_API bool IsPng(const void*, size_t)`

**功能**: 检查给定的字节序列是否为 PNG 图像

**参数**:
- 第一个参数: 指向数据缓冲区的指针
- 第二个参数: 缓冲区大小(字节)

**返回值**:
- `true`: 数据符合 PNG 文件头特征
- `false`: 不是有效的 PNG 数据

**检测机制**:
PNG 文件以固定的 8 字节魔数开头:
```
89 50 4E 47 0D 0A 1A 0A
\211 P  N  G  \r \n \032 \n
```

**使用场景**:
- 在解码前快速验证格式
- 自动格式识别系统
- 多格式解码器的分发逻辑

**性能**: 非常快,仅检查前几个字节

### 解码器创建

#### `SK_API std::unique_ptr<SkCodec> Decode(std::unique_ptr<SkStream>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从流中解码 PNG 图像

**参数**:
- `stream`: 唯一指针,指向包含 PNG 数据的输入流
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 可选的解码上下文,对于 PNG 应为 SkPngChunkReader*

**返回值**:
- 成功: 返回 SkCodec 智能指针
- 失败: 返回 nullptr,同时设置 result 参数

**result 可能的值**:
- `SkCodec::kSuccess`: 成功创建解码器
- `SkCodec::kInvalidInput`: 不是有效的 PNG
- `SkCodec::kUnimplemented`: 不支持的 PNG 特性
- `SkCodec::kInternalError`: libpng 内部错误

**DecodeContext 用法**:
```cpp
sk_sp<SkPngChunkReader> chunkReader = sk_make_sp<MyChunkReader>();
SkCodec::Result result;
std::unique_ptr<SkCodec> codec = SkPngDecoder::Decode(
    std::move(stream),
    &result,
    static_cast<SkCodecs::DecodeContext>(chunkReader.get())
);
```

#### `SK_API std::unique_ptr<SkCodec> Decode(sk_sp<const SkData>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从内存数据中解码 PNG 图像

**参数**:
- `data`: 智能指针,指向包含 PNG 数据的内存块
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 可选的 SkPngChunkReader*

**返回值**: 同流版本

**使用场景**:
- 数据已完全加载到内存
- 从网络请求或文件读取的完整数据
- 嵌入式图像资源

**性能**: 比流版本稍快,因为数据连续且可随机访问

#### `inline std::unique_ptr<SkCodec> Decode(sk_sp<SkData>, SkCodec::Result*, SkCodecs::DecodeContext)` (待移除)

**功能**: 兼容旧 API 的重载版本

**状态**: 标记为 "TODO: remove after client migration"

**说明**: 接受非 const SkData,内部转换为 const 版本

### 解码器描述符

#### `inline constexpr SkCodecs::Decoder Decoder()`

**功能**: 返回 PNG 解码器的描述符,用于注册到解码器系统

**返回值**: SkCodecs::Decoder 结构体,包含:
- `name`: "png"(格式名称)
- `probe`: IsPng(格式检测函数)
- `decode`: Decode(解码函数)

**使用场景**:
```cpp
// 注册 PNG 解码器
SkCodecs::Register(SkPngDecoder::Decoder());

// 之后可以通过通用接口解码 PNG
std::unique_ptr<SkCodec> codec = SkCodecs::Decode(stream, &result);
```

## 使用示例

### 示例 1: 基础解码

```cpp
#include "include/codec/SkPngDecoder.h"
#include "include/core/SkBitmap.h"
#include "include/core/SkStream.h"

bool decodePngFile(const char* path, SkBitmap* bitmap) {
    // 打开文件流
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    // 创建解码器
    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkPngDecoder::Decode(std::move(stream), &result);
    if (!codec) {
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

### 示例 2: 带元数据提取

```cpp
class MetadataReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data,
                   size_t length) override {
        if (strncmp(tag, "tEXt", 4) == 0) {
            std::string text(static_cast<const char*>(data), length);
            metadata_.push_back(text);
        }
        return true;
    }

    const std::vector<std::string>& getMetadata() const {
        return metadata_;
    }

private:
    std::vector<std::string> metadata_;
};

bool decodePngWithMetadata(sk_sp<SkData> data, SkBitmap* bitmap,
                           std::vector<std::string>* metadata) {
    // 创建元数据读取器
    sk_sp<MetadataReader> reader = sk_make_sp<MetadataReader>();

    // 解码
    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec = SkPngDecoder::Decode(
        data, &result,
        static_cast<SkCodecs::DecodeContext>(reader.get()));

    if (!codec) {
        return false;
    }

    // 获取像素
    SkImageInfo info = codec->getInfo();
    if (!bitmap->tryAllocPixels(info)) {
        return false;
    }

    result = codec->getPixels(info, bitmap->getPixels(),
                              bitmap->rowBytes());

    // 提取元数据
    if (metadata) {
        *metadata = reader->getMetadata();
    }

    return result == SkCodec::kSuccess;
}
```

### 示例 3: 格式检测

```cpp
bool isPngFile(const char* path) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    // 读取文件头
    uint8_t header[8];
    if (stream->read(header, 8) != 8) {
        return false;
    }

    // 检测格式
    return SkPngDecoder::IsPng(header, 8);
}
```

### 示例 4: 渐进式解码

```cpp
bool decodePngProgressively(std::unique_ptr<SkStream> stream,
                            SkBitmap* bitmap) {
    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkPngDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        return false;
    }

    SkImageInfo info = codec->getInfo();
    if (!bitmap->tryAllocPixels(info)) {
        return false;
    }

    // 逐行解码
    result = codec->startScanlineDecode(info);
    if (result != SkCodec::kSuccess) {
        return false;
    }

    for (int y = 0; y < info.height(); y++) {
        void* dst = bitmap->getAddr(0, y);
        int rowsDecoded = codec->getScanlines(dst, 1,
                                               bitmap->rowBytes());
        if (rowsDecoded != 1) {
            return false;
        }

        // 可在此处更新进度条
        updateProgress(y, info.height());
    }

    return true;
}
```

## 内部实现细节

### PNG 格式支持

支持的 PNG 特性:
- **颜色类型**: 灰度、RGB、调色板、灰度+Alpha、RGBA
- **位深度**: 1, 2, 4, 8, 16 位
- **隔行扫描**: Adam7 隔行
- **透明度**: tRNS 块、Alpha 通道
- **颜色校正**: gAMA、cHRM、sRGB
- **压缩**: DEFLATE(标准 PNG 压缩)

不支持的特性:
- APNG(动画 PNG)
- 某些非标准扩展

### libpng 集成

SkPngDecoder 内部使用 libpng:
- 处理底层 PNG 解析
- DEFLATE 解压缩
- CRC 校验
- 颜色转换

Skia 的角色:
- 提供统一的 SkCodec 接口
- 管理内存和错误处理
- 颜色空间转换
- 像素格式适配

### 内存管理

**流所有权**:
Decode 函数接受 `std::unique_ptr<SkStream>`,获取流的所有权

**数据所有权**:
Decode 函数接受 `sk_sp<const SkData>`,共享数据所有权

**解码器生命周期**:
返回的 SkCodec 管理所有解码资源,析构时自动清理

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkCodec.h | 解码器基类和接口 |
| SkRefCnt.h | 智能指针和引用计数 |
| SkAPI.h | API 导出宏 |
| libpng | 底层 PNG 解析(外部依赖) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkCodecs | 解码器注册和查找系统 |
| SkImage | 从 PNG 数据创建图像 |
| SkBitmap | 解码到位图 |

## 设计模式与设计决策

### 命名空间封装

使用命名空间而非类:
- 避免不必要的类层次
- 清晰的模块边界
- 便于条件编译(可选模块)

### 工厂模式

Decode 函数作为工厂方法:
- 隐藏具体实现类
- 统一的错误处理
- 便于替换实现

### 可插拔解码器架构

通过 Decoder() 描述符注册:
- 支持动态选择解码器
- 便于添加新格式
- 允许条件编译

### 类型安全的上下文传递

DecodeContext 作为 void* 的替代:
- 避免类型转换错误
- 编译期类型检查
- 明确的文档说明

## 性能考量

### 格式检测性能

IsPng 非常快速:
- 仅检查 8 字节魔数
- 无内存分配
- 适合批量检测

### 解码性能

影响因素:
- **图像大小**: 线性复杂度
- **压缩级别**: 高压缩解码慢
- **隔行扫描**: Adam7 需要多次 pass
- **颜色转换**: 某些格式需要额外转换

优化建议:
- 对于小图像,使用 SkData 版本(避免流开销)
- 大图像使用渐进式解码(减少内存峰值)
- 缓存解码结果避免重复解码

### 内存使用

典型内存需求:
- 解码器对象: ~1 KB
- 临时缓冲区: 图像行大小 × 2-4
- 输出位图: 宽 × 高 × 每像素字节数

## 平台相关说明

### libpng 依赖

不同平台的 libpng:
- **Linux**: 系统 libpng
- **macOS**: 系统或 Homebrew libpng
- **Windows**: 通常静态链接
- **Android/iOS**: Skia 内置或系统版本

### 编译选项

可选编译:
```gn
# BUILD.gn
skia_enable_png_codec = true
```

条件编译:
```cpp
#if defined(SK_CODEC_DECODES_PNG)
    // PNG 解码代码
#endif
```

## 相关文件

| 文件 | 关系 |
|------|------|
| include/codec/SkCodec.h | 解码器基类 |
| include/codec/SkPngChunkReader.h | PNG 元数据回调接口 |
| src/codec/SkPngCodec.h | PNG 解码器实现类 |
| src/codec/SkPngCodec.cpp | PNG 解码器实现 |
| include/core/SkData.h | 内存数据容器 |
| include/core/SkStream.h | 流接口 |
