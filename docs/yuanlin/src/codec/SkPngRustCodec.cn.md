# SkPngRustCodec - PNG 图像解码器（Rust 实现）

> 源文件: `src/codec/SkPngRustCodec.h`, `src/codec/SkPngRustCodec.cpp`

## 概述

`SkPngRustCodec` 是基于第三方 Rust `png` crate 的 PNG 图像解码器实现。它提供了与基于 libpng 的 `SkPngCodec` 相同的 `SkCodec` API，但底层 PNG 解压缩和解码由 Rust 代码完成。Skia 的 `SkSwizzler` 和 `skcms_Transform` 仍负责像素格式和颜色空间转换。该实现支持 APNG（动画 PNG），包括多帧解码、帧间混合和处置。

## 架构位置

```
SkCodec
  └── SkPngCodecBase (PNG 公共基类)
        ├── SkPngCodec (libpng C 实现)
        └── SkPngRustCodec (Rust png crate 实现, final)
              ├── rust_png::Reader (Rust PNG 读取器)
              ├── FrameHolder (帧管理)
              └── SkSwizzler / skcms_Transform (C++ 像素处理)
```

## 主要类与结构体

### `SkPngRustCodec`
- 继承自 `SkPngCodecBase`（`final` 类）
- 持有 `rust::Box<rust_png::Reader>` 作为 Rust 解码器
- 管理帧位置追踪、流所有权和增量解码状态
- 支持交错和非交错 PNG 以及 APNG 动画

### `DecodingDstInfo` (内部结构体)
描述解码目标缓冲区的信息：目标内存范围、行步进、行大小和每像素字节数。

### `DecodingState` (内部结构体)
保存增量解码状态：目标信息、预混合缓冲区、行范围和子集偏移。

### `FrameHolder` (内部类)
- 继承自 `SkFrameHolder`
- 管理 APNG 帧信息的集合
- 支持动态添加帧和标记帧为完全接收
- 内部使用 `PngFrame` 类存储帧数据

## 公共 API 函数

### 工厂方法
- `static MakeFromStream(std::unique_ptr<SkStream>, Result*)`: 创建解码器，初始化 Rust 读取器，验证图像信息和 fcTL 块

### 动画支持
- `onGetFrameCount()`: 返回当前已知的帧数
- `onGetFrameInfo(int, FrameInfo*)`: 获取帧信息
- `onGetRepetitionCount()`: 返回循环次数
- `onIsAnimated()`: 检查是否为动画图像

### 解码
- `onGetPixels(...)`: 完整解码
- `onStartIncrementalDecode(...)` / `onIncrementalDecode(...)`: 增量解码

## 内部实现细节

### Rust FFI 集成
- 通过 `rust/png/FFI.rs.h` 和 `cxx` 库进行 Rust-C++ 互操作
- Rust 类型（`ColorType`、`DisposeOp`、`BlendOp`）映射到 Skia 类型
- `SkStreamAdapter` 将 `SkStream` 适配为 Rust 可用的输入

### 颜色配置文件创建 (`CreateColorProfile`)
按优先级处理：
1. `cICP` 块（最高优先级，根据 PNG 3.0 规范）
2. `iCCP` 块（ICC 配置文件）
3. `sRGB` 块
4. `gAMA` + `cHRM` 块
5. 仅 `gAMA` 块（检查中性伽马以避免不必要的颜色配置文件）

### 帧导航
- `seekToStartOfFrame(int index)`: 导航到指定帧的数据起始位置
  - 支持回退（通过流的 rewind/seek）
  - 支持前进（通过 `readToStartOfNextFrame`）
- `fFrameAtCurrentStreamPosition`: 追踪当前流位置对应的帧
- `fStreamIsPositionedAtStartOfFrameData`: 标记流是否位于帧数据起始

### APNG 混合
使用 `SkRasterPipeline` 实现帧间混合：
- `blendRow`: 对单行执行 SrcOver 混合
- `blendAllRows`: 对整个帧缓冲区执行混合
- 支持预乘和非预乘 Alpha

### 交错图像处理
- 非交错: `incrementalDecode` 逐行读取和转换
- 交错: 使用 `fPreblendBuffer` 作为全帧缓冲区
- 子集处理: `getSubsetFromFullImage` 从全尺寸缓冲区提取子集

### fcTL 验证
在构造时验证 IDAT 之前的 `fcTL` 块（如果存在）：
- 宽高必须与 `IHDR` 一致
- 偏移必须为 (0,0)
- 这是深度防御措施（长期应在 Rust crate 中处理）

### 流管理
流被"隐藏"在 `fPrivStream` 中，不传给基类的 `SkCodec`，以避免不必要的 rewind 操作。

## 依赖关系

- `SkPngCodecBase`: PNG 公共基类
- Rust `png` crate（通过 `FFI.rs.h`）
- `cxx`: C++/Rust 互操作库
- `SkFrameHolder` / `SkFrame`: 动画帧管理
- `SkSwizzler`: 像素格式转换
- `skcms`: 颜色管理
- `SkRasterPipeline`: 像素管道（帧混合）
- `SkParseEncodedOrigin`: EXIF 方向解析
- `SkSafeMath`: 安全整数运算

## 设计模式与设计决策

### FFI 桥接
通过 `cxx` 库实现类型安全的 Rust-C++ 互操作，避免手动的 `unsafe` FFI。

### 延迟帧解析
帧信息（`fcTL` 块）按需解析，通过 `parseAdditionalFrameInfos` 逐步发现新帧。

### 流位置追踪
由于不可寻址流的限制，使用 `fFrameAtCurrentStreamPosition` 手动追踪流位置，而非依赖流的 seek 功能。

### 安全转换
广泛使用 `SkSafeMath` 和 `SkASSERT_RELEASE` 进行安全的类型转换，防止整数溢出。

### 尺寸限制
强制 PNG 尺寸不超过 1,000,000 像素（宽或高），防止内存溢出攻击。

## 性能考量

- Rust PNG 解码器处理解压缩，C++ 处理像素转换，各取所长
- 非交错图像的内存使用与图像宽度成正比
- 交错图像需要全帧缓冲区
- `canReadRow()` 检查是否可以直接读取到目标缓冲区（跳过中间转换）
- APNG 帧导航支持前向和后向定位，优化随机帧访问
- 预混合缓冲区仅在需要 SrcOver 混合时分配

## 相关文件

- `src/codec/SkPngCodecBase.h` / `.cpp`: PNG 公共基类
- `src/codec/SkPngCodec.h` / `.cpp`: libpng 实现（替代方案）
- `rust/png/FFI.rs.h`: Rust FFI 接口
- `src/codec/SkFrameHolder.h`: 动画帧管理
- `src/codec/SkPngPriv.h`: PNG 私有工具
- `src/codec/SkParseEncodedOrigin.h`: EXIF 方向解析
