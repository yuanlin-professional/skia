# SkBmpStandardCodec

> 源文件: src/codec/SkBmpStandardCodec.h, src/codec/SkBmpStandardCodec.cpp

## 概述

`SkBmpStandardCodec` 是 BMP 标准格式解码器，处理不包含位掩码或 RLE 压缩的 BMP 图片。支持 1/2/4/8 位索引色、24 位 BGR 和 32 位 BGRA 格式。该类继承自 `SkBmpBaseCodec`，实现了完整的解码流程，包括颜色表处理、像素转换和 ICO 嵌入 BMP 的透明掩码应用。

## 架构位置

继承层次: `SkCodec → SkBmpCodec → SkBmpBaseCodec → SkBmpStandardCodec`

## 主要成员变量

- `sk_sp<SkColorPalette> fColorTable`: 调色板（1-8 位图片使用）
- `const uint32_t fNumColors`: 颜色表中的颜色数
- `const uint32_t fBytesPerColor`: 每个颜色的字节数（3 或 4）
- `const uint32_t fOffset`: 像素数据偏移量
- `std::unique_ptr<SkSwizzler> fSwizzler`: 像素格式转换器
- `const bool fIsOpaque`: BMP 本身是否不透明
- `const bool fInIco`: 是否嵌入在 ICO 文件中
- `const size_t fAndMaskRowBytes`: AND 掩码行字节数（仅用于 ICO）

## 公共 API 函数

### 构造函数
```cpp
SkBmpStandardCodec(SkEncodedInfo&& info, std::unique_ptr<SkStream> stream,
                   uint16_t bitsPerPixel, uint32_t numColors, uint32_t bytesPerColor,
                   uint32_t offset, SkCodec::SkScanlineOrder rowOrder,
                   bool isOpaque, bool inIco)
```
初始化标准 BMP 解码器，计算 AND 掩码行字节数（ICO 中使用）。

### 核心解码方法

**onGetPixels**: 完整图片解码
1. 验证无子区域和缩放请求
2. 调用 `prepareToDecode` 准备颜色表和 Swizzler
3. 调用 `decodeRows` 逐行解码
4. 返回解码结果

**onPrepareToDecode**: 解码准备
1. 创建颜色表（调用 `createColorTable`）
2. 初始化 Swizzler（调用 `initializeSwizzler`）
3. 准备颜色转换缓冲区（如需要）

**decodeRows**: 逐行解码
1. 读取源行数据到 `srcBuffer()`
2. 确定目标行号（处理自底向上/自顶向下）
3. 使用 Swizzler 转换像素格式
4. 应用颜色转换（如需要）
5. 处理 ICO 透明掩码（如需要）

## 内部实现细节

### 颜色表处理（createColorTable）

**读取和解析**:
```cpp
uint32_t maxColors = 1 << bitsPerPixel();  // 1, 4, 16, 256
uint32_t numColorsToRead = std::min(fNumColors, maxColors);
colorBytes = numColorsToRead * fBytesPerColor;  // 读取字节数
```

**颜色打包**:
- 根据目标格式选择打包函数（`SkCodecPriv::ChoosePackColorProc`）
- BGR/BGRA 顺序读取：Blue, Green, Red, Alpha
- 不透明图片强制 Alpha = 0xFF
- 未使用的颜色表项填充黑色（防止越界访问）

**颜色转换**:
```cpp
if (this->colorXform() && !this->xformOnDecode()) {
    this->applyColorXform(colorTable, colorTable, maxColors);
}
```

**偏移量处理**:
- 非 ICO: 跳过到像素数据偏移量
- ICO: 像素数据紧跟颜色表

### Swizzler 初始化（initializeSwizzler）

Swizzler 负责像素格式转换：
- 索引色 → RGB/RGBA
- BGR → RGB
- BGRA → RGBA
- 处理采样（如需要）

**ICO 特殊处理**:
- 客户端接收 BGRA 格式（预留 Alpha 通道）
- Swizzler 需要知道实际 BMP 格式

**颜色转换模式**:
```cpp
if (this->xformOnDecode()) {
    swizzlerInfo = swizzlerInfo.makeColorType(kXformSrcColorType);  // BGRA_8888
    swizzlerInfo = swizzlerInfo.makeAlphaType(kUnpremul_SkAlphaType);
}
```

### ICO 透明掩码（decodeIcoMask）

ICO 中的 BMP 包含额外的 1 位 AND 掩码：
- 位为 1: 透明（Alpha = 0）
- 位为 0: 不透明（保留原 Alpha）

**掩码应用**:
```cpp
uint64_t alphaBit = (srcBuffer[quotient] >> shift) & 0x1;
dst[x] &= alphaBit - 1;  // alphaBit=1 → 0x0, alphaBit=0 → 0xFFFFFFFF
```

**扫描线解码**:
- 计算掩码在流中的位置
- 创建子流访问掩码数据
- 仅处理请求的扫描线

**采样支持**:
- 仅在 X 方向采样（Y 方向由 `SkSampledCodec` 处理）
- 根据采样因子跳过源像素

## 依赖关系

### 直接依赖
- **SkBmpBaseCodec**: 父类，提供源缓冲区
- **SkSwizzler**: 像素格式转换
- **SkColorPalette**: 调色板存储
- **SkCodecPriv**: 工具函数（行字节计算、颜色打包等）
- **SkColorPriv**: 颜色操作宏

## 设计模式与设计决策

### 模板方法模式
基类定义框架，子类实现具体步骤：
- `onGetPixels` 调用 `prepareToDecode` 和 `decodeRows`
- `decodeRows` 由子类实现具体解码逻辑

### 策略模式
根据图片属性选择不同策略：
- 颜色打包策略（预乘 vs 未预乘）
- Swizzler 策略（索引色、RGB、BGRA）
- ICO 掩码策略（有/无透明掩码）

### 防御性编程
- 未使用的颜色表项填充黑色
- 流读取失败时返回已解码行数
- 偏移量验证防止越界

## 性能考量

### 内存效率
- 单行源缓冲区重用
- 颜色表最多 256 项（1KB）
- 按需分配颜色转换缓冲区

### 解码性能
- Swizzler 使用 SIMD 优化（平台相关）
- 颜色表预转换（避免逐像素转换）
- 直接内存访问（无额外拷贝）

### ICO 特殊处理
- 掩码延迟应用（仅在需要时）
- 子流避免额外内存分配
- 扫描线模式支持增量解码

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/codec/SkBmpBaseCodec.h` | 父类 | 提供源缓冲区管理 |
| `src/codec/SkSwizzler.h` | 依赖 | 像素格式转换 |
| `src/codec/SkColorPalette.h` | 依赖 | 调色板存储 |
| `src/codec/SkCodecPriv.h` | 工具 | 内部工具函数 |
| `src/core/SkColorPriv.h` | 工具 | 颜色操作宏 |
