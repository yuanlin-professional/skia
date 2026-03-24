# SkCodecColorProfile - 颜色配置文件实现

> 源文件: `src/codec/SkCodecColorProfile.cpp`

## 概述

`SkCodecColorProfile.cpp` 实现了 `SkCodecs::ColorProfile` 类的方法和 `ICCProfileChromium` 接口。`ColorProfile` 是 Skia 图像解码管线中颜色管理的核心组件，负责解析 ICC 配置文件数据并将其转换为可用于颜色变换的形式。该文件支持三种颜色配置文件来源：ICC 数据（通过 skcms 或 Rust 解析）、`SkColorSpace` 对象和 CICP 编码参数。特别地，它实现了 Android 平台专用的颜色空间输出逻辑，包括对 PQ 和 HLG HDR 传输函数的特殊处理。

## 架构位置

该文件位于 `src/codec/` 目录下，是 `SkCodecPriv.h` 中声明的 `ColorProfile` 类的实现。它连接了外部颜色配置数据（ICC/CICP）与 Skia 的颜色变换管线，被各种图像格式解码器（JPEG、PNG、WebP、AVIF 等）使用。

## 主要类与结构体

### `SkCodecs::ColorProfile`
（类定义在 `SkCodecPriv.h` 中，此文件为其方法实现。）

### `ICCProfileChromiumImpl`
`ICCProfileChromium` 的具体实现类，包装 `ColorProfile` 供 Chromium 使用。

## 公共 API 函数

### `ColorProfile::MakeICCProfileWithSkCMS(sk_sp<const SkData>)`
使用 skcms 库解析 ICC 数据。调用 `skcms_Parse` 解析，成功则创建 `ColorProfile`。

### `ColorProfile::MakeICCProfile(sk_sp<const SkData>)`
ICC 配置文件的主入口。根据全局标志 `gForceSkcmsForICCProfiles` 和编译宏 `SK_CODEC_COLOR_PROFILE_PARSE_WITH_RUST` 选择解析后端。

### `ColorProfile::Make(sk_sp<SkColorSpace>)`
从已有的 `SkColorSpace` 创建。通过 `cs->toProfile()` 获取 `skcms_ICCProfile`。

### `ColorProfile::Make(skcms_TransferFunction, skcms_Matrix3x3)`
从传输函数和 toXYZD50 矩阵创建。使用 `skcms_Init`、`skcms_SetTransferFunction`、`skcms_SetXYZD50`。

### `ColorProfile::MakeCICP(uint8_t, uint8_t, uint8_t, uint8_t)`
从 CICP（Coding-Independent Code Points）四元组创建。CICP 值存储在 `skcms_ICCProfile::CICP` 中。

### `ColorProfile::clone() const`
深拷贝，包括 `fRetainedData` 的共享所有权。

### `ColorProfile::dataSpace() const`
返回 `DataSpace` 枚举：将 `skcms_Signature_RGB/CMYK/Gray` 映射到对应枚举值。

### `ColorProfile::getExactColorSpace() const`
尝试创建精确匹配的 `SkColorSpace`。如果 ICC 配置文件过于复杂无法表示，返回 nullptr。

### `ColorProfile::getAndroidOutputColorSpace() const`
Android 专用的输出色彩空间逻辑（始终返回非空值）：
1. 优先使用 CICP 信息
2. 回退到 ICC 配置文件创建 `SkColorSpace`
3. 如果有 toXYZD50 矩阵，使用 sRGB 传输函数
4. 最终回退到 sRGB

### `ICCProfileChromium::Make(sk_sp<SkData>)`
Chromium 专用接口，创建 `ICCProfileChromiumImpl` 包装。

### `ICCProfileChromium::ForceSkcms(bool)`
全局控制是否强制使用 skcms 解析 ICC 配置文件。

## 内部实现细节

### CICP Android 色彩空间转换
`cicp_get_android_sk_color_space()` 处理 CICP 到 `SkColorSpace` 的转换：
- 要求 `matrix_coefficients == 0`（非矩阵编码）和 `full_range_flag == 1`（全范围）
- 通过 `SkNamedPrimaries::GetCicp` 获取色度坐标
- 通过 `SkNamedTransferFn::GetCicp` 获取传输函数
- **PQ 特殊处理**（transfer_characteristics=16）：使用自定义传输函数使 203 nits 映射到 SDR 白
- **HLG 特殊处理**（transfer_characteristics=18）：使用 `skcms_TransferFunction_makeScaledHLGish` 使 203 nits 映射到 SDR 白

### 解析后端选择
```
MakeICCProfile -> gForceSkcmsForICCProfiles ?
  -> yes: MakeICCProfileWithSkCMS (skcms)
  -> no:  SK_CODEC_COLOR_PROFILE_PARSE_WITH_RUST ?
            -> yes: MakeICCProfileWithRust
            -> no:  MakeICCProfileWithSkCMS (skcms)
```

### 数据保持机制
`ColorProfile` 的私有构造函数接受 `skcms_ICCProfile` 和可选的 `sk_sp<const SkData>`。ICC 数据必须保持存活，因为 `skcms_ICCProfile` 的内部指针可能引用原始数据。`fRetainedData`（`shared_ptr<void>`）用于 Rust 解析器分配的外部数据。

## 依赖关系

- `include/private/chromium/SkCodecsICCProfileChromium.h`: Chromium 接口
- `modules/skcms/skcms.h`: ICC 配置文件解析库
- `src/codec/SkCodecPriv.h`: `ColorProfile` 类定义
- `src/core/SkColorSpacePriv.h`: 命名传输函数和色度坐标

## 设计模式与设计决策

1. **后端可替换**: 通过编译宏和运行时标志支持 skcms 和 Rust 两种 ICC 解析后端。
2. **永不返回空**: `getAndroidOutputColorSpace` 使用多级回退确保总是返回有效的色彩空间。
3. **Chromium 接口隔离**: `ICCProfileChromium` 和 `ICCProfileChromiumImpl` 为 Chromium 提供了独立的访问接口。
4. **203 nits SDR 白**: PQ/HLG 的特殊处理遵循 Android 的 HDR 显示规范。

## 性能考量

- **惰性解析**: `ColorProfile` 仅在创建时解析一次，之后通过指针访问
- **共享数据**: 通过 `sk_sp` 和 `shared_ptr` 避免不必要的数据拷贝
- **全局标志**: `gForceSkcmsForICCProfiles` 避免了每次调用时的运行时检查开销

## 相关文件

- `src/codec/SkCodecPriv.h`: `ColorProfile` 类定义
- `src/codec/SkCodecColorProfileRust.h`: Rust ICC 解析器接口
- `modules/skcms/skcms.h`: skcms ICC 解析库
- `src/core/SkColorSpacePriv.h`: 色彩空间私有工具
- `include/private/chromium/SkCodecsICCProfileChromium.h`: Chromium 接口
