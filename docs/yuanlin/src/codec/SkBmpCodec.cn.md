# SkBmpCodec

> 源文件: src/codec/SkBmpCodec.h, src/codec/SkBmpCodec.cpp

## 概述

`SkBmpCodec` 是 Skia 中 BMP (Bitmap) 图片格式解码器的核心基类，负责解析 BMP 文件头、识别格式变体，并创建相应的具体解码器子类。该类实现了 BMP 格式的完整头部解析逻辑，支持多种 BMP 版本（Windows V1-V5、OS/2 V1/VX）和压缩方式（无压缩、RLE、位掩码）。

作为抽象基类，`SkBmpCodec` 本身不执行像素解码，而是根据头部信息分派给专门的子类：`SkBmpStandardCodec`（标准格式）、`SkBmpMaskCodec`（位掩码格式）和 `SkBmpRLECodec`（RLE 压缩格式）。它还处理 BMP 嵌入在 ICO 文件中的特殊情况。

## 架构位置

`SkBmpCodec` 在 Skia 解码器体系中的位置：

```
SkCodec (所有解码器基类)
    ↓
SkBmpCodec (BMP 解码器基类)
    ↓
    ├─ SkBmpBaseCodec → SkBmpStandardCodec (标准格式)
    ├─ SkBmpBaseCodec → SkBmpMaskCodec (位掩码格式)
    └─ SkBmpRLECodec (RLE 压缩格式)
```

**职责划分**:
- **格式识别**: 静态方法 `IsBmp()` 检查文件魔数
- **头部解析**: `ReadHeader()` 解析所有 BMP 头部类型
- **子类分派**: 根据压缩方式和位深度创建具体解码器
- **公共功能**: 提供行顺序转换、缓冲区管理等共享功能

**支持的格式**:
- Windows BMP V1/V2/V3/V4/V5
- OS/2 BMP V1/VX
- 压缩方式：无压缩、4/8 位 RLE、位掩码
- 位深度：1、2、4、8、16、24、32 位
- 特殊场景：BMP 嵌入 ICO 文件

## 主要类与结构体

### SkBmpCodec 类

**继承关系**: `SkBmpCodec → SkCodec → SkRefCnt`

**主要成员变量**:
- `const uint16_t fBitsPerPixel`: 每像素位数
- `const SkScanlineOrder fRowOrder`: 行扫描顺序（自顶向下或自底向上）
- `const size_t fSrcRowBytes`: 源行字节数（4 字节对齐）
- `std::unique_ptr<uint32_t[]> fXformBuffer`: 颜色转换临时缓冲区

### 内部枚举类型

**BmpHeaderType** - BMP 头部类型
- `kInfoV1/V2/V3/V4/V5_BmpHeaderType`: Windows BMP 版本 1-5
- `kOS2V1/VX_BmpHeaderType`: OS/2 BMP 版本
- `kUnknown_BmpHeaderType`: 未知或不支持的类型

**BmpCompressionMethod** - 压缩方式
- `kNone_BmpCompressionMethod`: 无压缩
- `k4BitRLE/k8BitRLE_BmpCompressionMethod`: RLE 压缩
- `kBitMasks/kAlphaBitMasks_BmpCompressionMethod`: 位掩码
- `kJpeg/kPng_BmpCompressionMethod`: 嵌入 JPEG/PNG（不支持）
- `kCMYK_*`: CMYK 色彩空间（不支持）

**BmpInputFormat** - 输入格式类型
- `kStandard_BmpInputFormat`: 标准格式
- `kRLE_BmpInputFormat`: RLE 压缩
- `kBitMask_BmpInputFormat`: 位掩码
- `kUnknown_BmpInputFormat`: 未知格式

## 公共 API 函数

### 格式识别

**IsBmp**
```cpp
static bool IsBmp(const void* buffer, size_t bytesRead)
```
检查数据是否为 BMP 格式，通过验证魔数 "BM"（0x42 0x4D）。

**支持的魔数**: 当前仅支持 "BM"，TODO 注释表明未来可能支持 "IC"、"PT"、"CI"、"CP"、"BA" 等变体。

### 解码器创建

**MakeFromStream**
```cpp
static std::unique_ptr<SkCodec> MakeFromStream(std::unique_ptr<SkStream>, Result*)
```
从流创建 BMP 解码器，假设已通过 `IsBmp()` 检查。内部调用私有重载 `MakeFromStream(..., false)`。

**MakeFromIco**
```cpp
static std::unique_ptr<SkCodec> MakeFromIco(std::unique_ptr<SkStream>, Result*)
```
为 ICO 文件中嵌入的 BMP 创建解码器。ICO 中的 BMP 跳过文件头，且高度字段加倍（包含 XOR 和 AND 掩码）。

### 重写的基类方法

**onGetEncodedFormat**
```cpp
SkEncodedImageFormat onGetEncodedFormat() const override
```
返回 `SkEncodedImageFormat::kBMP`。

**onRewind**
```cpp
bool onRewind() override
```
倒回流并重新解析头部，验证格式仍然有效。

**onGetScanlineOrder**
```cpp
SkScanlineOrder onGetScanlineOrder() const override
```
返回 `fRowOrder`（`kTopDown` 或 `kBottomUp`）。

## 内部实现细节

### 头部解析流程（ReadHeader）

这是 `SkBmpCodec` 最复杂的方法，分为以下阶段：

**1. 读取第一头部** (非 ICO 模式)
```cpp
uint8_t hBuffer[kBmpHeaderBytesPlusFour];  // 14 + 4 = 18 字节
```
- 字节 0-1: 魔数 "BM"
- 字节 2-5: 文件总大小
- 字节 10-13: 像素数据偏移量
- 字节 14-17: 第二头部大小

**2. 识别头部类型**

根据第二头部大小判断版本：
- 12 字节: OS/2 V1
- 40 字节: Windows V1 (最常见)
- 52 字节: Windows V2
- 56 字节: Windows V3
- 108 字节: Windows V4
- 124 字节: Windows V5
- 64 字节: OS/2 V2
- 其他大小: OS/2 VX 的各种变体

**3. 解析图片信息**

根据头部类型提取不同的字段：

**Windows V1+ / OS/2 VX**:
- 宽度/高度: 32 位整数
- 每像素位数: 16 位整数
- 压缩方式: 32 位整数（V1+）
- 颜色表项数: 32 位整数
- 每色字节数: 4 字节

**OS/2 V1**:
- 宽度/高度: 16 位整数
- 每像素位数: 16 位整数
- 每色字节数: 3 字节

**4. 处理特殊情况**

**负高度**: 表示自顶向下扫描
```cpp
if (height < 0) {
    height = -height;
    rowOrder = kTopDown_SkScanlineOrder;
}
```

**ICO 嵌入**: 高度除以 2
```cpp
if (inIco) {
    height /= 2;  // XOR 掩码和 AND 掩码各占一半
}
```

**尺寸限制**: 最大 65536 x 65536（与 Chromium 一致）

**5. 处理位掩码**

**16 位无压缩**: 默认使用 555 掩码
```cpp
if (16 == bitsPerPixel && kNone_BmpCompressionMethod == compression) {
    inputMasks.red   = 0x7C00;  // 5 位
    inputMasks.green = 0x03E0;  // 5 位
    inputMasks.blue  = 0x001F;  // 5 位
}
```

**显式位掩码**: 从头部或附加数据读取
- V1: 12 字节附加掩码数据
- V2+: 头部包含红/绿/蓝/Alpha 掩码字段

**Alpha 掩码特殊处理**:
- V3 及以下: 忽略 Alpha 掩码（大多数图片留空）
- V4+: 使用 Alpha 掩码
- BMP-in-ICO V3: 使用 Alpha 掩码（特例）

**6. 创建具体解码器**

根据 `inputFormat` 分派：

**kStandard_BmpInputFormat**:
```cpp
*codecOut = std::make_unique<SkBmpStandardCodec>(...);
```
处理 1/2/4/8 位调色板、24 位 BGR、32 位 BGRA/BGRX。

**kBitMask_BmpInputFormat**:
```cpp
*codecOut = std::make_unique<SkBmpMaskCodec>(...);
```
处理 16/24/32 位带位掩码的 BMP。

**kRLE_BmpInputFormat**:
```cpp
*codecOut = std::make_unique<SkBmpRLECodec>(...);
```
处理 4/8 位 RLE 压缩的 BMP。

### 扫描线解码实现

**onStartScanlineDecode**: 调用 `prepareToDecode`，后者委托给纯虚函数 `onPrepareToDecode`（子类实现）。

**onGetScanlines**: 创建表示部分图片的 `SkImageInfo`，调用纯虚函数 `decodeRows`。

**onSkipScanlines**: 跳过指定行数，默认通过 `skipRows` 在流中跳过字节。

### 行顺序转换

**getDstRow**
```cpp
int32_t getDstRow(int32_t y, int32_t height) const
```
将编码行号转换为目标行号：
- `kTopDown`: 返回 `y`
- `kBottomUp`: 返回 `height - y - 1`（反转）

## 依赖关系

### 直接依赖
- **SkCodec**: 基类
- **SkEncodedInfo**: 编码元信息
- **SkStream**: 数据流接口
- **SkMasks**: 位掩码管理
- **SkCodecPriv**: 内部工具函数（字节读取、行字节计算）
- **skcms**: 颜色空间转换（像素格式常量）
- **SkBmpStandardCodec/SkBmpMaskCodec/SkBmpRLECodec**: 具体解码器

### 被依赖
- **SkBmpDecoder**: 公共 API 封装
- **SkCodec**: 通过工厂方法注册
- **ICO 解码器**: 用于解码 ICO 中的 BMP

## 设计模式与设计决策

### 工厂方法模式（Factory Method Pattern）

`ReadHeader` 是复杂的工厂方法：
- 解析头部确定格式
- 根据格式创建相应的子类实例
- 封装复杂的决策逻辑

### 策略模式（Strategy Pattern）

不同的压缩方式对应不同的解码策略（子类）：
- `SkBmpStandardCodec`: 无压缩策略
- `SkBmpRLECodec`: RLE 解码策略
- `SkBmpMaskCodec`: 位掩码转换策略

### 模板方法模式（Template Method Pattern）

基类定义解码流程，子类实现具体步骤：
- `prepareToDecode`: 调用子类的 `onPrepareToDecode`
- `onGetScanlines`: 调用子类的 `decodeRows`

### 错误处理策略

**渐进式验证**: 每个解析步骤都检查错误
```cpp
if (stream->read(buffer, size) != size) {
    SkCodecPrintf("Error: unable to read...\n");
    return kIncompleteInput;
}
```

**格式修正**: 部分错误尝试修复
```cpp
if (bitsPerPixel != 8 && compression == k8BitRLE) {
    SkCodecPrintf("Warning: correcting invalid bitmap format.\n");
    bitsPerPixel = 8;
}
```

**不支持的格式**: 明确返回 `kUnimplemented`
- JPEG/PNG 嵌入
- CMYK 色彩空间
- Huffman 压缩（OS/2 VX）

### 颜色格式选择

**常量定义**:
```cpp
inline static constexpr SkColorType kXformSrcColorType = kBGRA_8888_SkColorType;
inline static constexpr auto kXformSrcColorFormat = skcms_PixelFormat_BGRA_8888;
```

**原因**: BMP 通常使用 BGRA/BGR 顺序，比 RGBA 更高效（避免通道交换）。

## 性能考量

### 内存使用

**单行缓冲**: 仅分配一行的源数据（由 `SkBmpBaseCodec` 管理）
- 降低内存占用
- 支持流式解码
- 适合大图片

**颜色转换缓冲**: `fXformBuffer` 按需分配
- 用于颜色空间转换
- 大小根据输出宽度确定
- 避免重复分配

### 对齐优化

**4 字节行对齐**: BMP 格式要求
```cpp
fSrcRowBytes = SkAlign4(SkCodecPriv::ComputeRowBytes(width, bitsPerPixel))
```
确保 CPU 高效访问。

### 头部解析优化

**一次性读取**: 尽可能一次读取完整头部
```cpp
uint8_t hBuffer[kBmpHeaderBytesPlusFour];
stream->read(hBuffer, kBmpHeaderBytesPlusFour);
```

**避免重复解析**: `onRewind` 重新验证但不重新创建对象。

### 格式检测效率

**快速魔数检查**: `IsBmp` 仅检查 2 字节
**延迟详细解析**: 完整头部解析仅在需要解码时执行

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/codec/SkCodec.h` | 基类 | 所有解码器的基类 |
| `src/codec/SkBmpStandardCodec.h` | 子类 | 标准格式解码器 |
| `src/codec/SkBmpMaskCodec.h` | 子类 | 位掩码格式解码器 |
| `src/codec/SkBmpRLECodec.h` | 子类 | RLE 压缩格式解码器 |
| `src/codec/SkBmpBaseCodec.h` | 中间类 | 缓冲区管理基类 |
| `include/codec/SkBmpDecoder.h` | 公共 API | 公开的解码器接口 |
| `src/codec/SkCodecPriv.h` | 工具 | 内部工具函数 |
| `src/core/SkMasks.h` | 工具 | 位掩码处理 |
| `include/private/SkEncodedInfo.h` | 数据结构 | 编码信息 |
| `modules/skcms/skcms.h` | 依赖 | 颜色管理系统 |
