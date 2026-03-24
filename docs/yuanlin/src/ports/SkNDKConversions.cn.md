# SkNDKConversions - Android NDK 类型转换

> 源文件:
> - `src/ports/SkNDKConversions.h`
> - `src/ports/SkNDKConversions.cpp`

## 概述

`SkNDKConversions` 命名空间提供了 Skia 图像类型与 Android NDK 类型之间的双向转换功能。它处理颜色类型（`SkColorType` <-> `AndroidBitmapFormat`）、透明度类型（`SkAlphaType` -> Android alpha flags）以及颜色空间（`SkColorSpace` <-> `ADataSpace`）之间的映射。

这是 Skia 在 Android 平台上与原生位图和数据空间 API 互操作的关键桥接层。

## 架构位置

```
Android NDK APIs (bitmap.h, data_space.h)
  |
  v
src/ports/SkNDKConversions.h/.cpp    // 转换层（本文件）
  |
  v
Skia 核心类型 (SkColorType, SkAlphaType, SkColorSpace)
```

## 主要类与结构体

### 命名空间 `SkNDKConversions`

纯函数命名空间，不包含类。提供双向映射函数。

### 内部映射表

**颜色类型映射表 `gColorTypeTable`：**

| SkColorType | AndroidBitmapFormat |
|-------------|---------------------|
| `kRGBA_8888_SkColorType` | `ANDROID_BITMAP_FORMAT_RGBA_8888` |
| `kRGBA_F16_SkColorType` | `ANDROID_BITMAP_FORMAT_RGBA_F16` |
| `kRGB_565_SkColorType` | `ANDROID_BITMAP_FORMAT_RGB_565` |
| `kGray_8_SkColorType` | `ANDROID_BITMAP_FORMAT_A_8` |

注意：Android 的 A8 格式被复用来获取 8 位灰度像素。

**颜色空间映射表 `gColorSpaceTable`：**

| ADataSpace | 传递函数 | 色域 |
|------------|---------|------|
| `ADATASPACE_SRGB` | sRGB | sRGB |
| `ADATASPACE_SCRGB` | sRGB | sRGB |
| `ADATASPACE_SCRGB_LINEAR` | Linear | sRGB |
| `ADATASPACE_SRGB_LINEAR` | Linear | sRGB |
| `ADATASPACE_ADOBE_RGB` | 2.2 | AdobeRGB |
| `ADATASPACE_DISPLAY_P3` | sRGB | Display P3 |
| `ADATASPACE_BT2020` | Rec2020 | Rec2020 |
| `ADATASPACE_BT709` | Rec2020 | sRGB |
| `ADATASPACE_DCI_P3` | 2.6 | DCI-P3 |

## 公共 API 函数

### `toAndroidBitmapFormat(SkColorType)`

将 Skia 颜色类型转换为 Android 位图格式。不支持的类型返回 `ANDROID_BITMAP_FORMAT_NONE`。

### `toAndroidBitmapAlphaFlags(SkAlphaType)`

将 Skia 透明度类型转换为 Android 位图 alpha 标志：
- `kPremul` -> `ANDROID_BITMAP_FLAGS_ALPHA_PREMUL`
- `kOpaque` -> `ANDROID_BITMAP_FLAGS_ALPHA_OPAQUE`
- `kUnpremul` -> `ANDROID_BITMAP_FLAGS_ALPHA_UNPREMUL`

### `toColorType(AndroidBitmapFormat)`

将 Android 位图格式转换为 Skia 颜色类型。不支持的格式返回 `kUnknown_SkColorType`。

### `toDataSpace(SkColorSpace*)`

将 Skia 颜色空间转换为 Android 数据空间。`nullptr` 被视为 sRGB。使用近似比较匹配传递函数和色域矩阵。无法匹配时返回 `ADATASPACE_UNKNOWN`。

### `toColorSpace(ADataSpace)`

将 Android 数据空间转换为 Skia 颜色空间。使用表中的传递函数和色域创建 `SkColorSpace`。未知数据空间返回 `nullptr`。

## 内部实现细节

### 近似比较函数

`nearly_equal()` 系列函数用于比较传递函数参数和色域矩阵：
- 浮点数比较使用 0.002 的容差
- 传递函数比较所有 7 个参数（g, a, b, c, d, e, f）
- 矩阵比较所有 9 个元素

### DCI-P3 特殊处理

DCI-P3 使用自定义的 2.6 gamma 传递函数和自定义色域矩阵 `kDCIP3`（非标准 D65 白点），不使用 `SkNamedTransferFn` / `SkNamedGamut` 中的预定义值。

## 依赖关系

- `include/core/SkColorSpace.h` - 颜色空间
- `include/core/SkImageInfo.h` - 颜色类型、透明度类型
- `<android/bitmap.h>` - Android NDK 位图 API
- `<android/data_space.h>` - Android NDK 数据空间 API

## 设计模式与设计决策

1. **查表模式**：使用静态映射表进行类型转换，查找时线性遍历
2. **近似匹配**：颜色空间匹配使用近似比较而非精确比较，容忍浮点精度差异
3. **安全默认值**：未知/不支持的类型返回安全的默认值（NONE、Unknown、UNKNOWN）
4. **只支持常用子集**：颜色类型仅支持 4 种最常用格式，不尝试覆盖所有可能的类型

## 性能考量

1. 映射表很小（4-9 个条目），线性搜索开销可忽略
2. `toDataSpace()` 需要提取传递函数和色域矩阵，这些操作本身有一定开销
3. 这些函数通常在图像加载/创建时调用一次，不在热路径上

### 颜色空间转换流程

**SkColorSpace -> ADataSpace：**
```
SkColorSpace
  |
  +-- isNumericalTransferFn() -> skcms_TransferFunction
  +-- toXYZD50() -> skcms_Matrix3x3
  |
  v
遍历 gColorSpaceTable[9]
  |
  +-- nearly_equal(gamut) && nearly_equal(fn)
  |     -> 返回匹配的 ADataSpace
  |
  +-- 无匹配
        -> ADATASPACE_UNKNOWN
```

**ADataSpace -> SkColorSpace：**
```
ADataSpace
  |
  v
遍历 gColorSpaceTable[9]
  |
  +-- entry.dataSpace == dataSpace
  |     -> SkColorSpace::MakeRGB(transferFunction, gamut)
  |
  +-- 无匹配
        -> nullptr
```

### 颜色类型支持说明

当前仅支持 4 种颜色类型的映射。以下常见 Skia 颜色类型 **不被** 支持：

- `kBGRA_8888_SkColorType` - 无对应 Android 格式
- `kRGBA_1010102_SkColorType` - 无对应 Android 格式
- `kAlpha_8_SkColorType` - Android A8 被用于灰度
- `kRGB_888x_SkColorType` - 无直接对应

### 特殊颜色空间说明

`ADATASPACE_DCI_P3` 使用非标准参数：
- 传递函数：纯幂函数 gamma=2.6（非 sRGB 曲线）
- 色域矩阵：DCI-P3 原色（非 Display P3 的 D65 白点）

这与 `ADATASPACE_DISPLAY_P3` 不同，后者使用 sRGB 传递函数和 Display P3 色域。

## 相关文件

- `include/core/SkColorSpace.h` - Skia 颜色空间
- `include/core/SkImageInfo.h` - Skia 图像信息
- `include/android/SkImageAndroid.h` - Android 平台图像 API（可能的调用者）
- `include/third_party/skcms/skcms.h` - skcms 颜色管理
