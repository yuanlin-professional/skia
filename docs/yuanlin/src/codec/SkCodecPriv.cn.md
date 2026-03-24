# SkCodecPriv - 编解码器私有工具集

> 源文件: `src/codec/SkCodecPriv.h`

## 概述

`SkCodecPriv.h` 是 Skia 图像编解码器子系统的核心私有工具头文件，包含 `SkCodecs::ColorProfile` 颜色配置文件管理类、`SkCodecPriv` 静态工具类以及调试输出宏。`ColorProfile` 封装了 ICC 颜色配置文件的解析和管理，支持 skcms、Rust 和 CICP 多种解析后端。`SkCodecPriv` 提供了采样、缩放、像素格式转换、字节序处理等图像解码过程中常用的实用函数。

## 架构位置

该文件位于 `src/codec/` 目录下，被几乎所有具体的图像格式解码器（JPEG、PNG、WebP、GIF 等）所依赖。`ColorProfile` 类是编码图像颜色管理的核心，连接了 ICC 配置文件数据和 Skia 的 `SkColorSpace` 系统。`SkCodecPriv` 则提供了解码过程中的通用算法。

## 主要类与结构体

### `SkCodecs::ColorProfile`
颜色配置文件管理类，封装了 `skcms_ICCProfile` 和原始数据。

**工厂方法**:
- `MakeICCProfile(sk_sp<const SkData>)`: 从 ICC 数据创建（根据编译配置选择 skcms 或 Rust 解析器）
- `MakeICCProfileWithSkCMS(sk_sp<const SkData>)`: 强制使用 skcms 解析（仅测试用）
- `Make(sk_sp<SkColorSpace>)`: 从 `SkColorSpace` 创建
- `Make(skcms_TransferFunction, skcms_Matrix3x3)`: 从传输函数和矩阵创建
- `MakeCICP(uint8_t, uint8_t, uint8_t, uint8_t)`: 从 CICP 值创建

**查询方法**:
- `dataSpace()`: 返回颜色数据空间（RGB、CMYK、Gray、Other）
- `getExactColorSpace()`: 获取精确的 `SkColorSpace`（可能返回 nullptr）
- `getAndroidOutputColorSpace()`: 获取 Android 平台兼容的色彩空间（优先 CICP，不会返回 nullptr）
- `profile()`: 返回底层 `skcms_ICCProfile` 指针
- `data()`: 返回原始 ICC 数据

**`DataSpace` 枚举**: `kRGB`, `kCMYK`, `kGray`, `kOther`

### `SkCodecPriv`
静态工具类，提供解码辅助函数。

## 公共 API 函数

### ColorProfile 方法
见上述工厂方法和查询方法。

### SkCodecPriv 静态方法

#### 编码信息访问
- `GetEncodedInfo(const SkCodec*)`: 获取编码器的 `SkEncodedInfo`
- `GetEncodedData(const SkCodec*)`: 获取编码器的原始数据

#### 采样与缩放
- `GetScaleFromSampleSize(int)`: 采样大小转缩放因子（1/sampleSize）
- `GetSampledDimension(int srcDim, int sampleSize)`: 计算采样后的维度
- `GetStartCoord(int sampleFactor)`: 计算采样起始坐标
- `GetDstCoord(int srcCoord, int sampleFactor)`: 源坐标转目标坐标
- `IsCoordNecessary(int srcCoord, int sampleFactor, int scaledDim)`: 判断坐标是否参与采样

#### 验证
- `IsValidSubset(const SkIRect&, const SkISize&)`: 验证子集矩形是否在图像范围内
- `ValidAlpha(SkAlphaType, bool srcIsOpaque)`: 验证 alpha 类型兼容性
- `SelectXformFormat(SkColorType, bool, skcms_PixelFormat*)`: 选择颜色变换格式

#### 像素操作
- `ComputeRowBytes(int width, uint32_t bitsPerPixel)`: 计算行字节数
- `PremultiplyARGBasRGBA/BGRA(a, r, g, b)`: 预乘 alpha 颜色打包
- `ChoosePackColorProc(bool isPremul, SkColorType)`: 选择颜色打包函数

#### 字节序处理
- `IsValidEndianMarker(const uint8_t*, bool*)`: 验证 II/MM 字节序标记
- `GetEndianShort/Int(const uint8_t*, bool littleEndian)`: 按指定字节序读取 16/32 位值
- `UnsafeGetByte/Short/Int(const uint8_t*, uint32_t)`: 无边界检查的快速读取

### 调试宏
- `SkCodecPrintf(...)`: 条件编译的调试输出宏，仅在定义 `SK_PRINT_CODEC_MESSAGES` 时有效

## 内部实现细节

1. **颜色配置文件解析后端**: 通过 `SK_CODEC_COLOR_PROFILE_PARSE_WITH_RUST` 宏支持 Rust ICC 解析器，可通过 `gForceSkcmsForICCProfiles` 全局标志强制使用 skcms。

2. **Android CICP 优先**: `getAndroidOutputColorSpace` 优先使用 CICP 信息（如果存在），并对 PQ（transfer_characteristics=16）和 HLG（transfer_characteristics=18）传输函数进行特殊处理，使 203 nits 映射到 SDR 白。

3. **保留外部数据**: `fRetainedData` 成员（`shared_ptr<void>`）保持由 Rust 解析器分配的外部数据存活，因为 `skcms_ICCProfile` 的裸指针可能引用这些数据。

4. **采样算法**: 采样使用 "均匀跳跃" 策略，起始坐标为 `sampleFactor / 2`，之后每 `sampleFactor` 个像素取一个。

5. **行字节计算**: `ComputeRowBytes` 支持小于 1 字节/像素的格式（如 1bpp、2bpp、4bpp），通过 pixelsPerByte 计算。

## 依赖关系

- `include/codec/SkCodec.h`: 编解码器基类
- `include/private/SkEncodedInfo.h`: 编码信息
- `modules/skcms/skcms.h`: ICC 配置文件解析
- `src/codec/SkColorPalette.h`: 调色板
- `src/core/SkColorData.h`: 颜色数据工具

## 设计模式与设计决策

1. **策略模式**: `ChoosePackColorProc` 根据参数返回不同的颜色打包函数指针。
2. **编译时后端选择**: ICC 解析器通过编译宏在 skcms 和 Rust 之间选择。
3. **内联优化**: 大部分 `SkCodecPriv` 方法为内联 static 函数。
4. **HasDecoder 注册**: `SkCodecs::HasDecoder` 用于检查是否注册了指定 ID 的解码器。

## 性能考量

- **内联函数**: 所有 `SkCodecPriv` 方法均为 static inline
- **无安全检查的快速读取**: `UnsafeGet*` 系列函数在调用者保证边界安全时避免冗余检查
- **平台字节序优化**: 在小端平台上避免不必要的字节交换

## 相关文件

- `src/codec/SkCodecColorProfile.cpp`: `ColorProfile` 的方法实现
- `include/codec/SkCodec.h`: 编解码器基类
- `include/private/SkEncodedInfo.h`: 编码信息
- `modules/skcms/skcms.h`: skcms 颜色管理
