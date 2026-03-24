# SkCrabbyAvifCodec

> 源文件: src/codec/SkCrabbyAvifCodec.h, src/codec/SkCrabbyAvifCodec.cpp

## 概述

`SkCrabbyAvifCodec` 是 Skia 图像解码框架中专门处理 AVIF 和 HEIF 格式的解码器，基于 CrabbyAvif 库（一个用 Rust 编写的 libavif 兼容实现）。AVIF（AV1 Image File Format）是基于 AV1 视频编码的现代图像格式，提供卓越的压缩效率和 HDR 支持，广泛应用于 Web 和 Android 平台。

该解码器的核心特性包括：支持单帧和动画 AVIF、Gainmap（用于 HDR 渲染）、Clean Aperture 裁剪、图像变换（旋转和镜像）、子区域解码、缩放解码，以及与 Android MediaCodec 的集成以实现硬件加速。特别针对 Android 平台进行了优化，包括线程安全的 MediaCodec 访问和 YUV 格式的高效处理。

## 架构位置

```
SkCodec (抽象基类)
  └── SkScalingCodec (支持缩放的解码器基类)
        └── SkCrabbyAvifCodec (AVIF/HEIF 解码器)
              ├── CrabbyAvif (Rust libavif 实现)
              │     └── Android MediaCodec (硬件加速)
              └── FrameHolder (动画帧管理)
```

**关键特性：**
- 使用 Android MediaCodec 进行 YUV 解码（硬件加速）
- 支持 AVIF 和 HEIF 两种容器格式
- 支持 Gainmap 用于 HDR 渲染
- 支持 Clean Aperture 和 Sample Transform

## 主要类与结构体

### SkCrabbyAvifCodec

AVIF/HEIF 解码器主类。

**关键成员变量：**
- `sk_sp<const SkData> fData`: 图像数据（必须连续）
- `AvifDecoder fAvifDecoder`: CrabbyAvif 解码器实例
- `bool fUseAnimation`: 是否使用动画
- `bool fGainmapOnly`: 是否仅解码 Gainmap
- `SkEncodedImageFormat fFormat`: AVIF 或 HEIF
- `FrameHolder fFrameHolder`: 动画帧容器

**核心方法：**
- `IsAvif()`: 检测 AVIF 格式
- `MakeFromStream()`: 从流创建解码器
- `onGetPixels()`: 解码像素数据
- `onGetGainmapCodec()`: 获取 Gainmap 解码器

### Frame & FrameHolder

管理动画帧，类似于 WebP 和其他动画格式的实现。

### AvifDecoderDeleter

自定义删除器，确保 CrabbyAvif 解码器正确释放。

## 公共 API 函数

### IsAvif

```cpp
static bool IsAvif(const void* buffer, size_t bytesRead)
```

检测数据是否为有效的 AVIF 文件。使用 `avifPeekCompatibleFileType()` 检查文件签名。

### MakeFromStream

```cpp
static std::unique_ptr<SkCodec> MakeFromStream(
    std::unique_ptr<SkStream> stream,
    Result* result,
    bool gainmapOnly = false)
```

从输入流创建 AVIF 解码器。

**主要流程：**
1. **数据加载**：CrabbyAvif 需要连续内存，优先使用内存基址，否则复制流
2. **创建解码器**：`avifDecoderCreate()`
3. **配置解码器**：
   - 忽略 XMP 和 EXIF（避免等待尾部数据）
   - 禁用严格模式（允许某些不完全符合规范的文件）
   - 禁用 Sample Transform（Android 不支持）
4. **解析文件**：`avifDecoderParse()`
5. **提取元数据**：
   - ICC 配置文件或 CICP 颜色信息
   - Clean Aperture 裁剪信息
   - 图像变换（旋转/镜像）
6. **确定格式**：AVIF 或 HEIF（根据压缩格式）

**参数：**
- `gainmapOnly`: 如果为 true，仅解码 Gainmap 图像

### onGetPixels

```cpp
Result onGetPixels(const SkImageInfo& dstInfo,
                  void* dst,
                  size_t dstRowBytes,
                  const Options& options,
                  int* rowsDecoded) override
```

解码指定帧到目标缓冲区。

**操作顺序：**
1. **配置 MediaCodec 输出格式**：
   - RGBA_8888/BGRA_8888/RGB_565 → YUV420_FLEXIBLE
   - RGBA_F16/RGBA_1010102 → P010
2. **解码帧**：`avifDecoderNthImage()`
3. **Clean Aperture 裁剪**：如果存在 `clap` 属性
4. **子区域提取**：如果指定 `options.fSubset`
5. **缩放**：如果目标尺寸不匹配（需要复制以避免修改只读 MediaCodec 缓冲区）
6. **YUV → RGB 转换**：`avifImageYUVToRGB()`

**线程安全：**
使用静态互斥锁保护，避免同时创建多个 MediaCodec 实例（防止 binder 资源耗尽）。

### onGetGainmapCodec

```cpp
bool onGetGainmapCodec(SkGainmapInfo* info,
                       std::unique_ptr<SkCodec>* gainmapCodec) override
```

提取 Gainmap 信息并创建 Gainmap 解码器。

**流程：**
1. 解析 `avifGainMap` 结构到 `SkGainmapInfo`
2. 创建新的 `SkCrabbyAvifCodec` 实例（`gainmapOnly=true`）
3. 复用 `fData`（避免重新加载）

## 内部实现细节

### Gainmap 支持

Gainmap 是 AVIF 的扩展，用于在 SDR 和 HDR 显示器上提供优化的渲染。

**关键信息：**
- `baseHdrHeadroom` 和 `alternateHdrHeadroom`：确定基础图像和替代图像的 HDR 范围
- `gainMapMin/Max/Gamma`：每通道的增益映射参数
- `baseOffset` 和 `alternateOffset`：偏移量（epsilon）
- `altICC`：替代图像的 ICC 配置文件（可选）

**计算逻辑：**
```cpp
base_headroom = exp2(baseHdrHeadroom.n / baseHdrHeadroom.d);
alternate_headroom = exp2(alternateHdrHeadroom.n / alternateHdrHeadroom.d);
base_is_hdr = base_headroom > alternate_headroom;

for (i = 0; i < 3; i++) {
    ratioMin[i] = exp2(gainMapMin[i].n / gainMapMin[i].d);
    ratioMax[i] = exp2(gainMapMax[i].n / gainMapMax[i].d);
    gamma[i] = gainMapGamma[i].d / gainMapGamma[i].n;  // 倒数
}
```

### Clean Aperture (CLAP)

Clean Aperture 定义图像的可见区域，用于裁剪编码伪影或填充。

**处理流程：**
1. 检测 `AVIF_TRANSFORM_CLAP` 标志
2. 调用 `crabby_avifCropRectConvertCleanApertureBox()` 计算裁剪矩形
3. 使用 `crabby_avifImageSetViewRect()` 创建裁剪视图（零拷贝）

### 图像变换

支持旋转（irot）和镜像（imir）变换。

**映射表：**
```cpp
// [axis+1][angle] → SkEncodedOrigin
// axis: -1=无镜像, 0=上下镜像, 1=左右镜像
// angle: 0=0°, 1=90°, 2=180°, 3=270° (逆时针)
```

**示例：**
- `angle=1, axis=-1` → `kLeftBottom_SkEncodedOrigin`（90° 逆时针）
- `angle=0, axis=1` → `kTopRight_SkEncodedOrigin`（左右镜像）

### MediaCodec 集成

**YUV 格式选择：**
- **YUV420_FLEXIBLE**：用于 8 位输出（RGBA_8888, BGRA_8888, RGB_565）
- **P010**：用于 10+ 位输出（RGBA_F16, RGBA_1010102）

**只读缓冲区问题：**
MediaCodec 提供的 YUV 缓冲区是只读的，无法原地缩放。解决方案：
1. 检测是否需要缩放
2. 如需要，调用 `avifImageCopy()` 复制图像
3. 在副本上执行 `avifImageScale()`

### 操作顺序

**强制顺序：Crop → Subset → Scale**

理由：
1. **Crop 优先**：防止暴露不应显示的像素
2. **Subset 次之**：在裁剪后的图像上提取子区域
3. **Scale 最后**：确保输出尺寸精确匹配请求

## 依赖关系

### 直接依赖

- **SkScalingCodec**: 父类
- **CrabbyAvif (libavif_compat)**：Rust AVIF 库
- **skcms**: 颜色空间转换
- **SkFrameHolder**: 动画帧管理
- **SkGainmapInfo**: Gainmap 元数据

### 平台依赖

- **Android MediaCodec**：通过 CrabbyAvif 间接使用
- **SkMutex**: 线程同步

## 设计模式与设计决策

### 工厂模式

`MakeFromStream()` 和 `MakeFromData()` 作为工厂函数创建解码器实例。

### RAII

使用自定义删除器 `AvifDecoderDeleter` 确保资源正确释放。

### 延迟视图模式

Clean Aperture 和 Subset 使用视图而非复制，直到需要缩放时才复制。

### 设计决策

1. **强制连续内存**：libavif 要求，牺牲灵活性换取性能
2. **禁用 Sample Transform**：Android 管线不支持，避免兼容性问题
3. **静态互斥锁**：防止 MediaCodec binder 资源耗尽（Android 特有问题）
4. **忽略 EXIF/XMP**：避免等待流尾部数据，加快解码启动
5. **Gainmap 复用 fData**：避免重新加载相同数据
6. **宽松解析模式**：允许某些非严格符合规范的文件（提高兼容性）

## 性能考量

### 优化策略

1. **硬件加速**：MediaCodec 提供硬件 YUV 解码
2. **零拷贝视图**：Crop 和 Subset 使用视图，避免复制
3. **按需复制**：仅在缩放时复制图像
4. **颜色格式选择**：BGRA vs RGBA 无成本切换（YUV 转换阶段）

### 性能瓶颈

- **YUV → RGB 转换**：即使有硬件加速，仍需转换
- **缩放操作**：需要完整图像复制 + 缩放算法
- **Gainmap 解析**：额外的数学计算（exp2, 分数转换）
- **互斥锁**：串行化解码（但避免了 binder 崩溃）

### 内存使用

- **基本**：width × height × 4 字节（RGBA_8888）
- **F16**：width × height × 8 字节
- **缩放副本**：额外的 YUV 平面（width × height × 1.5）
- **Gainmap**：通常是基础图像的 25-50%

## 相关文件

### 核心文件

- `avif/avif.h`: CrabbyAvif C API
- `avif/libavif_compat.h`: 兼容性定义
- `src/codec/SkScalingCodec.h/cpp`: 父类
- `include/private/SkGainmapInfo.h`: Gainmap 元数据

### Android 特定

- `src/codec/SkAndroidCodec.cpp`: Android 集成
- Android MediaCodec: 系统硬件解码器

### 测试文件

- `tests/CodecTest.cpp`: 通用编解码器测试
- `tests/AvifTest.cpp`: AVIF 特定测试
