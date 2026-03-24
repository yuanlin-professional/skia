# SkWbmpCodec - WBMP 图像解码器

> 源文件: `src/codec/SkWbmpCodec.h`, `src/codec/SkWbmpCodec.cpp`

## 概述

`SkWbmpCodec` 是 Skia 编解码模块中用于解码 WBMP（Wireless Bitmap）格式图像的编解码器。WBMP 是一种极其简单的单色位图格式，最初为移动设备设计。每个像素仅用 1 位表示（黑或白），因此该编解码器使用 `SkSwizzler` 将位数据展开为目标颜色格式。

## 架构位置

```
SkCodec (基类)
  └── SkWbmpCodec (final 类)
        └── SkSwizzler (像素格式转换)
```

`SkWbmpCodec` 是一个叶子类（`final`），不允许进一步继承。

## 主要类与结构体

### `SkWbmpCodec`
- 继承自 `SkCodec`（`final`）
- 使用 `SkSwizzler` 进行像素格式转换
- 维护源行缓冲区用于逐行读取
- `fSrcRowBytes`: 源数据每行的字节数（按 8 位对齐后的位宽除以 8）

## 公共 API 函数

### `static bool IsWbmp(const void*, size_t)`
通过解析 WBMP 头部验证格式有效性。

### `static std::unique_ptr<SkCodec> MakeFromStream(std::unique_ptr<SkStream>, Result*)`
从流创建 WBMP 解码器，读取头部获取图像尺寸。

### `SkWbmpDecoder::Decode`
命名空间级别的解码入口，提供 `SkStream` 和 `SkData` 两种重载。

## 内部实现细节

### WBMP 头部解析 (`read_header`)
WBMP 头部格式：
1. 1 字节类型（必须为 0）
2. 1 字节固定头（低 5 位和最高位必须为 0）
3. 可变长度编码（MBF）的宽度
4. 可变长度编码（MBF）的高度

宽高使用可变长度编码（Variable-length quantity），每字节的最高位为续行标志。

### 源行字节计算
```cpp
static inline size_t get_src_row_bytes(int width) {
    return SkAlign8(width) >> 3;
}
```
宽度（位数）向上对齐到 8 的倍数，然后除以 8 得到字节数。

### 像素解码
- `onGetPixels`: 创建临时 `SkSwizzler`，逐行读取源数据并转换
- 扫描行解码: 使用 `fSwizzler`（持久化的）和 `fSrcBuffer` 进行逐行处理
- 不支持子集解码（返回 `kUnimplemented`）

### 颜色转换
- `conversionSupported`: 支持 RGBA_8888、BGRA_8888、Gray_8、RGB_565，以及有色彩空间时的 RGBA_F16
- `usesColorXform` 返回 `false`：因为像素只有黑白两色，无需颜色变换

## 依赖关系

- `SkCodec`: 基类
- `SkSwizzler`: 像素格式转换（将 1-bit 展开为目标格式）
- `SkStream`: 数据流操作
- `SkEncodedInfo`: 编码信息（灰度、不透明、1 位深度）
- `SkCodecPriv`: 工具函数（`ValidAlpha`）

## 设计模式与设计决策

### 简单直接的设计
WBMP 格式非常简单，因此编解码器也保持了最小化的实现。没有颜色表、无压缩、无 Alpha 通道。

### 无颜色变换
由于 WBMP 只有黑白两色，选择不使用颜色变换管线 (`usesColorXform() = false`)，简化了解码路径。

### 编码信息
图像始终报告为灰度（`kGray_Color`）、不透明（`kOpaque_Alpha`）、1 位深度。

## 性能考量

- 每行数据量极小（宽度/8 字节），逐行读取开销低
- `SkSwizzler` 内的 `swizzle_bit_to_*` 函数高效地将位数据展开为目标格式
- 跳过扫描行时直接使用流的 `skip` 方法，无需读取和处理数据

## 相关文件

- `include/codec/SkWbmpDecoder.h`: 公共 WBMP 解码器接口
- `src/codec/SkSwizzler.h` / `.cpp`: 像素格式转换器
- `src/codec/SkCodecPriv.h`: 编解码器私有工具
- `include/codec/SkCodec.h`: 编解码器基类
