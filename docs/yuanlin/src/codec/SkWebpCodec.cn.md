# SkWebpCodec

> 源文件: src/codec/SkWebpCodec.h, src/codec/SkWebpCodec.cpp

## 概述

`SkWebpCodec` 是 Skia 图像解码框架中专门处理 WebP 格式的解码器，基于 Google 的 libwebp 库实现。WebP 是一种现代图像格式，支持有损和无损压缩、动画、透明度等特性，广泛应用于 Web 和移动平台。该解码器继承自 `SkScalingCodec`，支持高效的缩放解码、子区域提取和动画帧处理。

该类的核心功能包括：识别 WebP 格式、解析容器结构（RIFF）、提取 ICCP 和 EXIF 元数据、解码单帧和多帧动画、支持 YUV 和 BGRA 两种编码格式的自动识别与转换。它特别优化了流式解码场景，支持仅解析头部进行快速元数据提取，延迟加载完整数据直到真正需要解码时。

## 架构位置

```
SkCodec (抽象基类)
  └── SkScalingCodec (支持缩放的解码器基类)
        └── SkWebpCodec (WebP 专用解码器)
              ├── libwebp (第三方库)
              │     ├── WebPDemuxer (容器解析)
              │     └── WebPDecoder (像素解码)
              └── FrameHolder (动画帧管理)
```

在解码流程中的作用：
1. **识别阶段**：`IsWebp()` 检查文件签名（"RIFF" + "WEBPVP"）
2. **创建阶段**：`MakeFromStream()` 解析头部，创建解码器实例
3. **元数据阶段**：提取 ICC 配置、EXIF 方向、动画信息
4. **解码阶段**：`onGetPixels()` 执行实际的像素解码和格式转换

## 主要类与结构体

### SkWebpCodec

WebP 解码器主类，封装 libwebp 功能。

**关键成员变量：**
- `SkAutoTCallVProc<WebPDemuxer, WebPDemuxDelete> fDemux`: libwebp 容器解析器
- `sk_sp<SkData> fData`: 图像原始数据（fDemux 持有指针）
- `FrameHolder fFrameHolder`: 动画帧信息容器
- `bool fFailed`: 标记帧解析是否失败
- `bool fOnlyHeaderParsed`: 标记是否仅解析了头部

**核心方法：**
- `IsWebp()`: 静态函数，检查数据是否为 WebP 格式
- `MakeFromStream()`: 工厂函数，创建解码器实例
- `onGetPixels()`: 解码单帧到目标缓冲区
- `ensureAllData()`: 确保完整数据已加载（延迟加载）

### Frame

继承自 `SkFrame`，表示动画的单帧。

**成员：**
- `SkEncodedInfo::Alpha fReportedAlpha`: 该帧的 alpha 类型

### FrameHolder

继承自 `SkFrameHolder`，管理所有动画帧。

**成员：**
- `std::vector<Frame> fFrames`: 帧列表

**方法：**
- `setScreenSize()`: 设置画布尺寸
- `appendNewFrame()`: 追加新帧
- `frame(int i)`: 获取指定索引的帧

### RPBlender

内部类，使用 `SkRasterPipeline` 实现帧混合。

**用途：** 当动画帧需要与前一帧混合时（`WEBP_MUX_BLEND` 模式），执行 src-over 合成。

## 公共 API 函数

### IsWebp

```cpp
static bool IsWebp(const void* buf, size_t bytesRead)
```

检查数据是否为有效的 WebP 格式。检查 RIFF 头部（"RIFF" + 4字节大小 + "WEBPVP"）。

**返回值：** 如果是 WebP 格式返回 true

### MakeFromStream

```cpp
static std::unique_ptr<SkCodec> MakeFromStream(
    std::unique_ptr<SkStream> stream,
    Result* result)
```

从输入流创建 WebP 解码器。

**流程：**
1. **数据加载**：优先使用内存基址，否则调用 `get_header_from_stream()` 智能读取
2. **容器解析**：使用 `WebPDemuxPartial()` 解析 RIFF 容器
3. **尺寸验证**：检查宽高是否溢出（防止整数溢出攻击）
4. **元数据提取**：
   - ICCP 块 → 颜色配置文件
   - EXIF 块 → 图像方向
5. **格式检测**：解析第一帧的特征（`WebPBitstreamFeatures`）
6. **颜色类型确定**：
   - `features.format = 0`（混合）或 `2`（无损）→ BGRA/BGRX
   - `features.format = 1`（有损）→ YUV/YUVA

**返回值：** 解码器实例或 nullptr（失败时）

### onGetPixels

```cpp
Result onGetPixels(const SkImageInfo& dstInfo,
                  void* dst,
                  size_t rowBytes,
                  const Options& options,
                  int* rowsDecodedPtr) override
```

解码指定帧到目标缓冲区。

**主要步骤：**
1. **配置解码器**：`WebPInitDecoderConfig()`
2. **获取帧数据**：`WebPDemuxGetFrame()`
3. **处理独立性**：检查是否需要依赖前一帧
4. **子区域处理**：
   - 调整坐标（libwebp 要求偶数对齐）
   - 设置裁剪参数（`config.options.crop_*`）
5. **缩放处理**：设置缩放目标尺寸（`config.options.scaled_*`）
6. **解码模式选择**：
   - 无颜色转换 + 无混合 → 直接解码到目标
   - 有颜色转换或混合 → 解码到临时缓冲区
7. **执行解码**：`WebPIDecode()` + `WebPIUpdate()`
8. **后处理**：
   - 颜色空间转换（如需要）
   - 帧混合（如需要）

## 内部实现细节

### 智能数据加载

`get_header_from_stream()` 实现了优化的流式解析：

```
目标：最小化内存占用，同时提取必要信息
策略：
  1. 读取 RIFF 头部（12 字节）
  2. 逐块读取：
     - VP8/VP8L → 读取图像头（3-5 字节）后返回
     - VP8X → 检查 EXIF 标志
       - 有 EXIF → 读取整个流（EXIF 在末尾）
       - 无 EXIF 且有动画 → 读取第一个 ANMF 帧后返回
     - ANMF → 如果是第一帧则返回
  3. 确保偶数对齐（RIFF 规范）
```

### 子区域解码约束

WebP 子区域解码的特殊要求：
- **偶数对齐**：`crop_left` 和 `crop_top` 必须是偶数
- **验证函数**：`onGetValidSubset()` 自动向下对齐到偶数
- **原因**：YUV 色度子采样（4:2:0）要求

### 缩放与子区域的交互

当同时使用缩放和子区域时的坐标计算：

```cpp
// 示例：原始 800x600，子区域 (100,100,400,400)，缩放到 100x100
float scaleX = 100.0 / 400 = 0.25;
float scaleY = 100.0 / 400 = 0.25;

// 帧偏移也需要缩放
dstX = floor(frameRect.x() * scaleX);
scaledWidth = floor(frameRect.width() * scaleX);
```

### 动画帧混合

WebP 动画支持两种混合模式：
- **WEBP_MUX_DISPOSE_BACKGROUND**：清除前一帧
- **WEBP_MUX_BLEND**：与前一帧混合（src-over）

混合实现使用 `SkRasterPipeline`：
```cpp
预乘目标 → 预乘源 → src-over → 非预乘（如需要） → 存储
```

### 颜色格式转换

libwebp 支持的输出格式：
- `MODE_BGRA` / `MODE_bgrA`（非预乘/预乘）
- `MODE_RGBA` / `MODE_rgbA`
- `MODE_RGB_565`

选择策略：
- 有颜色转换 → 强制 BGRA（无损格式原生，有损等价）
- 无颜色转换 → 匹配目标格式

### 增量解码

使用 `WebPIDecoder` 支持渐进式解码：
- `VP8_STATUS_OK` → 完整解码
- `VP8_STATUS_SUSPENDED` → 部分解码（返回已解码行数）

## 依赖关系

### 直接依赖

- **SkScalingCodec**: 父类，提供缩放支持
- **libwebp**: 第三方解码库
  - `WebPDemuxer`: 容器解析
  - `WebPDecoder`: 像素解码
- **SkFrameHolder**: 动画帧管理基类
- **SkRasterPipeline**: 像素混合管线

### 间接依赖

- **skcms**: 颜色空间转换
- **SkData**: 内存数据容器
- **SkStream**: 输入流接口

## 设计模式与设计决策

### 延迟加载模式

仅在创建时解析头部，完整数据在首次解码时加载（`ensureAllData()`）。

**优势：**
- 快速获取图像元数据（尺寸、格式）
- 减少内存占用（列表视图场景）
- 支持流式传输

### 策略模式

根据图像特征和解码选项动态选择解码路径：
- 直接解码 vs 双缓冲解码
- 有损（YUV）vs 无损（BGRA）
- 独立帧 vs 依赖帧

### 设计决策

1. **强制内存连续性**：libwebp 要求连续内存，不支持分段数据
2. **偶数对齐约束**：YUV 格式的硬性要求，暴露给调用者
3. **优先 BGRA**：无损 WebP 原生格式，减少格式转换
4. **完整帧缓存**：不支持逐行解码（libwebp 限制）
5. **EXIF 特殊处理**：EXIF 在文件末尾，必须读取完整文件

## 性能考量

### 优化策略

1. **头部解析优化**：
   - 仅读取 VP8/VP8L 头部（< 1KB）
   - 避免读取完整文件（除非有 EXIF）
2. **原生缩放**：libwebp 内部优化的缩放，性能优于后处理
3. **格式选择**：BGRA 避免 RGBA 转换（有颜色转换时）
4. **零拷贝**：内存基址场景使用 `MakeWithoutCopy`

### 性能瓶颈

- **YUV 转换**：有损 WebP 需要 YUV → RGB 转换
- **帧混合**：动画需要额外的合成步骤
- **颜色空间转换**：ICC 配置文件应用
- **内存分配**：双缓冲场景需要额外的帧缓冲区

### 内存使用

- **基本**：width × height × 4 字节（BGRA）
- **双缓冲**：2 × width × height × 4 字节
- **缩放**：scaled_width × scaled_height × 4 字节

### 典型场景

| 场景 | 性能 |
|------|------|
| 有损 WebP 完整解码 | 快（硬件优化的 YUV 转换） |
| 无损 WebP 完整解码 | 很快（直接 BGRA 输出） |
| 缩放解码（1/2、1/4） | 很快（libwebp 原生支持） |
| 子区域解码 | 快（硬件裁剪） |
| 动画解码（混合模式） | 中等（需要帧合成） |

## 相关文件

### 核心文件

- `include/codec/SkWebpDecoder.h`: 公共接口
- `src/codec/SkScalingCodec.h/cpp`: 父类
- `src/codec/SkFrameHolder.h/cpp`: 动画帧管理
- `src/codec/SkFrame.h/cpp`: 单帧抽象

### libwebp 库

- `webp/decode.h`: 解码 API
- `webp/demux.h`: 容器解析 API
- `webp/mux_types.h`: 类型定义

### 辅助文件

- `src/codec/SkParseEncodedOrigin.cpp`: EXIF 方向解析
- `src/core/SkRasterPipeline.h`: 混合管线
- `modules/skcms/skcms.h`: 颜色管理

### 测试文件

- `tests/CodecTest.cpp`: 通用编解码器测试
- `resources/*.webp`: WebP 测试图像
