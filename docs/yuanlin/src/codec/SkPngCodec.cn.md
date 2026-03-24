# SkPngCodec - PNG 图像解码器（libpng 实现）

> 源文件: `src/codec/SkPngCodec.h`, `src/codec/SkPngCodec.cpp`

## 概述

`SkPngCodec` 是基于 libpng 库的 PNG 图像解码器实现。它继承自 `SkPngCodecBase`，通过 libpng 的渐进式读取接口实现 PNG 数据的解析和解码。该类支持普通（非交错）和交错（interlaced）两种 PNG 格式的解码，同时支持增量解码、扫描行解码和增益图（gainmap）提取。为了避免在头文件中包含 libpng 的头文件，使用了 `voidp` 包装器来持有 `png_ptr` 和 `info_ptr`。

## 架构位置

```
SkCodec
  └── SkPngCodecBase (PNG 公共基类)
        └── SkPngCodec (libpng 实现)
              ├── SkPngNormalDecoder (非交错解码)
              └── SkPngInterlacedDecoder (交错解码)
```

## 主要类与结构体

### `SkPngCodec` (抽象基类)
- 继承自 `SkPngCodecBase`
- 持有 `png_ptr` 和 `info_ptr`（通过 `voidp` 包装）
- 管理 IDAT 长度和解码状态
- 支持增益图流和信息

### `voidp` (内部结构体)
透明的 void 指针包装器，支持自动类型转换和布尔检查，用于隐藏 libpng 类型。

### `AutoCleanPng` (RAII 辅助类)
管理 libpng 结构体的生命周期，在解码边界确定后将所有权转移给 `SkPngCodec`。

### `SkPngNormalDecoder` (非交错解码器)
- 继承自 `SkPngCodec`
- 逐行处理 PNG 数据
- 支持范围设置（`setRange`）用于增量解码

### `SkPngInterlacedDecoder` (交错解码器)
- 继承自 `SkPngCodec`
- 使用完整的行缓冲区处理 7 遍交错扫描
- 在所有遍次完成后批量输出

## 公共 API 函数

### 格式检测
- `static bool IsPng(const void*, size_t)`: 使用 `png_sig_cmp` 检查 PNG 签名

### 工厂方法
- `static MakeFromStream(std::unique_ptr<SkStream>, Result*, SkPngChunkReader*)`: 从流创建 PNG 解码器

### 增益图支持
- `onGetGainmapCodec(SkGainmapInfo*, std::unique_ptr<SkCodec>*)`: 获取增益图编解码器
- `onGetGainmapInfo(SkGainmapInfo*)`: 获取增益图信息

### 解码接口
- `onGetPixels(...)`: 完整像素解码
- `onStartIncrementalDecode(...)`: 开始增量解码
- `onIncrementalDecode(int*)`: 继续增量解码

## 内部实现细节

### setjmp/longjmp 错误处理
libpng 使用 `setjmp`/`longjmp` 进行错误处理。定义了三个 jump 值：
- `kSetJmpOkay (0)`: 正常
- `kPngError (1)`: libpng 内部错误
- `kStopDecoding (2)`: 已解码足够的行，主动停止

### 渐进式数据处理 (`processData`)
- 使用 4096 字节的固定缓冲区
- 首先处理 IDAT 块（使用缓存的长度）
- 然后逐块处理后续块直到 IEND
- 通过 `png_set_progressive_read_fn` 注册回调函数

### 颜色配置文件读取 (`read_color_profile`)
按优先级读取：
1. ICC 配置文件 (`iCCP` 块)
2. sRGB 标记 (`sRGB` 块)
3. 色度 + 伽马 (`cHRM` + `gAMA` 块)
4. 默认 sRGB

### 非交错解码器回调
- `AllRowsCallback`: 完整解码时的行回调，每行调用 `applyXformRow` 并前进目标指针
- `RowCallback`: 增量解码时的行回调，支持范围过滤和采样

### 交错解码器
- 分配 `fHeight * fSrcRowBytes` 的中间缓冲区
- 使用 `png_progressive_combine_row` 合并 7 遍扫描的行数据
- 所有遍次完成后一次性转换和输出

### 边界解码 (`decodeBounds`)
`AutoCleanPng::decodeBounds` 读取 PNG 头部直到第一个 IDAT 块：
- 解析签名（8 字节）
- 逐块处理直到遇到 IDAT
- 在 `infoCallback` 中创建适当的解码器子类

## 依赖关系

- `SkPngCodecBase`: PNG 编解码器公共基类
- libpng (`png.h`): PNG 解码库
- `SkSwizzler`: 像素格式转换
- `SkPngCompositeChunkReader`: 复合块读取器
- `SkPngChunkReader`: 用户自定义块读取器
- skcms: 颜色管理
- `SkGainmapInfo`: 增益图信息

## 设计模式与设计决策

### 模板方法模式
`SkPngCodec` 定义了 `decodeAllRows`、`setRange`、`decode` 三个纯虚方法，由子类（Normal/Interlaced）实现具体的解码策略。

### 类型擦除 (voidp)
使用 `voidp` 避免在头文件中包含 `png.h`，减少编译依赖。

### 错误恢复
区分 "incomplete input"（数据不完整但已正确解码）和 "error in input"（数据损坏），允许显示部分解码的图像。

### Android SafetyNet
在 Android 框架构建中，对特定错误情况记录 SafetyNet 日志。

## 性能考量

- 渐进式读取避免了将整个 PNG 文件加载到内存
- 非交错图像逐行解码，内存使用与图像宽度成正比
- 交错图像需要全图缓冲区，但在移动设备上仍然可接受
- `applyXformRow` 整合了 swizzle 和颜色转换，减少中间步骤
- 使用 `longjmp` 停止解码比继续读取不需要的数据更高效
- 4096 字节缓冲区在 I/O 效率和内存使用之间取得平衡

## 相关文件

- `src/codec/SkPngCodecBase.h` / `.cpp`: PNG 公共基类
- `src/codec/SkPngRustCodec.h` / `.cpp`: Rust png crate 的替代实现
- `src/codec/SkPngCompositeChunkReader.h`: 复合块读取器
- `src/codec/SkPngPriv.h`: PNG 私有工具
- `include/codec/SkPngChunkReader.h`: 用户块读取器接口
- `include/codec/SkPngDecoder.h`: PNG 解码器公共接口
