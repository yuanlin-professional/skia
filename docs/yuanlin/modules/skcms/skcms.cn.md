# skcms - Skia 色彩管理系统

> 源文件: [`modules/skcms/skcms.h`](../../modules/skcms/skcms.h), [`modules/skcms/src/skcms_public.h`](../../modules/skcms/src/skcms_public.h), [`modules/skcms/skcms.cc`](../../modules/skcms/skcms.cc)

## 概述

skcms（Skia Color Management System）是一个独立的、高性能的色彩管理库，用于 ICC 色彩配置文件的解析和像素数据的色彩空间转换。它提供纯 C 接口，可独立于 Skia 其他部分使用。

skcms 支持以下核心功能：
- 解析 ICC v2/v4 配置文件（包括 A2B/B2A 多维查找表）
- 评估和反转多种传输函数（sRGB、PQ、HLG 及其变体）
- 在不同色彩空间和像素格式之间进行高性能转换
- 色域矩阵运算（3x3 矩阵求逆、级联、色彩适应）
- 从色域原色和白点计算 XYZD50 变换矩阵

该模块是 Skia 的色彩管理基础设施，被 SkColorSpace 等核心类广泛使用。

## 架构位置

skcms 位于 Skia 模块层的最底层，作为一个几乎无外部依赖的独立库：

- **上层使用者**: SkColorSpace、SkImage、SkSurface、各种编解码器
- **同层模块**: 独立于其他 Skia 模块
- **外部依赖**: 仅标准 C 库（stdbool.h、stddef.h、stdint.h、string.h）
- **可选 SIMD 加速**: ARM NEON、SSE、AVX2、AVX-512

头文件 `skcms.h` 仅包含一行 `#include "src/skcms_public.h"`，实际的公共 API 全部定义在 `skcms_public.h` 中。

## 主要类与结构体

### `skcms_TransferFunction`
7 参数分段传输函数，表示编码值到线性值的映射：
```c
typedef struct skcms_TransferFunction {
    float g, a, b, c, d, e, f;
} skcms_TransferFunction;
// linear = sign(encoded) * (c*|encoded| + f),                0 <= |encoded| < d
//        = sign(encoded) * ((a*|encoded| + b)^g + e),         d <= |encoded|
```

### `skcms_TFType` 枚举
传输函数类型分类：
- `skcms_TFType_sRGBish` - 标准 sRGB 类传输函数
- `skcms_TFType_PQish` / `skcms_TFType_PQ` - SMPTE ST 2084 PQ 传输函数
- `skcms_TFType_HLGish` / `skcms_TFType_HLG` - HLG（混合对数伽马）传输函数
- `skcms_TFType_HLGinvish` - HLG 反函数
- `skcms_TFType_Invalid` - 无效

### `skcms_Matrix3x3` / `skcms_Matrix3x4`
行优先的 3x3 和 3x4 矩阵，用于色域变换。

### `skcms_Curve`
联合体，表示传输曲线——可以是参数化函数（skcms_TransferFunction），也可以是 8 位或 16 位查找表。

```c
typedef union skcms_Curve {
    struct { uint32_t alias_of_table_entries; skcms_TransferFunction parametric; };
    struct { uint32_t table_entries; const uint8_t* table_8; const uint8_t* table_16; };
} skcms_Curve;
```

### `skcms_A2B` / `skcms_B2A`
设备空间（A）与配置文件连接空间（B）之间的复杂变换管道：
- A2B: 设备 -> [A 曲线 -> CLUT] -> [M 曲线 -> 矩阵] -> B 曲线 -> PCS
- B2A: 反向流程

### `skcms_ICCProfile`
ICC 配置文件的内存表示，包含传输曲线（trc）、XYZD50 变换矩阵、A2B/B2A 变换、CICP 信息等。

### `skcms_PixelFormat` 枚举
支持的像素格式，涵盖 8 位、16 位、半精度浮点、单精度浮点等多种格式的 RGB/BGR/RGBA/BGRA 排列。

### `skcms_CICP`
编码独立的代码点（Coding-Independent Code Points），用于视频相关的色彩描述。

## 公共 API 函数

### 传输函数

| 函数 | 说明 |
|------|------|
| `skcms_TransferFunction_eval(tf, x)` | 评估传输函数在 x 处的值 |
| `skcms_TransferFunction_invert(src, dst)` | 计算传输函数的反函数 |
| `skcms_TransferFunction_getType(tf)` | 获取传输函数类型 |
| `skcms_TransferFunction_isSRGBish(tf)` | 是否为 sRGB 类型 |
| `skcms_TransferFunction_isPQish(tf)` | 是否为 PQ 类型 |
| `skcms_TransferFunction_isHLGish(tf)` | 是否为 HLG 类型 |
| `skcms_TransferFunction_makePQish(tf, A,B,C,D,E,F)` | 构造 PQish 传输函数 |
| `skcms_TransferFunction_makeScaledHLGish(tf, K,R,G,a,b,c)` | 构造带缩放的 HLGish 传输函数 |
| `skcms_TransferFunction_makePQ(tf, hdr_ref_white)` | 构造标准 PQ 传输函数 |
| `skcms_TransferFunction_makeHLG(tf, hdr_ref_white, peak, gamma)` | 构造标准 HLG 传输函数 |

### ICC 配置文件

| 函数 | 说明 |
|------|------|
| `skcms_Parse(buf, len, profile)` | 解析 ICC 配置文件 |
| `skcms_ParseWithA2BPriority(buf, len, priority, n, profile)` | 带 A2B 优先级的解析 |
| `skcms_sRGB_profile()` | 获取标准 sRGB 配置文件 |
| `skcms_XYZD50_profile()` | 获取 XYZD50 配置文件 |
| `skcms_ApproximatelyEqualProfiles(A, B)` | 近似相等测试 |
| `skcms_GetCHAD(profile, m)` | 获取色彩适应矩阵 |
| `skcms_GetWTPT(profile, xyz)` | 获取白点 |
| `skcms_GetInputChannelCount(profile)` | 获取输入通道数 |

### 色彩空间转换

| 函数 | 说明 |
|------|------|
| `skcms_Transform(src, srcFmt, srcAlpha, srcProfile, dst, dstFmt, dstAlpha, dstProfile, n)` | 像素数据色彩空间转换 |
| `skcms_MakeUsableAsDestination(profile)` | 使配置文件可用作目标 |
| `skcms_MakeUsableAsDestinationWithSingleCurve(profile)` | 单曲线目标 |

### 矩阵运算

| 函数 | 说明 |
|------|------|
| `skcms_Matrix3x3_invert(src, dst)` | 3x3 矩阵求逆 |
| `skcms_Matrix3x3_concat(A, B)` | 3x3 矩阵级联 |
| `skcms_AdaptToXYZD50(wx, wy, toXYZD50)` | Bradford 色彩适应 |
| `skcms_PrimariesToXYZD50(rx,ry,gx,gy,bx,by,wx,wy,toXYZD50)` | 从色域原色计算 XYZD50 矩阵 |

### 曲线近似

| 函数 | 说明 |
|------|------|
| `skcms_ApproximateCurve(curve, approx, max_error)` | 用参数函数近似查找表曲线 |
| `skcms_AreApproximateInverses(curve, inv_tf)` | 测试曲线是否近似为给定函数的反函数 |

## 内部实现细节

### 传输函数编码技巧
HDR 传输函数（PQ、HLG）通过在 `g` 字段存储负数标记来复用 skcms_TransferFunction 结构体。`classify()` 函数根据 `g` 的值判断类型：
- `g >= 0`: sRGBish（标准类型）
- `g = -3`: PQish
- `g = -4`: HLGish
- `g = -5`: PQ
- `g = -6`: HLG

### 自定义数学函数
为了跨平台一致性和性能，skcms 实现了自己的数学函数：
- `log2f_()`: 使用 IEEE 754 浮点位操作的快速 log2 近似
- `exp2f_()`: 对应的快速 exp2 近似
- `powf_()`: 通过 `exp2(log2(x) * y)` 实现

### ICC 解析
`skcms_ParseWithA2BPriority()` 解析流程：
1. 验证文件头（签名 'acsp'、大小、版本、D50 光源）
2. 验证所有标签条目的偏移和大小
3. 解析 TRC（传输响应曲线）标签——支持 curv 和 para 两种格式
4. 解析 XYZ 标签构建 toXYZD50 矩阵
5. 按优先级解析 A2B0/A2B1 标签（支持 mft1、mft2、mAB 三种格式）
6. 解析 B2A 标签
7. 解析 CICP 标签

### 配置文件近似相等
`skcms_ApproximatelyEqualProfiles()` 使用 252 个随机字节作为测试数据，分别通过两个配置文件转换到 XYZD50 空间，然后比较结果（允许每字节 1 位误差）。

### 色彩适应
使用 Bradford 方法进行色彩适应（白点转换），通过 LMS 锥形响应空间进行缩放。

## 依赖关系

- 标准 C 库: `<stdbool.h>`, `<stddef.h>`, `<stdint.h>`, `<string.h>`, `<stdlib.h>`, `<float.h>`, `<limits.h>`, `<math.h>`
- `src/skcms_internals.h` - 内部工具宏和函数
- `src/skcms_Transform.h` / `.cc` - 实际的像素转换实现（SIMD 优化）
- 可选 SIMD 头: `<arm_neon.h>`, `<immintrin.h>`

## 设计模式与设计决策

### 纯 C 接口
skcms 使用纯 C API 以实现最大的可移植性和兼容性。内部实现使用 C++ 模板来避免 A2B/B2A 解析中的代码重复。

### 零分配设计
ICC 配置文件的 buffer 指针直接引用调用者提供的内存，skcms 不进行任何额外分配。曲线的 table_8/table_16 指针直接指向输入缓冲区中的数据。

### 负数标记编码
利用传输函数 `g` 字段不可能为负数这一特性，用负值编码 HDR 传输函数类型，优雅地复用了同一个结构体来表示多种完全不同的函数形式。

### 运行时 CPU 检测
`skcms_DisableRuntimeCPUDetection()` 允许禁用运行时 CPU 能力检测，用于测试或嵌入式环境。

### 安全解析
ICC 解析中大量使用 `SAFE_SIZEOF`、`SAFE_FIXED_SIZE` 宏和溢出检查，防止恶意配置文件导致的缓冲区溢出。

## 性能考量

1. **SIMD 加速**: 像素转换核心使用 ARM NEON、SSE、AVX2、AVX-512 等 SIMD 指令集加速
2. **自定义数学**: 用位操作实现的 log2/exp2 近似比标准库 libm 函数更快
3. **查找表插值**: 曲线评估对查找表使用线性插值，支持 8 位和 16 位精度
4. **静态 sRGB 配置文件**: `skcms_sRGB_profile()` 返回编译时常量，避免运行时构造
5. **恒等曲线规范化**: `canonicalize_identity()` 将恒等查找表转换为参数函数，跳过不必要的表查找
6. **批量像素处理**: `skcms_Transform` 一次处理多个像素，充分利用 SIMD 向量宽度
7. **内存零分配**: 解析和转换过程中不进行堆分配，避免分配器开销
8. **Bradford 色彩适应**: 使用被广泛认为最准确的 Bradford 方法进行白点转换

## 相关文件

- `modules/skcms/src/skcms_public.h` - 完整的公共 API 头文件
- `modules/skcms/src/skcms_internals.h` - 内部工具和宏定义
- `modules/skcms/src/skcms_Transform.h` / `.cc` - SIMD 优化的像素转换实现
- `include/core/SkColorSpace.h` - Skia 色彩空间类（skcms 的主要使用者）
- `src/core/SkColorSpaceXformSteps.h` - 色彩空间转换步骤
