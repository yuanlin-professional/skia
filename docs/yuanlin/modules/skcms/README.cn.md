# skcms - 色彩管理系统

## 概述

`modules/skcms` 是 Skia 的色彩管理系统 (Skia Color Management System),提供 ICC 颜色配置文件解析、颜色空间转换和传递函数运算等核心色彩管理功能。该模块以 C 语言 API 编写,具有独立性强、性能优异的特点,可以被 Skia 内部和外部项目(如 Chromium)独立使用。

skcms 的核心功能是 `skcms_Transform()` 函数,它能够在任意两个颜色配置文件之间进行像素格式和颜色空间的转换。支持的像素格式极为丰富,从 8 位 RGBA 到 32 位浮点,涵盖 RGB_565、RGBA_8888、RGBA_16161616、半精度浮点、单精度浮点等数十种格式,并支持多种 Alpha 预乘模式。

传递函数 (Transfer Function) 子系统支持标准的 sRGB 式分段函数、PQ (SMPTE ST 2084) HDR 函数和 HLG (Hybrid Log-Gamma) HDR 函数。模块提供了传递函数的求值、求逆、类型检测等操作,以及从曲线数据近似拟合参数化传递函数的能力。

ICC 配置文件解析器能够处理标准的 ICC v2/v4 配置文件,提取 TRC (Transfer Response Curves)、色度矩阵 (toXYZD50)、A2B/B2A 多级转换管线以及 CICP 标签。模块还提供了 sRGB 和 XYZD50 的标准配置文件常量。

在性能优化方面,skcms 采用了平台特定的 SIMD 加速。在 x86_64 平台上支持 Haswell (HSW/AVX2) 和 Skylake-X (SKX/AVX-512) 指令集的运行时检测和动态分派。转换核心通过内联模板 (`Transform_inl.h`) 实现,由不同的编译单元以不同的指令集编译。

## 架构图

```
+----------------------------------+
|          skcms 公共 API           |
| skcms_Transform()                |
| skcms_Parse()                    |
| skcms_TransferFunction_*()       |
+----------------------------------+
        |              |
        v              v
+---------------+  +-------------------+
| ICC Profile   |  | Transfer Function |
| Parser        |  | Engine            |
| (skcms.cc)    |  | - sRGBish         |
| - TRC 提取    |  | - PQish (HDR)     |
| - Matrix 提取 |  | - HLGish (HDR)    |
| - A2B/B2A     |  | - PQ / HLG        |
| - CICP        |  +-------------------+
+---------------+
        |
        v
+----------------------------------+
|    Transform 管线                 |
|  skcms_TransformBaseline.cc      |
|  skcms_TransformHsw.cc (AVX2)   |
|  skcms_TransformSkx.cc (AVX-512)|
|  Transform_inl.h (模板核心)      |
+----------------------------------+
        |
        v
+----------------------------------+
|    像素格式转换                   |
|    Alpha 处理                    |
|    颜色空间变换 (3x3/3x4 矩阵)  |
+----------------------------------+
```

## 目录结构

```
modules/skcms/
+-- BUILD.gn                # GN 构建配置
+-- BUILD.bazel             # Bazel 构建配置
+-- skcms.gni               # GNI 源文件列表
+-- skcms.h                 # 公共 API 入口 (包含 skcms_public.h)
+-- skcms.cc                # ICC 配置文件解析核心实现
+-- OWNERS                  # 代码所有者
+-- README.chromium         # Chromium 集成说明
+-- version.sha1            # 版本哈希
+-- src/
    +-- skcms_public.h      # 完整公共 API 定义 (C 接口)
    +-- skcms_internals.h   # 内部共享 API (测试工具使用)
    +-- skcms_Transform.h   # Transform 管线内部接口
    +-- Transform_inl.h     # Transform 核心内联模板
    +-- skcms_TransformBaseline.cc  # 基线 (无 SIMD) 实现
    +-- skcms_TransformHsw.cc      # Haswell AVX2 实现
    +-- skcms_TransformSkx.cc      # Skylake-X AVX-512 实现
```

## 关键类与函数

| 函数/类型 | 文件 | 说明 |
|----------|------|------|
| `skcms_Transform()` | `src/skcms_public.h` | 核心: 在两个配置文件间转换像素数据 |
| `skcms_Parse()` | `src/skcms_public.h` | 解析 ICC 配置文件数据 |
| `skcms_ICCProfile` | `src/skcms_public.h` | ICC 配置文件结构体 (TRC/矩阵/A2B/B2A/CICP) |
| `skcms_TransferFunction` | `src/skcms_public.h` | 7参数分段传递函数 |
| `skcms_TransferFunction_eval()` | `src/skcms_public.h` | 传递函数求值 |
| `skcms_TransferFunction_invert()` | `src/skcms_public.h` | 传递函数求逆 |
| `skcms_TransferFunction_makePQ()` | `src/skcms_public.h` | 构造 PQ HDR 传递函数 |
| `skcms_TransferFunction_makeHLG()` | `src/skcms_public.h` | 构造 HLG HDR 传递函数 |
| `skcms_sRGB_profile()` | `src/skcms_public.h` | 返回标准 sRGB 配置文件 |
| `skcms_ApproximatelyEqualProfiles()` | `src/skcms_public.h` | 配置文件近似相等比较 |
| `skcms_ApproximateCurve()` | `src/skcms_public.h` | 从曲线数据拟合参数化传递函数 |
| `skcms_PrimariesToXYZD50()` | `src/skcms_public.h` | 从色域原色计算 XYZD50 矩阵 |
| `skcms_Matrix3x3` | `src/skcms_public.h` | 3x3 行优先矩阵 |
| `skcms_PixelFormat` | `src/skcms_public.h` | 像素格式枚举 (数十种格式) |
| `skcms_AlphaFormat` | `src/skcms_public.h` | Alpha 格式 (Opaque/Unpremul/PremulAsEncoded) |
| `skcms_A2B` / `skcms_B2A` | `src/skcms_public.h` | A-to-B / B-to-A 复杂转换管线 |
| `skcms_Curve` | `src/skcms_public.h` | 曲线联合体 (参数化或表格) |
| `skcms_TFType` | `src/skcms_public.h` | 传递函数类型枚举 |

## 依赖关系

- **无外部依赖**: skcms 设计为完全独立的 C 语言库
- **标准 C 库**: `stdbool.h`, `stddef.h`, `stdint.h`, `string.h`
- **被依赖**: Skia 核心的 `SkColorSpace` 系统大量使用 skcms

## 设计模式分析

1. **C 接口封装**: 整个模块使用纯 C 接口 (`extern "C"`)，确保最大的二进制兼容性和跨语言互操作性。

2. **编译时多态 (Template Specialization)**: `Transform_inl.h` 通过内联模板在不同编译单元中生成不同 SIMD 指令集的代码,实现编译时多态。

3. **运行时分派**: 在 x86_64 平台上,通过 CPU 特性检测在 Baseline/HSW/SKX 三个实现之间动态选择最优的 Transform 路径。

4. **联合体优化 (Union)**: `skcms_Curve` 使用 C 联合体 (union) 在参数化传递函数和查找表之间共享存储空间。

5. **不可变数据模式**: ICC 配置文件解析后的 `skcms_ICCProfile` 结构体直接引用原始数据缓冲区 (零拷贝),调用者必须保证缓冲区生命周期。

## 数据流

```
ICC 配置文件二进制数据
       |
       v
skcms_Parse() --> skcms_ICCProfile
       |              |
       |              +-- has_trc: 传递函数曲线 trc[3]
       |              +-- has_toXYZD50: 色度矩阵
       |              +-- has_A2B: 复杂 A2B 转换
       |              +-- has_B2A: 复杂 B2A 转换
       |              +-- has_CICP: 编解码标识
       v
skcms_Transform(src, srcFmt, srcAlpha, srcProfile,
                dst, dstFmt, dstAlpha, dstProfile, npixels)
       |
       v
内部管线 (Transform_inl.h):
  1. 解包源像素 (srcFmt -> float RGBA)
  2. 源 Alpha 去预乘
  3. 源传递函数逆运算 (线性化)
  4. 源到 PCS (3x3 矩阵 或 A2B CLUT)
  5. PCS 到目标 (3x3 矩阵 或 B2A CLUT)
  6. 目标传递函数正运算 (编码)
  7. 目标 Alpha 预乘
  8. 打包目标像素 (float RGBA -> dstFmt)
```

## 相关文档与参考

- ICC 规范: https://www.color.org/specification/ICC.1-2022-05.pdf
- sRGB 标准: IEC 61966-2-1
- PQ (ST 2084): SMPTE ST 2084
- HLG: ARIB STD-B67
- Chromium 集成: `modules/skcms/README.chromium`
- Skia SkColorSpace: `include/core/SkColorSpace.h`
