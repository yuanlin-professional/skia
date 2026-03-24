# SkSwizzler - 像素格式转换与采样器

> 源文件: `src/codec/SkSwizzler.h`, `src/codec/SkSwizzler.cpp`

## 概述

`SkSwizzler` 是 Skia 编解码模块中最核心的像素处理组件之一，负责将编码图像的原始像素数据转换（swizzle）为 Skia 内部使用的目标像素格式。它同时承担像素格式转换和降采样两项关键职责。该类支持丰富的源格式（1-bit 位图、调色板索引、灰度、灰度带 Alpha、RGB、RGBA、BGR、BGRA、CMYK 等）到多种目标格式（RGBA_8888、BGRA_8888、RGB_565、Gray_8、RGBA_F16 等）的转换，包括预乘 Alpha 处理。

## 架构位置

```
SkSampler (采样基类)
  └── SkSwizzler
        ├── RowProc (函数指针, 实际转换逻辑)
        │   ├── fFastProc (优化路径, 不支持采样)
        │   ├── fSlowProc (通用路径, 支持采样)
        │   └── fActualProc (当前激活的处理函数)
        └── 子集/帧管理参数
```

`SkSwizzler` 被 PNG、BMP、WBMP、GIF 等几乎所有图像编解码器使用。

## 主要类与结构体

### `SkSwizzler`
- 继承自 `SkSampler`
- 通过函数指针 (`RowProc`) 实现多态的行处理
- 管理源/目标偏移、采样率和子集参数
- 支持两种子集模式：部分扫描行和帧子集

### `RowProc` 类型定义
```cpp
typedef void (*RowProc)(void* dstRow, const uint8_t* src,
    int dstWidth, int bpp, int deltaSrc, int offset, const SkPMColor ctable[]);
```
每个 RowProc 处理一行像素，参数包括目标缓冲区、源数据、宽度、每像素位/字节数、源步进、偏移和颜色表。

## 公共 API 函数

### 工厂方法
- `Make(const SkEncodedInfo&, const SkPMColor*, const SkImageInfo&, const SkCodec::Options&, const SkIRect*)`: 根据编码信息和目标格式创建完整的 swizzler，自动选择最佳的转换函数。
- `MakeSimple(int srcBPP, const SkImageInfo&, const SkCodec::Options&, const SkIRect*)`: 创建仅执行采样的简化 swizzler，不做格式转换。

### 操作方法
- `swizzle(void* dst, const uint8_t* src)`: 转换一行像素数据。
- `sampleX()`: 获取当前 X 采样率。
- `swizzleWidth()`: 获取实际写入的像素数。
- `swizzleOffsetBytes()`: 获取写入的字节偏移。
- `fillWidth()`: 获取填充宽度（用于 SkSampler 接口）。

## 内部实现细节

### 转换函数选择
`Make` 方法中的大型 switch-case 结构根据源颜色类型和目标颜色类型组合选择最佳的 RowProc。选择逻辑考虑：
- 源格式：Gray(1/8bit)、GrayAlpha、Palette(1/2/4/8bit)、RGB(8/16bit)、RGBA(8/16bit)、BGR、BGRA、InvertedCMYK
- 目标格式：RGBA_8888、BGRA_8888、RGB_565、Gray_8、Alpha_8、RGBA_F16
- Alpha 处理：预乘 vs 非预乘
- 零初始化优化：使用 `SkipLeading8888ZerosThen` 跳过前导零像素

### 快速路径与慢速路径
- `fFastProc`: 使用 `SkOpts` 平台优化函数（如 `RGBA_to_rgbA`、`gray_to_RGB1`），不支持采样
- `fSlowProc`: 通用实现，支持任意采样率
- 当 `sampleX == 1` 且 `fFastProc` 存在时使用快速路径

### 子集处理
支持两种互斥的子集模式：
1. **部分扫描行**：客户端只需源像素的子集（通过 `options.fSubset` 指定）
2. **帧子集**：客户端解码整行但写入目标内存的子集（用于 GIF 帧）

关键字段包括 `fSrcOffset`、`fDstOffset`、`fSrcWidth`、`fDstWidth`、`fSwizzleWidth`、`fAllocatedWidth`。

### CMYK 转换
使用简化的公式进行反转 CMYK 到 RGB 的转换：
```
R = C * K / 255
G = M * K / 255
B = Y * K / 255
```
（其中 CMYK 值已被 libjpeg 反转）

### 16 位分量处理
16 位 RGB/RGBA 源数据通过 `strip16to8` lambda 截断为 8 位。

### 零像素跳过优化
`SkipLeading8888ZerosThen` 和 `SkipLeadingGrayAlphaZerosThen` 模板函数在零初始化的目标内存上跳过前导零值源像素，减少不必要的写入。

## 依赖关系

- `SkSampler`: 基类，提供采样接口
- `SkEncodedInfo`: 编码格式描述
- `SkCodec::Options`: 解码选项（子集、零初始化等）
- `SkOpts`: 平台优化的批量像素处理函数
- `SkCodecPriv`: 私有工具函数（预乘、坐标计算等）
- `SkColorData` / `SkColorPriv`: 颜色打包/拆包函数
- `SkHalf`: 半精度浮点数支持（F16 格式）

## 设计模式与设计决策

### 策略模式
通过函数指针 (`RowProc`) 实现运行时的策略选择，避免虚函数调用开销。

### 双层优化
快速路径（批量操作）和慢速路径（逐像素操作）并存，根据采样状态动态切换。

### 不支持同时使用两种子集模式
部分扫描行和帧子集是互斥的（由断言保证），简化了实现。

### Android Framework 兼容
在 Android 框架构建中，包含针对特定安全问题的 SafetyNet 日志。

## 性能考量

- **快速路径**使用 SIMD 优化的批量操作（`SkOpts::RGBA_to_rgbA` 等），处理非采样场景
- **采样时跳过像素**而非解码后丢弃，通过 `deltaSrc = sampleX * srcBPP` 直接跳过源数据
- **零像素跳过**在透明图像中显著减少目标写入量
- **`copy` 函数**对于不需要转换的格式直接使用 `memcpy`
- **帧子集偏移**预计算为字节偏移，避免每行的乘法运算
- 采样率变化时动态切换处理函数，避免不必要的分支检查

## 相关文件

- `src/codec/SkSampler.h`: 采样基类
- `src/codec/SkMaskSwizzler.h` / `.cpp`: 掩码位图的 swizzler
- `src/codec/SkCodecPriv.h`: 编解码器私有工具
- `src/core/SkSwizzlePriv.h`: 平台优化的 swizzle 函数
- `include/private/SkEncodedInfo.h`: 编码格式描述
- `src/core/SkColorData.h` / `SkColorPriv.h`: 颜色操作函数
