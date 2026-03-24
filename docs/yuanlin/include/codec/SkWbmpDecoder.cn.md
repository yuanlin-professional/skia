# SkWbmpDecoder

> 源文件: `include/codec/SkWbmpDecoder.h`

## 概述

SkWbmpDecoder 命名空间提供了 WBMP(Wireless Bitmap)图像格式的解码功能。WBMP 是一种简单的单色位图格式,专为早期移动设备设计,文件体积极小,仅支持黑白两色。尽管现代应用很少使用,Skia 保留了对该格式的支持以实现完整的格式兼容性。

## 架构位置

SkWbmpDecoder 位于 Skia 图像编解码子系统的格式特定层,属于 WBMP 解码模块。由于 WBMP 格式极其简单,该模块不依赖外部库,完全由 Skia 自身实现。它通过标准的解码器注册机制与 Skia 核心集成,是 Skia 模块化图像解码架构中最简单的解码器之一。

## 主要函数

### 格式检测

#### `SK_API bool IsWbmp(const void*, size_t)`

**功能**: 检查给定的字节序列是否为 WBMP 图像

**参数**:
- 第一个参数: 指向数据缓冲区的指针
- 第二个参数: 缓冲区大小(字节)

**返回值**:
- `true`: 数据符合 WBMP 文件头特征
- `false`: 不是有效的 WBMP 数据

**检测机制**:
WBMP 文件头结构:
```
字节 0: Type Field (通常为 0x00)
字节 1: Fix Header Field (0x00)
字节 2+: Width (多字节整数)
字节 N+: Height (多字节整数)
字节 M+: 像素数据
```

**典型文件头**:
```
00 00 [width] [height] [data...]
```

**最小检测大小**: 至少 4-5 字节

**使用场景**:
- 识别传统移动设备图像
- 向后兼容性支持
- 简单位图格式处理

### 解码器创建

#### `SK_API std::unique_ptr<SkCodec> Decode(std::unique_ptr<SkStream>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从流中解码 WBMP 图像

**参数**:
- `stream`: 唯一指针,指向包含 WBMP 数据的输入流
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 被忽略(WBMP 解码不使用上下文)

**返回值**:
- 成功: 返回 SkCodec 智能指针
- 失败: 返回 nullptr,同时设置 result 参数

**result 可能的值**:
- `SkCodec::kSuccess`: 成功创建解码器
- `SkCodec::kInvalidInput`: 不是有效的 WBMP
- `SkCodec::kInternalError`: 解析错误

**WBMP 格式特性**:
- **颜色**: 仅黑白两色(1 位/像素)
- **压缩**: 无压缩,原始位图数据
- **透明度**: 不支持
- **动画**: 不支持
- **元数据**: 不支持

#### `SK_API std::unique_ptr<SkCodec> Decode(sk_sp<const SkData>, SkCodec::Result*, SkCodecs::DecodeContext = nullptr)`

**功能**: 从内存数据中解码 WBMP 图像

**参数**:
- `data`: 智能指针,指向包含 WBMP 数据的内存块
- `result`: 输出参数,返回解码结果状态
- `DecodeContext`: 被忽略

**返回值**: 同流版本

**使用场景**:
- 嵌入式资源(图标、符号)
- 网络传输的小图标
- 测试和兼容性验证

### 解码器描述符

#### `inline constexpr SkCodecs::Decoder Decoder()`

**功能**: 返回 WBMP 解码器的描述符,用于注册到解码器系统

**返回值**: SkCodecs::Decoder 结构体,包含:
- `name`: "wbmp"(格式名称)
- `probe`: IsWbmp(格式检测函数)
- `decode`: Decode(解码函数)

**使用场景**:
```cpp
// 注册 WBMP 解码器
SkCodecs::Register(SkWbmpDecoder::Decoder());
```

## WBMP 格式详解

### 文件结构

**完整格式**:
```
TypeField:      1 字节  (0x00 = Type 0: B/W, Uncompressed bitmap)
FixHeaderField: 1 字节  (0x00)
Width:          多字节  (变长编码)
Height:         多字节  (变长编码)
Data:           N 字节  (位图数据,每行向上取整到字节边界)
```

### 多字节整数编码

WBMP 使用变长编码存储宽度和高度:
- 每个字节的最高位(bit 7)表示是否有后续字节
- 低 7 位存储实际数值
- 大端序

**示例**:
```
值 127:    0x7F (01111111)
值 128:    0x81 0x00 (10000001 00000000)
值 255:    0x81 0x7F (10000001 01111111)
值 65535:  0x83 0xFF 0x7F (10000011 11111111 01111111)
```

### 像素数据

**编码方式**:
- 1 位/像素
- 0 = 白色, 1 = 黑色
- 从左到右,从上到下
- 每行向上取整到字节边界

**示例**(4×2 图像):
```
像素模式:
1 0 1 0
0 1 0 1

编码为: 0xA5 (10100101)
        0x5A (01011010)
```

## 使用示例

### 示例 1: 基础解码

```cpp
#include "include/codec/SkWbmpDecoder.h"
#include "include/core/SkBitmap.h"
#include "include/core/SkStream.h"

bool decodeWbmpFile(const char* path, SkBitmap* bitmap) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkWbmpDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        return false;
    }

    // WBMP 解码为灰度或 RGBA
    SkImageInfo info = codec->getInfo();
    if (!bitmap->tryAllocPixels(info)) {
        return false;
    }

    result = codec->getPixels(info, bitmap->getPixels(),
                              bitmap->rowBytes());
    return result == SkCodec::kSuccess;
}
```

### 示例 2: 格式检测

```cpp
bool isWbmpFile(const char* path) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    uint8_t header[8];
    size_t bytesRead = stream->peek(header, 8);
    if (bytesRead < 4) {
        return false;
    }

    return SkWbmpDecoder::IsWbmp(header, bytesRead);
}
```

### 示例 3: 创建 WBMP 图像

虽然 SkWbmpDecoder 仅负责解码,但了解编码有助于理解格式:

```cpp
// 注意: 这是示意代码,Skia 不提供 WBMP 编码 API
std::vector<uint8_t> encodeAsWbmp(const bool* pixels,
                                   int width, int height) {
    std::vector<uint8_t> wbmp;

    // Type Field
    wbmp.push_back(0x00);

    // Fix Header Field
    wbmp.push_back(0x00);

    // Width (变长编码)
    encodeMultiByte(wbmp, width);

    // Height (变长编码)
    encodeMultiByte(wbmp, height);

    // 像素数据
    int bytesPerRow = (width + 7) / 8;
    for (int y = 0; y < height; y++) {
        uint8_t byte = 0;
        int bit = 7;
        for (int x = 0; x < width; x++) {
            if (pixels[y * width + x]) {
                byte |= (1 << bit);
            }
            bit--;
            if (bit < 0) {
                wbmp.push_back(byte);
                byte = 0;
                bit = 7;
            }
        }
        if (bit < 7) {
            wbmp.push_back(byte); // 最后不完整的字节
        }
    }

    return wbmp;
}

void encodeMultiByte(std::vector<uint8_t>& vec, int value) {
    std::vector<uint8_t> bytes;
    bytes.push_back(value & 0x7F);
    value >>= 7;

    while (value > 0) {
        bytes.push_back((value & 0x7F) | 0x80);
        value >>= 7;
    }

    // 反向添加(大端序)
    for (auto it = bytes.rbegin(); it != bytes.rend(); ++it) {
        vec.push_back(*it);
    }
}
```

### 示例 4: 转换为彩色图像

```cpp
bool decodeWbmpToColor(const char* path, SkBitmap* bitmap) {
    std::unique_ptr<SkFILEStream> stream =
        SkFILEStream::Make(path);
    if (!stream) {
        return false;
    }

    SkCodec::Result result;
    std::unique_ptr<SkCodec> codec =
        SkWbmpDecoder::Decode(std::move(stream), &result);
    if (!codec) {
        return false;
    }

    // 强制解码为 RGBA
    SkImageInfo srcInfo = codec->getInfo();
    SkImageInfo dstInfo = srcInfo.makeColorType(kRGBA_8888_SkColorType);

    if (!bitmap->tryAllocPixels(dstInfo)) {
        return false;
    }

    result = codec->getPixels(dstInfo, bitmap->getPixels(),
                              bitmap->rowBytes());
    return result == SkCodec::kSuccess;
}
```

## 内部实现细节

### 解析流程

1. **读取 Type Field**: 验证为 0x00
2. **读取 Fix Header**: 验证为 0x00
3. **解码宽度**: 读取变长整数
4. **解码高度**: 读取变长整数
5. **计算数据大小**: `ceil(width/8) * height` 字节
6. **读取位图数据**: 逐字节读取并解包为像素

### 像素转换

WBMP 1 位数据转换为 Skia 像素格式:
- **0 (白色)** → RGB(255, 255, 255)
- **1 (黑色)** → RGB(0, 0, 0)

如果目标格式为灰度:
- **0** → Gray 255
- **1** → Gray 0

### 错误处理

常见错误情况:
- Type Field 不为 0x00
- Fix Header 不为 0x00
- 无效的变长整数编码
- 文件截断(数据不足)
- 宽度或高度为 0
- 宽度或高度过大(可能导致整数溢出)

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkCodec.h | 解码器基类和接口 |
| SkRefCnt.h | 智能指针和引用计数 |
| SkAPI.h | API 导出宏 |

**无外部库依赖**: WBMP 格式简单,完全由 Skia 实现

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkCodecs | 解码器注册和查找系统 |
| 向后兼容层 | 处理旧格式数据 |

## 设计模式与设计决策

### 保留遗留格式支持

保留 WBMP 支持的原因:
- 向后兼容性
- 完整的格式覆盖
- 简单的参考实现
- 代码体积小(< 500 行)

### 自包含实现

不依赖外部库:
- 格式极其简单
- 避免引入依赖
- 减小编译复杂度

### 统一接口

遵循 SkCodec 接口:
- 与其他解码器一致的 API
- 可插拔架构
- 标准错误处理

## 性能考量

### 文件大小

WBMP 文件极小:
- 100×100 图像: ~1.3 KB
- 200×200 图像: ~5 KB
- 无压缩,文件大小可预测

**计算公式**:
```
文件大小 ≈ 2 + len(width) + len(height) + ceil(width/8) * height
```

### 解码性能

WBMP 解码非常快速:
- 无压缩,直接位操作
- 简单的位解包
- 最小的 CPU 和内存开销

典型性能:
- 100×100 图像: < 1 ms
- 1000×1000 图像: < 10 ms

### 内存使用

内存需求极小:
- 解码器对象: ~200 字节
- 输入缓冲: 文件大小(KB 级)
- 输出位图: 宽 × 高 × 1-4 字节(取决于目标格式)

## 历史背景

### WAP 时代

WBMP 设计于 WAP(Wireless Application Protocol)时代:
- **1990 年代末**: 移动互联网萌芽期
- **设备限制**: 128×128 像素屏幕,KB 级内存
- **网络限制**: 9600 bps 拨号连接
- **用途**: 移动网页图标、小图片

### 现代应用

现代 WBMP 使用场景:
- 电子墨水屏显示(如电子书阅读器)
- 简单的黑白图标
- 向后兼容的数据处理
- 教学和参考实现

### 替代格式

现代替代方案:
- **PNG**: 支持索引颜色和 Alpha
- **WebP**: 更好的压缩
- **SVG**: 矢量图形,无损缩放

## 平台相关说明

### 编译选项

可选编译:
```gn
# BUILD.gn
skia_enable_wbmp_codec = true
```

条件编译:
```cpp
#if defined(SK_CODEC_DECODES_WBMP)
    // WBMP 解码代码
#endif
```

### 无平台差异

WBMP 格式和实现完全平台无关:
- 纯 C++ 实现
- 无汇编优化
- 无系统 API 调用

## 与其他单色格式对比

### WBMP vs PBM (Portable Bitmap)

**PBM 优势**:
- ASCII 和二进制两种格式
- 更好的工具支持
- 更清晰的规范

**WBMP 优势**:
- 稍小的文件大小(变长编码)
- WAP 标准的一部分

### WBMP vs 1-bit PNG

**PNG 优势**:
- 通用格式,广泛支持
- 可选压缩
- 支持元数据

**WBMP 优势**:
- 更简单的解析
- 更小的解码器代码

## 相关文件

| 文件 | 关系 |
|------|------|
| include/codec/SkCodec.h | 解码器基类 |
| src/codec/SkWbmpCodec.h | WBMP 解码器实现类 |
| src/codec/SkWbmpCodec.cpp | WBMP 解码器实现 |
| include/core/SkData.h | 内存数据容器 |
| include/core/SkStream.h | 流接口 |
